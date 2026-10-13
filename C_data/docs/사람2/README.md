# 사람 2 담당 데이터: HOMOGLYPH · TRANSPARENT 권장판 (2026-10-12, TRANSPARENT 는 10-13 2차판으로 교체)

바탕화면 ZIP 을 풀어 **권장판만** 한 폴더에 모았다. 파일 내용은 ZIP 원본과 바이트 단위로 같다(SHA-256 확인).

- `사람2_HOMOGLYPH_실데이터_테스트셋.zip` -> `homoglyph/`
- `사람2_TRANSPARENT_실데이터_테스트셋_v2_2026-10-13.zip` -> `transparent/` (10-13 교체. 바탕화면 `pkg.zip` 은 이 ZIP 과 내용이 같다)
- 두 ZIP 에 같은 `validate.py` 가 들어 있어(해시 같음) `tools/` 에 하나만 두었다. `render_check.py` 도 `tools/` 로 옮겼다. 2차판의 두 스크립트도 1차판과 해시가 같다.

| 파일 | 건수 | 내용 |
|---|---:|---|
| `homoglyph/homoglyph_real_test_capped.yaml` | 372 | 권장판(캠페인당 최대 5건). tier A 327 · B 45. digit_letter 103 · enclosed_alnum 75 · fullwidth 50 · hangul_lookalike 47 · fullwidth_symbol 45 · partial_token 34 · cyrillic_greek 18 |
| `transparent/transparent_real_test_rec20.yaml` | 232 | 2차판 기본셋(완전 중복을 뺀 뒤 사이트당 최대 20건). opacity_zero 110 · color_matches_bg 88 · color_alpha_zero 34. 해외 기관 26개 사이트 |
| `transparent/transparent_real_test_rec20_render.yaml` | 232 | 기본셋 샘플별 단독 렌더링 결과. 전부 `invisible` |
| `homoglyph/README.md` · `transparent/README.md` | - | 사람 2 원본 설명서(수집 방법·필드·출처 부록·팀 확인 요청) |

## TRANSPARENT 1차판 -> 2차판에서 바뀐 것

| | 1차판(10-08) | 2차판(10-13) |
|---|---:|---:|
| 권장판 건수 | 107(사이트당 10) | 232(사이트당 20) |
| 전체판 건수 | 338 | 541(고유 436) |
| 사이트 수 | 19 | 26(새로 7곳, 태국 kma.ac.th 포함) |
| color_alpha_zero(권장판) | 3 | 34(`#ffffff00` 표기 포함) |
| 1위 사이트 비중(권장판) | 9.3%(10/107) | 8.6%(20/232) |

- 1차판 전체판 338건은 2차판 전체판에 id·html·문구가 같은 채로 모두 남아 있다. id 는 이어서 붙였다(TR-RT-0339~0541 이 새 몫).
- 1차판 권장판 107건 가운데 105건이 2차판 권장판에 있다. 빠진 둘(TR-RT-0013 kencang77, TR-RT-0287 toto slot)은 지워진 것이 아니라 전체판에는 남아 있고, 사이트당 20건을 다시 뽑을 때 고르지 않았다.

## 넣지 않은 것

권장판만 쓰기로 해서 아래는 이 폴더에 두지 않았다. 필요하면 ZIP 에서 다시 꺼낸다.

- HOMOGLYPH 전체판 `homoglyph_real_test.yaml`(1,777건)
- TRANSPARENT 2차판 전체판 `transparent_real_test_full.yaml`(541건)
- TRANSPARENT 2차판 경계 사례 `transparent_real_borderline.yaml`(22건: ejournal.unp.ac.id 20 · ojs.stiem-bongaya.ac.id 2). 사람 눈에는 안 보이지만 픽셀 비교 기준을 넘어 기본셋에서 빠진 것
- TRANSPARENT 1차판 전부(권장 107 · 전체 338). 2차판으로 대체했다

하위 폴더의 사람 2 원본 README 는 손대지 않았다. 그래서 거기 나오는 전체판·경계 사례 언급은 이 폴더에 없는 파일을 가리킨다.

## 확인한 것

- 10-12: `tools/validate.py` 를 HOMOGLYPH 권장판에 돌려 통과(오류 0).
- 10-13: TRANSPARENT 2차판 기본셋 232 · 전체판 541 · 경계 22 모두 `validate.py` 통과(오류 0). 2차판 README 의 건수·하위 유형 분포·사이트 수 26·1위 8.6%·상위 4곳 34.5%·전체판 고유 436 을 직접 세어 같음을 확인했다. 기본셋 232건은 전체판의 같은 id 레코드와 내용이 똑같다(부분집합).
- `source_type` 은 전부 `real`, `split` 은 전부 `test` 다.
- `render_check.py` 는 다시 돌리지 않았다. 표의 `invisible` 은 ZIP 에 든 `*_render.yaml` 을 센 값이다.

## 주의

- HOMOGLYPH 는 **10-02 게이트 제출본**(권장 372)이다.
- 바탕화면 `team_TR.zip` 은 TRANSPARENT 1차판 ZIP 과, `person1_DECOY.zip` 안의 `team_HG/` 는 HOMOGLYPH ZIP 과 해시가 같은 중복이라 따로 넣지 않았다.
- TRANSPARENT 기본셋 232건 가운데 72건은 흰 글자에 1px 를 함께 써서 OFFSCREEN 과 겹친다(2차판 README 6절). 이 파일에는 TRANSPARENT 건만 들어 있다.
- 원본 URL·링크 주소에 광고 문구와 도박 사이트 도메인이 그대로 들어 있다. 사람 2 는 원본 페이지 일부에 악성 스크립트가 있다고 적었다(Windows Defender 탐지). 원본 URL 을 직접 열지 말고, 공개 저장소에 올릴 때 주의한다.
