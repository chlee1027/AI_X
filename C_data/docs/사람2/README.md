# 사람 2 담당 데이터: HOMOGLYPH · TRANSPARENT 권장판

| 파일 | 건수 | 내용 |
|---|---:|---|
| `homoglyph/homoglyph_real_test_capped.yaml` | 378 | 권장판(캠페인당 최대 5건). tier A 333 · B 45. digit_letter 109 · enclosed_alnum 75 · fullwidth 50 · hangul_lookalike 47 · fullwidth_symbol 45 · partial_token 34 · cyrillic_greek 18. 20개 사이트 · 130개 캠페인. 10-13에 geomorphology.or.kr 6건 추가, `campaign` 칸의 번호를 해시로 바꿈 |
| `transparent/transparent_real_test_rec20.yaml` | 232 | 권장판(완전 중복을 뺀 뒤 사이트당 최대 20건). opacity_zero 110 · color_matches_bg 88 · color_alpha_zero 34. 해외 기관 26개 사이트 |
| `transparent/transparent_real_test_rec20_render.yaml` | 232 | 권장판 샘플별 단독 렌더링 결과. 전부 `invisible` |
| `transparent/transparent_real_negative.yaml` | 560 | TRANSPARENT 음성(오탐 확인용, `is_positive: false`). 해외 기관 118개 사이트, 사이트당 최대 10건. 안 보이지만 광고가 아닌 것 547(같은 색 꾸밈 222 · 기타 opacity 0 170 · 애니메이션 시작 상태 113 · 메뉴 15 · 아이콘 글자 11 · 화면낭독기용 8 · 슬라이더 8)과 광고 문구지만 실제로는 보이는 것 13. 각 샘플의 `render_standalone` 칸에 단독 렌더링 결과가 있다 |
| `transparent/answer_result.json` | 304 | TRANSPARENT 권장판 정답. TRANSPARENT 232건 + 렌더링 글자 크기 1px 라 같은 요소에 따로 세는 OFFSCREEN 72건(아래 결정 5) |
| `transparent/negatives.json` | 560 | TRANSPARENT 음성셋 정답(이 요소를 내면 오탐) |
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

## 사람 2 확인 요청에 대한 결정 (2026-10-13)

계획서 11절의 다섯 가지를 아래처럼 정한다.

| # | 요청 | 결정 | 근거 |
|---|---|---|---|
| 1 | 해외 기관 사이트 사례(TR 양성 232 · 음성 560)를 테스트셋으로 인정할지 | **인정한다.** 성적표에는 「해외 기관 26곳 실례」로 출처를 붙이고, 국내 실례가 0건이라는 사실을 함께 적는다 | 투명 처리는 CSS 수법이라 언어에 매이지 않는다. 국내 감염 게시판 약 100곳과 게시글 172건에서 실례가 0건이었으니, 인정하지 않으면 TR 실데이터 테스트셋이 0건이 된다 |
| 2 | 재배치 시험(T3 · T5: 실제 문구를 모의 사이트에 배치)을 별도 표기 조건으로 할지 | **별도 표기 조건으로 한다.** 실데이터 성적(T1 · T2 · T4)과 한 숫자로 합치지 않는다 | 문구는 실제지만 위치는 우리가 정했다. 합치면 실데이터 성적이 배치 설계에 따라 움직인다 |
| 3 | `hangul_lookalike`(`ㅋr톡`) 47건을 HOMOGLYPH 양성으로 볼지 | **양성으로 본다.** 다만 하위 유형별 재현율을 따로 내서, 주최 측 해석이 다를 때 이 47건만 빼고 다시 계산할 수 있게 둔다 | 한글 모음 `ㅏ` 자리에 라틴 `r` 을 넣어 같은 글자처럼 보이게 한 것으로, 요강의 「그 외 유사하게 생긴 문자」에 해당한다. 실례에서도 연락처(`ㅋr톡 @…`)를 숨기는 데 쓰였다 |
| 4 | 검색결과 반사 19건을 양성으로 볼지 | **양성으로 본다.** 성적표에서는 게시판 353건과 나눠 보고한다 | 공공 사이트 주소(easylaw 7 · mtu 5 · gangnam · mohw · motir 각 2 · mois 1)에서 닮은꼴 광고 문구가 화면에 그려진다. 요강은 쿼리 값이 다르면 다른 페이지로 보므로 채점 단위도 성립한다. 다만 진입 URL 에서 따라가는 크롤러는 이 페이지에 닿지 못할 수 있어, 탐지 성적과 수집 성적을 섞지 않으려고 따로 보고한다 |
| 5 | TR · OFFSCREEN 겹침 72건의 OFFSCREEN 건을 사람 3 데이터에 넣을지 | **사람 3 데이터(`offscreen/`)에는 넣지 않는다.** 대신 정답셋에서 이 72개 요소에는 TRANSPARENT 와 OFFSCREEN 두 건을 정답으로 둔다(`transparent/answer_result.json` 에 반영) | 요강은 한 요소에 기법이 둘이면 두 건으로 센다. OFFSCREEN 정답을 빼면 탐지기가 맞게 낸 OFFSCREEN 이 오탐으로 잡힌다. 그렇다고 `offscreen/` 에 섞으면 국내 원문 100건 사이에 같은 해외 사이트의 72건이 끼어들어 쏠림이 생긴다. 사람 3 도 font-size 0~1px 를 OFFSCREEN 으로 다룬다(`docs/사람3/` 의 기법 할당표) |

