# TRANSPARENT 음성(오탐 확인용) 실데이터 (사람 2)

작성: 김준아 / 기준일: 2026-10-13

## 1. 요약

| 파일 | 건수 | 용도 |
|---|---:|---|
| `transparent_real_negative.yaml` | **560** | **기본 음성셋**. 실제 페이지의 마크업 그대로, 단독 렌더링 상태가 원래 화면과 같은 것만 |
| `transparent_real_negative_render_mismatch.yaml` | 159 | 제외분. 사이트 CSS(배경 이미지·clip 등)가 빠져 단독으로 열면 원래와 다르게 보이는 것 |
| `transparent_real_negative_render.yaml` | - | 719건의 단독 렌더링 결과 |

- 전부 `category: TRANSPARENT`, `is_positive: false`, `source_type: real`, `split: test`. 생성·합성 0건.
- 118개 사이트(인도네시아 학교·마을·대학, 인도, 태국, 나이지리아, 콜롬비아, 파키스탄 등). 사이트당 최대 10건, 1위 사이트 10건(1.8%).
- `validate.py` 통과(양식 + 정답 선택자가 조각 안 요소 1개).
- 탐지기가 이 샘플의 `expected_location`을 TRANSPARENT로 잡으면 **오탐**이다.

## 2. 종류(subtype)

| subtype | 내용 | 건수 | 단독 렌더링 |
|---|---|---:|---|
| neg_same_color_decor | 배경과 같은 색 글자(템플릿 꾸밈, 푸터 등). 광고 아님 | 222 | 안 보임 |
| neg_opacity_other | 기타 정상 opacity 0 요소 | 170 | 안 보임 |
| neg_animation_state | 스크롤·등장 애니메이션 시작 전 상태(opacity 전환) | 113 | 안 보임 |
| neg_menu_dropdown | 접힌 메뉴·드롭다운 | 15 | 안 보임 |
| neg_transparent_icon_text | 아이콘·버튼의 color:transparent 글자 | 11 | 안 보임 |
| neg_a11y_hidden_text | 화면낭독기용 숨김 글자 | 8 | 안 보임 |
| neg_slider_inactive | 슬라이더의 현재 안 보이는 슬라이드 | 8 | 안 보임 |
| neg_visible_failed_hide | 숨기려 했지만 배경과 색이 달라 **보이는** 도박 문구(javeriana.edu.co, e-journal.upr.ac.id) | 11 | 보임 |
| neg_gradient_text_fill | `text-fill-color:transparent` + `background-clip:text` 그라데이션 글자 | 1 | 보임(옅음) |
| neg_gradient_text_fill_spam | 도박 제목이지만 그라데이션으로 보이게 처리(raksana.sch.id) | 1 | 보임 |

- 앞의 7종(547건)은 "안 보이지만 광고가 아님", 뒤의 3종(13건)은 "광고 문구이거나 투명처럼 보이는 스타일이지만 실제로는 보임"이다. 둘 다 TRANSPARENT 정답이 아니다.
- neg_visible_failed_hide 11건은 불법 광고 문구이긴 하다. 다만 요강의 투명 텍스트(시각적 은닉)는 아니므로 TRANSPARENT로 내면 오답이다.

## 3. 만든 방법

1. 대상: TR 양성 수집 때 감염 검사로 렌더링한 해외 기관 페이지에서, 안 보이지만 광고 어휘가 없는 요소 7,211행을 기록해 두었다.
2. 보수적으로 거름: 스팸이 나온 사이트 제외, 도박·의약품 어휘 제외, 스팸식 인라인 숨김 블록 제외 → 고유 2,859개.
3. 사이트당 10개까지 종류를 번갈아 골라 1,105개 → 224쪽을 2026-10-13에 Edge(일반 UA)로 다시 렌더링해 숨김 범위 마크업을 원문 그대로 자름.
4. 같은 사이트의 다른 요소에 도박 메뉴·문구가 있는 **감염·도메인 탈취 사이트 29곳 제외**. 23곳은 사이트 전체 어휘 검사로, 6곳은 조각 마크업 전수 검사로 찾았다.
5. 다시 열어 보니 opacity 0이 아닌 것(62), 선택자를 못 만든 것(99), 요소를 못 찾은 것(85) 제외 → 719.
6. 단독 렌더링(외부 요청 차단)으로 원래 화면 상태와 같은지 확인 → 560.

## 4. 필드

양성 TR 파일과 같다. 추가·차이:

| 필드 | 의미 |
|---|---|
| `css` | 원본에서 상속받던 배경색·글자색 + 숨김 값이 사이트 CSS·스크립트에서 온 경우 그 **계산값**(opacity·글자색·그라데이션)을 같은 요소에 복원. `notes`에 "css 복원:"으로 표시 |
| `inline_hide` | 숨김·색 스타일이 조각 안 인라인 style에 직접 있으면 true(137건). 문자열만 보는 탐지기에 특히 까다로운 함정 |
| `render_standalone` | 단독 렌더링 결과 |
| `origin.page_location` | 원본 페이지 기준 선택자(근접 오답·raksana는 문구로 찾아서 비어 있음) |

## 5. 쓰는 법

- 오탐률 = 음성 중 탐지기가 TRANSPARENT로 잡은 비율. 종류별로 따로 낸다.
- 양성 TR(232)과 사이트가 겹치는 것은 e-journal.upr.ac.id 5건뿐이다. 양성과 같은 사이트에서 음성을 뽑아 사이트 암기를 막는 효과는 작다.
- 원본 HTML은 저장하지 않았다. 조각은 YAML 안에만 있다.
- 개인정보: 조각 안 휴대폰 번호(인도네시아 08xx, 1개 번호 5곳)는 가운데 자리를 0으로 가렸다. 기관 대표 이메일·주소는 공개 정보라 그대로 두었다.

## 6. 덤으로 나온 것

감염 검사 과정에서 hamdardislamicus.com.pk(파키스탄 학술지)의 `<a style="color: transparent;">slot88</a>`(TR 양성 후보), reiagro.ugto.mx·jokli.fk.unand.ac.id의 숨긴 도박 링크 블록을 봤다. 양성 세트에는 아직 넣지 않았다.
