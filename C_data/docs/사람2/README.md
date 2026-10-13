# 사람 2 담당 데이터: HOMOGLYPH · TRANSPARENT 권장판

| 파일 | 건수 | 내용 |
|---|---:|---|
| `homoglyph/homoglyph_real_test_capped.yaml` | 378 | 권장판(캠페인당 최대 5건). tier A 333 · B 45. digit_letter 109 · enclosed_alnum 75 · fullwidth 50 · hangul_lookalike 47 · fullwidth_symbol 45 · partial_token 34 · cyrillic_greek 18. 20개 사이트 · 130개 캠페인. 10-13에 geomorphology.or.kr 6건 추가, `campaign` 칸의 번호를 해시로 바꿈 |
| `transparent/transparent_real_test_rec20.yaml` | 232 | 권장판(완전 중복을 뺀 뒤 사이트당 최대 20건). opacity_zero 110 · color_matches_bg 88 · color_alpha_zero 34. 해외 기관 26개 사이트 |
| `transparent/transparent_real_test_rec20_render.yaml` | 232 | 권장판 샘플별 단독 렌더링 결과. 전부 `invisible` |
| `transparent/transparent_real_negative.yaml` | 560 | TRANSPARENT 음성(오탐 확인용, `is_positive: false`). 해외 기관 118개 사이트, 사이트당 최대 10건. 안 보이지만 광고가 아닌 것 547(같은 색 꾸밈 222 · 기타 opacity 0 170 · 애니메이션 시작 상태 113 · 메뉴 15 · 아이콘 글자 11 · 화면낭독기용 8 · 슬라이더 8)과 광고 문구지만 실제로는 보이는 것 13. 각 샘플의 `render_standalone` 칸에 단독 렌더링 결과가 있다 |
| `homoglyph/HG_cap_difficulty.tsv` | 372 | HOMOGLYPH 권장판 샘플별 난이도 등급(L1~L3)과 가중치(`weight`). 10-13에 추가된 geomorphology.or.kr 6건(HG-RT-1778~1782 · 1791)은 표에 없다 |
| `transparent/TR_cap_difficulty.tsv` | 232 | TRANSPARENT 권장판 샘플별 난이도 등급과 가중치. 권장판 232건과 id 가 모두 맞는다 |
| `homoglyph/README.md` · `transparent/README.md` · `transparent/README_음성.md` | - | 사람 2 원본 설명서(수집 방법·필드·출처 부록·팀 확인 요청) |
| `docs/사람2/사람2_실데이터_특성_수집근거_테스트계획_20261013.md` | - | 사람 2 계획서: 데이터 특성·수집량 근거·편향 점검·테스트 투입 계획(T1~T5, 난이도 가중 재현율)·팀 결정 사항(11절) |
| `tools/validate.py` · `tools/render_check.py` | - | 팀 공통 양식 검사기 · 단독 렌더링 검사기 |

## 넣지 않은 것

권장판만 쓴다. 아래는 저장소에 없다(사람 2 ZIP 에 있음).

- HOMOGLYPH 전체판 `homoglyph_real_test.yaml`(1,791건)
- TRANSPARENT 전체판 `transparent_real_test_full.yaml`(541건)
- TRANSPARENT 경계 사례 `transparent_real_borderline.yaml`(22건: ejournal.unp.ac.id 20 · ojs.stiem-bongaya.ac.id 2). 사람 눈에는 안 보이지만 픽셀 비교 기준을 넘어 권장판에서 빠진 것

- TRANSPARENT 음성 제외분 `transparent_real_negative_render_mismatch.yaml`(159건). 사이트 CSS 가 빠져 단독으로 열면 원래 화면과 다르게 보이는 것
- TRANSPARENT 음성 렌더링 결과 `transparent_real_negative_render.yaml`(719건, 제외분 포함). 음성셋 560건의 결과는 각 샘플의 `render_standalone` 칸에 이미 있다
- 계획서 근거 파일(`hg_liveness_20261013.json` · `pww_tf*.jsonl` · `p2_stats.json`)과 사람 2 분석 스크립트(`analyze_p2.py` 등 8개). 근거 파일에는 도박 URL 이 들어 있고, 스크립트는 사람 2 PC 의 수집 원문 경로를 기준으로 짜여 있어 저장소만으로는 돌릴 수 없다. 함께 온 `validate.py` 는 `tools/validate.py` 와 같은 파일이다

하위 폴더의 사람 2 원본 README 와 계획서에 나오는 전체판·경계 사례·위 파일 언급, 사람 2 PC 경로(부록 A)는 저장소에 없는 파일을 가리킨다. `transparent/README_음성.md` 에 적힌 `split: test` 칸은 다른 데이터와 맞춰 저장소 파일에서 뺐다.

## 확인한 것

- `tools/validate.py` 로 두 권장판과 TRANSPARENT 음성셋 560건 모두 통과(오류 0).
- 음성셋 560건은 저장소의 다른 데이터와 HTML 조각이 겹치지 않는다. 사이트는 TRANSPARENT 권장판과 e-journal.upr.ac.id 하나만 겹친다.
- `source_type` 은 전부 `real` 이다.
- `render_check.py` 는 다시 돌리지 않았다. 표의 `invisible` 은 `*_render.yaml` 을 센 값이다.

## 주의

- TRANSPARENT 권장판 232건 가운데 72건은 흰 글자에 1px 를 함께 써서 OFFSCREEN 과 겹친다(`transparent/README.md` 6절). 이 파일에는 TRANSPARENT 건만 들어 있다.
- 원본 URL·링크 주소에 광고 문구와 도박 사이트 도메인이 그대로 들어 있다. 사람 2 는 원본 페이지 일부에 악성 스크립트가 있다고 적었다(Windows Defender 탐지). 원본 URL 을 직접 열지 않는다.
- 음성셋의 `neg_visible_failed_hide` 11건과 `neg_gradient_text_fill_spam` 1건은 도박 문구다. 화면에 보이므로 TRANSPARENT 정답은 아니다(`transparent/README_음성.md` 2절).
