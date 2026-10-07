# 공공 웹사이트 불법광고 탐지 도구 공모전 — 역할 C(데이터·평가) 작업 공간

행정안전부·NIA 「공공 웹사이트 불법광고 탐지 도구 개발 공모전」(접수 마감 2026-10-23 18시)의 데이터·평가 몫이다. 요강 원문은 `공공 웹사이트 불법광고 탐지 도구 개발 공모전 모집요강.pdf`(18쪽), 팀 설계는 `총계획서_최종_공공웹사이트_불법광고_탐지도구.md` 이다.

## DECOY · ETC · 난독화 조합 · JAMO · OFFSCREEN · 사전 — 실측 수집 결과

수집일 2026-10-03(토)~10-05(월). 10-04 에 DECOY·ETC 를 200개로, 조합을 250개로 늘렸다. DECOY·ETC·조합은 사람 1(역할 C) 담당분이다. JAMO·사전은 사람 4 담당분을 10-05 에 역할 C 가 점검·수정해 넣었고, 10-06 에 사람 4 추가분 JAMO 5건을 붙였다. OFFSCREEN 은 사람 3 담당분을 10-05 에 역할 C 가 점검·수정하고 10-06 에 visibility_hidden 원문 7개를 보충해 넣었다(`data/offscreen/`).

**사람 1 의 DECOY·ETC·조합 샘플과 그 수집·생성·선별 로직(`tools/`)은 탐지기(B) 담당에게 공개하지 않는다.** B 는 채점기 점수만 본다. JAMO 샘플과 사전(`data/lexicon/seed.yaml`)은 정규화·탐지에 쓰는 재료라 B 가 써도 된다(데이터 수집 계획 「정보 차단」 규칙 범위).

**샘플 파일(decoy·etc·combo_real·jamo)과 OFFSCREEN 원문 100개는 모두 실제 웹페이지나 피해 코드 공개 자료에서 찾아 잘라 낸 것이다.** 생성 데이터는 별도로 만든다. OFFSCREEN 의 CSS 시험용 100개만은 실측 광고 문구에 라이브러리 숨김 CSS 를 건 파생 자료이고, 원문 개수에 더하지 않는다. 사전의 어휘도 모두 실측 원문이나 규제기관 문서에서 확인한 것이다.

## 결과

| 파일 | 개수 | 구성 | 검증 |
|---|---|---|---|
| `data/samples/decoy.yaml` | **200** | a11y_sr_only 80 · hidden_menu 60 · policy_text 30 · risky_word_normal 30 | 오류 0. 53개 기관·업체 사이트 실측 |
| `data/samples/etc.yaml` | **220** | zero_width 99 · link_cloaking 41 · encoding 60(URL 퍼센트 40 · 숫자 엔티티 20) · meta_cloaking 20 · css_content 0 | 오류 0. 51개 사이트. css_content 만 쿼터(20)에 못 미친다. 10-06 중복 정리(아래 「10-06 중복 정리」), 10-07 숫자 엔티티 20 덧붙임(ET-210~229, 아래 「10-07 숫자 엔티티」) |
| `data/samples/combo_real.yaml` | **250** | 한 요소에 회피 수법 2~5개가 겹친 실제 광고 | 오류 0. 44개 사이트. 194번부터는 「안 쏠리게」 규칙으로 덧붙인 것(아래 「덧붙이기」), CB-251~258 은 10-06 중복 정리로 채운 것 |
| `data/samples/jamo.yaml` | **147** | 사람 4 몫 JAMO 실측 (compat_full 17 · partial_mix 58 · conjoining_u1100 20 · mixed_technique 52) | 2026-10-05 역할 C 점검·수정, 10-06 사람 4 추가분 5건(JM-143~147). `data/JAMO_LEXICON_변경요약_20261005.md` 참고 |
| `data/offscreen/data/originals/offscreen_originals.yaml` | **100** | 사람 3 몫 OFFSCREEN 광고 원문 (font_left_display 45 · visibility_hidden 15 · clip 15 · text_indent 10 · transform_outside 15) | 계획서 쿼터 충족. 100개 모두 html·css 만 띄워 숨김 확인(`tools/validate/check_offscreen.py`). `data/offscreen/변경요약_20261005.md` 참고 |
| `data/offscreen/data/samples/offscreen.yaml` | **100** + 대조군 7 | 위 원문 문구에 Bootstrap·Tailwind·HTML5BP·전자정부 숨김 CSS 를 건 시험용(분류별 개수 원문과 같음), 보여야 하는 대조군 7 | 시험용 100 숨김 · 대조군 7 보임 확인. 화면은 `data/offscreen/fixtures/` |
| `data/homoglyph/homoglyph_real_test_capped.yaml` | **370** (전체판 1,777) | 사람 2 몫 HOMOGLYPH 실측, 캠페인당 최대 5건 (digit_letter 103 · enclosed_alnum 76 · fullwidth 50 · hangul_lookalike 48 · fullwidth_symbol 45 · partial_token 29 · cyrillic_greek 19) | 2026-10-06 역할 C 점검·수정(번호 가림 1 · 라벨 5 · 중복 4 · 키릴 실측 보충 4). 키릴·그리스는 쿼터 25 에 6 모자라고 19 로 둔다. `data/homoglyph/README.md` 참고 |
| `data/lexicon/seed.yaml` | **624** | 사람 4 몫 사전: gambling_core·lure·contact·adult 각 100, whitelist 130, gambling_weak 94 | 모두 `reviewed: true`. 바뀐 401개 목록 `data/lexicon/review_20261005.csv` |

검증 명령은 아래 둘이다.
- `python tools/validate/validate_samples.py data/samples/decoy.yaml data/samples/etc.yaml`
- `python tools/validate/validate_combo.py data/samples/combo_real.yaml`
- `python tools/validate/validate_homoglyph.py data/homoglyph/homoglyph_real_test.yaml data/homoglyph/homoglyph_real_test_capped.yaml`
- `python tools/validate/check_offscreen.py data/offscreen/data/originals/offscreen_originals.yaml out.json` (시험용·대조군도 같은 명령에 파일만 바꿈)

**ETC 하위 유형 비율이 쿼터와 다른 이유.** 실제 웹에 있는 비율이 그렇다. 받은 원문 2,654페이지와 그 사이트들의 자체 CSS 파일 621개를 전부 훑은 결과다. 쿼터를 맞추려고 생성분을 섞지 않았다.
- **zero_width 가 많은 이유:** 「KC7979.COM」 업자 캠페인이 `토­토`, `카­지노`, `먹­튀`처럼 음절마다 소프트 하이픈을 넣은 글을 여러 사이트에 대량으로 올리고 있기 때문이다.
- **css_content:** 0건. `::before/::after` 로 광고를 넣은 실사례가 없었다.
  - 페이지 안 style 과 사이트 자체 CSS 파일 621개를 모두 훑었다. content 에 한글이 든 규칙 137건은 전부 「학점」·「새창」·「작성자」 같은 화면 라벨이었다.
