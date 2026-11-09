# 이미지 불법광고 탐지: 채현 몫 모델 (B1, B1+)

재계획 4절의 B1(OCR + v9n 그대로)과 B1+(OCR 글로 다시 학습한 텍스트 분류기), H6 글 임베딩을 만든다.
M3 는 M2 검증 점수(다영, 11.14~11.15)가 오면 이 폴더에 더한다.

## 지키는 규칙 (코드가 막는 것)

| 규칙 | 어디서 |
|---|---|
| 평가(test) 몫은 읽지 않는다 | `imgcommon.load()` 가 train·val 만 남긴다. `--allow-test` 는 준아의 평가셋 추론 전용 |
| 양성 = `label == illegal`, `unsure == 1` 은 학습·채점에서 뺀다 | `imgcommon.load()` 의 `y`, `scored` 열 |
| 어휘·가중치는 학습 몫으로만 | `b1plus_tfidf.py`, `b1plus_klue.py` |
| 문턱값·C 는 검증셋으로만 | `best_threshold()`, `C_grid` |
| v9n 규칙은 고치지 않는다 | `b1_v9n.py` 는 `package/model_v9n/model.pkl` 을 읽기만 한다 |

## 입력 (H4 로 받는 것)

- `split_v1.csv`: image_id, split, group_id
- `meta.csv`(채현)와 `hard/meta_hard.csv`(정연): 둘 다 `--meta` 에 준다
- `ocr.csv`(채현)와 `hard/ocr_hard.csv`(정연): 둘 다 `--ocr` 에 준다

## 실행 순서

```
A="--split split_v1.csv --meta meta.csv meta_hard.csv --ocr ocr.csv ocr_hard.csv"

# 1. B1 (로컬)
python b1_v9n.py $A --config configs/b1.yaml

# 2. B1+ TF-IDF (로컬)
python b1plus_tfidf.py $A --config configs/b1plus_tfidf.yaml

# 3. B1+ KLUE-RoBERTa (Colab L4): 시드 3회 + H6 용 OOF 5겹 = 미세조정 8번
pip install transformers==4.46.3
python b1plus_klue.py $A --config configs/b1plus_klue.yaml
```

결과는 `runs/<model_id>/` 에 쌓이고, 실험 로그는 `runs/experiments.csv` 한 장이다.
`runs/` 는 저장소에 올리지 않는다(이미지 ID 와 점수가 들어 있다).

## 결과 파일

| 파일 | 내용 |
|---|---|
| `pred_<id>_val.csv` | H7 형식(image_id, score, pred, model_id, config_hash, commit). pred 는 검증셋 문턱값 |
| `pred_<id>_train_oof.csv` | 학습 몫 group_id 5겹 OOF 점수. M2 가 학습 몫 점수를 쓸 때 부풀지 않게 |
| `fpr_site_<id>_val.csv` | 사이트 종류별 오탐률 |
| `report_<id>.json` | 고른 C·문턱값, train·val 지표, 시드 평균 ± 표준편차 |
| `emb_b1plus_klue_val.npy`, `emb_b1plus_klue_train_oof.npy` | **H6 (11.13, 다영에게)**. 768차원 float16, 행 순서는 같은 이름의 `_ids.csv` |

H6 학습 몫 임베딩은 OOF 다. 자기 학습 데이터를 본 모델에서 뽑은 임베딩으로 M2 를 학습하면, 검증·평가에서는 나오지 않는 깨끗한 신호를 배우기 때문이다.

## 평가셋 추론 (준아, H7 뒤)

```
A="--split split_v1.csv --meta ... --ocr ... --allow-test --out runs_test"
python b1_v9n.py $A --config configs/b1.yaml --score-only --thr 0.5
python b1plus_tfidf.py $A --config configs/b1plus_tfidf.yaml --infer-only runs/b1plus_tfidf/model_b1plus_tfidf.pkl
python b1plus_klue.py $A --config configs/b1plus_klue.yaml --infer-only runs/b1plus_klue/ckpt_s0 --thr <report 의 seed 0 문턱>
```

`pred_<id>_test.csv` 와 `emb_b1plus_klue_test.npy`(M2 평가셋 추론용)가 나온다.

## 알려진 한계

- 글자가 없는 이미지는 빈 글자로 점수를 낸다. 세 모델 모두 그런 이미지에서는 같은 점수를 준다
- TF-IDF + 로지스틱 회귀(lbfgs)는 시드로 바뀌지 않아 한 번만 돌린다. KLUE 만 시드 3회
- B1 은 감싼 링크(`link_href`)를 넣지 않는다(`use_href: false`). 재계획에서 B1 은 「글만」 보는 모델이다
