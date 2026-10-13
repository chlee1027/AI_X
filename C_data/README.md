# C_data: 실측 데이터 (2026-10-13)

카테고리마다 폴더 하나다. 전부 실제 사이트에서 받은 원문에서 뽑은 것이고, 수집 원문(`data/raw/`)은 올리지 않는다.

| 폴더 | 담당 | 파일 | 건수 |
|---|---|---|---:|
| `decoy/` | 사람 1 | `decoy.yaml` 정상 요소(오탐 확인용) · `negatives.json` 정답(음성) | 816 · 816 |
| `etc/` | 사람 1 | `etc.yaml` 4종 밖 회피 수법 · `answer_result_extra_etc.json` 정답 · `퍼센트인코딩_손검토_20261012.csv` | 473 · 473 |
| `combo/` | 사람 1 | `combo_real.yaml` 수법 2개 이상이 겹친 광고 · `answer_result.json` 4종 코드 정답 · `answer_result_extra_combo.json` 추가 수법 정답 | 529 · 419 · 668 |
| `homoglyph/` | 사람 2 | `homoglyph_real_test_capped.yaml` 닮은꼴 글자 권장판(캠페인당 5건) · `README.md` | 378 |
| `transparent/` | 사람 2 | `transparent_real_test_rec20.yaml` 투명 텍스트 권장판(사이트당 20건, 해외 기관 26곳) · `_render.yaml` 단독 렌더링 결과 · `README.md` | 232 |
| `offscreen/` | 사람 3 | `offscreen_originals.yaml` 실제 원문(OF-108~207) · `reference_only.json` 참고 사례 · `offscreen.yaml` CSS 동작 확인용 fixture(원문에서 만든 파생, 독립 평가용 아님) · `offscreen_controls.json` 가시 대조군(음성) | 100 · 2 · 100 · 7 |
| `jamo/` | 사람 4 | `jamo.yaml` 자모 분해 실제 원문(JM-001~130) | 130 |
| `lexicon/` | 사람 4 | `seed.yaml` 어휘 사전(gambling_core · gambling_lure · contact · adult · whitelist 각 100) | 500 |

- `tools/validate.py` 는 팀 공통 양식 검사기(`python tools/validate.py <파일>`), `tools/render_check.py` 는 단독 렌더링 검사기(Playwright + Edge)다.
- 사람별 설명 문서는 `docs/사람N/` 에 있다. 사람 3·4 원본 문서 속 경로(`samples/…`, `data/samples/…`)는 위 표의 폴더로 읽는다.
- `tools/validate.py` 는 사람 1 의 `etc.yaml`·`combo_real.yaml` 을 오류로 센다(etc 142건, combo 529건). etc 는 증거가 링크 주소·meta 같은 속성값에 있는데 검사기가 보이는 글자만 보고, combo 는 필드 이름이 `extra_findings`(복수)라서다. 데이터 오류가 아니라 양식 차이다.
- offscreen 원문 OF-133·OF-178 도 선택자가 `body > …` 로 시작해 검사기에서 매칭 0개로 걸린다(문서 전체로 읽으면 맞음, `docs/사람3/README.md`).