- **encoding:** 60건. 40건은 **URL 퍼센트 인코딩**(아래), 20건은 10-07 에 덧붙인 **숫자 엔티티**(아래 「10-07 숫자 엔티티」)다. base64 실사례는 0건이다(base64 로 잡힌 것은 모두 아임웹 사이트 설정 JSON).

  > 10-03~10-06 판에는 「숫자 엔티티·base64 실사례 0건」으로 적었다. 숫자 엔티티는 우리가 받은 원문(국내 게시판 위주)에서 0건이었던 것이고, 10-07 에 HTML 소스 검색 엔진으로 해외 페이지를 찾아 20건을 넣었다.
  - 형태: 화면 앵커는 「신용회복가망바로가기」인데 href 는 무관한 외부 사이트의 검색 주소이고, 검색어 자리에 `%E2%82%B1%EB%8C%80%EC%B6%9C…` 처럼 인코딩된 광고 문구(「대출연체디비 토토디비판매사이트」, `@FUTIN888`)가 들어 있다.
  - 요강의 encoding 예시(엔티티·Base64)와 수법이 다르므로 팀이 이 하위 유형으로 인정할지 확인이 필요하다(아래 「결정이 필요한 것」). 인정하지 않아도 숫자 엔티티 20건은 남는다.
  - 10-04 에 `tools/analyze/scan_encoding.py` 로 원문 2,654쪽을 다시 훑었다. 속성 안 Base64(`go.php?url=aHR0c…` 꼴)·숫자 엔티티는 0건, 스크립트 안 Base64 237건은 전부 사이트 설정 JSON, `\u` 이스케이프 30,351건은 전부 아임웹이 글 데이터를 저장한 형식이었다(26,141건은 같은 문구가 화면에도 보인다. 나머지 4,210건도 모두 아임웹 페이지의 스크립트 데이터다).

## 무엇이 들어 있나

### DECOY 200
- **a11y_sr_only·hidden_menu:**
  - `tools/collect/dump_hidden.py` 가 사이트를 polite 모드로 렌더링했다. 1차 30곳(정부·지자체·규제기관·대학·은행·서점)에 10-04 에 35곳(부처·광역시·공기업·대학·병원·은행·서점·방송)을 더했다.
  - 숨김 텍스트 요소와 그 요소에 실제로 적용된 CSS 규칙을 함께 덤프했다.
  - `tools/build/build_decoy.py` 가 조상 3단만 잘랐고, 그 조각과 규칙만으로 숨김이 재현되는 것만 남겼다.
  - `tools/build/select_decoy.py` 가 기관을 돌아가며 골랐다. a11y 숨김 기법은 clip 28 · font-size 22 · 오프셋 15 · text-indent 8 · 1px 7 이다. 건너뛰기 링크는 6개로 제한했다.
- **policy_text·risky_word_normal:** 사감위·생활법령·교육청·관세청·복지로·지역화폐·서점 공지 등의 실제 본문이다. 후보 136개를 읽고 뜻으로 30개씩 골랐다. 「①」·「출처」·첨부파일명 같은 조각과 이미 고른 것과 같은 조문은 뺐다.
- 100개 판은 `data/raw/decoy/decoy_100_backup.yaml` 에 있다. 앞 100개의 선택 번호는 그대로이고 뒤에 덧붙였다.

### ETC 220

| 하위 유형 | 출처 | 실제 형태 |
|---|---|---|
| zero_width 42 | 「KC7979.COM」 캠페인과 같은 계열: 황비·HB투어리조트·C&P그룹·세계스피드공기협회(wsgga) | 음절마다 소프트 하이픈(U+00AD): `토­토`, `카­지노`, `먹­튀`, `주­소`, `도­메인`, `홀­덤game` |
| zero_width 31 | 비엔웍스 쇼핑몰, 영테크(아임웹), 지니몬테소리 | 소프트 하이픈: `바­카라사이트디시`, `인디언슬­롯게임`, `웹홀­덤­사이트` |
| zero_width 20 | 의약품 스팸: kmc1958·피자브라더스·쿠마·smh-hospital | `비­아그라`, `시­알리스`, `레­비트라`, `클­릭­이­동`, 레비트라 광고 앞 U+200C, 이성만남 광고 앞 U+200E |
| zero_width 2 | 하우스코디 자료실 (성매매 광고) | `콜걸은​수년간`(U+200B) + 변형 전화번호 |
| zero_width 1 | 부발지역아동센터 | `카­지노game`, `토­토사이트` |
| zero_width 3 | 공감오래(gonggam.zieo.net) 게시판 | 토토 광고 문구 안의 제로폭·소프트 하이픈 |
| link_cloaking 4 | 해킹된 대학 도메인 도어웨이 (중앙대 contil·germania, 창원대, 충북보건과학대) | 「로그인」「회원가입」 → `wwnnh.com/gate`, `bit.ly/…`, `*.pages.dev` |
| link_cloaking 2 | 연세대 대학원 총학생회 게시판 | 「공식 파트너」「바로가입」 → 한글 도메인의 퓨니코드 주소 `xn--…` |
| link_cloaking 28 | 아임웹 기업·단체 사이트 14곳의 같은 캠페인(@NAD258). 사이트마다 앵커 둘 | 「접속 불가 시 클릭」·「지금 바로 시작하기」 → `qkc709.com/?ac=…` |
| link_cloaking 6 | 인시스템즈·테너지먼트·피자브라더스 | 「지금 가입하기」→`qb-700.com`, 「링크 이동」→`dtbn1818.com`, 「사이트 입장」·「바로가기」→한글 퓨니코드 도메인 |
| encoding 25 | uisp.ikw.ac.kr·jnbburi.or.kr·ypcd.or.kr·kusta.or.kr·dspremiumlounge.com 게시판 스팸 (@FUTIN888 디비 판매) | 앵커 「신용회복가망바로가기」, href 는 `…/search?q=%E2%82%B1%EB%8C%80%EC%B6%9C…` → 디코딩하면 「₱대출연체디비⩂토토디비판매사이트…」 |
| encoding 10 | mcmuni.com(신분 위조·대출 대행)·ymhitech.hdib.gethompy.com(테더 현금화) 게시판 | 앵커 「신원조사 의뢰」·「테더코인이체구입」, href 검색어 → 「…@lhhjjhh 소명자료 편집…작업대출 외주대행」, 「텔레@tetherzon…테더코인매입」 |
| encoding 5 | biam.co.kr 게시판 (선불유심 대출) | 앵커 「선불유심대출」, href 검색어 → 「〘선불유심대출〘】선불유심개통】「비상금대출「…」 |
| encoding 14 (숫자 엔티티, 가) | 넘어간 도메인 7곳: coinist.io · migraineresearchfoundation.org · sociologyinfocus.com · binaryuno.com · ptep-online.com · readytalk.com · snappytv.com. 사이트당 2건(제목 하나·본문 하나) | 페이지 전체가 한국어 도박 홍보이고 본문 한글이 전부 `&#52852;&#51648;&#45432;`(카지노) 꼴 숫자 엔티티. migraineresearchfoundation.org 는 원래 메뉴가 남은 채 테마가 바뀐 해킹 워드프레스 |
| encoding 6 (숫자 엔티티, 나) | 해외 블로그 5곳: indexrotator.com · svarogday.com · thebestofcafucus.com(2) · valid.global · newsfiber.com | 정상 제목 페이지의 바닥글 링크 목록·본문 링크 앵커가 `&#53664;&#53664;&#49324;&#51060;&#53944;`(토토사이트) 꼴. 목적지 bio-medicine.org·upkorea.net·doteshopping.com·slatewinebar.com·verlocal.com·busiweek.com(넘어간 도메인, 미방문) |
| meta_cloaking 10 | UNIST 헬스케어센터 Q&A | 스팸 글 본문은 지워져 404 인데 title·description·og·twitter 메타에 광고가 남음 |
| meta_cloaking 10 | tvo.kr(테헤란밸리 오케스트라) XE 방명록 | 비회원에게 본문은 「요청한 기능을 실행할 수 있는 권한이 없습니다」로 막혀 있는데 description·og:description 에 스팸 글(내구제 대출·비아그라 판매·작업대출) 내용이 그대로 남음 |

