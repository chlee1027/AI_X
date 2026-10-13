# 사람 1(역할 C) 담당 데이터: DECOY · ETC · 조합 (2026-10-12, ETC 는 10-13 보충 합침)

팀 저장소 chlee1027/AI_X 커밋 `3235270` 의 `C_data/data/` 에서 사람 1 몫만 복사했고, 10-13 에 마지막 판 `15a3612` 의 CB-600 을 더해 그 판과 맞췄다(DECOY·옛 ETC·정답 파일 모두 일치 확인). 10-13 ETC 보충은 이 폴더에만 있고 저장소에는 아직 안 들어갔다(이 폴더가 더 새 판).

| 파일 | 건수 | 내용 |
|---|---:|---|
| `samples/decoy.yaml` | 516 | 정상 요소(오탐 확인용). a11y_sr_only 170 · hidden_menu 150 · risky_word_normal 83 · policy_text 54 · homoglyph_like_normal 40 · legal_ad_spam 19. 출처 167곳 |
| `samples/etc.yaml` | 473 | zero_width 306 · link_cloaking 86 · encoding 59(URL 퍼센트 32 · 숫자 엔티티 24 · Base64 3) · meta_cloaking 21 · css_content 1. 출처 136곳 (2026-10-13 보충 합침) |
| `samples/combo_real.yaml` | 529 | 한 요소에 회피 수법 2개 이상이 겹친 실제 광고. 강화군 게시판 62건은 쏠림 보완으로 뺐다. CB-600(숨김+난독화 첫 실측, 같은 색 숨김 속 ㅌㅌ) 포함. 출처 96곳 |
| `answers/answer_result.json` | 419 | 조합 가운데 4종 코드가 있는 것(HOMOGLYPH 398 · JAMO 20 · TRANSPARENT 1) |
| `answers/answer_result_extra.json` | 1,141 | ETC 473 + 조합의 추가 수법 668 (2026-10-13 다시 만듦) |
| `answers/negatives.json` | 516 | DECOY |

- 정답 파일 셋은 저장소 정답셋에서 id 가 `DC-`·`ET-`·`CB-` 인 것만 골랐다. 저장소 정답셋의 나머지(HOMOGLYPH·JAMO·OFFSCREEN)는 사람 2·3·4 몫이다.
- `split` 칸은 10-07 분할 기록(train·val·test)이다. 10-09~11 새 수집분(DC-260~516 · ET-230~514 · CB-260~599)에는 이 칸이 없다.
> 10-12 판의 미결(퍼센트 인코딩 인정 여부, 소프트 하이픈 76.3%, css_content 0)은 10-13 에 정리했다: 손 검토에서 「인정」이 아닌 퍼센트 107건을 빼고 보충 75건을 더해 473건, 소프트 하이픈만 쓴 것은 238/306(77.8%), css_content 1건. 자세한 수치는 `통계_20261013.md`, 옛 판은 `이전판_20261012/`.
