# OFFSCREEN 변형 조합 100개 검수 계획

100개는 변형·검수 계획이며 광고 positive 데이터 100개가 아닙니다. 가시 대조군이 포함되어 있어 최종 쿼터 충족에는 대체 수집이 필요할 수 있습니다.

| 구간 | 유형 | 배정 |
|---|---|---|
| V001–V015 | font-size 0–1px | 15 |
| V016–V030 | left 음수 | 15 |
| V031–V045 | display:none | 15 |
| V046–V060 | visibility:hidden | 15 |
| V061–V075 | clip·clip-path | 15 |
| V076–V085 | text-indent | 10 |
| V086–V100 | transform·문서 밖 좌표 | 15 |

V001–V045는 PDF의 요강 3종 합계 45개를 배정했습니다. 원본에서 발견하지 못한 속성은 변형 제안으로 표시했습니다.

| ID | 유형 | 조합 | 원본 규칙 | 검수 조건 |
|---|---|---|---|---|
| OF-V001 | font_size_0_1px | span / font-size:0 | CSS-117 | 상속·자손 font-size 재설정·최소 글꼴 크기·DPR 확인. 1px가 항상 완전히 안 보이는 것은 아님. |
| OF-V002 | font_size_0_1px | span / font-size:0.25px | CSS-117 | 상속·자손 font-size 재설정·최소 글꼴 크기·DPR 확인. 1px가 항상 완전히 안 보이는 것은 아님. |
| OF-V003 | font_size_0_1px | span / font-size:0.5px | CSS-117 | 상속·자손 font-size 재설정·최소 글꼴 크기·DPR 확인. 1px가 항상 완전히 안 보이는 것은 아님. |
| OF-V004 | font_size_0_1px | span / font-size:0.75px | CSS-117 | 상속·자손 font-size 재설정·최소 글꼴 크기·DPR 확인. 1px가 항상 완전히 안 보이는 것은 아님. |
| OF-V005 | font_size_0_1px | span / font-size:1px | CSS-117 | 상속·자손 font-size 재설정·최소 글꼴 크기·DPR 확인. 1px가 항상 완전히 안 보이는 것은 아님. |
| OF-V006 | font_size_0_1px | div / font-size:0 | CSS-117 | 상속·자손 font-size 재설정·최소 글꼴 크기·DPR 확인. 1px가 항상 완전히 안 보이는 것은 아님. |
| OF-V007 | font_size_0_1px | div / font-size:0.25px | CSS-117 | 상속·자손 font-size 재설정·최소 글꼴 크기·DPR 확인. 1px가 항상 완전히 안 보이는 것은 아님. |
| OF-V008 | font_size_0_1px | div / font-size:0.5px | CSS-117 | 상속·자손 font-size 재설정·최소 글꼴 크기·DPR 확인. 1px가 항상 완전히 안 보이는 것은 아님. |
| OF-V009 | font_size_0_1px | div / font-size:0.75px | CSS-117 | 상속·자손 font-size 재설정·최소 글꼴 크기·DPR 확인. 1px가 항상 완전히 안 보이는 것은 아님. |
| OF-V010 | font_size_0_1px | div / font-size:1px | CSS-117 | 상속·자손 font-size 재설정·최소 글꼴 크기·DPR 확인. 1px가 항상 완전히 안 보이는 것은 아님. |
| OF-V011 | font_size_0_1px | a / font-size:0 | CSS-117 | 상속·자손 font-size 재설정·최소 글꼴 크기·DPR 확인. 1px가 항상 완전히 안 보이는 것은 아님. |
| OF-V012 | font_size_0_1px | a / font-size:0.25px | CSS-117 | 상속·자손 font-size 재설정·최소 글꼴 크기·DPR 확인. 1px가 항상 완전히 안 보이는 것은 아님. |
| OF-V013 | font_size_0_1px | a / font-size:0.5px | CSS-117 | 상속·자손 font-size 재설정·최소 글꼴 크기·DPR 확인. 1px가 항상 완전히 안 보이는 것은 아님. |
| OF-V014 | font_size_0_1px | a / font-size:0.75px | CSS-117 | 상속·자손 font-size 재설정·최소 글꼴 크기·DPR 확인. 1px가 항상 완전히 안 보이는 것은 아님. |
| OF-V015 | font_size_0_1px | a / font-size:1px | CSS-117 | 상속·자손 font-size 재설정·최소 글꼴 크기·DPR 확인. 1px가 항상 완전히 안 보이는 것은 아님. |
| OF-V016 | left_negative | absolute / left:-9999px | CSS-117 | position:static이면 left가 작동하지 않음. containing block·스크롤·viewport 확인. |
| OF-V017 | left_negative | absolute / left:-10000px | CSS-117 | position:static이면 left가 작동하지 않음. containing block·스크롤·viewport 확인. |
| OF-V018 | left_negative | absolute / left:-9999em | CSS-117 | position:static이면 left가 작동하지 않음. containing block·스크롤·viewport 확인. |
| OF-V019 | left_negative | absolute / left:-1000% | CSS-117 | position:static이면 left가 작동하지 않음. containing block·스크롤·viewport 확인. |
| OF-V020 | left_negative | absolute / left:calc(-1 * 10000px) | CSS-117 | position:static이면 left가 작동하지 않음. containing block·스크롤·viewport 확인. |
| OF-V021 | left_negative | fixed / left:-9999px | CSS-117 | position:static이면 left가 작동하지 않음. containing block·스크롤·viewport 확인. |
| OF-V022 | left_negative | fixed / left:-10000px | CSS-117 | position:static이면 left가 작동하지 않음. containing block·스크롤·viewport 확인. |
| OF-V023 | left_negative | fixed / left:-9999em | CSS-117 | position:static이면 left가 작동하지 않음. containing block·스크롤·viewport 확인. |
| OF-V024 | left_negative | fixed / left:-1000% | CSS-117 | position:static이면 left가 작동하지 않음. containing block·스크롤·viewport 확인. |
| OF-V025 | left_negative | fixed / left:calc(-1 * 10000px) | CSS-117 | position:static이면 left가 작동하지 않음. containing block·스크롤·viewport 확인. |
| OF-V026 | left_negative | relative / left:-9999px | CSS-117 | position:static이면 left가 작동하지 않음. containing block·스크롤·viewport 확인. |
| OF-V027 | left_negative | relative / left:-10000px | CSS-117 | position:static이면 left가 작동하지 않음. containing block·스크롤·viewport 확인. |
| OF-V028 | left_negative | relative / left:-9999em | CSS-117 | position:static이면 left가 작동하지 않음. containing block·스크롤·viewport 확인. |
| OF-V029 | left_negative | relative / left:-1000% | CSS-117 | position:static이면 left가 작동하지 않음. containing block·스크롤·viewport 확인. |
| OF-V030 | left_negative | relative / left:calc(-1 * 10000px) | CSS-117 | position:static이면 left가 작동하지 않음. containing block·스크롤·viewport 확인. |
| OF-V031 | display_none | Bootstrap 5.3.8 / self | CSS-047 | 원본 CSS 적용. display:none인 조상 아래 최심부 텍스트 위치를 라벨링. |
| OF-V032 | display_none | Bootstrap 5.3.8 / parent | CSS-047 | 원본 CSS 적용. display:none인 조상 아래 최심부 텍스트 위치를 라벨링. |
| OF-V033 | display_none | Bootstrap 5.3.8 / grandparent | CSS-047 | 원본 CSS 적용. display:none인 조상 아래 최심부 텍스트 위치를 라벨링. |
| OF-V034 | display_none | Bootstrap 4.6.2 / self | CSS-081 | 원본 CSS 적용. display:none인 조상 아래 최심부 텍스트 위치를 라벨링. |
| OF-V035 | display_none | Bootstrap 4.6.2 / parent | CSS-081 | 원본 CSS 적용. display:none인 조상 아래 최심부 텍스트 위치를 라벨링. |
| OF-V036 | display_none | Bootstrap 4.6.2 / grandparent | CSS-081 | 원본 CSS 적용. display:none인 조상 아래 최심부 텍스트 위치를 라벨링. |
| OF-V037 | display_none | HTML5 Boilerplate main.css 3.0.0 / self | CSS-091 | 원본 CSS 적용. display:none인 조상 아래 최심부 텍스트 위치를 라벨링. |
| OF-V038 | display_none | HTML5 Boilerplate main.css 3.0.0 / parent | CSS-091 | 원본 CSS 적용. display:none인 조상 아래 최심부 텍스트 위치를 라벨링. |
| OF-V039 | display_none | HTML5 Boilerplate main.css 3.0.0 / grandparent | CSS-091 | 원본 CSS 적용. display:none인 조상 아래 최심부 텍스트 위치를 라벨링. |
| OF-V040 | display_none | Tailwind CSS (static map conversion) 3.4.17 / self | CSS-097 | 원본 CSS 적용. display:none인 조상 아래 최심부 텍스트 위치를 라벨링. |
| OF-V041 | display_none | Tailwind CSS (static map conversion) 3.4.17 / parent | CSS-097 | 원본 CSS 적용. display:none인 조상 아래 최심부 텍스트 위치를 라벨링. |
| OF-V042 | display_none | Tailwind CSS (static map conversion) 3.4.17 / grandparent | CSS-097 | 원본 CSS 적용. display:none인 조상 아래 최심부 텍스트 위치를 라벨링. |
| OF-V043 | display_none | eGovFrame common components 4.3.0 / self | CSS-135 | 원본 CSS 적용. display:none인 조상 아래 최심부 텍스트 위치를 라벨링. |
| OF-V044 | display_none | eGovFrame common components 4.3.0 / parent | CSS-135 | 원본 CSS 적용. display:none인 조상 아래 최심부 텍스트 위치를 라벨링. |
| OF-V045 | display_none | eGovFrame common components 4.3.0 / grandparent | CSS-135 | 원본 CSS 적용. display:none인 조상 아래 최심부 텍스트 위치를 라벨링. |
| OF-V046 | visibility_hidden | Bootstrap / self | CSS-048 | 레이아웃 공간은 유지. 자손 visibility:visible 재설정 여부 확인. |
| OF-V047 | visibility_hidden | Bootstrap / parent | CSS-048 | 레이아웃 공간은 유지. 자손 visibility:visible 재설정 여부 확인. |
| OF-V048 | visibility_hidden | Bootstrap / grandparent | CSS-048 | 레이아웃 공간은 유지. 자손 visibility:visible 재설정 여부 확인. |
| OF-V049 | visibility_hidden | Bootstrap / 조상 hidden·자손 visible | CSS-048 | 자손 visible은 정상 가시 대조군. positive 쿼터에 자동 포함 금지. |
| OF-V050 | visibility_hidden | Bootstrap / hidden·높이 확보 | CSS-048 | 높이가 있는 부모에서도 hidden은 유지되는지 확인. |
| OF-V051 | visibility_hidden | HTML5 Boilerplate main.css / self | CSS-094 | 레이아웃 공간은 유지. 자손 visibility:visible 재설정 여부 확인. |
| OF-V052 | visibility_hidden | HTML5 Boilerplate main.css / parent | CSS-094 | 레이아웃 공간은 유지. 자손 visibility:visible 재설정 여부 확인. |
| OF-V053 | visibility_hidden | HTML5 Boilerplate main.css / grandparent | CSS-094 | 레이아웃 공간은 유지. 자손 visibility:visible 재설정 여부 확인. |
| OF-V054 | visibility_hidden | HTML5 Boilerplate main.css / 조상 hidden·자손 visible | CSS-094 | 자손 visible은 정상 가시 대조군. positive 쿼터에 자동 포함 금지. |
| OF-V055 | visibility_hidden | HTML5 Boilerplate main.css / hidden·높이 확보 | CSS-094 | 높이가 있는 부모에서도 hidden은 유지되는지 확인. |
| OF-V056 | visibility_hidden | Tailwind CSS (static map conversion) / self | CSS-098 | 레이아웃 공간은 유지. 자손 visibility:visible 재설정 여부 확인. |
| OF-V057 | visibility_hidden | Tailwind CSS (static map conversion) / parent | CSS-098 | 레이아웃 공간은 유지. 자손 visibility:visible 재설정 여부 확인. |
| OF-V058 | visibility_hidden | Tailwind CSS (static map conversion) / grandparent | CSS-098 | 레이아웃 공간은 유지. 자손 visibility:visible 재설정 여부 확인. |
| OF-V059 | visibility_hidden | Tailwind CSS (static map conversion) / 조상 hidden·자손 visible | CSS-098 | 자손 visible은 정상 가시 대조군. positive 쿼터에 자동 포함 금지. |
| OF-V060 | visibility_hidden | Tailwind CSS (static map conversion) / hidden·높이 확보 | CSS-098 | 높이가 있는 부모에서도 hidden은 유지되는지 확인. |
| OF-V061 | clip_clip_path | Bootstrap / 원본 | CSS-044, CSS-045, CSS-046 |  |
| OF-V062 | clip_clip_path | Bootstrap / 자손 텍스트 | CSS-044, CSS-045, CSS-046 |  |
| OF-V063 | clip_clip_path | Bootstrap / 링크 | CSS-044, CSS-045, CSS-046 | Tab focus 시에도 이 클래스만으로는 자동 복원되지 않음. focusable 변형과 구별. |
| OF-V064 | clip_clip_path | Bootstrap / clip-path:inset(50%) | CSS-044 | 원본 CSS에 없는 clip-path 변형 제안. 렌더링 필요. |
| OF-V065 | clip_clip_path | Bootstrap / clip-path:circle(0) | CSS-044 | 원본 CSS에 없는 clip-path 변형 제안. 렌더링 필요. |
| OF-V066 | clip_clip_path | HTML5 Boilerplate main.css / 원본 | CSS-092 |  |
| OF-V067 | clip_clip_path | HTML5 Boilerplate main.css / 자손 텍스트 | CSS-092 |  |
| OF-V068 | clip_clip_path | HTML5 Boilerplate main.css / 링크 | CSS-092 | Tab focus 시에도 이 클래스만으로는 자동 복원되지 않음. focusable 변형과 구별. |
| OF-V069 | clip_clip_path | HTML5 Boilerplate main.css / clip-path:inset(50%) | CSS-092 | 원본 CSS에 없는 clip-path 변형 제안. 렌더링 필요. |
| OF-V070 | clip_clip_path | HTML5 Boilerplate main.css / clip-path:circle(0) | CSS-092 | 원본 CSS에 없는 clip-path 변형 제안. 렌더링 필요. |
| OF-V071 | clip_clip_path | Tailwind CSS (static map conversion) / 원본 | CSS-095 |  |
| OF-V072 | clip_clip_path | Tailwind CSS (static map conversion) / 자손 텍스트 | CSS-095 |  |
| OF-V073 | clip_clip_path | Tailwind CSS (static map conversion) / 링크 | CSS-095 | Tab focus 시에도 이 클래스만으로는 자동 복원되지 않음. focusable 변형과 구별. |
| OF-V074 | clip_clip_path | Tailwind CSS (static map conversion) / clip-path:inset(50%) | CSS-095 | 원본 CSS에 없는 clip-path 변형 제안. 렌더링 필요. |
| OF-V075 | clip_clip_path | Tailwind CSS (static map conversion) / clip-path:circle(0) | CSS-095 | 원본 CSS에 없는 clip-path 변형 제안. 렌더링 필요. |
| OF-V076 | text_indent | block / text-indent:-99999em | CSS-140 | 들여쓰기는 첫 줄에 적용. white-space·줄바꿈·블록 폭을 함께 확인. 이미지 대체 텍스트는 정상 용도 가능. |
| OF-V077 | text_indent | block / text-indent:-9999px | CSS-140 | 들여쓰기는 첫 줄에 적용. white-space·줄바꿈·블록 폭을 함께 확인. 이미지 대체 텍스트는 정상 용도 가능. |
| OF-V078 | text_indent | block / text-indent:-10000em | CSS-140 | 들여쓰기는 첫 줄에 적용. white-space·줄바꿈·블록 폭을 함께 확인. 이미지 대체 텍스트는 정상 용도 가능. |
| OF-V079 | text_indent | block / text-indent:-1000% | CSS-140 | 들여쓰기는 첫 줄에 적용. white-space·줄바꿈·블록 폭을 함께 확인. 이미지 대체 텍스트는 정상 용도 가능. |
| OF-V080 | text_indent | block / text-indent:-100vw | CSS-140 | 들여쓰기는 첫 줄에 적용. white-space·줄바꿈·블록 폭을 함께 확인. 이미지 대체 텍스트는 정상 용도 가능. |
| OF-V081 | text_indent | inline-block / text-indent:-99999em | CSS-140 | 들여쓰기는 첫 줄에 적용. white-space·줄바꿈·블록 폭을 함께 확인. 이미지 대체 텍스트는 정상 용도 가능. |
| OF-V082 | text_indent | inline-block / text-indent:-9999px | CSS-140 | 들여쓰기는 첫 줄에 적용. white-space·줄바꿈·블록 폭을 함께 확인. 이미지 대체 텍스트는 정상 용도 가능. |
| OF-V083 | text_indent | inline-block / text-indent:-10000em | CSS-140 | 들여쓰기는 첫 줄에 적용. white-space·줄바꿈·블록 폭을 함께 확인. 이미지 대체 텍스트는 정상 용도 가능. |
| OF-V084 | text_indent | inline-block / text-indent:-1000% | CSS-140 | 들여쓰기는 첫 줄에 적용. white-space·줄바꿈·블록 폭을 함께 확인. 이미지 대체 텍스트는 정상 용도 가능. |
| OF-V085 | text_indent | inline-block / text-indent:-100vw | CSS-140 | 들여쓰기는 첫 줄에 적용. white-space·줄바꿈·블록 폭을 함께 확인. 이미지 대체 텍스트는 정상 용도 가능. |
| OF-V086 | transform_document_coords | translateX(-10000px) | CSS-117 | 원본 라이브러리에서 확인한 transform 규칙 아님. %는 자기 크기 기준. 양수 이동은 스크롤로 보일 수 있으므로 문서·viewport를 구분. |
| OF-V087 | transform_document_coords | translateY(-10000px) | CSS-117 | 원본 라이브러리에서 확인한 transform 규칙 아님. %는 자기 크기 기준. 양수 이동은 스크롤로 보일 수 있으므로 문서·viewport를 구분. |
| OF-V088 | transform_document_coords | translate(-10000px,-10000px) | CSS-117 | 원본 라이브러리에서 확인한 transform 규칙 아님. %는 자기 크기 기준. 양수 이동은 스크롤로 보일 수 있으므로 문서·viewport를 구분. |
| OF-V089 | transform_document_coords | translateX(10000px) | CSS-117 | 원본 라이브러리에서 확인한 transform 규칙 아님. %는 자기 크기 기준. 양수 이동은 스크롤로 보일 수 있으므로 문서·viewport를 구분. |
| OF-V090 | transform_document_coords | translateY(10000px) | CSS-117 | 원본 라이브러리에서 확인한 transform 규칙 아님. %는 자기 크기 기준. 양수 이동은 스크롤로 보일 수 있으므로 문서·viewport를 구분. |
| OF-V091 | transform_document_coords | translate3d(-10000px,0,0) | CSS-117 | 원본 라이브러리에서 확인한 transform 규칙 아님. %는 자기 크기 기준. 양수 이동은 스크롤로 보일 수 있으므로 문서·viewport를 구분. |
| OF-V092 | transform_document_coords | matrix(1,0,0,1,-10000,0) | CSS-117 | 원본 라이브러리에서 확인한 transform 규칙 아님. %는 자기 크기 기준. 양수 이동은 스크롤로 보일 수 있으므로 문서·viewport를 구분. |
| OF-V093 | transform_document_coords | translateX(calc(-1 * 10000px)) | CSS-117 | 원본 라이브러리에서 확인한 transform 규칙 아님. %는 자기 크기 기준. 양수 이동은 스크롤로 보일 수 있으므로 문서·viewport를 구분. |
| OF-V094 | transform_document_coords | translateX(-1000%) | CSS-117 | 원본 라이브러리에서 확인한 transform 규칙 아님. %는 자기 크기 기준. 양수 이동은 스크롤로 보일 수 있으므로 문서·viewport를 구분. |
| OF-V095 | transform_document_coords | translateY(-1000%) | CSS-117 | 원본 라이브러리에서 확인한 transform 규칙 아님. %는 자기 크기 기준. 양수 이동은 스크롤로 보일 수 있으므로 문서·viewport를 구분. |
| OF-V096 | transform_document_coords | absolute / top:-9000em;left:0; | CSS-134 | 문서 밖 좌표 제안. right/bottom·양수 범위는 스크롤·부모 클리핑 확인. |
| OF-V097 | transform_document_coords | absolute / top:0;left:-9000em; | CSS-134 | 문서 밖 좌표 제안. right/bottom·양수 범위는 스크롤·부모 클리핑 확인. |
| OF-V098 | transform_document_coords | absolute / top:-9999px;left:-9999px; | CSS-134 | 문서 밖 좌표 제안. right/bottom·양수 범위는 스크롤·부모 클리핑 확인. |
| OF-V099 | transform_document_coords | absolute / right:-10000px;top:0; | CSS-134 | 문서 밖 좌표 제안. right/bottom·양수 범위는 스크롤·부모 클리핑 확인. |
| OF-V100 | transform_document_coords | absolute / bottom:-10000px;left:0; | CSS-134 | 문서 밖 좌표 제안. right/bottom·양수 범위는 스크롤·부모 클리핑 확인. |