### 10-07 숫자 엔티티 (ET-210~229)

요강의 encoding 예시인 HTML 숫자 엔티티 실사례를 우리 원문(국내 게시판 위주 2,654쪽)에서 못 찾아, 해외 페이지까지 넓혀 찾았다.
- **찾은 방법:** HTML 소스를 검색하는 PublicWWW 에서 도박 어휘를 엔티티로 쓴 문자열(`&#52852;&#51648;&#45432;` 등 18개 낱말과 목적지 도메인)을 찾았다(`tools/collect/harvest_publicwww.py`). 이 엔진은 영문자 토큰만 검색해서 한글 원문으로는 못 찾고 엔티티 문자열로는 찾는다. 「카지노」 엔티티 424쪽, 「토토」 204쪽 등이 나왔지만 무료 화면은 검색어마다 앞쪽 11곳 안팎만 주소를 보여 준다.
- **원문:** 원 사이트에는 접속하지 않고 인터넷 아카이브(Wayback) 사본만 받았다(`tools/collect/fetch_wayback.py`, 사본 39쪽). 페이지 자체가 도박 홍보인 것이 섞여 있어서다. source 칸에 원 주소와 사본 주소를 함께 적었다.
- **고른 규칙:** `tools/analyze/find_entity.py` 가 엔티티 덩어리를 풀어 도박 어휘가 있는 가장 깊은 요소를 찾고, `tools/build/add_etc_entity.py` 가 사이트당 2건까지 골랐다(넘어간 도메인은 제목 하나·본문 하나). 휴대폰 번호 꼴이 든 요소는 뺐다. 조각은 요소 원문(엔티티 그대로)에 조상 3단을 씌운 것이다.
- **갈래:** (가) 넘어간 도메인의 도박 홍보 페이지 7곳 14건, (나) 정상 페이지에 심은 링크 앵커 5곳 6건. 갈래는 notes 에 적었다.
- **알게 된 것:**
  - 같은 링크 판매 네트워크라도 앵커가 엔티티인 사이트와 평문 한글인 사이트가 섞여 있다. 목적지 도메인으로 찾은 링크 네트워크 쪽 사본 19쪽 가운데 엔티티는 0쪽이고, 7쪽은 같은 목적지로 가는 평문 한글 앵커(「안전한 토토사이트」 등)였다. 그래서 엔티티는 업자가 일부러 고른 것이라기보다 사이트(워드프레스 저장 방식 등)가 그렇게 내보낸 것일 수 있다. indexrotator·newsfiber 두 건은 같은 페이지가 키릴·일본어도 엔티티로 내보내 notes 에 적었다. 탐지기 입장에서는 소스에 엔티티로 들어 있다는 점은 같다.
  - PublicWWW 검색에 걸린 도메인 가운데 skaratoken·karnatakavarthe·legtm·bitflip 등은 아카이브 최신 사본에 한글이 없었다(사본 시점이 다름). 넣지 않았다.
- 덧붙이기 전 판은 `data/raw/etc_before_entity_20261007.yaml` 에 있다.

선별 기준(`tools/build/build_etc_found.py`)은 이렇다.
- **link_cloaking:**
  - 앵커가 일반 안내 문구여야 한다. 안내 문구를 빼고 남는 글자가 「지금·공식·파트너·불가 시」 같은 일반 낱말이 아니면 뺐다.
    - 빠진 예: 「사업자대출디비구입문의바로가기」, 「세션쿠키탈취공식사이트」, 브랜드명이 든 「인디고 주소」
  - 목적지가 텔레그램·노션 등 메신저·문서 서비스이거나 주요 정상 도메인이면 뺐다.
  - 무관한 사이트 검색 페이지에 스팸 문구를 검색어로 넣은 링크(검색창 악용)는 링크 클로킹에서 뺐다. 목적지가 도박 도메인이 아니기 때문이다. 검색어가 퍼센트 인코딩된 광고 문구이면 encoding 으로 넣었다(사이트당 5건, 디코딩 문구가 다른 것만).
  - 사이트당 5건까지. 목적지나 앵커 문구가 다른 것만 넣었다.
- **zero_width:**
  - 보이지 않는 문자가 광고 키워드·연락처·도메인 바로 안이나 옆(±4자)에 있어야 넣었다.
  - 빠진 예: 긴 본문에 복사로 딸려 온 제로폭(「룰렛 추첨기」 소개글), 이모지 둘을 잇는 결합 문자 U+200D
  - 사이트당 10건까지, 서로 다른 글만 넣었다. 10-06 중복 정리에서는 남은 후보가 모두 10건을 채운 사이트에만 있어, C&P그룹·영테크·황비 세 곳에 하나씩만 11건째를 넣었다.
- **meta_cloaking:** 사이트 기본 메타와 글 메타가 함께 있으면 evidence 와 값이 맞는 원문 태그를 그대로 썼다. 사이트당 10건까지.
  - 빠진 예: co-o-zam.co.kr 쇼핑몰 Q&A. JS 를 끄면 본문 전체가 비어 보이는 구조라, 「본문에는 광고가 없다」는 판정이 렌더링 방식 탓이다.
- **200개 맞추기(`tools/build/trim_etc.py`):** 넘친 만큼을 가장 흔한 zero_width 에서, 항목이 가장 많은 사이트부터 하나씩 뺐다. 192개 판은 `data/raw/etc/etc_192_backup.yaml` 에 있다.
- **목적지:** 도박 목적지는 한 번도 접속하지 않았다.
- **도박 사이트 자체 제외(10-04):** `magino.co.kr` 은 스팸이 올라온 정상 사이트로 알고 받았는데, 사이트 이름이 「온라인 홀덤사이트 - 인디고게임」인 도박 홍보 사이트 자체였다(r12 에 검색 결과 글 1쪽을 받음). 여기서 나온 ETC 8개·조합 8개를 뺐고, 빈자리는 같은 규칙으로 다시 채웠다(ETC 는 trim 전 후보에서, 조합은 덧붙이기로). 수집 도구(`fetch_ua.py`·`crawl_board.py`)는 이 호스트를 요청하지 않도록 막았다.

### OFFSCREEN 원문 100 · 시험용 100 (사람 3, `data/offscreen/`)

사람 3 이 낸 묶음을 역할 C 가 점검·수정한 판이다. 묶음 안 `README.md` 본문은 사람 3 이 처음 낸 판 기준이고, 지금 숫자와 바뀐 내용은 `data/offscreen/변경요약_20261005.md` 에 있다.
- **원문 100:** 공개 웹페이지 실측과, 실제 피해 HTML·CSS 를 공개한 보고서·포럼 글의 사본이다. 한국어 광고는 19개이고 나머지는 외국어다.
- **10-05 점검·수정 (`tools/build/fix_offscreen.py`):**
  - 상품명이 점(.)으로 가려져 광고 내용이 없는 Ranum 사본 7개와 그 시험용 7개를 뺐다.
  - html·css 만으로는 숨김이 재현되지 않던 원문 45개를 고쳤다. 방법은 원래 부모 태그 복원 10, 원래 선언을 건 감싸는 요소 재구성 34, 공백 정리 1 이다.
  - subtype 을 계획서 5종으로 통일했다.
