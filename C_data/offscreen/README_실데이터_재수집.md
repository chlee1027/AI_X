# OFFSCREEN 실데이터 재수집 (2026-10-15)

기존 사람 3 offscreen 350건을 보완하려고 새로 모은 **실제 사이트 데이터**입니다. 모든 샘플은 실제 공개 페이지를 Edge로 그린 뒤, 글자가 실제로 화면에 보이지 않는 것을 확인한 것만 넣었습니다. 생성하거나 손으로 만든 샘플은 없습니다.

## 파일

| 파일 | 내용 | 건수 |
|---|---|---:|
| `offscreen_real_test_rec.yaml` | **권장판**. 사이트당 5건(국내는 15건), 나라·수법 쏠림 제한 | 722 |
| `answer_result_real.json` | 권장판 정답(`technique: OFFSCREEN`) | 722 |
| (저장소 밖) `offscreen_real_test_cap15.yaml` | 전체판. 사이트당 15건 상한. 저장소 규칙(권장판만)에 따라 올리지 않고 사람 2 로컬에 둠 | 4,350 |
| `offscreen_real_negative.yaml` / `negatives.json` | 음성. 같은 감염·정상 사이트에서 숨겨져 있지만 광고가 아닌 글자(메뉴, 본문 바로가기, 슬라이드 등). 사이트당 5건 | 2,451 |
| `offscreen_real_boundary_template.yaml` | 경계 사례. 광고 문구지만 광고하는 쪽이 아니라 CMS 템플릿이 숨긴 경우(그누보드 `#hd_h1` 접근성 제목, KBoard 이전/다음 글 등). 같은 문구가 본문에는 보이게 있음. 팀 판정 필요 | 15 |
| `*_render.yaml` | 단독 렌더링 결과(invisible / zero-box / offscreen) | |

양식은 팀 공통 11칸에 TR 실데이터와 같은 `origin`·`source_type: real`을 더했습니다. `tools/validate.py` 통과를 확인했습니다.

- `expected_location`: `html` 발췌 기준 선택자(발췌 안에서 유일).
- `origin.page_location`: **원래 페이지 전체 기준 선택자**. `page_location_unique`에 페이지에서 유일한지를 함께 적었습니다. 기존 350건에서 OF-128~150이 실패했던 문제(발췌와 전체 페이지 선택자가 섞임)를 두 칸으로 나눠 해결했습니다.
- `origin.hide_origin`: `inline`(광고 요소에 직접 숨김 스타일) / `site_css`(사이트 CSS 때문에 숨겨짐. 예: 진도군 게시판 댓글 영역 `.comment{position:absolute;left:-99999px}`) / `template`.
- `css`: 숨김을 재현하는 규칙 `#root > :first-child{...}`. 사이트 CSS로 숨겨진 경우에도 단독 렌더링에서 숨김이 재현됩니다.
- `subtype`: 렌더링에서 실제로 글자를 숨긴 원인 기준. 기존 7종에 `zero_size_overflow`(1px 상자 + overflow:hidden), `transform_scale0`을 더했습니다.
- 휴대폰 번호 가운데 자리는 0으로, 스팸 댓글 속 개인 이메일은 앞 두 글자만 남기고 가렸습니다(11건).

## 수치

| | 권장판 | 전체판(로컬) | 음성 |
|---|---:|---:|---:|
| 건수 | 722 | 4,350 | 2,451 |
| 사이트 | 235 | 402 | 544 |
| 사이트 1위 | cwworld.co.kr 15 (2.1%) | cwworld.co.kr 15 (0.3%) | 5건씩 |
| 국내 | 35 (cwworld 15, 진도군 13, sgr21 3, bigbook 2, smlu 2) | 39 | 301 (70곳) |
| 한국어 광고 문구 | 35 | 39 | - |

권장판 하위 유형: display_none 240 (33%) · negative_left 200 (28%) · visibility_hidden 96 · zero_size_overflow 71 · clip_or_clip_path 52 · font_size_zero_or_tiny 31 · transform_or_document_coordinates 19 · negative_text_indent 13.

