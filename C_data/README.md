# C_data: 실측 데이터 (2026-10-13)

카테고리마다 폴더 하나다. 전부 실제 사이트에서 받은 원문에서 뽑은 것이고, 수집 원문(`data/raw/`)은 올리지 않는다.

| 폴더 | 담당 | 파일 | 건수 |
|---|---|---|---:|
| `decoy/` | 사람 1 | `decoy.yaml` 정상 요소(오탐 확인용) · `negatives.json` 정답(음성) | 816 · 816 |
| `etc/` | 사람 1 | `etc.yaml` 4종 밖 회피 수법 · `answer_result_extra_etc.json` 정답 · `퍼센트인코딩_손검토_20261012.csv` | 473 · 473 |
| `combo/` | 사람 1 | `combo_real.yaml` 수법 2개 이상이 겹친 광고 · `answer_result.json` 4종 코드 정답 · `answer_result_extra_combo.json` 추가 수법 정답 | 529 · 419 · 668 |
| `homoglyph/` | 사람 2 | `homoglyph_real_test_capped.yaml` 닮은꼴 글자 권장판(캠페인당 5건) · `HG_cap_difficulty.tsv` 샘플별 난이도 등급 · `README.md` | 378 · 372 |
| `transparent/` | 사람 2 | `transparent_real_test_rec20.yaml` 투명 텍스트 권장판(사이트당 20건, 해외 기관 26곳) · `_render.yaml` 단독 렌더링 결과 · `answer_result.json` 정답(TRANSPARENT 232 + 같은 요소의 OFFSCREEN 72) · `transparent_real_negative.yaml` 투명처럼 보이지만 광고가 아닌 음성(오탐 확인용, 해외 기관 118곳) · `negatives.json` 음성 정답 · `TR_cap_difficulty.tsv` 샘플별 난이도 등급 · `README.md` · `README_음성.md` | 232 · 232 · 304 · 560 · 560 · 232 |
| `offscreen/` | 사람 3 | `offscreen_originals.yaml` 실제 원문(OF-001~OF-350), 7 subtype별 50건 | 350 |
| `offscreen/` (재수집) | 사람 2 | `offscreen_real_test_rec.yaml` 렌더링으로 숨김을 확인한 실데이터 권장판(사이트당 5, 국내 15, 235곳, 한국어 35) · `answer_result_real.json` 정답 · `offscreen_real_negative.yaml`·`negatives.json` 숨겨진 정상 글자 음성(544곳) · `offscreen_real_boundary_template.yaml` 템플릿이 숨긴 스팸 제목(경계) · `README_실데이터_재수집.md` | 722 · 722 · 2,451 · 2,451 · 15 |
| `jamo/` | 사람 4 | `jamo.yaml` 자모 분해 실제 원문(JM-001~130) | 130 |
| `lexicon/` | 사람 4 | `seed.yaml` 어휘 사전(gambling_core · gambling_lure · contact · adult · whitelist 각 100) | 500 |

- 개인정보: 휴대폰 · 050 · 070 번호는 가운데 자리를 0으로 가렸다. 닮은꼴 숫자로 쓴 번호(`⓿❶⓿＊❼❹❻❺＊…`)는 같은 모양의 0(`⓿⓿⓿⓿`)으로 바꿔 위장 모양을 남겼고, html · evidence_text · 정답 JSON · `campaign` 토큰을 같은 값으로 바꿔 서로 맞는다. 광고에 실린 사람 이름 1건도 가렸다(`김○○`). 기관 대표 이메일 · 주소는 공개 정보라 두었다(2026-10-13).
- `tools/validate.py` 는 팀 공통 양식 검사기(`python tools/validate.py <파일>`), `tools/render_check.py` 는 단독 렌더링 검사기(Playwright + Edge)다. `tools/render_check_off.py` 는 같은 검사기에서 음수 좌표(화면 밖) 요소를 오류 대신 'offscreen'으로 기록하는 사본이다.
- 사람별 설명 문서는 `docs/사람N/` 에 있다. 사람 3·4 원본 문서 속 경로(`samples/…`, `data/samples/…`)는 위 표의 폴더로 읽는다.
- `tools/validate.py` 는 사람 1 의 `etc.yaml`·`combo_real.yaml` 을 오류로 센다(etc 142건, combo 529건). etc 는 증거가 링크 주소·meta 같은 속성값에 있는데 검사기가 보이는 글자만 보고, combo 는 필드 이름이 `extra_findings`(복수)라서다. 데이터 오류가 아니라 양식 차이다.

- 최신 offscreen 350건 중 23건(OF-128~OF-150)은 전체 원문 기준 선택자와 HTML 발췌 범위가 달라 공통 검사기의 선택자 검증을 통과하지 않습니다. 상세 내용은 `docs/사람3/README.md` 및 `350건_검증결과.json`을 참고하세요.