- **10-06 visibility_hidden 보충 (`tools/build/add_offscreen.py`):**
  - SitePoint 포럼의 피해자 공개 코드 게시글에서 원문 7개(OF-208~214)와 시험용 7개(OF-215~221)를 넣어 15/15 를 채웠다.
  - visibility_hidden 15개 중 11개가 같은 `hideMeya` 캠페인이다(WordPress Stack Exchange 4 · SitePoint 7). 공개 보고서·포럼·블로그·GitHub 이슈를 훑었지만, 업자가 `visibility:hidden` 으로 광고 링크를 숨긴 다른 원문은 나오지 않았다.
- **목록 화면:** `data/offscreen/시작.html` 이다. 시험용 화면은 외부 요청과 JS 없이 열린다.
- **라이선스:** 시험용에 쓴 라이브러리 CSS 의 라이선스 원문은 `data/offscreen/licenses/`, 출처는 `THIRD_PARTY.md` 에 있다.
- **요약 파일:**
  - 묶음의 `검증결과.json`·`최종현황.json`·`패키지_SHA256.json` 은 10-06 에 `tools/build/refresh_offscreen_meta.py` 로 지금 데이터에 맞춰 다시 썼다.
  - SHA256 은 이 PC 작업 사본의 바이트 기준이다. git 이 체크아웃할 때 줄바꿈을 바꾸는 설정(autocrlf)이면 다른 사본에서는 텍스트 파일의 해시가 다를 수 있다.

### 10-06 중복 정리

데이터 전체를 다시 훑어 세 가지를 고쳤다. 고친 뒤 두 검증기 모두 오류 0이다.

1. **조합 안 같은 글 2개 삭제 (CB-220·231):**
   - CB-045·046 과 글이 완전히 같았다. 같은 업자가 다른 쇼핑몰 게시판(bienworks → mi-art)에 다시 올린 글이다.
   - 원인은 10-04 덧붙이기 도구(`extend_combo.py`)가 같은 사이트 안에서만 중복을 걸렀기 때문이다.
   - 같은 규칙의 후보에서 채웠다(CB-251 nebuah · CB-252 vestmall). 이번에는 사이트와 상관없이 글이 같으면 빼고, ETC·JAMO 와 같은 글도 뺐다(`tools/build/dedupe_refill_20261006.py`).
2. **ETC 와 조합에 같은 요소가 함께 든 6건 정리:**
   - ET-027·071·084·171·185·190 은 조합 항목과 같은 페이지·같은 선택자·같은 글이었다.
   - 조합은 한 요소에 수법 2개 이상인 것이 정의상 들어갈 자리라 조합 쪽을 남겼다. ETC 에서는 빼고, 같은 하위 유형(zero_width) 실측 후보로 채웠다(ET-201~206).
3. **숨김 사본을 가리키던 위치 고침:**
   - 11건(ETC 4 · 조합 7, 모두 kmc1958 게시글 하나)의 위치가 그누보드 댓글 수정용 숨김 사본(`textarea#save_comment_N`, `display:none`)이었다. 같은 글이 화면에는 `#c_N > p` 로 보인다.
   - 원문에서 보이는 댓글 요소를 다시 잘라 위치를 바꿨다(`tools/build/fix_hidden_copy_location.py`). 증거는 그 요소의 텍스트 노드 그대로로 다시 골랐다.
   - 그 결과 셋이 드러났다.
     - **ETC 3건(ET-086·088·090):** 같은 페이지의 보이는 댓글 샘플(ET-085·087·089)과 같은 댓글이었다. 보이는 쪽과 숨김 사본이 두 번 들어가 있던 것이다. 빼고 zero_width 로 채웠다(ET-207~209).
     - **조합 6건(CB-060·061·063·064·065·066):** 보이는 요소에서는 적힌 수법들이 한 텍스트 노드에 함께 있지 않았다(숨김 사본에서만 여러 줄이 한 덩어리였음). CB-061 은 남는 노드가 회사 표기 「㈜」뿐이었다. 조합이 아니게 되어 빼고 같은 규칙으로 채웠다(CB-253~258).
     - **CB-062:** 보이는 요소의 텍스트 노드로 그대로 살렸다.
- **상한을 한 칸 올린 곳:** 채울 후보가 모두 상한을 채운 사이트에만 남아 있었다. 그래서 한 사이트에 하나씩만 넣는다는 조건으로 올렸다.
  - 조합: 10-04 덧붙임 사이트 상한 5 -> 6(아이앙띠·진산스포츠·러브리올·키타몰·Nebuah)
  - ETC zero_width: 사이트 상한 10 -> 11(C&P그룹·영테크·황비)
  - 새 사이트를 찾으려면 새로 수집해야 하는데, 10-04 에 새 게시판 30여 곳을 받아 4개만 늘었던 적이 있어 이번에는 하지 않았다.
- **지운 id 는 다시 쓰지 않았다.** 새 항목은 ET-201~209, CB-251~258 이다.
- **정답셋:** 조합에 같은 페이지·같은 글이 이미 JAMO 라벨로 있는 JAMO 샘플 2건(JM-133·140)은 정답에 두 번 넣지 않게 했다(`to_answer.py`). 샘플 파일에는 둘 다 남겼다.
- 고치기 전 판은 `data/raw/` 아래에 두지 않았다. git 이력(10-06 이전 커밋)에서 꺼낼 수 있다.

### 난독화 조합 250

| 출처 | 개수 | 실제 형태 |
|---|---|---|
| 강화군 보건소 자유게시판 댓글 | 72 | `ぜ ＵＳＡ８７２。ｘｙｚ っ`, `K O C 1 2 3 4 。COM`, `B｜ｃ２0１4。ｃoM`, `188BLUE쩜컴` + 기사 문장 섞기 |
| annaprez.com 주문게시판 (홀덤·카지노 「인디고게임」 캠페인) | 38 | `카|지노게|임`(소프트 하이픈), `blgm7.cOM`(대소문자), `카 톡 텔 레: oi…` |
| dhtndus1004.woobi.co.kr 게시판 (같은 캠페인) | 20 | `【BLＧM 7.ＣＯM】` 전각 + CJK 괄호 |
| skin-skin1.ms8344.cafe24.com 상품 Q&A | 10 | `scmbet주소｡com ⁄ 텔 @…⁇`, 쉼표를 `، ˏ ˎ ‚` 로, `【찌라시.COM】` |
| 하우스코디 (성매매·구글찌라시) 7 · kmc1958.or.kr (의약품) 1 | 8 | 전각 + 대소문자 섞은 도메인 / `o10―XXXX﹣XXXX` + 제로폭, `찌라시｡COM` |
| 10-04 덧붙임 20곳 + 10-06 채움 (아래, 목포대·코리아왁스 등 일부는 위 사이트와 겹침) | 61 | 10-04 는 사이트당 5개 이하, 10-06 채움으로 6곳이 6개 |
| 그 밖 19곳 (선진설비·바주카·C&P그룹·비엔웍스·뉴바인·목포대·코오잠 등, 10-04 덧붙임 전) | 39 | `０１0ㅡ５8l５`, `ㅋ ㅏ톡`, `O 1 O - X X X X`, `BiS55닷CoM`, `ⓞ①ⓞ`, `여왕벌.𝐧𝐞𝐭` 등 |

