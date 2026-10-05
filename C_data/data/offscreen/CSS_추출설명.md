# CSS 숨김 규칙 추출

공식 배포 패키지에서 읽은 선언의 `display:none`, `visibility:hidden/collapse`, `font-size:0–1px`, 큰 음수 좌표, 음수 text-indent, clip 및 clip-path 후보를 추출했습니다. focus 상태의 복원 규칙도 함께 보존합니다. **141개는 규칙 수이며 서로 다른 숨김 클래스 141개를 뜻하지 않습니다.** 같은 클래스의 버전별·반응형 규칙, ID·요소·가상요소·컴포넌트 선택자가 포함됩니다.

| 라이브러리 | 고정 버전 | 규칙 수 | 주요 규칙 |
|---|---|---:|---|
| Bootstrap | 5.3.8·4.6.2 | 90 | `.visually-hidden`, `.visually-hidden-focusable`, `.sr-only`, `.sr-only-focusable`, `.d-none`, `.d-*-none`, `.invisible`, 닫힌 collapse·dropdown·modal |
| Tailwind CSS | 3.4.17 | 5 | `.sr-only`, `.not-sr-only` 복원, `.hidden`, `.invisible`, `.collapse` |
| HTML5 Boilerplate의 main.css | 3.0.0 | 4 | `.hidden, [hidden]`, `.visually-hidden`, `.visually-hidden.focusable:active/:focus` 복원, `.invisible` |
| eGovFrame 공통컴포넌트 | 4.3.0 | 42 | `.hide`, `.blind`, `.invisible`, `caption`, `legend`, 파일 업로드·페이징·이미지 대체 텍스트 |

Bootstrap과 HTML5BP의 시각적 숨김은 화면 낭독기 접근성을 위한 정상 기능입니다. [Bootstrap 공식 설명](https://getbootstrap.com/docs/5.3/helpers/visually-hidden/)과 [Tailwind 공식 설명](https://tailwindcss.com/docs/display)을 확인했습니다. 현재 Tailwind 문서는 다른 주 버전일 수 있으므로 이 번들의 **실제 값은 3.4.17 소스**를 기준으로 합니다. HTML5BP 공식 홈페이지는 [main.css를 구성 요소로 안내](https://html5boilerplate.com/)합니다.

Bootstrap의 `.visually-hidden-focusable`은 focus/focus-within에 따라 복원됩니다. HTML5BP는 `.visually-hidden.focusable:active/:focus`에서 복원됩니다. Tailwind의 `.not-sr-only`는 숨김을 취소합니다. 반응형 `.d-md-none` 등은 @media 조건을 벗어나면 동일한 결과가 나오지 않습니다. 추출 JSON의 `at_context`와 `usable_css`는 조건을 보존합니다. `raw_css`는 중첩 조건 내부의 원문 규칙입니다.

전자정부에서 직접 확인한 예:

```css
caption span, .hide, legend { position:absolute; left:-1000%; top:0; }
.blind {position:absolute; left:-9999px; top:-9999px; font-size:0; }
.hide { text-indent:-99999em; }
```

첫 두 규칙은 `com.css`, 마지막 규칙은 `uss/ion/ntm/note_manage.css`의 원문입니다. 게시판 `cop/bbs/style.css`에는 `caption, .hide, .blind`의 display:none 및 caption/legend의 음수 좌표·text-indent·visibility:hidden 중첩이 있습니다. 이미지 대체 텍스트·표 caption은 정상 용도이므로 광고라는 근거가 아닙니다.

전자정부 CSS는 `com.css`, `com12.css`, `popup_com.css`, `button.css`, `cop/bbs/style.css`, `uss/ion/ntm/note_manage.css`, `cmm/left.css` 7개 파일을 읽었습니다. 번들에 들어 있는 jQuery UI·CKEditor 같은 외부 구성 요소는 이 추출 범위에서 제외했습니다. [공식 공통컴포넌트 배포 페이지](https://www.egovframe.go.kr/home/sub.do?menuNo=49)와 [공식 라이선스 페이지](https://www.egovframe.go.kr/home/sub.do?menuNo=23)를 출처로 기록했습니다.

Tailwind는 `package/src/corePlugins.js`의 정적 객체 5개를 추출했습니다. CSS의 camelCase 속성을 kebab-case로 옮긴 기계 변환이며 생성된 CSS와 원본 JS 행 번호는 `tailwind_source_map.json`에 대응시켰습니다. 정적 정의·원문은 보존했지만 Tailwind CLI 전체 빌드와 임의 값 유틸리티 생성은 수행하지 않았습니다.

clip-path·transform 조합은 이 고정 버전의 추출 결과에서 실제 원문 규칙으로 확인되지 않았습니다. 100개 카탈로그에서는 **변형 제안**으로 표시했습니다. font-size 1px와 viewport 밖 이동은 완전 비가시성과 같지 않으며, 스크롤·DPR·브라우저 설정 확인이 필요합니다. aria-hidden, pointer-events:none, overflow:hidden, zero width/height만으로 숨김을 단정하지 않았습니다.