권장판 나라(최상위 도메인): id 280 (38.8%) · ar 40 · kr 35 · th 33 · org 31 · pk 29 · br 28 · com 23 · in 21 · edu 16 등. 숨김 출처: inline 555 · site_css 167.

권장판 뽑는 규칙: 단독 렌더링에서 숨김이 재현된 것만, 사이트당 5건(국내 15건), 같은 광고 목적지 5건, 같은 문구는 사이트당 2건. id·display_none·negative_left는 목표 800건 기준 35/30/25% 상한을 두어 실제 38.8/33/28%입니다.

단독 렌더링(전체판 4,403건): zero-box 2,435 · 화면 밖 좌표 1,581 · 픽셀 차이 없음 334. 보임 45 · 요소 못 찾음 8건은 뺐습니다. 팀 `render_check.py`는 음수 좌표 요소에서 캡처 오류로 멈춰서, 그 경우를 'offscreen'으로 기록하는 사본(`C_data/tools/render_check_off.py`)으로 돌렸습니다.

## 어떻게 모았나

1. **국내**: 검색 도메인 필터(go.kr·or.kr·ac.kr·re.kr 등) + 불법광고 어휘로 약 130개 공공·민간 페이지 후보를 찾고, 예전 HG 게시판 순회에서 나온 스팸 글 167개를 렌더링했습니다. 국내 게시판 스팸은 대부분 **보이게** 올라옵니다(스팸 글 68개 중 숨김 0건). 숨김은 다음 경우에만 나왔습니다.
   - 진도군청 자유게시판: 스팸 댓글(카지노사이트·출장안마·영문 스팸)이 사이트 CSS 때문에 left:-99999px 1×1 영역에 놓여 화면에 보이지 않습니다. 표본 334개 글 중 14개에서 확인했습니다.
   - smlu.or.kr(서울교통공사통합노조)·sgr21.or.kr: 게시판 템플릿에 `width:1px;height:1px;overflow:hidden` 블록이 심겨 있습니다(출장안마 링크, 흰 글자).
   - cwworld.co.kr: 게시글 안에 `font-size:0` 링크(롤토토·먹튀·구글상위노출 등 한국 백링크 업자 패턴).
   - bigbook.or.kr: 해킹으로 올라간 페이지의 display:none 블록(흥신소·도청).
2. **해외**: 10-08 TR 수집 때 스팸 감염을 확인한 기관 페이지 952개(664개 사이트)를 다시 렌더링했습니다. 인니 정부(go.id)·마을(desa.id)·학교(sch.id)·대학 저널과 중남미·파키스탄·우크라이나 대학 저널 등입니다.
3. 판정은 숨김(렌더링) × 광고(도박·성인·의약품·불법금융 어휘 또는 그런 목적지 링크)입니다. '도박 근절' 같은 정상 기사 제목, 숫자, 기관 메뉴(Daftar Informasi Publik 등)는 제외했습니다. 무작위 표본을 두 번 검수해 오탐 패턴을 고쳤습니다.
4. 단독 렌더링에서 숨김이 재현되지 않은 샘플은 뺐습니다.

## 쏠림·한계 (그대로 적음)

- 해외, 특히 인니 비중이 큽니다. 국내 OFFSCREEN 실례가 원래 드물기 때문입니다. 권장판에서 .id는 38.8%입니다(전체판 약 64%).
- 국내는 5개 사이트(cwworld·진도군·smlu·sgr21·bigbook)뿐입니다.
- 기존 350건과 같은 사이트가 일부 겹칩니다(um-sorong, unp, stiem-bongaya 등). 요소·페이지는 새로 뽑았습니다.
- 페이지가 바뀌거나 정리되면 원본 URL에서 더는 재현되지 않을 수 있습니다(수집 시점 2026-10-15).
- 광고 판정은 수집자 판단이며 법적 판단이 아닙니다.