10-04 덧붙임 57개의 출처는 굿웹플·아이앙띠·진산스포츠·러브리올·키타몰 각 5, 동광장갑·미아트·Nebuah·베스트몰·예원방 각 4, 배진금속·옐로포스트 각 2, 그 밖 8곳 각 1 이었다. 10-06 정리 뒤에는 아이앙띠·진산스포츠·러브리올·키타몰·Nebuah 각 6, 베스트몰·예원방 각 5, 미아트 2 다. 형태 예: `카지노(인디go 홀뎜 게­임) 아이슬­롯`, `"⓿❶⓿＊❼❹❻❺＊…"`, `◈ㄴㄲㅏ톡 탤ㄹㅔ sk5775 ◈`, `( cpangpond168.cOm)`, `◆카턱.텔.레 oio365◆ ㅋr톡, # 텔ㄹㅔ그램`.

라벨은 두 갈래다.
- `label_codes`: 요강 4종으로 옮길 수 있는 것이다. HOMOGLYPH 173, JAMO 12.
- `extra_findings`: 요강에 없는 회피 수법이다. 유형명은 제안이다.

| extra_findings | 개수 |
|---|---|
| SYMBOL_SEPARATOR | 106 |
| ZERO_WIDTH | 75 |
| KANA_SEPARATOR | 71 |
| KEYWORD_SPACING | 41 |
| DOMAIN_SPACING | 39 |
| CASE_MIX | 31 |
| PUNCT_VARIANT | 21 |
| DOT_SUBSTITUTION | 14 |
| SPELLING_VARIANT | 12 |
| JAMO_SEPARATOR | 1 |

한 요소에 겹친 수법 수는 2개 161건, 3개 58건, 4개 26건, 5개 5건이다.

선별 기준(`tools/analyze/analyze_obf.py` → `tools/build/build_combo_real.py`)은 이렇다.
- **조합:** 장식용 이모지는 세지 않았다.
- **중복:** 위장된 도메인·연락처 토큰이 같으면 하나만 남겼다. 공백·기호만 다른 같은 글도 하나로 합쳤다(`tools/build/finalize_combo.py`).
- **상한:** 같은 사이트·같은 수법 조합은 7개까지다(106개 판에서는 4개). 200개를 넘는 몫은 가장 많은 사이트(강화군)에서 뺐다. 106개 판은 `data/raw/etc/combo_106_backup.yaml` 에 있다.
- **특징 보강(10-04):** 전화번호 숫자 사이의 자모 `ㅡ`(대시 대신)와 숫자 자리의 영문 `l`(`５8l５`)을 잡도록 고쳤다.
- **대상:** 한글이 없는 외국어 스팸은 뺐다. evidence 텍스트 자체에 뜻이 분명한 불법광고 어휘(카지노·비아그라·출장안마·내구제·카톡 등)가 있어야 넣었다.
  - 「급전」「텔레」「일수」처럼 공백을 지우면 일반 문장(「석유 수급 전망」, 「텔레메트릭스」, 「높일 수」)에도 생기는 말은 판정에 쓰지 않았다.
  - 이 기준으로 정부 문서가 잡힌 오탐(산업통상부 검색 결과)을 뺐다.
- **덧붙이기(10-04, `tools/build/extend_combo.py`, 한 회차는 `tools/build/combo_round.py`):** 사용자 목표 250개. 기존 200개(magino 7개를 뺀 193개)는 그대로 두고, 기존에 20개 이상 있는 사이트(강화군·annaprez·dhtndus1004)는 빼고, 새 항목은 사이트당 5개까지 사이트를 돌아가며 골랐다. `www.`·`m.`·`en.` 만 다른 주소는 같은 사이트로 센다.
  - 수법이 두 가지 이상 겹친 글은 드물다. 새 게시판 100곳 넘게 받았고, 실제로 들어간 것은 20곳이다.
  - 덧붙인 57개는 대부분 홀덤·카지노 「인디고게임·블루게임·아이슬롯」 계열 캠페인(`oio365`·`sk5775`·`zxzx1225`)이다. **사이트는 고르게 퍼졌지만 업자(캠페인)로 보면 한 계열에 몰려 있다.** 이 계열이 소프트 하이픈·자모 분해·철자 변형을 함께 써서 조합 기준(2개 이상)에 걸리기 때문이다.
  - 중간에 폴더 이름이 바뀌어(불법광고_수집 → project/C_data) 분석 결과 속 원문 경로가 옛 경로로 남아 선별이 실패했고, 옛 후보 파일이 그대로 쓰였다. `combo_round.py` 가 경로를 지금 폴더로 다시 붙이고, 선별이 실패하면 멈추도록 고쳤다.
  - 웹 검색은 세션 한도(200회)를 다 써서, 마지막 두 회차는 이미 찾은 게시판의 깊은 쪽(최대 8쪽)을 받아 채웠다.
- **철자 변형 특징(10-04):** `캬톡`·`카토옥`·`텔래그램`·`비아그랴`·`홀뎜` 처럼 키워드를 일부러 틀리게 쓴 것을 `spelling_variant`(SPELLING_VARIANT)로 센다.
- **개인정보:** 전화번호는 앞 세 자리의 난독화 모양만 남기고 나머지를 `X` 로 가렸다. 10-04 에 자모 `ㅡ` 를 구분자로 쓴 번호(`０１0ㅡ５8l５ㅡ…`)도 가리도록 고쳤다. 이때 기존 2건(CB-078·079)에서 드러나 있던 번호를 찾아 가렸고, 가린 뒤 보이는 수법만 라벨에 남겼다. `０１０`·`ⓞ①ⓞ`·`o10―` 꼴까지 포함한다.

## 수집 경로와 규모

- **원문 3,655페이지(ETC·조합용, 1,000바이트 넘는 것)와 CSS 파일 621개를 받았다.** 경로는 셋이다.
  - 검색으로 찾은 스팸 글·해킹 페이지 (`fetch_ua.py`). 검색어는 도박·의약품·유흥·불법대출·「구글찌라시」(불법광고 대행)에 걸쳤다. 소프트 하이픈이 든 문자열(`카­지노`, `비­아그라`) 자체로도 검색했다.
  - 스팸이 쌓인 게시판 목록에서 최신 글 따라가기 (`crawl_board.py`).
    - 회차별 게시판 목록은 `data/raw/etc/boards_r*.txt` 에 있다. 실사례가 나온 게시판은 목록을 최대 8쪽까지 넘기며 받았다.
    - 게시판 주소는 글 주소에서 `derive_boards.py` 로 거슬러 만들었다. 앞 회차에서 받은 글은 건너뛴다.
  - DECOY 용 사이트 덤프
- **요청 기록:** 5,269건의 대상·일시·결과가 `data/collection_log.csv` 에 있다.
- **polite:**
  - robots.txt 를 지켰다. 이 때문에 장훈고·가평 등은 받지 않았다.
  - 순차 요청에 간격은 1.5초다.
  - 로그인이 필요한 게시판(ksmart 등)은 들어가지 않았다.
