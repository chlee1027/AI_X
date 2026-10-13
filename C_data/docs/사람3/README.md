# 사람 3 담당 데이터: OFFSCREEN (2026-10-12)

바탕화면 `ai-x_sample-main.zip` 의 `사람3_최종결과_20261005/` 에서 데이터 파일만 골라 모았다. 파일 내용은 ZIP 원본과 같다. 설명은 함께 넣은 `사람3_데이터수집_분석및생성_최종정리_20261012.md` 를 따른다.

| 파일 | 건수 | 내용 |
|---|---:|---|
| `originals/offscreen_originals.yaml` | 100 | **실제 원문**(OF-108~OF-207). 전부 양성. 현재 페이지 52 · 과거 피해 코드 공개 사본 48. 숨김 유형 45/15/15/10/15(font-size·음수 left·display:none / visibility:hidden / clip / text-indent / transform) |
| `originals/reference_only.json` | 2 | 참고 사례. 원문 100 집계에서 뺀 것 |
| `samples/offscreen.yaml` | 100 | CSS 동작 확인용 양성 fixture(OF-001~OF-100). 원문 문구에 라이브러리 CSS 를 입힌 **파생 자료**다 |
| `samples/offscreen_controls.json` | 7 | 가시 대조군(OF-101~OF-107). 전부 음성 |
| `사람3_원본_README.md` | - | 사람 3 패키지 원본 설명서 |
| `tools/validate.py` | - | 팀 공통 양식 검사기(사람 2 ZIP 의 것과 같다) |

- **독립 원문은 100건이다.** fixture 100 은 원문에서 만든 것이라 합쳐 200 으로 세지 않는다. fixture 100 가운데 98 은 원문과 출처·문구가 똑같다.
- 실제 test 분할은 없다. fixture 는 CSS 동작 확인용이지 독립 평가용 test set 이 아니다.

## 확인한 것 (2026-10-12)

- `tools/validate.py` 결과: `samples/offscreen.yaml` 100 · `samples/offscreen_controls.json` 7 은 통과(오류 0). `originals/offscreen_originals.yaml` 은 100 가운데 98 통과, **OF-133 · OF-178 두 건이 선택자 매칭 0개**로 걸렸다.
  - 원인: 두 건의 `expected_location` 이 `body > ...` 로 시작한다. 검사기는 `html` 을 `<div>` 로 감싸 읽어서 `body` 가 없다. 문서 전체로 읽으면 두 건 모두 요소 1개에 맞고 그 안에 `evidence_text` 가 있다. 데이터가 틀린 것이 아니라 선택자 형식이 검사기와 다르다.
- YAML 과 JSON 판이 같은지 비교했다(원문 · fixture 둘 다 같음). 그래서 YAML 만 넣었다.
- ZIP 의 `패키지_SHA256.json` 188 항목 가운데, ZIP 에 든 177 개는 해시가 전부 맞는다. 나머지 11 개는 `data/raw/`(라이브러리 CSS 원문)이고 `.gitignore` 로 ZIP 에 처음부터 빠져 있다.
- 렌더링은 다시 돌리지 않았다. 「렌더링 214회 통과」는 ZIP 의 `검증결과.json` 에 적힌 값이다.

## 넣지 않은 것

- **합성 데이터 112개**(`사람3_출처편향_생성데이터_20261011/`: `합성데이터_112개.json`, `split_manifest.json` 등): 최종정리 md 가 가리키지만 ZIP 에도 바탕화면에도 없다. **보류**: 사람 3 이 데이터 확인 후 주기로 했다(10-12).
- 최종정리 md 가 가리키는 `원문100개_출처분류.csv` · `쏠림검증_집계.json` 도 같은 폴더에 있어야 하는데 없다.
- ZIP 에 있는 보조 자료(필요하면 ZIP 에서 꺼낸다): `fixtures/` HTML 107 · `시작.html` · `원문검수_보관.html`(5.7MB) · `근거이미지/` 21 · `data/css/`(CSS 규칙 141) · `data/catalog/` · `data/review/` · `data/unicode/`(Unicode 17.0.0) · `licenses/` · `scripts/` · `검증결과.json` · `최종현황.json`.

## 주의

- 양성 라벨은 OFFSCREEN 숨김 홍보 탐지용이다. 법적 불법성을 판정한 라벨이 아니다.
- `.go.kr` 출처는 0건이다. 출처는 산업·협회 사이트, 개인 홈페이지, 보안 보고서 등이다.
- 원문 HTML 에 광고 사이트 주소가 그대로 들어 있다. 공개 저장소에 올릴 때 주의한다.
