# 사람 1(역할 C) 담당 데이터: DECOY · ETC · 조합

| 파일 | 건수 | 내용 |
|---|---:|---|
| `decoy/decoy.yaml` | 516 | 정상 요소(오탐 확인용). a11y_sr_only 170 · hidden_menu 150 · risky_word_normal 83 · policy_text 54 · homoglyph_like_normal 40 · legal_ad_spam 19. 출처 167곳 |
| `decoy/negatives.json` | 516 | DECOY 정답(음성) |
| `etc/etc.yaml` | 473 | zero_width 306 · link_cloaking 86 · encoding 59(URL 퍼센트 32 · 숫자 엔티티 24 · Base64 3) · meta_cloaking 21 · css_content 1. 출처 136곳 |
| `etc/answer_result_extra_etc.json` | 473 | ETC 정답 |
| `etc/퍼센트인코딩_손검토_20261012.csv` | - | URL 퍼센트 인코딩 후보 손 검토 기록. 「인정」만 etc.yaml 에 들어 있다 |
| `combo/combo_real.yaml` | 529 | 한 요소에 회피 수법 2개 이상이 겹친 실제 광고. 출처 96곳 |
| `combo/answer_result.json` | 419 | 조합 가운데 4종 코드가 있는 것(HOMOGLYPH 398 · JAMO 20 · TRANSPARENT 1) |
| `combo/answer_result_extra_combo.json` | 668 | 조합의 추가 수법 |

- 전부 실측이고 생성 데이터는 0건이다.
- 정답 id 는 `<샘플 id>_<코드>` 이고 url 은 샘플 `source` 의 첫 주소다.
- 자세한 분포는 `통계_20261013.md`.