## 확인한 것

- `tools/validate.py` 로 두 권장판과 TRANSPARENT 음성셋 560건 모두 통과(오류 0).
- 두 정답 파일의 `location` 은 원본 페이지 기준 선택자(`origin.page_location`)다. 조각 기준 `expected_location` 을 쓰면 같은 페이지의 샘플끼리 url · location · technique 가 겹쳐(양성 247건) 요강 채점에서 1건으로 합쳐진다. `page_location` 으로는 양성 304건이 모두 서로 다르고, 양성과 음성이 같은 요소를 가리키는 경우도 없다. 음성 12건은 `page_location` 이 비어 있어(문구로 찾은 것) `expected_location` 을 썼고, 그중 8건이 서로 겹친다. 음성은 내면 안 되는 요소의 목록이라 채점 건수에는 영향이 없다.
- OFFSCREEN 72건은 `notes` 에 「OFFSCREEN 별도 1건」이 적힌 요소다. 렌더링으로 잰 글자 크기가 1px 이고, 52건은 조각 안에 `font-size:1px` 가 있고 20건은 조상에서 물려받았다.
- 휴대폰 번호: 사람 2 는 가운데 자리를 0으로 가렸다고 적었지만 HG-RT 한 건(`010 – 7921 – 8428`, 이름과 함께 실림)이 빠져 있었고, HG-RT-1296 의 `campaign` 토큰(`token:0102136335`)에 가리기 전 가운데 자리가 남아 있었다. 10-13 에 둘 다 0으로 가렸다(`homoglyph_real_test_capped.yaml` · `HG_cap_difficulty.tsv`).
- 음성셋 560건은 저장소의 다른 데이터와 HTML 조각이 겹치지 않는다. 사이트는 TRANSPARENT 권장판과 e-journal.upr.ac.id 하나만 겹친다.
- `source_type` 은 전부 `real` 이다.
- `render_check.py` 는 다시 돌리지 않았다. 표의 `invisible` 은 `*_render.yaml` 을 센 값이다.

## 주의

- TRANSPARENT 권장판 232건 가운데 72건은 흰 글자에 1px 를 함께 써서 OFFSCREEN 과 겹친다(`transparent/README.md` 6절). 이 파일에는 TRANSPARENT 건만 들어 있다.
- 원본 URL·링크 주소에 광고 문구와 도박 사이트 도메인이 그대로 들어 있다. 사람 2 는 원본 페이지 일부에 악성 스크립트가 있다고 적었다(Windows Defender 탐지). 원본 URL 을 직접 열지 않는다.
- 음성셋의 `neg_visible_failed_hide` 11건과 `neg_gradient_text_fill_spam` 1건은 도박 문구다. 화면에 보이므로 TRANSPARENT 정답은 아니다(`transparent/README_음성.md` 2절).
