# 제3자 자료 출처·라이선스 — 사람 3 인계용 초안

확인일: 2026-10-04. 원본 파일은 `data/raw/`, 실제 사용한 Unicode 데이터는 `data/unicode/`, 라이선스 원문은 `licenses/`에 보관했습니다. 다운로드 URL·일시·크기·SHA-256은 [source_manifest.json](data/source_manifest.json)에, 추출한 CSS 파일의 해시는 [source_files.json](data/css/source_files.json)에 있습니다.

| 구성 요소 | 고정 버전 | 라이선스 | 포함한 라이선스 파일 |
|---|---|---|---|
| Bootstrap | 5.3.8 | MIT | [Bootstrap 5](licenses/Bootstrap-5.3.8-LICENSE.txt) |
| Bootstrap | 4.6.2 | MIT | [Bootstrap 4](licenses/Bootstrap-4.6.2-LICENSE.txt) |
| Tailwind CSS | 3.4.17 | MIT | [Tailwind](licenses/Tailwind-LICENSE.txt) |
| HTML5 Boilerplate main.css | 3.0.0 | MIT | [HTML5BP main.css](licenses/HTML5BP-main-LICENSE.txt) |
| 전자정부 공통컴포넌트 자체 CSS | 4.3.0 | Apache-2.0 | [배포 ZIP의 원문](licenses/eGovFrame-Apache-2.0.txt) |
| Unicode confusables·Scripts·IdentifierType | 17.0.0 | Unicode-3.0 | [Unicode License v3](licenses/Unicode-LICENSE.txt) |

Bootstrap 5의 원문 고지는 `2011–2025 The Bootstrap Authors`, Bootstrap 4는 `2011–2022 Twitter, Inc.`와 `2011–2022 The Bootstrap Authors`입니다. Tailwind는 Tailwind Labs, Inc., main.css는 HTML5 Boilerplate입니다. 실제 저작권·허락·면책 전문은 위 파일에 보존했습니다. 배포 패키지의 MIT 고지를 사용하며 사이트 문서의 라이선스로 대체하지 않습니다.

MIT 구성 요소를 재배포할 때는 저작권 고지와 허락 전문을 복사본 또는 중요한 부분에 함께 포함합니다. 발췌 CSS만 전달할 경우에도 이 문서와 해당 라이선스 파일을 함께 전달합니다.

전자정부 자체 소스는 [공식 라이선스 안내](https://www.egovframe.go.kr/home/sub.do?menuNo=23) 및 배포 ZIP의 `src/main/webapp/META-INF/license`에서 Apache 2.0을 확인했습니다. 복사한 원본은 수정하지 않았으며, 별도 발췌 파일에는 출처·규칙 ID를 추가했습니다. 카탈로그에서 선택자 변경·단위 변경·속성 분리·clip-path/transform 추가를 한 부분은 `proposed_variation_of_upstream_signal`로 표시했습니다. 재배포 시 Apache 2.0 전문과 관련 고지를 포함하고, 변경한 파일에는 변경 사실을 표시합니다. upstream NOTICE가 적용되는 자료를 추가하면 해당 고지도 함께 보존해야 합니다.

전자정부 ZIP 전체에는 별도 라이선스의 외부 오픈소스가 포함됩니다. 이 번들은 ZIP을 원문 보관용으로 유지하되 추출 범위를 문서에 명시한 자체 CSS 7개로 한정했습니다. **전체 ZIP의 모든 구성 요소를 Apache 2.0으로 분류하지 않습니다.** jQuery UI·CKEditor·아이콘·폰트·이미지를 프로젝트에 추가하려면 그 구성 요소의 원래 고지를 별도로 확인해야 합니다. 현재 발췌물에 폰트·이미지 바이너리는 포함하지 않았습니다.

Unicode는 [공식 데이터 파일 라이선스 정책](https://www.unicode.org/policies/licensing_policy.html)과 [Unicode License v3 전문](https://www.unicode.org/license.txt)을 확인했습니다. [공식 FAQ](https://www.unicode.org/faq/unicode_license.html)는 SPDX 식별자를 `Unicode-3.0`으로 안내합니다. 세 파일 헤더의 2025 Unicode 고지를 보존했고, 다운로드한 라이선스 전문에는 1991–2026 Unicode, Inc. 고지가 있습니다. 데이터 복사본 또는 동봉 문서에 저작권·허락 고지를 포함합니다. **Unicode-3.0은 라이선스 이름이며 데이터 버전 3.0을 뜻하지 않습니다.** 이 번들의 데이터 버전은 17.0.0입니다.

eGovFrame 위키 문서의 CC BY-NC-SA 안내는 코드 라이선스와 구분합니다. 이 번들은 위키 본문이나 기술 보고서 전문을 재배포하지 않으며, 설명은 직접 작성하고 원문 링크를 제공합니다.

배포 파일의 출처:

- [Bootstrap 5.3.8 공식 npm 패키지](https://registry.npmjs.org/bootstrap/-/bootstrap-5.3.8.tgz)
- [Bootstrap 4.6.2 공식 npm 패키지](https://registry.npmjs.org/bootstrap/-/bootstrap-4.6.2.tgz)
- [Tailwind 3.4.17 공식 npm 패키지](https://registry.npmjs.org/tailwindcss/-/tailwindcss-3.4.17.tgz)
- [HTML5BP main.css 3.0.0 공식 npm 패키지](https://registry.npmjs.org/main.css/-/main.css-3.0.0.tgz)
- [전자정부 공통컴포넌트 공식 다운로드](https://www.egovframe.go.kr/home/sub.do?menuNo=49) — `egovframework-all-in-oneAllNew-4.3.0.zip`, 공개 SHA-1 `B7B387E6FCAE443D8BCB8F92C1AAE9766565D0E8`. 실제 첨부 URL은 세션에 따라 바뀌므로 재다운로드 스크립트가 공개 페이지에서 다시 읽습니다.
- [Unicode 17.0.0 security 공식 디렉터리](https://www.unicode.org/Public/17.0.0/security/), [UCD 디렉터리](https://www.unicode.org/Public/17.0.0/ucd/)

최종 인계 패키지(2026-10-05)는 라이브러리의 실제 사용한 CSS 및 Tailwind corePlugins.js 원문, Unicode 데이터, 라이선스와 발췌 규칙을 포함합니다. 다운로드 아카이브 전체 및 기사 전체 원문은 포함하지 않습니다. source_manifest.json의 다운로드 아카이브 해시는 작업용 원본 보관 위치의 해시입니다. 시험용 선택자/값/마크업의 변경은 각 시험용 레코드에 표시했습니다.
