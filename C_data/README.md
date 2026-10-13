# C_data: 실측 데이터 (2026-10-13)

카테고리마다 폴더 하나다. 전부 실제 사이트에서 받은 원문에서 뽑은 것이고, 수집 원문(`data/raw/`)은 올리지 않는다.

| 폴더 | 담당 | 파일 | 건수 |
|---|---|---|---:|
| `decoy/` | 사람 1 | `decoy.yaml` 정상 요소(오탐 확인용) · `negatives.json` 정답(음성) | 516 · 516 |
| `etc/` | 사람 1 | `etc.yaml` 4종 밖 회피 수법 · `answer_result_extra_etc.json` 정답 · `퍼센트인코딩_손검토_20261012.csv` | 473 · 473 |
| `combo/` | 사람 1 | `combo_real.yaml` 수법 2개 이상이 겹친 광고 · `answer_result.json` 4종 코드 정답 · `answer_result_extra_combo.json` 추가 수법 정답 | 529 · 419 · 668 |

- 사람별 원래 README·현황 문서는 `docs/사람N/` 에 그대로 옮겼다. 그 문서 속 경로(`samples/…`, `answers/…`)는 바탕화면 정리 폴더 기준이니 위 표의 폴더로 읽는다.
- 사람 1 의 `answer_result_extra.json`(1,141건)은 카테고리에 맞춰 ETC 473 과 조합 668 로 나눴다. 항목은 바꾸지 않았다.
