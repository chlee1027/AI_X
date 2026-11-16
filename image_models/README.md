# 이미지 불법광고 탐지: 채현 몫 모델 (B1, B1+)

재계획 4절의 B1(OCR + v9n 그대로)과 B1+(OCR 글로 다시 학습한 텍스트 분류기), H6 글 임베딩을 만든다.
M3(`m3_claude.py`)는 바탕 모델 점수가 애매한 이미지만 Claude 비전에 다시 묻는다. 바탕은 B1+ TF-IDF 로 시작하고, M2 검증 점수(다영)가 11.15 안에 오고 검증 PR-AUC 가 TF-IDF 이상이면 M2 로 바꾼다(11.13 에 정한 규칙).

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

## M3: 애매한 이미지만 Claude 비전에 묻기

API 키는 환경 변수 `ANTHROPIC_API_KEY` 로 준다. 설정은 `configs/m3.yaml`, 프롬프트는 `prompts/m3_v1.txt`(가이드라인 v1.1 요약).

```
A="--split split_v1_trainval.csv --meta meta_trainval.csv --ocr ocr_trainval.csv --images <H4_trainval 폴더>"
B="--base runs/m2/pred_m2_val.csv"   # 다영 M2 검증 점수(image_id,score)에 검증 F1 최대 문턱 0.657093 으로 pred 를 붙인 것

# 1. API 없이 구간별 호출 수·어림 비용
python m3_claude.py $A $B --config configs/m3.yaml --dry-run
# 2. 무작위 20장만 물어 장당 실제 비용 재기
python m3_claude.py $A $B --config configs/m3.yaml --limit 20
# 3. 가장 넓은 구간 전체를 묻고 구간 고르기 (2 에서 물은 답은 캐시에서 다시 쓴다)
python m3_claude.py $A $B --config configs/m3.yaml
```

- 검증셋에서는 `widest_zone` 안의 이미지를 한 번만 묻고, 그 안의 작은 구간마다 fix·break·순이득·호출 수·비용을 다시 계산한다(`zones_m3_val.csv`). 고르는 규칙은 순이득 최대, 같으면 호출 적은 쪽.
- 답은 `runs/m3/claude_cache.jsonl` 에 쌓이고, 같은 프롬프트·모델·설정이면 다시 묻지 않는다. 거절·형식 오류는 다시 묻지 않고, 연결·속도 제한 오류만 다시 묻는다.
- `fix_human`·`break_human` 은 사람이 확인한 라벨(labeler 에 채현·정연·확인)만 센 값이다. 라벨 초안 대부분을 Claude 가 달았으므로 Claude 를 쓰는 M3 점수는 이 열과 같이 본다.
- 평가셋(준아): `--allow-test --zone <lo> <hi> --base pred_<바탕>_test.csv --out runs_test` 로 고른 구간 하나만 묻는다.

## 평가셋 추론 (준아, H7 뒤)

노트북 `colab_test_inference.ipynb`(Colab T4)로 돌린다. 준비물과 순서는 노트북 첫 칸에 있다. 칸마다 검증 몫을 먼저 다시 돌려 앞서 낸 점수와 같은지 확인하고, 다르면 멈춘다.

```
A="--split split_v1.csv --meta meta.csv --ocr ocr.csv --allow-test --out runs_test"
python b1_v9n.py $A --config configs/b1.yaml --score-only --thr 0.922496          # 검증셋 F1 최대 문턱
python b1plus_tfidf.py $A --config configs/b1plus_tfidf.yaml --infer-only model_b1plus_tfidf.pkl
python b1plus_klue.py $A --config configs/b1plus_klue.yaml --infer-only ckpt_s0 --thr 0.953839   # seed 0 문턱
# M2 (다영 추론 코드): KLUE 가 낸 emb_b1plus_klue_test.npy 를 받아 점수, 다영 동결 문턱 0.5903098977202796 으로 pred(검증 판정은 0.657093 과 같음)
python m3_claude.py $A --config configs/m3.yaml --base runs_test/m2/pred_m2_test.csv --images <test 폴더> --zone 0.05 0.8
```

- KLUE → M2 → M3 는 앞 단계 출력을 받으므로 이 순서다.
- 평가셋 모드에서는 라벨을 쓰지 않는다. `describe()` 는 평가 몫의 장 수만 내고, M3 는 바탕 점수가 평가 몫 전부에 있어야 돈다.

## M2 Grad-CAM: 배너 비율 지름길 점검 (검증셋)

다영의 동결 M2 묶음(`infer_m2.py` 와 같은 전처리)으로 검증셋 3,026장을 다시 돌려, 그림 쪽이 흰 여백(원래 비율)을 단서로 쓰는지 본다. 평가셋은 쓰지 않는다. 라벨은 마지막 요약에만 쓴다.

```
python m2_gradcam.py --h4 <H4_trainval> --m2 <M2_inference_H7_20261116> \
  --text-emb emb_b1plus_klue_val.npy --text-ids emb_b1plus_klue_val_ids.csv --out runs/m2_gradcam
python m2_gradcam_summary.py --run runs/m2_gradcam --h4 <H4_trainval> --out runs/m2_gradcam/summary
```

- 열지도: CLIP 마지막 블록 입력 토큰(7x7 조각)의 Grad-CAM. 목표는 시드 셋의 logit 평균이다.
- 여백 몫: 열지도 중 흰 여백에 놓인 몫을 여백 넓이와 비교한다. 1이면 고르게 퍼진 것과 같다.
- 모양만 남긴 대조: 그림 내용을 회색으로 지우고 여백 윤곽만 남긴 이미지를 넣어, 그림 쪽 점수의 PR-AUC 를 잰다.
- 결과(2026-11-17): 점수 재현 최대 차이 3.3e-4, 문턱 판정 차이 0. 여백 있는 불법 71장에서 열지도의 여백 몫 중앙 15%(여백 넓이 40%). 모양만 남긴 이미지의 그림 쪽 PR-AUC 0.036 [0.016, 0.073], 무작위 0.038, 실제 이미지 0.683. 정사각형 불법 36장은 여백이 없어 이 점검 밖이고, 파일 크기·압축 흔적은 재지 않았다.
- 필요한 패키지: `transformers==4.46.3`(다영 5.17.0 대비 점수 차이는 위 재현 값), torch(CPU 로 돈다), pillow, pandas, matplotlib.

## 알려진 한계

- 글자가 없는 이미지는 빈 글자로 점수를 낸다. 세 모델 모두 그런 이미지에서는 같은 점수를 준다
- TF-IDF + 로지스틱 회귀(lbfgs)는 시드로 바뀌지 않아 한 번만 돌린다. KLUE 만 시드 3회
- B1 은 감싼 링크(`link_href`)를 넣지 않는다(`use_href: false`). 재계획에서 B1 은 「글만」 보는 모델이다
