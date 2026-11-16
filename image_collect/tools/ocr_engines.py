"""OCR 엔진 감싸개. 엔진 고르기(ocr_select/compare.py)와 이후 ocr.csv 만들기에서 같은 코드를 쓴다.

run(path) -> dict(text, n_boxes, conf_mean, boxes=[{box, text, conf}])
text 는 명세 6절대로 글상자를 위에서 아래, 왼쪽에서 오른쪽 순으로 이어 붙이고 사이는 빈칸 하나.
GIF 는 첫 프레임만 읽는다(명세 6절): 첫 프레임을 RGB numpy 배열로 바꿔 엔진에 넘긴다.
"""
import os

import numpy as np

os.environ.setdefault("PADDLE_PDX_CACHE_HOME", r"C:\Users\Public\pdxcache")  # 영문 경로여야 Paddle 추론이 모델을 읽는다
from PIL import Image  # noqa: E402


MAX_SIDE = 1600  # 11-04: 긴 변이 이보다 큰 이미지는 OCR 전에 줄인다(A4 스캔 한 장 25초 -> 수 초). 글상자 좌표는 원본 크기로 되돌린다


def load_rgb(path, max_side=MAX_SIDE):
    """-> (RGB 배열, 배율). 배율 = 원본 / 줄인 크기 (줄이지 않으면 1)."""
    im = Image.open(path)
    im.seek(0)
    im = im.convert("RGB")
    scale = 1.0
    if max_side and max(im.size) > max_side:
        scale = max(im.size) / max_side
        im = im.resize((round(im.width / scale), round(im.height / scale)), Image.LANCZOS)
    return np.array(im), scale


def order_boxes(items):
    """items: [(poly(4x2), text, conf)] -> 위에서 아래, 같은 줄이면 왼쪽에서 오른쪽.
    같은 줄 판정: 세로 중심 차이가 두 상자 높이 평균의 절반 이하."""
    rows = []
    for poly, t, c in items:
        p = np.asarray(poly, dtype=float).reshape(-1, 2)
        rows.append(dict(x=p[:, 0].min(), yc=(p[:, 1].min() + p[:, 1].max()) / 2, h=p[:, 1].max() - p[:, 1].min(),
                         box=p.round(1).tolist(), text=t, conf=float(c)))
    rows.sort(key=lambda r: r["yc"])
    lines, cur = [], []
    for r in rows:
        if cur and abs(r["yc"] - np.mean([q["yc"] for q in cur])) > 0.5 * np.mean([q["h"] for q in cur] + [r["h"]]):
            lines.append(cur)
            cur = []
        cur.append(r)
    if cur:
        lines.append(cur)
    out = []
    for ln in lines:
        out += sorted(ln, key=lambda r: r["x"])
    return out


def pack(items):
    boxes = order_boxes([it for it in items if str(it[1]).strip()])
    text = " ".join(b["text"].strip() for b in boxes)
    return dict(text=text, n_boxes=len(boxes), conf_mean=(round(float(np.mean([b["conf"] for b in boxes])), 4) if boxes else ""),
                boxes=[dict(box=b["box"], text=b["text"], conf=round(b["conf"], 4)) for b in boxes])


class EasyOCR:
    name = "easyocr"

    def __init__(self):
        import easyocr
        self.version = easyocr.__version__
        self.r = easyocr.Reader(["ko", "en"], gpu=False, verbose=False)

    def run(self, path):
        img, sc = load_rgb(path)
        res = self.r.readtext(img)
        return pack([(np.asarray(b, dtype=float) * sc, t, c) for b, t, c in res])


class Paddle:
    """모델 캐시는 영문 경로여야 한다(한글 사용자 폴더에서는 Paddle 추론이 모델 파일을 못 읽음). oneDNN 은 Paddle 3.3 CPU 버그로 끈다."""
    name = "paddleocr"

    DET = os.environ.get("OCR_DET", "PP-OCRv5_mobile_det")  # 11-04: server_det 은 oneDNN 을 끈 CPU 에서 빈 1600px 한 장에 16.8초

    def __init__(self, det=None):
        import paddleocr
        from paddleocr import PaddleOCR
        self.version = paddleocr.__version__
        self.det = det or self.DET
        self.r = PaddleOCR(text_detection_model_name=self.det, text_recognition_model_name="korean_PP-OCRv5_mobile_rec", use_doc_orientation_classify=False, use_doc_unwarping=False,
                           use_textline_orientation=False, device="cpu", enable_mkldnn=False,
                           text_det_limit_type="max", text_det_limit_side_len=1280)
        # 11-04: 검출 입력의 긴 변을 1280px 로 제한(기본은 짧은 변 64px 이상, 긴 변 4000px 까지라 큰 사진 한 장에 CPU 50초).
        # 합성 비교 배너는 모두 728px 이하라 이 제한에 걸리지 않으므로 엔진 비교 결과는 그대로다. 인식은 원본 해상도 조각으로 한다.

    def run(self, path):
        img, sc = load_rgb(path)
        img = img[:, :, ::-1].copy()  # PaddleOCR 는 BGR 을 받는다
        items = []
        for r in self.r.predict(img):
            for poly, t, c in zip(r["rec_polys"], r["rec_texts"], r["rec_scores"]):
                items.append((np.asarray(poly, dtype=float) * sc, t, c))
        return pack(items)


class PaddleServerDet(Paddle):
    name = "paddleocr"

    def __init__(self):
        super().__init__(det="PP-OCRv5_server_det")


ENGINES = {"easyocr": EasyOCR, "paddleocr": Paddle, "paddleocr_serverdet": PaddleServerDet}
