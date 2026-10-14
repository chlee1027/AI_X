# 사람 3 담당 데이터: OFFSCREEN (2026-10-14)

실제 원문 350건을 `../../offscreen/offscreen_originals.yaml`에 저장했습니다. ID는 OF-001~OF-350이며 모두 기존 11개 필드를 유지합니다. 최신 사람 3 최종 결과의 YAML과 바이트 단위로 동일합니다.

| ID 범위 | subtype | 건수 |
|---|---|---:|
| OF-001~OF-050 | `font_size_zero_or_tiny` | 50 |
| OF-051~OF-100 | `negative_text_indent` | 50 |
| OF-101~OF-150 | `clip_or_clip_path` | 50 |
| OF-151~OF-200 | `display_none` | 50 |
| OF-201~OF-250 | `negative_left` | 50 |
| OF-251~OF-300 | `transform_or_document_coordinates` | 50 |
| OF-301~OF-350 | `visibility_hidden` | 50 |

350건 모두 원문 CSS에 해당 subtype의 속성이 존재합니다. 여러 숨김 속성이 함께 쓰인 사례도 있으며, font-size 그룹 45건에는 음수 left가 함께 있습니다. `transform_or_document_coordinates` 50건은 모두 음수 좌표 이동이고 실제 transform 선언은 0건입니다.

공개 피해 보고서·과거 저장 원문도 포함하므로 현재 URL이 열리거나 모든 목적지가 현재 운영 중임을 뜻하지 않습니다. 불법 광고 양성 판정은 저장된 문맥과 근거를 바탕으로 한 수집자의 판단이며 법원의 확정 판단이 아닙니다. 광고 링크 전체가 아니라 접근성 설명 문구만 숨겨진 사례도 포함합니다.

원문 URL + 요소 위치 + 숨김 방식 조합으로 중복을 검사했고, 수집 출처군당 최대 15건을 유지했습니다. HTML·CSS·광고 문구·출처는 최종 결과와 동일하며 이 저장소 반영을 위해 수정하지 않았습니다.

이전 원문 100건을 350건으로 교체하고, 이전 파생 시험용 `offscreen.yaml`, 가시 대조군 `offscreen_controls.json`, 참고 사례 `reference_only.json`은 제거했습니다. 이전 100건·파생 자료를 설명하던 과거 문서 2개도 삭제했습니다. 이 폴더에는 현재 350건 안내와 검증 결과만 남겼습니다.

전체 원문·검수 근거·이전 ID 매핑·CSS/Unicode/라이선스·검증 자료는 [사람 3 최종 결과](https://github.com/dyhan2/ai-x_sample/tree/main/사람3_최종결과_350건)에 보존되어 있습니다.

## 검증 범위

최종 결과 YAML과의 바이트 동일성, 350개 연속 ID, 11개 필드, 7 subtype별 50건을 확인했습니다. 전체 패키지 검증은 원문·아티팩트 해시 등 모든 항목을 통과했습니다.

이 저장소의 `C_data/tools/validate.py`에서는 327건이 통과하고 OF-128~OF-150 23건이 선택자 매칭 0개로 실패했습니다. 이 23건은 `expected_location`이 원문 페이지의 상위 구조를 포함하지만 저장된 `html`은 그 구조를 생략한 발췌입니다. 발췌를 전체 문서로 파싱해도 0개로 나타납니다. 따라서 이 23건을 공통 검사기 통과 자료라고 해석하면 안 됩니다. 원문 보존 및 최종 결과와의 동일성을 위해 선택자를 임의로 수정하지 않았습니다. 세부 결과는 [350건_검증결과.json](350건_검증결과.json)에 기록했습니다.
