# 사람 2 담당 데이터: HOMOGLYPH · TRANSPARENT 권장판

| 파일 | 건수 | 내용 |
|---|---:|---|
| `homoglyph/homoglyph_real_test_capped.yaml` | 372 | 권장판(캠페인당 최대 5건). tier A 327 · B 45. digit_letter 103 · enclosed_alnum 75 · fullwidth 50 · hangul_lookalike 47 · fullwidth_symbol 45 · partial_token 34 · cyrillic_greek 18 |
| `transparent/transparent_real_test_rec20.yaml` | 232 | 권장판(완전 중복을 뺀 뒤 사이트당 최대 20건). opacity_zero 110 · color_matches_bg 88 · color_alpha_zero 34. 해외 기관 26개 사이트 |
| `transparent/transparent_real_test_rec20_render.yaml` | 232 | 권장판 샘플별 단독 렌더링 결과. 전부 `invisible` |
| `homoglyph/README.md` · `transparent/README.md` | - | 사람 2 원본 설명서(수집 방법·필드·출처 부록·팀 확인 요청) |
| `tools/validate.py` · `tools/render_check.py` | - | 팀 공통 양식 검사기 · 단독 렌더링 검사기 |

## 넣지 않은 것

권장판만 쓴다. 아래는 저장소에 없다(사람 2 ZIP 에 있음).

- HOMOGLYPH 전체판 `homoglyph_real_test.yaml`(1,777건)
- TRANSPARENT 전체판 `transparent_real_test_full.yaml`(541건)
- TRANSPARENT 경계 사례 `transparent_real_borderline.yaml`(22건: ejournal.unp.ac.id 20 · ojs.stiem-bongaya.ac.id 2). 사람 눈에는 안 보이지만 픽셀 비교 기준을 넘어 권장판에서 빠진 것

하위 폴더의 사람 2 원본 README 에 나오는 전체판·경계 사례 언급은 저장소에 없는 파일을 가리킨다.

## 확인한 것

- `tools/validate.py` 로 두 권장판 모두 통과(오류 0).
- `source_type` 은 전부 `real` 이다.
- `render_check.py` 는 다시 돌리지 않았다. 표의 `invisible` 은 `*_render.yaml` 을 센 값이다.

## 주의

- TRANSPARENT 권장판 232건 가운데 72건은 흰 글자에 1px 를 함께 써서 OFFSCREEN 과 겹친다(`transparent/README.md` 6절). 이 파일에는 TRANSPARENT 건만 들어 있다.
- 원본 URL·링크 주소에 광고 문구와 도박 사이트 도메인이 그대로 들어 있다. 사람 2 는 원본 페이지 일부에 악성 스크립트가 있다고 적었다(Windows Defender 탐지). 원본 URL 을 직접 열지 않는다.