- **안전:** 해킹·스팸 페이지는 JS 를 끄고 네트워크를 전부 막은 채 렌더링했다. 도메인 자체가 도박 사이트인 곳은 받지 않았다. 다만 `magino.co.kr` 한 곳은 도박 홍보 사이트인 줄 모르고 글 1쪽을 받았다(위 「도박 사이트 자체 제외」). 10-04 에 받은 모든 샘플 출처의 사이트 이름을 다시 확인했고, 그 밖에 도박 사이트 자체는 없었다.
- **삭제된 글:** 검색 결과에 걸린 글의 상당수는 이미 지워져 있었다(「글이 존재하지 않습니다」). 그래서 실측 수는 검색 결과 수보다 훨씬 적다.

## 수집하며 확인한 것 (기획서·설계에 쓸 만한 것)

1. **실제 공공 도메인 오염의 대부분은 「보이는」 광고다.** 두 갈래가 있다.
   - 해킹된 호스트에 심은 도어웨이 페이지
   - 게시판 스팸 글·댓글

   요강 기법보다 텍스트 난독화(전각·가나 구분자·도메인 공백·부호 바꿔치기)가 훨씬 많다.
2. **도어웨이는 UA 가 아니라 Referer 로 클로킹한다.**
   - `Referer: https://www.google.com/` 로 받으면 7개 호스트가 301/302 로 외부 게이트·트래커로 보냈다.
   - Googlebot UA 응답은 브라우저 응답과 바이트까지 같았다.
   - ASEC 보고서(asec.ahnlab.com/ko/64558)의 수법과 같다.
3. **실제 도박 게이트 도메인은 이름에 bet·casino 가 없다.**
   - 예: `wwnnh.com`, `qkc709.com`, 퓨니코드 한글 도메인 `xn--…`, `bit.ly`, `*.pages.dev`
   - 계획서 사전의 도메인 정규식으로는 못 잡는다.
4. **삭제된 글의 메타가 남는다.** UNIST 는 본문을 지운 404 화면에도 글 title·description 이 남아 검색엔진에 광고가 계속 노출된다.
5. **검색창 악용이 두 방향으로 쓰인다.** 둘 다 링크 클로킹 정의(href 가 도박 도메인)에 맞지 않아 샘플에서는 뺐다.
   - **해외 사이트 검색 페이지로 링크:** 국제사이버대·jnbburi.or.kr 스팸은 블리자드·entegris 등 무관한 해외 사이트의 검색 페이지로 링크를 걸고, 검색어 자리에 스팸 문구를 퍼센트 인코딩해 넣었다(`@FUTIN888`). 링크 클로킹에서는 뺐고 encoding 으로 넣었다(같은 수법의 다른 게시판까지 40건).
   - **국내 정부 사이트 검색 결과에 노출:** 안전디딤돌TV·국립무형유산원·의약품안전나라·산업통상부·개인정보 포털의 통합검색 결과 페이지가 스팸 문구를 검색어로 받은 채 검색엔진에 색인돼 있다(예: `텔𝙖𝙙𝙨𝙜𝙤𝙜𝙤 구글찌라시`).
   - 탐지 도구가 사이트 내부 검색 결과 페이지까지 크롤링하면 이 반사 문구를 광고로 잡을 수 있어, 정밀도 관리 대상이다.
6. **오픈 리다이렉트 세탁.** CBMC 스팸은 링크를 `ad1.dyntracker.com/set.aspx?dt_url=…` 같은 제3자 리다이렉터로 감쌌다.

## 한계 (그대로 적는다)

- **ETC 200개 중 css_content 만 0건이다.**
  - zero_width 99 로 쏠려 있다.
  - css_content 실사례는 2,654페이지와 CSS 621개에서 0건이다. encoding 은 URL 퍼센트 인코딩만 있다. 원문 소스 전체를 인코딩 수법 7가지(packer·fromCharCode·unescape·atob·\x·\u·숫자 엔티티)로 훑었는데, 걸린 것은 모두 플랫폼이 자동으로 만든 것(아임웹 설정 JSON, 카페24 통화 기호, 아임웹이 글 데이터를 \u 로 저장한 것)이었다.
- **숨김 + 난독화:** 숨김 요소 안의 광고 문구 642건은 모두 게시판 프로그램이 만든 것이다(그누보드 댓글 수정용 숨김 textarea, 숨긴 이전·다음 글 링크). 업자가 숨긴 실사례는 0건이다.
- **캠페인 쏠림:**
  - zero_width 대부분이 소프트 하이픈 캠페인 몇 개다.
  - link_cloaking 41개 중 30개가 같은 `qkc709.com` 캠페인이다.
  - encoding 의 URL 퍼센트 40개는 「@FUTIN888 디비 판매」·「선불유심 대출」·「신분 위조·대출 대행」·「테더 현금화」 네 계열이다. 숫자 엔티티 20개는 12곳이지만, (나) 6개는 해외 링크 판매 네트워크 하나로 보인다(목적지 도메인이 서로 겹친다).
  - meta_cloaking 20개는 UNIST·tvo.kr 두 곳이다. 사이트당 상한을 6에서 10으로 올려 채웠다.
- **조합 250개 중 72개가 강화군 한 게시판, 58개가 annaprez·dhtndus1004 두 곳이다.** 출처는 44곳이다. 10-04 덧붙임 57개는 사이트당 5개 이하로 퍼졌지만, 업자로 보면 「인디고게임·블루게임·아이슬롯」 계열이 대부분이다.
  - 10-04 에 다른 업자 게시판 9곳과 Goodreads 스팸 태그 15건을 더 받았지만, 대부분 수법이 하나뿐(`Oloㅡ8359`, `텔레𝘓𝘖𝘈𝘕46`)이라 조합(2개 이상)에 거의 들지 않았다. 200개를 맞추려고 같은 사이트·같은 수법 조합 상한을 4에서 7로 올렸기 때문에 쏠림이 106개 판보다 커졌다.
- **숨김 + 난독화가 겹친 실사례는 0건이다.**
- **분석 안정성:** 처음에는 한 탭으로 수백 페이지를 돌리다 상태가 꼬여 일부 페이지·회차가 실행마다 빠졌다. 지금은 세 가지로 막았다.
  - 회차 폴더별로 나눠 돌린다.
  - 실패한 페이지는 새 탭에서 다시 시도한다.
  - 선택자 계산은 새 탭에서 한다.

  그 결과 최종 분석에서 건너뛴 페이지는 0개다.
- **해킹 사이트에 심은 외부 스크립트(10-04 사용자 허락으로 조사):** 받은 원문의 외부 스크립트 주소를 모두 뽑았지만 도박 스크립트는 없었다. 대학 서버의 `?play=` 도어웨이는 쿠팡 상품 페이지를 통째로 복제하고 키워드만 바꾼 것이라 숨김·인코딩이 아니다. Kaspersky Securelist 2025 보고서의 숨김 링크 사례도 포르투갈어·영어·일본어 대상이고 한국어 사례는 없다. 검색에서는 만료된 단체 도메인(`bdsj.or.kr`·`suwonsc.or.kr` 등)이 통째로 토토 홍보 사이트가 된 것이 보였는데, 불법 사이트 자체라 접속하지 않았다.
- **써 보지 못한 출처:** mude.co.kr(목록이 자바스크립트로 이동)과 auf.co.kr(비밀글)은 같은 캠페인 글이 대량으로 있었지만 원문을 얻지 못했다.

