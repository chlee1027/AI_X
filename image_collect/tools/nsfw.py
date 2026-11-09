"""성인 노출 이미지 거르개 (명세 3절 「저장하지 않는 이미지」).

공개 분류기 Falconsai/nsfw_image_detection(ViT, 라벨 normal/nsfw)을 CPU 로 돌린다.
문턱 THR 은 보수적으로 0.30: 놓쳐서 저장하는 쪽이 잘못 버리는 쪽보다 비싸다고 보고 낮게 잡았다.
버린 이미지는 파일이 남지 않으므로, 잘못 버린 비율은 skipped.csv 의 adult 건수와 출처로만 짐작할 수 있다(보고서 한계).
"""
import os

MODEL = "Falconsai/nsfw_image_detection"
THR = float(os.environ.get("NSFW_THR", "0.30"))
_pipe = None


def _load():
    global _pipe
    if _pipe is None:
        from transformers import pipeline
        _pipe = pipeline("image-classification", model=MODEL, device=-1)
    return _pipe


def score(img):
    """PIL RGB 이미지 -> nsfw 확률(0~1)."""
    res = _load()(img)
    return next((r["score"] for r in res if r["label"].lower() == "nsfw"), 0.0)


def is_adult(img):
    return score(img) >= THR
