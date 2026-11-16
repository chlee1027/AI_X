"""Summarise gradcam_val.csv: padding share of CAM mass, shape-only control, example figure."""
import argparse, json
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageOps
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

THR = 0.5903098977202796
MIN_PAD = 1 / 7          # at least one patch row/column of padding
LABELS = ['illegal', 'legal_ad', 'campaign', 'normal']


def ap(y, s):
    """Average precision (same definition as sklearn average_precision_score)."""
    o = np.argsort(-s, kind='mergesort'); y = y[o]; s = s[o]
    tp = np.cumsum(y); fp = np.cumsum(1 - y)
    last = np.r_[np.where(np.diff(s))[0], len(s) - 1]
    prec, rec = tp[last] / (tp[last] + fp[last]), tp[last] / tp[-1]
    return float(np.sum(np.diff(np.r_[0, rec]) * prec))


def group_boot(df, col, n=2000, seed=0):
    rng = np.random.default_rng(seed)
    groups = df.group_id.unique(); idx = {g: np.where(df.group_id.values == g)[0] for g in groups}
    y, s = df.y.values, df[col].values
    vals = []
    for _ in range(n):
        take = np.concatenate([idx[g] for g in rng.choice(groups, len(groups))])
        if y[take].sum() == 0:
            continue
        vals.append(ap(y[take], s[take]))
    return np.percentile(vals, [2.5, 97.5])


def main():
    a = argparse.ArgumentParser()
    a.add_argument('--run', required=True); a.add_argument('--h4', required=True); a.add_argument('--out', required=True)
    a = a.parse_args()
    run, h4, out = Path(a.run), Path(a.h4), Path(a.out); out.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(run / 'gradcam_val.csv', dtype={'unsure': str})
    cams = np.load(run / 'gradcam_val_cam.npy')
    grp = pd.read_csv(h4 / 'split_v1_trainval.csv', dtype=str)[['image_id', 'group_id']]
    df = df.merge(grp, on='image_id', how='left')
    df['row'] = np.arange(len(df))
    df['pred'] = (df.score >= THR).astype(int)
    df['cam_ratio'] = df.cam_pad_mass / df.pad_area
    df['gxa_ratio'] = df.gxa_pad_mass / df.pad_area
    sure = df[df.unsure == '0'].copy()
    sure['y'] = (sure.label == 'illegal').astype(int)
    lines = [f'validation images {len(df)}, confident {len(sure)}, illegal {sure.y.sum()}',
             f'max |score - reference| = {(df.score - df.ref).abs().max():.2e}', '']

    # 1. padding share of CAM mass
    lines.append('## CAM mass on padding (images with padding >= 1/7 of the area)')
    lines.append('group | images | padded | median pad area | median CAM mass on pad | median ratio | share ratio>1 | grad x act median ratio')
    tab = []
    def row(name, d):
        p = d[(d.pad_area >= MIN_PAD) & ~d.cam_zero]
        r = dict(group=name, n=len(d), padded=len(p), pad_area=p.pad_area.median(), cam_mass=p.cam_pad_mass.median(),
                 ratio=p.cam_ratio.median(), above1=(p.cam_ratio > 1).mean(), gxa_ratio=p.gxa_ratio.median())
        tab.append(r)
        lines.append(f"{name} | {r['n']} | {r['padded']} | {r['pad_area']:.3f} | {r['cam_mass']:.3f} | {r['ratio']:.2f} | {r['above1']:.2f} | {r['gxa_ratio']:.2f}")
    for lab in LABELS:
        row(lab, sure[sure.label == lab])
    row('illegal, M2 pred=1', sure[(sure.label == 'illegal') & (sure.pred == 1)])
    row('not illegal, M2 pred=1 (FP)', sure[(sure.label != 'illegal') & (sure.pred == 1)])
    pd.DataFrame(tab).to_csv(out / 'pad_mass_by_group.csv', index=False)

    # 2. shape-only control
    lines += ['', '## Shape-only control (content replaced by flat gray, only aspect/padding left)']
    base = sure.y.mean()
    for col, name in [('img_logit', 'real image, image branch only'), ('shape_img_logit', 'shape-only image, image branch'), ('pad_area', 'padding area itself')]:
        v = ap(sure.y.values, sure[col].values); lo, hi = group_boot(sure, col)
        lines.append(f'{name}: PR-AUC {v:.3f} [{lo:.3f}, {hi:.3f}]  (random {base:.3f}, x{v / base:.1f})')
    sq = sure[sure.pad_area < 1e-9]
    lines.append(f'square images (no padding): {len(sq)} of {len(sure)}, illegal {sq.y.sum()} of {sure.y.sum()}')
    lines.append(f'shape-only logit spread: sd {sure.shape_img_logit.std():.3f} vs real image logit sd {sure.img_logit.std():.3f}')

    (out / 'summary.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('\n'.join(lines))

    # 3. example figure: highest-scored padded images per group
    plt.rcParams['font.family'] = 'Malgun Gothic'
    picks = []
    for name, d in [('불법 (M2 맞힘)', sure[(sure.label == 'illegal') & (sure.pred == 1)]),
                    ('계도 포스터', sure[sure.label == 'campaign']),
                    ('합법 광고', sure[sure.label == 'legal_ad']),
                    ('일반', sure[sure.label == 'normal'])]:
        d = d[(d.pad_area >= MIN_PAD) & ~d.cam_zero].sort_values('score', ascending=False).head(4)
        picks += [(name, r) for _, r in d.iterrows()]
    cols = 4; rows = int(np.ceil(len(picks) / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 3.2, rows * 3.6))
    for ax in axes.ravel():
        ax.axis('off')
    for ax, (name, r) in zip(axes.ravel(), picks):
        with Image.open(h4 / r.file) as o:
            im = ImageOps.pad(ImageOps.exif_transpose(o).convert('RGB'), (224, 224), method=Image.Resampling.BICUBIC, color='white')
        c = cams[int(r.row)].reshape(7, 7); c = c / c.max() if c.max() > 0 else c
        heat = np.array(Image.fromarray((c * 255).astype(np.uint8)).resize((224, 224), Image.Resampling.BILINEAR)) / 255
        ax.imshow(im); ax.imshow(heat, cmap='jet', alpha=0.45, vmin=0, vmax=1)
        l, t, rr, b = json.loads(r.box)
        ax.add_patch(plt.Rectangle((l, t), rr - l, b - t, fill=False, ec='white', lw=1.5, ls='--'))
        ax.set_title(f'{name}\nM2 {r.score:.2f} · 여백 {r.pad_area:.0%} · 열지도 {r.cam_pad_mass:.0%}', fontsize=9)
    fig.suptitle('M2 Grad-CAM (검증셋, 점선 안 = 원래 그림, 밖 = 흰 여백)', fontsize=12)
    fig.tight_layout(); fig.savefig(out / 'gradcam_examples_val.png', dpi=130); plt.close(fig)


if __name__ == '__main__':
    main()