## 결정이 필요한 것

- **실측 샘플의 실제 도박 도메인·텔레그램 핸들:** 원문 그대로 두었다. 테스트 데이터가 소스코드와 함께 제출되므로, 제출 전에 가명으로 바꿀지 팀에서 정해야 한다.
- **DECOY css 칸:** 원 시트 바이트가 아니라 브라우저 CSSOM 이 직렬화한 규칙이다. 원 시트 URL 은 notes 에 있다.
- **meta_cloaking html:** `<head>` 안에 넣을 조각이다.
- **URL 퍼센트 인코딩 40건을 encoding 으로 인정할지:** 요강 예시는 HTML 엔티티·Base64 인데, 이 40건은 링크 주소 안의 URL 퍼센트 인코딩이다. 광고 문구가 사람에게는 안 보이고 인코딩된 채 소스에만 있다는 점은 같다. 인정하지 않으면 encoding 실측은 숫자 엔티티 20건이다.
- **숫자 엔티티 (가) 14건을 넣을지:** 정상 사이트에 심은 광고가 아니라 넘어간 도메인의 페이지 전체가 도박 홍보다. 10-07 사용자 결정으로 (가)·(나) 둘 다 넣었고 notes 에 갈래를 적었다. 빼려면 notes 에 「(가)」가 든 14건을 지운다.

## 요강 기준 정답셋 (`data/answers/`)

`python tools/build/to_answer.py` 가 실측 라벨을 요강 붙임4 스키마(UTF-8, BOM 없음)로 바꾼다. 원본 YAML 은 건드리지 않는다.
- 읽는 파일: decoy·etc·combo_real·jamo, OFFSCREEN 원문(`data/offscreen/data/originals/offscreen_originals.yaml`)
- 10-06 부터 JAMO·OFFSCREEN 도 읽는다.
- OFFSCREEN 의 CSS 시험용 100개와 가시 대조군 7개는 실측이 아니라 파생 자료라 넣지 않는다.

| 파일 | 요강의 자리 | 건수 |
|---|---|---|
| `answer_result.json` | `result.json` — 적격평가 대상 주요 탐지 유형 4종 | 430 (HOMOGLYPH 173 · JAMO 157 · TRANSPARENT 0 · OFFSCREEN 100). JAMO 157 = jamo.yaml 145(조합과 같은 요소 2건 제외) + 조합의 JAMO 라벨 12 |
| `answer_result_extra.json` | `result_extra.json` — 추가 유형, `technique: "ETC"` + `extra_finding` | 631 (etc 220 + 조합의 extra_findings 411) |
| `negatives.json` | 정답 아님. 숨김 신호가 있는 정상 요소라 여기에 걸리면 오탐(정답 추출 정확도 35점) | 200 |

- 검출 1건 = `(url + location + technique)`. 한 요소에 기법이 겹치면 기법마다 객체를 따로 만들었다(요강 붙임4). `id` 는 `샘플id_기법`(예: `CB-003_HOMOGLYPH`).
- `url` 은 샘플을 잘라 온 실제 페이지 주소, `location` 은 잘라 낸 조각(`html`) 안의 유일 선택자다. 그래서 지금은 **조각 단위 채점**만 된다. 페이지 단위 채점은 mocksite 에 조각을 심은 뒤 그 주소로 다시 만든다.
- 조합 250개 중 72개는 4종 코드가 없어 `answer_result_extra.json` 에만 들어간다. 이 72개는 적격평가 점수에 기여하지 않는다.
- **적격평가 4종 중 TRANSPARENT 는 실측 정답이 0건이다.** 재현율은 생성 데이터로만 잴 수 있다.
- **OFFSCREEN 원문 100건의 `url`:**
  - 공개 웹페이지 실측 52건은 그 페이지 주소다.
  - 과거 피해 코드 공개 사본 48건은 코드를 실은 보고서·포럼 글의 주소다. 그 페이지에서 코드는 글자로 보이지 숨겨져 있지 않으므로, 실제 페이지에 대고 채점하는 용도가 아니라 조각 단위 정답이다.

## 채점기 (`tests/scorer.py`)

```
python tests/scorer.py 제출.json 정답.json                   # 브라우저로 같은 요소인지 확인 (기본)
python tests/scorer.py 제출.json 정답.json --resolve string  # 페이지 없이 선택자 문자열로 비교
python tests/scorer.py 제출_extra.json 정답_extra.json --extra
python -m pytest tests/test_scorer.py -q                    # 채점기 자체 테스트
```

- 출력: 정답·제출·정답 검출 건수, 정밀도·재현율·F1, 기법별 tp/fp/fn, 30분 상한 판정. `--report` 를 주면 FP·FN 목록을 JSON 으로 남긴다.
- 요강대로 옮긴 규칙: 세 필드(url · location · technique) 일치, URL 비교 규칙(끝 `/`·http/https·`#` 무시, 쿼리 순서 무시), 같은 요소면 표기가 달라도 정답, 두 곳 이상 가리키면 오답, 같은 항목 복수 제출은 1건, 파일 파싱 불가는 0점. iframe 은 `iframe[src="절대주소"] >>> 선택자` 를 프레임마다 따라가고, src 가 상대 경로인 iframe 도 절대 주소로 맞춘다.
- 요강이 정하지 않아 채점기가 정한 것: 스키마 미준수 항목은 오답으로 셈(붙임2 와 붙임4 가 다르다, `--schema-miss exclude` 로 바꿈) · `is_violation: false` 는 제출 건수에 넣고 정답으로 치지 않음 · BOM 은 0점 · 「참고 점수」는 45 x 재현율, 35 x 정밀도라는 가정 · 시간 20점은 상한 판정만.
- 브라우저 방식은 `--allow-host`(기본 127.0.0.1, localhost)의 페이지만 연다. 실제 사이트에는 요청하지 않는다.

**지금 정답셋으로 돌리면 생기는 일.** `data/answers/answer_result.json` 의 건수가 채점기 안에서 크게 줄어든다. 10-06 판은 430건이 287건으로 합쳐진다. 기법별로는 HOMOGLYPH 173 -> 102, OFFSCREEN 100 -> 28 이고 JAMO 157 은 그대로다. OFFSCREEN 은 같은 보고서·게시판 주소에서 잘라 온 조각들이 모두 `a` 같은 선택자를 쓰기 때문이다. 같은 페이지의 댓글 여러 개가 모두 `p.txt` 같은 조각 선택자를 써서 url · location · technique 가 겹치기 때문이다(채점기가 경고로 알린다). 조각 단위 정답셋으로는 페이지 단위 채점을 할 수 없다는 뜻이고, mocksite 에 조각을 하나씩 심어 페이지 주소와 페이지 안 유일 선택자를 새로 매기면 풀린다.

## 남은 일 (10-06 기준)

1. **생성 데이터:** 실측으로 못 채운 몫이다.
   - JAMO 호환자모 전체 분해 23 (실측 17/40. 10-06 사람 4 추가분 5건 포함, 공개 게시판 원문 3,638쪽에서는 실례 0건)
   - css_content 20
   - encoding 의 엔티티·Base64 형태
   - 숨김+난독화 조합
   - 적격평가 4종 중 TRANSPARENT 정답
