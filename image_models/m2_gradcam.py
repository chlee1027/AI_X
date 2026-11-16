"""M2 Grad-CAM on the validation split (labels used only for the summary, never for the model).

What it does, per validation image:
  1. Same preprocessing as infer_m2.py (exif, RGB, white pad to 224x224, CLIP processor).
  2. Full M2 score (CLIP image + KLUE text, 3-seed mean) -> compared to Dayoung's reference scores.
  3. Grad-CAM on the input tokens of the last CLIP block (7x7 patch grid), target = mean seed logit.
  4. How much of the CAM mass sits on white padding, against the padding's share of the area.
  5. Shape-only control: the same image with its content replaced by flat gray (only the
     padding outline = aspect ratio is left) -> image-branch logit, to see whether aspect alone
     ranks illegal images.
"""
import argparse, json
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from PIL import Image, ImageOps
from transformers import CLIPImageProcessor, CLIPVisionModelWithProjection

SIDE, GRID, P = 224, 7, 32


def pad_box(w, h):
    """Content box of ImageOps.pad(image, (224,224)) in output pixels (left, top, right, bottom)."""
    if w / h >= 1:
        nw, nh = SIDE, max(1, round(SIDE * h / w))
    else:
        nw, nh = max(1, round(SIDE * w / h)), SIDE
    left, top = (SIDE - nw) // 2, (SIDE - nh) // 2
    return left, top, left + nw, top + nh


def pad_fraction(box):
    """Per-patch fraction of area that is padding, shape (49,)."""
    l, t, r, b = box
    out = np.zeros((GRID, GRID))
    for i in range(GRID):
        for j in range(GRID):
            y0, y1, x0, x1 = i * P, (i + 1) * P, j * P, (j + 1) * P
            inter = max(0, min(x1, r) - max(x0, l)) * max(0, min(y1, b) - max(y0, t))
            out[i, j] = 1 - inter / (P * P)
    return out.ravel()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--h4', required=True)
    ap.add_argument('--m2', required=True)
    ap.add_argument('--text-emb', required=True)
    ap.add_argument('--text-ids', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--batch', type=int, default=16)
    ap.add_argument('--limit', type=int, default=0)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    torch.manual_seed(0)

    h4, m2 = Path(a.h4), Path(a.m2)
    split = pd.read_csv(h4 / 'split_v1_trainval.csv', dtype=str)
    meta = pd.read_csv(h4 / 'meta_trainval.csv', dtype=str, keep_default_na=False)
    val = split[split.split == 'val'][['image_id']].merge(meta[['image_id', 'file', 'label', 'subtype', 'unsure']], on='image_id', how='left', validate='one_to_one')
    if a.limit:
        val = val.iloc[:a.limit]
    ref = pd.read_csv(m2 / 'verification' / 'm2_raw_val_images.csv', dtype={'image_id': str}).set_index('image_id').score

    tid = pd.read_csv(a.text_ids, dtype=str).image_id.tolist()
    temb = np.load(a.text_emb).astype(np.float64)
    tpos = {v: i for i, v in enumerate(tid)}
    text = temb[[tpos[i] for i in val.image_id]]

    p = np.load(m2 / 'model' / 'params.npz')
    W = torch.tensor(p['coefficients'])            # (3,1280)
    Wi, Wt = W[:, :512], W[:, 512:]
    mu, sc = torch.tensor(p['image_mean']), torch.tensor(p['image_scale'])
    tfeat = (text - p['text_mean']) / p['text_scale'] / np.sqrt(768)
    tlog = torch.tensor(tfeat @ p['coefficients'][:, 512:].T + p['intercepts'])   # (N,3) text part + bias

    enc = m2 / 'model' / 'clip_encoder'
    model = CLIPVisionModelWithProjection.from_pretrained(enc, local_files_only=True).eval()
    model.requires_grad_(False)
    proc = CLIPImageProcessor.from_pretrained(enc, local_files_only=True)
    store = {}
    layer = model.vision_model.encoder.layers[-1].layer_norm1
    def hook(_m, _i, o):
        if o.requires_grad:
            o.retain_grad(); store['a'] = o
    layer.register_forward_hook(hook)

    def img_logit(pix):
        e = model(pixel_values=pix).image_embeds.double()
        e = e / e.norm(dim=-1, keepdim=True)
        f = (e - mu) / sc / np.sqrt(512)
        return f @ Wi.T                              # (B,3) image part of each seed logit

    rows, cams = [], []
    for s in range(0, len(val), a.batch):
        chunk = val.iloc[s:s + a.batch]
        imgs, shapes, boxes = [], [], []
        for f in chunk.file:
            with Image.open(h4 / f) as o:
                im = ImageOps.exif_transpose(o).convert('RGB')
            box = pad_box(*im.size)
            imgs.append(ImageOps.pad(im, (SIDE, SIDE), method=Image.Resampling.BICUBIC, color='white'))
            g = Image.new('RGB', (SIDE, SIDE), 'white'); g.paste((128, 128, 128), box)
            shapes.append(g); boxes.append(box)
        pix = proc(images=imgs, return_tensors='pt')['pixel_values'].requires_grad_(True)
        il = img_logit(pix)
        logit = il + tlog[s:s + len(chunk)]
        score = torch.sigmoid(logit).mean(1)
        logit.mean(1).sum().backward()
        A, G = store['a'][:, 1:, :].detach().double(), store['a'].grad[:, 1:, :].double()
        cam = torch.relu((A * G.mean(1, keepdim=True)).sum(-1)).numpy()          # Grad-CAM (B,49)
        gxa = torch.relu((A * G).sum(-1)).numpy()                                # grad x activation (B,49)
        with torch.no_grad():
            spix = proc(images=shapes, return_tensors='pt')['pixel_values']
            sil = img_logit(spix).mean(1).numpy()
        for k, (iid, box) in enumerate(zip(chunk.image_id, boxes)):
            pf = pad_fraction(box)
            pad_area = pf.mean()
            def mass(c):
                t = c.sum()
                return float((c * pf).sum() / t) if t > 0 else np.nan
            rows.append({'image_id': iid, 'score': float(score[k]), 'ref': float(ref[iid]),
                         'img_logit': float(il[k].mean()), 'shape_img_logit': float(sil[k]),
                         'pad_area': float(pad_area), 'cam_pad_mass': mass(cam[k]), 'gxa_pad_mass': mass(gxa[k]),
                         'cam_zero': bool(cam[k].sum() == 0), 'box': json.dumps(box)})
            cams.append(cam[k])
        model.zero_grad(set_to_none=True)
        print(f'{min(s + a.batch, len(val))}/{len(val)}', flush=True)

    df = val.merge(pd.DataFrame(rows), on='image_id')
    df.to_csv(out / 'gradcam_val.csv', index=False)
    np.save(out / 'gradcam_val_cam.npy', np.stack(cams))
    print('max |score - ref| =', (df.score - df.ref).abs().max())


if __name__ == '__main__':
    main()