2. **mocksite:** `tests/mocksite/` 에 조각을 심어 페이지 단위 정답셋을 만든다. 지금 정답셋은 조각 단위라 같은 선택자가 겹쳐 합쳐진다.
3. **팀 결정:** 위 「결정이 필요한 것」의 도메인 가명화·encoding 인정 여부. (git 원격은 10-04 에 비공개로 돌렸다.)
4. **일정:** 10-09 F1 0.85 게이트, 10-16 클린 VM, 10-21 풀런 3회, 10-22 제출.

> 10-06 까지 남은 일이던 「JAMO·OFFSCREEN 을 정답셋에 넣기」는 10-06 에 했다. `to_answer.py` 가 jamo.yaml 147건과 OFFSCREEN 원문 100건을 읽어 `answer_result.json` 이 187 -> 430건이 되었다(위 「요강 기준 정답셋」, 10-06 중복 정리 뒤 숫자).

## 폴더

총계획서 §3.4 저장소 구조 가운데 **역할 C 몫**(`tests/mocksite/`, `tests/scorer.py`, `data/patterns/`)을 같은 자리에 맞춰 둔 작업 공간이다. 라벨·생성 로직은 B 에게 공개하지 않고, B 는 채점기 점수만 본다(§9.3).

```
tests/
  mocksite/             (아직 비어 있음) generate.py · labels.json 자리 — SPEC 60쪽, 4기법 x 25, decoy 40/30/15/10
  scorer.py             요강 붙임4 「평가 참고사항」을 재현하는 채점기 (아래 「채점기」 절)
  test_scorer.py        채점기 테스트 24개 (요강 예시 URL·iframe·중복·스키마 규칙)
data/
  samples/              decoy.yaml · etc.yaml · combo_real.yaml · jamo.yaml  (실측 라벨 원본, 위 「결과」 표)
  lexicon/              seed.yaml(사람 4 사전 624개) · review_20261005.csv(바뀐 어휘 검수 목록)
  JAMO_LEXICON_작업노트.md         사람 4 작업 노트 원문 + 끝에 「2026-10-05 점검 뒤 고친 것」
  JAMO_LEXICON_변경요약_20261005.md  JAMO·LEXICON 을 무엇을 왜 바꿨는지 한눈에 보는 표
  offscreen/            사람 3 OFFSCREEN 묶음: data/originals(원문 100) · data/samples(시험용 100 · 대조군 7) · fixtures(시험용 화면 107)
                        · data/css·catalog(라이브러리 숨김 규칙·변형 목록) · licenses · 시작.html(목록) · 변경요약_20261005.md
  unicode/              Unicode 17.0.0 confusables.txt · Scripts.txt · IdentifierType.txt (사람 3 번들, 10-06 offscreen 묶음에서 옮김) · 라이선스
  answers/              요강 붙임4 스키마 정답셋 (to_answer.py 가 만든다, 위 절)
  patterns/             (아직 비어 있음) catalog.yaml 자리 — 실측 은닉 패턴, 탐지 규칙 근거이자 mocksite 입력
  collection_log.csv    요청 5,269건의 대상·일시·결과
  raw/                  (gitignore) 원문 HTML, 분석 JSON, 후보 YAML, 이전 판 백업
tools/
  collect/              수집
    fetch_ua.py           URL 목록을 UA·Referer 조건별로 받기 (JS 실행 안 함, 리다이렉트 안 따라감)
    crawl_board.py        스팸 게시판 목록 → 최신 글 따라가기 (polite)
    derive_boards.py      글 주소 → 게시판 목록 주소 (그누보드·카페24·아임웹·XE·KBoard)
    dump_hidden.py        숨김 신호 요소 덤프 (+ probe_hidden.js, 같은 폴더에 있어야 한다)   ← 게이트 산출물 "덤프 스크립트"
    render_offline.py     저장한 원문을 JS 끄고 네트워크 막은 채 렌더링
    make_collection_log.py  data/collection_log.csv 작성
    build_corpus.py       받아 둔 원문 → 보이는 글자 색인(corpus.jsonl, raw 아래에 둔다)
  analyze/              원문 분석
    analyze_etc.py        원문 → ETC 5종 실측 후보
    analyze_obf.py        원문 → 난독화 특징 (build_combo_real · validate_combo 가 import 한다)
    scan_css_content.py   내려받은 CSS 파일의 content 규칙 훑기
    scan_encoding.py      원문 전체에서 속성·스크립트 Base64, 숫자 엔티티, \u 이스케이프로 감춘 광고 훑기
    scan_raw.py           원문 바이트 수준 ETC 신호 훑기
    find_jamo.py · find_jamo_diverse.py   원문 색인에서 자모 분해 광고 찾기 (JAMO 보충·쏠림 완화)
    mine_terms.py         원문 색인에서 도박 핵심어·유인어·연락 표기 후보 뽑기 (LEXICON 보충)
  build/                후보 → 샘플 파일 → 정답셋
    build_decoy.py        덤프 → DECOY 후보 (조각 재현 확인)
    select_decoy.py       후보 → decoy.yaml
    build_etc_real.py     도어웨이 링크 클로킹 실측 4
    build_etc_found.py    ETC 후보 선별 → etc.yaml
    trim_etc.py           ETC 를 정해진 개수로 맞춤
    build_combo_real.py   조합 선별 → combo_real.yaml
    extend_combo.py · finalize_combo.py   조합 덧붙이기 · 중복 합치고 개수 맞춤
    combo_round.py        조합 덧붙이기 한 회차 (새 회차 분석 → 후보 → 덧붙이기)
    to_answer.py          samples·jamo·OFFSCREEN 원문 → data/answers (요강 붙임4 스키마)
    fix_jamo.py · fix_lexicon.py   JAMO·LEXICON 점검 결과 고치기 (2026-10-05)
    add_jamo.py           JAMO 덧붙이기, 기존 id 유지 (2026-10-06)
    fix_offscreen.py      사람 3 OFFSCREEN 점검 결과 고치기 (2026-10-05)
    add_offscreen.py      OFFSCREEN 원문·시험용 덧붙이기 (2026-10-06)
    dedupe_refill_20261006.py  ETC·조합 중복 정리와 같은 규칙으로 채우기 (2026-10-06)
    fix_hidden_copy_location.py  숨김 사본(textarea)을 가리키던 위치를 보이는 요소로, 증거를 그 텍스트 노드로 (2026-10-06)
    refresh_offscreen_meta.py  OFFSCREEN 묶음 요약 파일(검증결과·최종현황·SHA256·원문 메타데이터)을 지금 데이터로 다시 쓰기 (2026-10-06)
  validate/
    validate_samples.py   DECOY·ETC 양식·렌더링 검증                         ← 게이트 산출물 "양식 검증 스크립트"
    validate_combo.py     조합 검증
    check_offscreen.py    OFFSCREEN 원문·시험용·대조군 렌더링 검증(선택자 유일, 숨김 여부와 이유)
  archive/
    gen_etc.py            (이번 결과물에는 안 씀. 예전 생성분 백업: data/raw/etc/etc_with_generated_backup.yaml)
```

명령은 모두 이 폴더(`C_data/`)에서 실행한다. 입출력 경로는 인자로 받는다.

브라우저: 번들 Chromium 다운로드가 시간 초과로 실패해서 시스템 Edge(`channel="msedge"`)를 쓴다.
