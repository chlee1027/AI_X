# TRANSPARENT(투명 텍스트) 실데이터 테스트셋 (사람 2) — 2차판

작성: 김준아 / 기준일: 2026-10-13 / 이전판: 2026-10-08 (권장판 107건, 전체판 338건)

## 1. 요약

| 파일 | 건수 | 용도 |
|---|---|---|
| `transparent_real_test_rec20.yaml` | **232** | **기본 테스트셋(권장)**: 완전 중복을 뺀 뒤 사이트당 최대 20건, 수법을 골고루 뽑음 |
| `transparent_real_test_full.yaml` | 541 | 전체판: 확정된 전부 (참고·추가 평가용, 같은 블록 안 반복 포함) |
| `transparent_real_borderline.yaml` | 22 | 기본셋에서 뺀 경계 사례 (4절) |
| `transparent_real_test_rec20_render.yaml` | - | 기본셋 샘플별 단독 렌더링 결과 (232/232 `invisible`) |
| `validate.py` | - | 팀 공통 양식 검사기 (`python validate.py <파일>`) |
| `render_check.py` | - | 단독 렌더링 검사기 (`python render_check.py <파일>`, Playwright + Edge 필요) |

- 전부 **실제 웹사이트에서 직접 수집한 페이지**에서 뽑았다. 생성·합성 샘플이나 손으로 숨김 스타일을 넣은 샘플은 **0건**이다 (`source_type: real`, `split: test`).
- 각 샘플의 출처(원본 페이지 URL, 수집일)는 **부록 A~D**에 전부 적었다. YAML의 `source`, `origin.url` 필드에도 같은 URL이 들어 있다.
- **국내 사이트가 아니라 해외 기관 사이트**다. 국내 공공 사이트에서는 실제 투명 처리 광고가 0건이었다(6절).
- 26개 사이트: 인도네시아 22곳(대학 학술지, 지방정부 go.id 2곳, 학교), 브라질 2곳, 나이지리아 1곳, 태국 1곳. 경계 사례만 나온 ejournal.unp.ac.id까지 치면 27곳이다.
- 기본셋 쏠림: 1위 사이트 8.6%(20/232), 상위 4곳 34.5%.
- 기본셋과 전체판 모두 `validate.py` 통과. 기본셋은 단독 렌더링에서 232/232 모두 정답 요소가 실제로 안 보인다.
- 기본셋의 id는 전체판의 id와 같다(기본셋은 전체판의 부분집합).

## 2. 하위 유형 분포

| subtype | 요강 정의 | 실제 수법 예 | 전체판 | 기본셋 |
|---|---|---|---|---|
| opacity_zero | opacity:0 | `<div style="opacity:0; position:absolute; pointer-events:none; height:0; overflow:hidden;">` | 270 | 110 |
| color_matches_bg | 배경색과 동일한 색상 | `<a style="font-size: 1px; color: #ffffff;">`(흰 배경), `<a style="color:#fff;background:#fff;">` | 211 | 88 |
| color_alpha_zero | color:transparent | `<a style="color:transparent;">`, `<a style="color: #ffffff00; font-size: 1pt;">` | 60 | 34 |
| text_fill_color | (계획서 하위 유형) | 실제 사례 없음 | 0 | 0 |
| bg_image_hold | (계획서 하위 유형) | 실제 사례 없음 | 0 | 0 |

- `color_alpha_zero`에는 `color:transparent` 외에 **8자리 hex 알파 0**(`#ffffff00`) 표기도 있다(kma.ac.th). 탐지기가 `transparent`라는 단어만 찾으면 놓친다.
- `text_fill_color`와 `bg_image_hold`는 실제 사례가 없었다. 생성 데이터로 채우지 않았고, 발견 사항으로 보고한다.

## 3. 수집 방법

1. 대상 목록:
   - 학술지 색인(SINTA, DOAJ 38개국)
   - Common Crawl URL 색인의 기관 도메인 호스트(desa.id·go.id·or.id·ac.id·sch.id, ac.th, edu.vn 등)
   - 감염 페이지의 스팸 링크가 가리키는 다른 기관 호스트
   - (2차판 추가) 웹 검색으로 찾은 감염 학술지 페이지
2. 각 페이지를 1회 받아 다국어 스팸 어휘로 감염 여부를 정적 검사했다.
3. 감염된 페이지는 **전부 실제 브라우저(Edge)로 렌더링**하고, 화면에 그려지는 요소 중 안 보이는 글자를 계산된 스타일로 찾았다. 기준은 다음 셋 중 하나다.
   - opacity 누적 0
   - 글자색 알파 0
   - 글자색이 실제 배경색과 같음(채널 차 16 이하)
4. **엄격 확정**: 숨김 스타일이 그 요소나 조상에 **인라인 style로 직접** 지정된 경우만 넣었다. 다음은 제외했다.
   - 메뉴 버튼·슬라이드 애니메이션 상태(예: sulsel.ddi.or.id 9건)
   - 도박 사이트를 통째로 복제한 페이지의 메뉴 토글
   - 반투명 배경 위 글자
   - 사이트 자체 CSS 때문에 우연히 흰색이 된 글자
5. 확정된 요소마다 원본 페이지에서 **숨김 범위의 마크업을 그대로** 잘라 팀 양식으로 변환했다.
6. 기본셋 선정:
   - html·css·expected_location이 모두 같은 완전 중복을 뺐다.
   - 사이트당 20건까지 뽑았다. 수법을 번갈아 고르고, 도박 문구·도메인이 있는 것과 서로 다른 문구를 우선했다.

수집 규칙:
- robots.txt를 지켰다. 요청 간격은 호스트당 1.2초 이상이다.
- 403/429 응답이나 robots 차단은 우회하지 않았다.
- 기관 도메인만 접속했다. 광고가 가리키는 도박 사이트에는 접속하지 않았다.
- 일부 사이트는 자동화 브라우저에는 스팸을 숨긴다(클로킹). 그래서 일반 브라우저 UA로 렌더링했다.

## 4. 기본셋에서 뺀 것

- **완전 중복**: 한 숨김 블록 안에서 같은 링크가 반복된 경우다. 전체판 541건 중 고유한 것은 436건이다.
- **경계 사례 22건** (`transparent_real_borderline.yaml`):
  - ejournal.unp.ac.id 20건: 흰 글자(1px)가 미색 배경 rgb(251,251,243) 위에 있다. 채널 차가 최대 12라 사람 눈에는 안 보이지만, 단독 렌더링 픽셀 비교에서 완전 invisible 기준(차 8 이하)을 넘는다.
  - ojs.stiem-bongaya.ac.id 2건: 글자는 안 보이지만, 링크에 지정된 흰 배경 상자가 회색 바탕에서 드러난다.
- jurnalkonstan.ac.id의 숨김 블록에는 도박 링크와 일반 업체 링크(링크 농장)가 섞여 있다. 기본셋에는 도박 문구·도메인이 있는 것만 들어갔다. 전체판에는 둘 다 있다.

## 5. 필드 설명

팀 공통 필드(`id, category, subtype, html, css, evidence_text, expected_location, is_positive, extra_finding, source, notes`)에 아래 필드를 추가했다.

| 필드 | 의미 |
|---|---|
| `html` | 원본 페이지의 **숨김 범위 마크업 그대로**: 숨김 스타일을 가진 조상부터 정답 요소까지. 블록이 20KB를 넘으면 정답 요소까지의 조상 사슬만 남기고 형제 요소는 생략했다(태그·속성은 원문 그대로, `notes`에 표기). |
| `css` | 원본 페이지에서 그 범위가 상속받던 **배경색·글자색만** 복원 (`body{background:…;color:…}`) |
| `evidence_text` | 숨겨진 광고 문구(원문 그대로) |
| `expected_location` | 위 `html` 조각 기준 CSS 선택자 (조각 안에서 유일) |
| `source` | "직접 수집(해외 기관 웹사이트) · 원본 페이지 URL" |
| `notes` | 렌더링 실측값(글자색, 배경, 글자크기, opacity), 링크 대상 주소, OFFSCREEN 겹침 여부, 형제 생략 여부 |
| `origin.url` / `origin.host` | 수집한 원본 페이지 URL / 호스트 |
| `origin.page_location` | **원본 페이지 전체** 기준 선택자 (참고용) |
| `source_type` / `split` | 모두 `real` / `test` |

`extra_finding`은 전부 `null`이다. id는 `TR-RT-0001`~`TR-RT-0541`(전체판 기준), 경계 사례는 `TR-RB-0001`~`TR-RB-0022`다.

## 6. 함께 알아야 할 점 (보고서 발견 사항 후보)

- **OFFSCREEN 겹침**: 흰 글자에 font-size 1px까지 쓴 요소가 기본셋에 72건 있다(`notes`에 "OFFSCREEN 별도 1건" 표기). 채점 규칙상 같은 요소에 OFFSCREEN 1건이 따로 생긴다. 이 파일에는 TRANSPARENT 건만 넣었다.
- **국내 공공 사이트에는 실제 투명 처리 광고가 없었다.** 감염 게시판 약 100곳과 게시글 본문 172건을 검사했다. 국내 스팸은 `display:none`이나 검색결과 반사를 쓴다.
- 요강상 적격평가는 주최 측이 직접 구축한 비공개 테스트 사이트로 한다(모집요강 4쪽).
- 실제 투명 수법은 거의 인라인 `opacity:0`, 흰 배경 위 흰 글자, `color:transparent`/`#ffffff00`뿐이다. `-webkit-text-fill-color`와 배경이미지 수법은 없었다.
- 렌더링 없이 HTML 문자열만 보면 오탐이 많다. 정상 페이지에도 애니메이션용 opacity:0과 메뉴 토글이 흔하다.
- **사이트 상태 변화**: 감염 블록은 기관이 발견하면 지워진다. 원본 URL에서 지금은 안 보일 수 있으니, 판정은 파일의 `html`+`css` 기준으로 한다.
- **주의**:
  - 원본 URL과 링크 주소에 도박 사이트 도메인이 그대로 있다. 공개 저장소에 올릴 때 주의하고, 링크를 클릭하지 말 것.
  - 원본 페이지 중 일부에는 해커가 심은 악성 스크립트가 있다. Windows Defender가 원본 HTML을 `Trojan:HTML/Redirector`로 탐지한 사례가 있다. 원본 URL을 직접 열어 볼 때 주의하라.
  - 이 패키지의 YAML에는 숨김 범위 마크업만 들어 있다.

## 7. 팀 확인 요청

1. 해외 기관 사이트 사례를 테스트셋으로 인정할지 (국내 0건이라 해외에서 수집)
2. 기본 테스트셋을 기본셋(232)으로 할지, 전체판(541)으로 할지
3. 흰 글자+1px 요소(OFFSCREEN 겹침)의 OFFSCREEN 건을 사람 3 데이터에 추가할지
4. `text_fill_color`·`bg_image_hold` 부족분을 나중 생성 세트에서 채울지 (테스트셋에는 넣지 않음)


## 부록 A. 사이트별 출처

각 사이트에서 실제로 받아 렌더링한 원본 페이지 URL과 수집일이다. "경계"는 `transparent_real_borderline.yaml` 건수다.

| 사이트 | 기관 | 전체판 | 기본셋 | 수법 | 원본 페이지 URL (수집일) |
|---|---|---|---|---|---|
| dinkopumkm.endekab.go.id | 인도네시아 엔데군 정부(협동조합·중소기업과) | 144 | 20 | 0 | opacity_zero | https://dinkopumkm.endekab.go.id (2026-10-08) |
| ejournal.um-sorong.ac.id | 인도네시아 무함마디야 소롱대 학술지 | 98 | 20 | 0 | color_matches_bg | https://www.ejournal.um-sorong.ac.id/index.php/gl (2026-10-12~13) |
| syekhnurjati.ac.id | 인도네시아 대학 학술지 | 55 | 20 | 0 | color_matches_bg | https://syekhnurjati.ac.id/jurnal/index.php/eduma (2026-10-08) |
| jurnalkonstan.ac.id | 인도네시아 학술지(ac.id) | 46 | 20 | 0 | color_alpha_zero | https://jurnalkonstan.ac.id (2026-10-12~13) |
| mibaida.sch.id | 인도네시아 학교 | 36 | 20 | 0 | opacity_zero | https://mibaida.sch.id (2026-10-08) |
| journal.unucirebon.ac.id | 인도네시아 대학 학술지 | 32 | 16 | 0 | opacity_zero | https://journal.unucirebon.ac.id/index.php/asf (2026-10-12~13)<br>https://journal.unucirebon.ac.id/index.php/ijpess/index (2026-10-08)<br>https://journal.unucirebon.ac.id/index.php/jakir (2026-10-12~13)<br>https://journal.unucirebon.ac.id/index.php/judicial (2026-10-12~13) |
| oyostate.gov.ng | 나이지리아 오요주 정부 | 27 | 20 | 0 | color_matches_bg | https://oyostate.gov.ng (2026-10-08) |
| revistas.ufrj.br | 브라질 연방 리우데자네이루대 학술지 | 18 | 17 | 0 | opacity_zero | https://revistas.ufrj.br/index.php/dilemas/index (2026-10-08) |
| ojs.udb.ac.id | 인도네시아 대학 학술지 | 12 | 8 | 0 | color_matches_bg, opacity_zero | https://ojs.udb.ac.id (2026-10-08)<br>https://ojs.udb.ac.id/DJP (2026-10-12~13) |
| ejurnal.unisri.ac.id | 인도네시아 대학 학술지 | 11 | 10 | 0 | color_matches_bg | https://ejurnal.unisri.ac.id/index.php/jpaud (2026-10-08)<br>https://ejurnal.unisri.ac.id/index.php/jtpr (2026-10-08) |
| bestjournal.untad.ac.id | 인도네시아 대학 학술지 | 10 | 10 | 0 | color_matches_bg | https://bestjournal.untad.ac.id/index.php/sciencetech (2026-10-08) |
| kma.ac.th | 태국 교육기관(ac.th) | 10 | 10 | 0 | color_alpha_zero | https://kma.ac.th (2026-10-12~13) |
| ojs.uhnsugriwa.ac.id | 인도네시아 대학 학술지 | 9 | 9 | 0 | opacity_zero | https://ojs.uhnsugriwa.ac.id/index.php/jpr (2026-10-08) |
| ojs.stiem-bongaya.ac.id | 인도네시아 STIEM 봉가야 학술지 | 6 | 6 | 2 | color_alpha_zero, color_matches_bg, opacity_zero | https://ojs.stiem-bongaya.ac.id/BJRA (2026-10-12~13)<br>https://ojs.stiem-bongaya.ac.id/BJRM (2026-10-12~13) |
| jitekin-upiyptk.org | 인도네시아 대학 학술지 | 3 | 3 | 0 | opacity_zero | https://jitekin-upiyptk.org/ojs/index.php/Teknologi (2026-10-08) |
| journal.ar-raniry.ac.id | 인도네시아 UIN 아르라니리 학술지 | 3 | 2 | 0 | opacity_zero | https://journal.ar-raniry.ac.id/index.php/ojs-training (2026-10-12~13) |
| journal.iaincurup.ac.id | 인도네시아 대학 학술지 | 3 | 3 | 0 | opacity_zero | https://journal.iaincurup.ac.id/index.php/disclosure (2026-10-08) |
| jurnal.polteknaker.ac.id | 인도네시아 노동폴리텍 학술지 | 3 | 3 | 0 | color_matches_bg | https://jurnal.polteknaker.ac.id/index.php/jpk (2026-10-12~13) |
| jurnal.unigo.ac.id | 인도네시아 대학 학술지 | 3 | 3 | 0 | opacity_zero | https://jurnal.unigo.ac.id/gjise (2026-10-08) |
| jurnal.unimed.ac.id | 인도네시아 메단국립대 학술지 | 3 | 3 | 0 | opacity_zero | https://jurnal.unimed.ac.id/2012/index.php/tgeo/manuscripttemplate (2026-10-12~13) |
| periodicos.unimontes.br | 브라질 몬치스클라루스대 학술지 | 3 | 3 | 0 | opacity_zero | https://www.periodicos.unimontes.br/index.php/caminhosdahistoria (2026-10-08) |
| e-journal.upr.ac.id | 인도네시아 팔랑카라야대 학술지 | 2 | 2 | 0 | color_alpha_zero | https://e-journal.upr.ac.id/index.php/JPTS (2026-10-08) |
| galuhvirtual.ciamiskab.go.id | 인도네시아 치아미스군 정부 | 1 | 1 | 0 | color_matches_bg | https://galuhvirtual.ciamiskab.go.id (2026-10-08) |
| journal.ibrahimy.ac.id | 인도네시아 대학 학술지 | 1 | 1 | 0 | color_matches_bg | https://journal.ibrahimy.ac.id/index.php/JSAPI (2026-10-08) |
| journal.uinmataram.ac.id | 인도네시아 UIN 마타람 학술지 | 1 | 1 | 0 | color_alpha_zero | https://journal.uinmataram.ac.id/index.php/schemata (2026-10-08) |
| jurnal.ulb.ac.id | 인도네시아 대학 학술지 | 1 | 1 | 0 | color_matches_bg | https://jurnal.ulb.ac.id/index.php/advokasi (2026-10-08) |
| ejournal.unp.ac.id | 인도네시아 파당국립대 학술지 | 0 | 0 | 20 | color_matches_bg | https://ejournal.unp.ac.id/index.php/komposisi/about (2026-10-12~13) |

## 부록 B. 기본셋 샘플별 출처 (232건)

`transparent_real_test_rec20.yaml`의 모든 샘플. id는 전체판과 같다. 각 샘플의 `source`·`origin.url` 필드에도 같은 URL이 들어 있다.

| id | subtype | 사이트 | 숨겨진 문구(evidence_text) | 원본 페이지 URL | 수집일 |
|---|---|---|---|---|---|
| TR-RT-0001 | color_matches_bg | bestjournal.untad.ac.id | mahjong ways 2 | https://bestjournal.untad.ac.id/index.php/sciencetech | 2026-10-08 |
| TR-RT-0002 | color_matches_bg | bestjournal.untad.ac.id | yuantoto | https://bestjournal.untad.ac.id/index.php/sciencetech | 2026-10-08 |
| TR-RT-0005 | color_matches_bg | bestjournal.untad.ac.id | slot gacor | https://bestjournal.untad.ac.id/index.php/sciencetech | 2026-10-08 |
| TR-RT-0006 | color_matches_bg | bestjournal.untad.ac.id | slot 4D | https://bestjournal.untad.ac.id/index.php/sciencetech | 2026-10-08 |
| TR-RT-0009 | color_matches_bg | bestjournal.untad.ac.id | parlay | https://bestjournal.untad.ac.id/index.php/sciencetech | 2026-10-08 |
| TR-RT-0010 | color_matches_bg | bestjournal.untad.ac.id | slot777 | https://bestjournal.untad.ac.id/index.php/sciencetech | 2026-10-08 |
| TR-RT-0003 | color_matches_bg | bestjournal.untad.ac.id | yuantoto | https://bestjournal.untad.ac.id/index.php/sciencetech | 2026-10-08 |
| TR-RT-0004 | color_matches_bg | bestjournal.untad.ac.id | yuantoto | https://bestjournal.untad.ac.id/index.php/sciencetech | 2026-10-08 |
| TR-RT-0007 | color_matches_bg | bestjournal.untad.ac.id | slot gacor | https://bestjournal.untad.ac.id/index.php/sciencetech | 2026-10-08 |
| TR-RT-0008 | color_matches_bg | bestjournal.untad.ac.id | SLOT GACOR | https://bestjournal.untad.ac.id/index.php/sciencetech | 2026-10-08 |
| TR-RT-0011 | opacity_zero | dinkopumkm.endekab.go.id | kencang77 | https://dinkopumkm.endekab.go.id | 2026-10-08 |
| TR-RT-0012 | opacity_zero | dinkopumkm.endekab.go.id | situs slot gacor | https://dinkopumkm.endekab.go.id | 2026-10-08 |
| TR-RT-0014 | opacity_zero | dinkopumkm.endekab.go.id | Tinjauan Sosio Ekonomi Judi Online | https://dinkopumkm.endekab.go.id | 2026-10-08 |
| TR-RT-0015 | opacity_zero | dinkopumkm.endekab.go.id | Bahaya Game Digital Mirip Judi | https://dinkopumkm.endekab.go.id | 2026-10-08 |
| TR-RT-0016 | opacity_zero | dinkopumkm.endekab.go.id | Tanda Perilaku Adiktif Judi Online | https://dinkopumkm.endekab.go.id | 2026-10-08 |
| TR-RT-0017 | opacity_zero | dinkopumkm.endekab.go.id | Bahaya Mengejar Kekalahan Slot Online | https://dinkopumkm.endekab.go.id | 2026-10-08 |
| TR-RT-0018 | opacity_zero | dinkopumkm.endekab.go.id | Pandangan Syariat Dampak Hasil Judi | https://dinkopumkm.endekab.go.id | 2026-10-08 |
| TR-RT-0019 | opacity_zero | dinkopumkm.endekab.go.id | Analisis Kesehatan Mental Pelarian Slot | https://dinkopumkm.endekab.go.id | 2026-10-08 |
| TR-RT-0020 | opacity_zero | dinkopumkm.endekab.go.id | Bahaya Slot Online Merusak Keluarga | https://dinkopumkm.endekab.go.id | 2026-10-08 |
| TR-RT-0021 | opacity_zero | dinkopumkm.endekab.go.id | Efek Kecanduan Judi Pada Otak | https://dinkopumkm.endekab.go.id | 2026-10-08 |
| TR-RT-0022 | opacity_zero | dinkopumkm.endekab.go.id | Batas Etis Hukum Judi Islam | https://dinkopumkm.endekab.go.id | 2026-10-08 |
| TR-RT-0023 | opacity_zero | dinkopumkm.endekab.go.id | Langkah Awal Pemulihan Berhenti Judi | https://dinkopumkm.endekab.go.id | 2026-10-08 |
| TR-RT-0024 | opacity_zero | dinkopumkm.endekab.go.id | Bahaya Berjudi Berkedok Game Digital | https://dinkopumkm.endekab.go.id | 2026-10-08 |
| TR-RT-0025 | opacity_zero | dinkopumkm.endekab.go.id | Membangun Self Control Bebas Slot | https://dinkopumkm.endekab.go.id | 2026-10-08 |
| TR-RT-0026 | opacity_zero | dinkopumkm.endekab.go.id | Algoritma Slot Menang Jangka Panjang | https://dinkopumkm.endekab.go.id | 2026-10-08 |
| TR-RT-0027 | opacity_zero | dinkopumkm.endekab.go.id | Bahaya Chasing Losses Slot Online | https://dinkopumkm.endekab.go.id | 2026-10-08 |
| TR-RT-0028 | opacity_zero | dinkopumkm.endekab.go.id | Pengingat Prioritas Ibadah Bahaya Slot | https://dinkopumkm.endekab.go.id | 2026-10-08 |
| TR-RT-0029 | opacity_zero | dinkopumkm.endekab.go.id | Menghentikan Kebiasaan Mengejar Kekalahan Judi | https://dinkopumkm.endekab.go.id | 2026-10-08 |
| TR-RT-0030 | opacity_zero | dinkopumkm.endekab.go.id | Baccarat Poker Slot Digemari Anak Muda | https://dinkopumkm.endekab.go.id | 2026-10-08 |
| TR-RT-0031 | opacity_zero | dinkopumkm.endekab.go.id | Pinjol Modal Judi Ujungnya Jurang | https://dinkopumkm.endekab.go.id | 2026-10-08 |
| TR-RT-0155 | color_alpha_zero | e-journal.upr.ac.id | gacor | https://e-journal.upr.ac.id/index.php/JPTS | 2026-10-08 |
| TR-RT-0156 | color_alpha_zero | e-journal.upr.ac.id | ABC1131 | https://e-journal.upr.ac.id/index.php/JPTS | 2026-10-08 |
| TR-RT-0157 | color_matches_bg | ejurnal.unisri.ac.id | kampungbet | https://ejurnal.unisri.ac.id/index.php/jpaud | 2026-10-08 |
| TR-RT-0158 | color_matches_bg | ejurnal.unisri.ac.id | situs toto | https://ejurnal.unisri.ac.id/index.php/jpaud | 2026-10-08 |
| TR-RT-0159 | color_matches_bg | ejurnal.unisri.ac.id | susterslot | https://ejurnal.unisri.ac.id/index.php/jpaud | 2026-10-08 |
| TR-RT-0163 | color_matches_bg | ejurnal.unisri.ac.id | Toto | https://ejurnal.unisri.ac.id/index.php/jpaud | 2026-10-08 |
| TR-RT-0164 | color_matches_bg | ejurnal.unisri.ac.id | 838win | https://ejurnal.unisri.ac.id/index.php/jpaud | 2026-10-08 |
| TR-RT-0165 | color_matches_bg | ejurnal.unisri.ac.id | tobrut888 | https://ejurnal.unisri.ac.id/index.php/jtpr | 2026-10-08 |
| TR-RT-0166 | color_matches_bg | ejurnal.unisri.ac.id | kokitoto | https://ejurnal.unisri.ac.id/index.php/jtpr | 2026-10-08 |
| TR-RT-0167 | color_matches_bg | ejurnal.unisri.ac.id | slot server thailand | https://ejurnal.unisri.ac.id/index.php/jtpr | 2026-10-08 |
| TR-RT-0160 | color_matches_bg | ejurnal.unisri.ac.id | susterslot | https://ejurnal.unisri.ac.id/index.php/jpaud | 2026-10-08 |
| TR-RT-0162 | color_matches_bg | ejurnal.unisri.ac.id | susterslot | https://ejurnal.unisri.ac.id/index.php/jpaud | 2026-10-08 |
| TR-RT-0168 | color_matches_bg | galuhvirtual.ciamiskab.go.id | situs toto | https://galuhvirtual.ciamiskab.go.id | 2026-10-08 |
| TR-RT-0169 | opacity_zero | jitekin-upiyptk.org | EROPA99 Slot | https://jitekin-upiyptk.org/ojs/index.php/Teknologi | 2026-10-08 |
| TR-RT-0170 | opacity_zero | jitekin-upiyptk.org | BEST 188 | https://jitekin-upiyptk.org/ojs/index.php/Teknologi | 2026-10-08 |
| TR-RT-0171 | opacity_zero | jitekin-upiyptk.org | geber88 | https://jitekin-upiyptk.org/ojs/index.php/Teknologi | 2026-10-08 |
| TR-RT-0173 | opacity_zero | journal.iaincurup.ac.id | 7meter parlay | https://journal.iaincurup.ac.id/index.php/disclosure | 2026-10-08 |
| TR-RT-0174 | opacity_zero | journal.iaincurup.ac.id | 7meter sbobet | https://journal.iaincurup.ac.id/index.php/disclosure | 2026-10-08 |
| TR-RT-0172 | opacity_zero | journal.iaincurup.ac.id | deposit pulsa | https://journal.iaincurup.ac.id/index.php/disclosure | 2026-10-08 |
| TR-RT-0175 | color_matches_bg | journal.ibrahimy.ac.id | Garuda888 | https://journal.ibrahimy.ac.id/index.php/JSAPI | 2026-10-08 |
| TR-RT-0176 | color_alpha_zero | journal.uinmataram.ac.id | slot online | https://journal.uinmataram.ac.id/index.php/schemata | 2026-10-08 |
| TR-RT-0177 | opacity_zero | journal.unucirebon.ac.id | slot gacor | https://journal.unucirebon.ac.id/index.php/ijpess/index | 2026-10-08 |
| TR-RT-0178 | opacity_zero | journal.unucirebon.ac.id | slot88 | https://journal.unucirebon.ac.id/index.php/ijpess/index | 2026-10-08 |
| TR-RT-0179 | opacity_zero | journal.unucirebon.ac.id | slot online | https://journal.unucirebon.ac.id/index.php/ijpess/index | 2026-10-08 |
| TR-RT-0180 | opacity_zero | journal.unucirebon.ac.id | slot indonesia | https://journal.unucirebon.ac.id/index.php/ijpess/index | 2026-10-08 |
| TR-RT-0181 | opacity_zero | journal.unucirebon.ac.id | idnslot | https://journal.unucirebon.ac.id/index.php/ijpess/index | 2026-10-08 |
| TR-RT-0182 | opacity_zero | journal.unucirebon.ac.id | slot thailand | https://journal.unucirebon.ac.id/index.php/ijpess/index | 2026-10-08 |
| TR-RT-0183 | opacity_zero | journal.unucirebon.ac.id | slot777 | https://journal.unucirebon.ac.id/index.php/ijpess/index | 2026-10-08 |
| TR-RT-0184 | opacity_zero | journal.unucirebon.ac.id | slot88 | https://journal.unucirebon.ac.id/index.php/ijpess/index | 2026-10-08 |
| TR-RT-0350 | opacity_zero | journal.unucirebon.ac.id | slot gacor | https://journal.unucirebon.ac.id/index.php/jakir | 2026-10-12~13 |
| TR-RT-0351 | opacity_zero | journal.unucirebon.ac.id | slot88 | https://journal.unucirebon.ac.id/index.php/jakir | 2026-10-12~13 |
| TR-RT-0352 | opacity_zero | journal.unucirebon.ac.id | slot online | https://journal.unucirebon.ac.id/index.php/jakir | 2026-10-12~13 |
| TR-RT-0353 | opacity_zero | journal.unucirebon.ac.id | slot indonesia | https://journal.unucirebon.ac.id/index.php/jakir | 2026-10-12~13 |
| TR-RT-0354 | opacity_zero | journal.unucirebon.ac.id | idnslot | https://journal.unucirebon.ac.id/index.php/jakir | 2026-10-12~13 |
| TR-RT-0355 | opacity_zero | journal.unucirebon.ac.id | slot thailand | https://journal.unucirebon.ac.id/index.php/jakir | 2026-10-12~13 |
| TR-RT-0356 | opacity_zero | journal.unucirebon.ac.id | slot777 | https://journal.unucirebon.ac.id/index.php/jakir | 2026-10-12~13 |
| TR-RT-0357 | opacity_zero | journal.unucirebon.ac.id | slot88 | https://journal.unucirebon.ac.id/index.php/jakir | 2026-10-12~13 |
| TR-RT-0185 | color_matches_bg | jurnal.ulb.ac.id | HOKI138 | https://jurnal.ulb.ac.id/index.php/advokasi | 2026-10-08 |
| TR-RT-0186 | opacity_zero | jurnal.unigo.ac.id | toto slot | https://jurnal.unigo.ac.id/gjise | 2026-10-08 |
| TR-RT-0187 | opacity_zero | jurnal.unigo.ac.id | slot qris | https://jurnal.unigo.ac.id/gjise | 2026-10-08 |
| TR-RT-0188 | opacity_zero | jurnal.unigo.ac.id | OKESLOT | https://jurnal.unigo.ac.id/gjise | 2026-10-08 |
| TR-RT-0189 | opacity_zero | mibaida.sch.id | psk casino aplikacija | https://mibaida.sch.id | 2026-10-08 |
| TR-RT-0190 | opacity_zero | mibaida.sch.id | Le casino en ligne Stake s’est impose comme une reference in | https://mibaida.sch.id | 2026-10-08 |
| TR-RT-0191 | opacity_zero | mibaida.sch.id | stake code | https://mibaida.sch.id | 2026-10-08 |
| TR-RT-0192 | opacity_zero | mibaida.sch.id | mrbit rotiri fara depunere | https://mibaida.sch.id | 2026-10-08 |
| TR-RT-0193 | opacity_zero | mibaida.sch.id | Platforma se distinge prin interfata moderna si intuitiva, c | https://mibaida.sch.id | 2026-10-08 |
| TR-RT-0194 | opacity_zero | mibaida.sch.id | Dlaczego fireball casino przyciąga graczy z całej Polski? | https://mibaida.sch.id | 2026-10-08 |
| TR-RT-0195 | opacity_zero | mibaida.sch.id | fireball casino kod promocyjny bez depozytu | https://mibaida.sch.id | 2026-10-08 |
| TR-RT-0196 | opacity_zero | mibaida.sch.id | stake pba | https://mibaida.sch.id | 2026-10-08 |
| TR-RT-0197 | opacity_zero | mibaida.sch.id | juegos de casino | https://mibaida.sch.id | 2026-10-08 |
| TR-RT-0198 | opacity_zero | mibaida.sch.id | La ruleta es uno de los juegos más emblemáticos que existen  | https://mibaida.sch.id | 2026-10-08 |
| TR-RT-0199 | opacity_zero | mibaida.sch.id | Explorando la experiencia de juego en TodoSlots | https://mibaida.sch.id | 2026-10-08 |
| TR-RT-0200 | opacity_zero | mibaida.sch.id | El mercado de los casinos digitales ha crecido exponencialme | https://mibaida.sch.id | 2026-10-08 |
| TR-RT-0201 | opacity_zero | mibaida.sch.id | todoslots goldenpark gratis | https://mibaida.sch.id | 2026-10-08 |
| TR-RT-0202 | opacity_zero | mibaida.sch.id | gratogana casino | https://mibaida.sch.id | 2026-10-08 |
| TR-RT-0203 | opacity_zero | mibaida.sch.id | Wszystko co warto wiedzieć o Total Casino | https://mibaida.sch.id | 2026-10-08 |
| TR-RT-0204 | opacity_zero | mibaida.sch.id | casino total | https://mibaida.sch.id | 2026-10-08 |
| TR-RT-0205 | opacity_zero | mibaida.sch.id | nv casino bonus | https://mibaida.sch.id | 2026-10-08 |
| TR-RT-0206 | opacity_zero | mibaida.sch.id | Dlaczego Bison Casino przyciąga polskich graczy? | https://mibaida.sch.id | 2026-10-08 |
| TR-RT-0207 | opacity_zero | mibaida.sch.id | bison casino 2 | https://mibaida.sch.id | 2026-10-08 |
| TR-RT-0208 | opacity_zero | mibaida.sch.id | W kwestii bezpieczeństwa, Bison Casino stawia na zaawansowan | https://mibaida.sch.id | 2026-10-08 |
| TR-RT-0225 | color_matches_bg | ojs.udb.ac.id | link slot gacor | https://ojs.udb.ac.id | 2026-10-08 |
| TR-RT-0438 | opacity_zero | ojs.udb.ac.id | togel online | https://ojs.udb.ac.id/DJP | 2026-10-12~13 |
| TR-RT-0226 | color_matches_bg | ojs.udb.ac.id | slot | https://ojs.udb.ac.id | 2026-10-08 |
| TR-RT-0439 | opacity_zero | ojs.udb.ac.id | CARAWD88 gacor | https://ojs.udb.ac.id/DJP | 2026-10-12~13 |
| TR-RT-0440 | opacity_zero | ojs.udb.ac.id | slot gacor gampang menang | https://ojs.udb.ac.id/DJP | 2026-10-12~13 |
| TR-RT-0441 | opacity_zero | ojs.udb.ac.id | slot gacor | https://ojs.udb.ac.id/DJP | 2026-10-12~13 |
| TR-RT-0437 | opacity_zero | ojs.udb.ac.id | deposit pulsa | https://ojs.udb.ac.id/DJP | 2026-10-12~13 |
| TR-RT-0443 | opacity_zero | ojs.udb.ac.id | slot | https://ojs.udb.ac.id/DJP | 2026-10-12~13 |
| TR-RT-0227 | opacity_zero | ojs.uhnsugriwa.ac.id | LGO99 Deposit Qris | https://ojs.uhnsugriwa.ac.id/index.php/jpr | 2026-10-08 |
| TR-RT-0228 | opacity_zero | ojs.uhnsugriwa.ac.id | CARAWD88 | https://ojs.uhnsugriwa.ac.id/index.php/jpr | 2026-10-08 |
| TR-RT-0229 | opacity_zero | ojs.uhnsugriwa.ac.id | hemat138 slot | https://ojs.uhnsugriwa.ac.id/index.php/jpr | 2026-10-08 |
| TR-RT-0230 | opacity_zero | ojs.uhnsugriwa.ac.id | bandar togel online | https://ojs.uhnsugriwa.ac.id/index.php/jpr | 2026-10-08 |
| TR-RT-0231 | opacity_zero | ojs.uhnsugriwa.ac.id | toto togel online | https://ojs.uhnsugriwa.ac.id/index.php/jpr | 2026-10-08 |
| TR-RT-0232 | opacity_zero | ojs.uhnsugriwa.ac.id | slot | https://ojs.uhnsugriwa.ac.id/index.php/jpr | 2026-10-08 |
| TR-RT-0233 | opacity_zero | ojs.uhnsugriwa.ac.id | bolaslot99 | https://ojs.uhnsugriwa.ac.id/index.php/jpr | 2026-10-08 |
| TR-RT-0234 | opacity_zero | ojs.uhnsugriwa.ac.id | demo slot | https://ojs.uhnsugriwa.ac.id/index.php/jpr | 2026-10-08 |
| TR-RT-0235 | opacity_zero | ojs.uhnsugriwa.ac.id | slot pulsa | https://ojs.uhnsugriwa.ac.id/index.php/jpr | 2026-10-08 |
| TR-RT-0236 | color_matches_bg | oyostate.gov.ng | samudrabet | https://oyostate.gov.ng | 2026-10-08 |
| TR-RT-0237 | color_matches_bg | oyostate.gov.ng | officialbro138.com | https://oyostate.gov.ng | 2026-10-08 |
| TR-RT-0238 | color_matches_bg | oyostate.gov.ng | officialbosswin168.com | https://oyostate.gov.ng | 2026-10-08 |
| TR-RT-0239 | color_matches_bg | oyostate.gov.ng | officialjuraganslot.com | https://oyostate.gov.ng | 2026-10-08 |
| TR-RT-0240 | color_matches_bg | oyostate.gov.ng | officialalbaslot.com | https://oyostate.gov.ng | 2026-10-08 |
| TR-RT-0241 | color_matches_bg | oyostate.gov.ng | garasislotofficial.com | https://oyostate.gov.ng | 2026-10-08 |
| TR-RT-0242 | color_matches_bg | oyostate.gov.ng | officialsoju88.com | https://oyostate.gov.ng | 2026-10-08 |
| TR-RT-0243 | color_matches_bg | oyostate.gov.ng | officialsupraslot.com | https://oyostate.gov.ng | 2026-10-08 |
| TR-RT-0245 | color_matches_bg | oyostate.gov.ng | officialnusantara88.com | https://oyostate.gov.ng | 2026-10-08 |
| TR-RT-0247 | color_matches_bg | oyostate.gov.ng | merdekawinofficial.com | https://oyostate.gov.ng | 2026-10-08 |
| TR-RT-0249 | color_matches_bg | oyostate.gov.ng | mamibetofficial.com | https://oyostate.gov.ng | 2026-10-08 |
| TR-RT-0250 | color_matches_bg | oyostate.gov.ng | probet88loginresmi.com | https://oyostate.gov.ng | 2026-10-08 |
| TR-RT-0251 | color_matches_bg | oyostate.gov.ng | mahkotaslotlinklogin.com | https://oyostate.gov.ng | 2026-10-08 |
| TR-RT-0252 | color_matches_bg | oyostate.gov.ng | hbowinofficial.com | https://oyostate.gov.ng | 2026-10-08 |
| TR-RT-0254 | color_matches_bg | oyostate.gov.ng | ibetslotasli.com | https://oyostate.gov.ng | 2026-10-08 |
| TR-RT-0256 | color_matches_bg | oyostate.gov.ng | sihokislotlogin.com | https://oyostate.gov.ng | 2026-10-08 |
| TR-RT-0262 | color_matches_bg | oyostate.gov.ng | pamanslotofficial.com | https://oyostate.gov.ng | 2026-10-08 |
| TR-RT-0244 | color_matches_bg | oyostate.gov.ng | ajaib88resmi.com | https://oyostate.gov.ng | 2026-10-08 |
| TR-RT-0246 | color_matches_bg | oyostate.gov.ng | usaha188resmi.com | https://oyostate.gov.ng | 2026-10-08 |
| TR-RT-0248 | color_matches_bg | oyostate.gov.ng | merdeka777alternatif.com | https://oyostate.gov.ng | 2026-10-08 |
| TR-RT-0263 | opacity_zero | revistas.ufrj.br | slot demo mahjong ways | https://revistas.ufrj.br/index.php/dilemas/index | 2026-10-08 |
| TR-RT-0264 | opacity_zero | revistas.ufrj.br | kenzobet | https://revistas.ufrj.br/index.php/dilemas/index | 2026-10-08 |
| TR-RT-0266 | opacity_zero | revistas.ufrj.br | kenzototo | https://revistas.ufrj.br/index.php/dilemas/index | 2026-10-08 |
| TR-RT-0268 | opacity_zero | revistas.ufrj.br | slot gacor | https://revistas.ufrj.br/index.php/dilemas/index | 2026-10-08 |
| TR-RT-0271 | opacity_zero | revistas.ufrj.br | Slot Demo | https://revistas.ufrj.br/index.php/dilemas/index | 2026-10-08 |
| TR-RT-0272 | opacity_zero | revistas.ufrj.br | slot pulsa | https://revistas.ufrj.br/index.php/dilemas/index | 2026-10-08 |
| TR-RT-0273 | opacity_zero | revistas.ufrj.br | nagacor181 | https://revistas.ufrj.br/index.php/dilemas/index | 2026-10-08 |
| TR-RT-0274 | opacity_zero | revistas.ufrj.br | roma77 | https://revistas.ufrj.br/index.php/dilemas/index | 2026-10-08 |
| TR-RT-0276 | opacity_zero | revistas.ufrj.br | toto slot gacor | https://revistas.ufrj.br/index.php/dilemas/index | 2026-10-08 |
| TR-RT-0277 | opacity_zero | revistas.ufrj.br | hoki99 | https://revistas.ufrj.br/index.php/dilemas/index | 2026-10-08 |
| TR-RT-0269 | opacity_zero | revistas.ufrj.br | deposit pulsa | https://revistas.ufrj.br/index.php/dilemas/index | 2026-10-08 |
| TR-RT-0267 | opacity_zero | revistas.ufrj.br | kenzototo | https://revistas.ufrj.br/index.php/dilemas/index | 2026-10-08 |
| TR-RT-0270 | opacity_zero | revistas.ufrj.br | kenzototo | https://revistas.ufrj.br/index.php/dilemas/index | 2026-10-08 |
| TR-RT-0275 | opacity_zero | revistas.ufrj.br | roma77 | https://revistas.ufrj.br/index.php/dilemas/index | 2026-10-08 |
| TR-RT-0278 | opacity_zero | revistas.ufrj.br | hoki99 | https://revistas.ufrj.br/index.php/dilemas/index | 2026-10-08 |
| TR-RT-0279 | opacity_zero | revistas.ufrj.br | hoki99 | https://revistas.ufrj.br/index.php/dilemas/index | 2026-10-08 |
| TR-RT-0280 | opacity_zero | revistas.ufrj.br | hoki99 | https://revistas.ufrj.br/index.php/dilemas/index | 2026-10-08 |
| TR-RT-0281 | color_matches_bg | syekhnurjati.ac.id | pestotosalak.com | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 |
| TR-RT-0282 | color_matches_bg | syekhnurjati.ac.id | hokiraja | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 |
| TR-RT-0283 | color_matches_bg | syekhnurjati.ac.id | hoki raja | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 |
| TR-RT-0284 | color_matches_bg | syekhnurjati.ac.id | angsa11 | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 |
| TR-RT-0285 | color_matches_bg | syekhnurjati.ac.id | Bmw777 | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 |
| TR-RT-0286 | color_matches_bg | syekhnurjati.ac.id | toto slot | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 |
| TR-RT-0288 | color_matches_bg | syekhnurjati.ac.id | link gacor | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 |
| TR-RT-0289 | color_matches_bg | syekhnurjati.ac.id | slot gacor malam ini | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 |
| TR-RT-0290 | color_matches_bg | syekhnurjati.ac.id | Pg slot | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 |
| TR-RT-0291 | color_matches_bg | syekhnurjati.ac.id | slot88 | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 |
| TR-RT-0292 | color_matches_bg | syekhnurjati.ac.id | situs slot777 | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 |
| TR-RT-0294 | color_matches_bg | syekhnurjati.ac.id | pgslot | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 |
| TR-RT-0295 | color_matches_bg | syekhnurjati.ac.id | slot gacor | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 |
| TR-RT-0297 | color_matches_bg | syekhnurjati.ac.id | situs slot gacor | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 |
| TR-RT-0301 | color_matches_bg | syekhnurjati.ac.id | cipit88 | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 |
| TR-RT-0303 | color_matches_bg | syekhnurjati.ac.id | yuantoto | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 |
| TR-RT-0306 | color_matches_bg | syekhnurjati.ac.id | slot depo 5k | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 |
| TR-RT-0307 | color_matches_bg | syekhnurjati.ac.id | bosgacor | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 |
| TR-RT-0311 | color_matches_bg | syekhnurjati.ac.id | sbobet | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 |
| TR-RT-0315 | color_matches_bg | syekhnurjati.ac.id | situs toto | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 |
| TR-RT-0336 | opacity_zero | periodicos.unimontes.br | kenzobet | https://www.periodicos.unimontes.br/index.php/caminhosdahistoria | 2026-10-08 |
| TR-RT-0337 | opacity_zero | periodicos.unimontes.br | kenzototo | https://www.periodicos.unimontes.br/index.php/caminhosdahistoria | 2026-10-08 |
| TR-RT-0338 | opacity_zero | periodicos.unimontes.br | kenzototo | https://www.periodicos.unimontes.br/index.php/caminhosdahistoria | 2026-10-08 |
| TR-RT-0340 | opacity_zero | journal.ar-raniry.ac.id | slot online | https://journal.ar-raniry.ac.id/index.php/ojs-training | 2026-10-12~13 |
| TR-RT-0341 | opacity_zero | journal.ar-raniry.ac.id | partaitogel | https://journal.ar-raniry.ac.id/index.php/ojs-training | 2026-10-12~13 |
| TR-RT-0366 | color_matches_bg | jurnal.polteknaker.ac.id | slot maxwin | https://jurnal.polteknaker.ac.id/index.php/jpk | 2026-10-12~13 |
| TR-RT-0367 | color_matches_bg | jurnal.polteknaker.ac.id | slot gacor | https://jurnal.polteknaker.ac.id/index.php/jpk | 2026-10-12~13 |
| TR-RT-0368 | color_matches_bg | jurnal.polteknaker.ac.id | tiga333 | https://jurnal.polteknaker.ac.id/index.php/jpk | 2026-10-12~13 |
| TR-RT-0369 | opacity_zero | jurnal.unimed.ac.id | slot pulsa | https://jurnal.unimed.ac.id/2012/index.php/tgeo/manuscripttemplate | 2026-10-12~13 |
| TR-RT-0370 | opacity_zero | jurnal.unimed.ac.id | 7meter parlay | https://jurnal.unimed.ac.id/2012/index.php/tgeo/manuscripttemplate | 2026-10-12~13 |
| TR-RT-0371 | opacity_zero | jurnal.unimed.ac.id | 7meter sbobet | https://jurnal.unimed.ac.id/2012/index.php/tgeo/manuscripttemplate | 2026-10-12~13 |
| TR-RT-0372 | color_alpha_zero | jurnalkonstan.ac.id | maggiemakesitbetter.com | https://jurnalkonstan.ac.id | 2026-10-12~13 |
| TR-RT-0373 | color_alpha_zero | jurnalkonstan.ac.id | cyclowing.com | https://jurnalkonstan.ac.id | 2026-10-12~13 |
| TR-RT-0374 | color_alpha_zero | jurnalkonstan.ac.id | growing-years.net | https://jurnalkonstan.ac.id | 2026-10-12~13 |
| TR-RT-0375 | color_alpha_zero | jurnalkonstan.ac.id | dlja-windows.com | https://jurnalkonstan.ac.id | 2026-10-12~13 |
| TR-RT-0376 | color_alpha_zero | jurnalkonstan.ac.id | windowinstallationmidlandtx.com | https://jurnalkonstan.ac.id | 2026-10-12~13 |
| TR-RT-0377 | color_alpha_zero | jurnalkonstan.ac.id | betasetup.com | https://jurnalkonstan.ac.id | 2026-10-12~13 |
| TR-RT-0378 | color_alpha_zero | jurnalkonstan.ac.id | betflixpr.com | https://jurnalkonstan.ac.id | 2026-10-12~13 |
| TR-RT-0379 | color_alpha_zero | jurnalkonstan.ac.id | windowtintingtoday.com | https://jurnalkonstan.ac.id | 2026-10-12~13 |
| TR-RT-0380 | color_alpha_zero | jurnalkonstan.ac.id | wingsnbags.com | https://jurnalkonstan.ac.id | 2026-10-12~13 |
| TR-RT-0381 | color_alpha_zero | jurnalkonstan.ac.id | thehomewind.com | https://jurnalkonstan.ac.id | 2026-10-12~13 |
| TR-RT-0383 | color_alpha_zero | jurnalkonstan.ac.id | baldwinhillsclassroom.org | https://jurnalkonstan.ac.id | 2026-10-12~13 |
| TR-RT-0384 | color_alpha_zero | jurnalkonstan.ac.id | swindonlightningcheerleading.com | https://jurnalkonstan.ac.id | 2026-10-12~13 |
| TR-RT-0385 | color_alpha_zero | jurnalkonstan.ac.id | gocoastalrowing.com | https://jurnalkonstan.ac.id | 2026-10-12~13 |
| TR-RT-0386 | color_alpha_zero | jurnalkonstan.ac.id | crumpetsteaandsewing.com | https://jurnalkonstan.ac.id | 2026-10-12~13 |
| TR-RT-0387 | color_alpha_zero | jurnalkonstan.ac.id | amp-1tiara4d.xyz | https://jurnalkonstan.ac.id | 2026-10-12~13 |
| TR-RT-0388 | color_alpha_zero | jurnalkonstan.ac.id | lebah4d-amp.com | https://jurnalkonstan.ac.id | 2026-10-12~13 |
| TR-RT-0389 | color_alpha_zero | jurnalkonstan.ac.id | tiara4d-amp.com | https://jurnalkonstan.ac.id | 2026-10-12~13 |
| TR-RT-0390 | color_alpha_zero | jurnalkonstan.ac.id | laris4d-amp.com | https://jurnalkonstan.ac.id | 2026-10-12~13 |
| TR-RT-0391 | color_alpha_zero | jurnalkonstan.ac.id | lebah4d-alternatif.com | https://jurnalkonstan.ac.id | 2026-10-12~13 |
| TR-RT-0392 | color_alpha_zero | jurnalkonstan.ac.id | laris4d-alternatif.com | https://jurnalkonstan.ac.id | 2026-10-12~13 |
| TR-RT-0418 | color_alpha_zero | kma.ac.th | 1win online | https://kma.ac.th | 2026-10-12~13 |
| TR-RT-0419 | color_alpha_zero | kma.ac.th | pinup casino | https://kma.ac.th | 2026-10-12~13 |
| TR-RT-0420 | color_alpha_zero | kma.ac.th | mostbets | https://kma.ac.th | 2026-10-12~13 |
| TR-RT-0421 | color_alpha_zero | kma.ac.th | mostbet kz | https://kma.ac.th | 2026-10-12~13 |
| TR-RT-0422 | color_alpha_zero | kma.ac.th | mosbet casino | https://kma.ac.th | 2026-10-12~13 |
| TR-RT-0423 | color_alpha_zero | kma.ac.th | mosbet | https://kma.ac.th | 2026-10-12~13 |
| TR-RT-0424 | color_alpha_zero | kma.ac.th | pin up casino india | https://kma.ac.th | 2026-10-12~13 |
| TR-RT-0425 | color_alpha_zero | kma.ac.th | mostbet uz | https://kma.ac.th | 2026-10-12~13 |
| TR-RT-0426 | color_alpha_zero | kma.ac.th | mosbet | https://kma.ac.th | 2026-10-12~13 |
| TR-RT-0427 | color_alpha_zero | kma.ac.th | mosbet | https://kma.ac.th | 2026-10-12~13 |
| TR-RT-0429 | opacity_zero | ojs.stiem-bongaya.ac.id | partaitogel | https://ojs.stiem-bongaya.ac.id/BJRM | 2026-10-12~13 |
| TR-RT-0433 | color_alpha_zero | ojs.stiem-bongaya.ac.id | slot gacor | https://ojs.stiem-bongaya.ac.id/BJRM | 2026-10-12~13 |
| TR-RT-0432 | opacity_zero | ojs.stiem-bongaya.ac.id | ups4d | https://ojs.stiem-bongaya.ac.id/BJRM | 2026-10-12~13 |
| TR-RT-0428 | opacity_zero | ojs.stiem-bongaya.ac.id | บาคาร่า | https://ojs.stiem-bongaya.ac.id/BJRM | 2026-10-12~13 |
| TR-RT-0430 | opacity_zero | ojs.stiem-bongaya.ac.id | partaitogel | https://ojs.stiem-bongaya.ac.id/BJRM | 2026-10-12~13 |
| TR-RT-0431 | opacity_zero | ojs.stiem-bongaya.ac.id | partaitogel | https://ojs.stiem-bongaya.ac.id/BJRM | 2026-10-12~13 |
| TR-RT-0444 | color_matches_bg | ejournal.um-sorong.ac.id | rubahtoto | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |
| TR-RT-0446 | color_matches_bg | ejournal.um-sorong.ac.id | idn slot | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |
| TR-RT-0447 | color_matches_bg | ejournal.um-sorong.ac.id | https://yuantoto.tech/ | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |
| TR-RT-0448 | color_matches_bg | ejournal.um-sorong.ac.id | slot deposit 5000 | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |
| TR-RT-0449 | color_matches_bg | ejournal.um-sorong.ac.id | yuantoto | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |
| TR-RT-0451 | color_matches_bg | ejournal.um-sorong.ac.id | slot gacor | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |
| TR-RT-0452 | color_matches_bg | ejournal.um-sorong.ac.id | slot deposit 1000 | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |
| TR-RT-0454 | color_matches_bg | ejournal.um-sorong.ac.id | slot online | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |
| TR-RT-0455 | color_matches_bg | ejournal.um-sorong.ac.id | slot 4D | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |
| TR-RT-0457 | color_matches_bg | ejournal.um-sorong.ac.id | pestoto | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |
| TR-RT-0463 | color_matches_bg | ejournal.um-sorong.ac.id | gading22 | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |
| TR-RT-0464 | color_matches_bg | ejournal.um-sorong.ac.id | mahjong | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |
| TR-RT-0467 | color_matches_bg | ejournal.um-sorong.ac.id | toto slot | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |
| TR-RT-0468 | color_matches_bg | ejournal.um-sorong.ac.id | situs toto | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |
| TR-RT-0472 | color_matches_bg | ejournal.um-sorong.ac.id | sbobet | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |
| TR-RT-0475 | color_matches_bg | ejournal.um-sorong.ac.id | bosgacor | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |
| TR-RT-0478 | color_matches_bg | ejournal.um-sorong.ac.id | slot depo 5k | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |
| TR-RT-0482 | color_matches_bg | ejournal.um-sorong.ac.id | cipit88 | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |
| TR-RT-0485 | color_matches_bg | ejournal.um-sorong.ac.id | medantoto | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |
| TR-RT-0486 | color_matches_bg | ejournal.um-sorong.ac.id | situs slot gacor | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |

## 부록 C. 경계 사례 샘플별 출처 (22건)

`transparent_real_borderline.yaml`. 기본셋에서 뺀 이유는 4절 참고.

| id | subtype | 사이트 | 숨겨진 문구(evidence_text) | 원본 페이지 URL | 수집일 |
|---|---|---|---|---|---|
| TR-RB-0001 | color_matches_bg | ejournal.unp.ac.id | badak178 | https://ejournal.unp.ac.id/index.php/komposisi/about | 2026-10-12~13 |
| TR-RB-0002 | color_matches_bg | ejournal.unp.ac.id | toto | https://ejournal.unp.ac.id/index.php/komposisi/about | 2026-10-12~13 |
| TR-RB-0003 | color_matches_bg | ejournal.unp.ac.id | Bmw777 | https://ejournal.unp.ac.id/index.php/komposisi/about | 2026-10-12~13 |
| TR-RB-0004 | color_matches_bg | ejournal.unp.ac.id | toto slot | https://ejournal.unp.ac.id/index.php/komposisi/about | 2026-10-12~13 |
| TR-RB-0005 | color_matches_bg | ejournal.unp.ac.id | link gacor | https://ejournal.unp.ac.id/index.php/komposisi/about | 2026-10-12~13 |
| TR-RB-0006 | color_matches_bg | ejournal.unp.ac.id | slot gacor malam ini | https://ejournal.unp.ac.id/index.php/komposisi/about | 2026-10-12~13 |
| TR-RB-0007 | color_matches_bg | ejournal.unp.ac.id | Pg slot | https://ejournal.unp.ac.id/index.php/komposisi/about | 2026-10-12~13 |
| TR-RB-0008 | color_matches_bg | ejournal.unp.ac.id | slot88 | https://ejournal.unp.ac.id/index.php/komposisi/about | 2026-10-12~13 |
| TR-RB-0009 | color_matches_bg | ejournal.unp.ac.id | agen slot777 | https://ejournal.unp.ac.id/index.php/komposisi/about | 2026-10-12~13 |
| TR-RB-0010 | color_matches_bg | ejournal.unp.ac.id | pgslot | https://ejournal.unp.ac.id/index.php/komposisi/about | 2026-10-12~13 |
| TR-RB-0011 | color_matches_bg | ejournal.unp.ac.id | slot gacor | https://ejournal.unp.ac.id/index.php/komposisi/about | 2026-10-12~13 |
| TR-RB-0012 | color_matches_bg | ejournal.unp.ac.id | situs slot | https://ejournal.unp.ac.id/index.php/komposisi/about | 2026-10-12~13 |
| TR-RB-0013 | color_matches_bg | ejournal.unp.ac.id | medantoto | https://ejournal.unp.ac.id/index.php/komposisi/about | 2026-10-12~13 |
| TR-RB-0014 | color_matches_bg | ejournal.unp.ac.id | situs slot gacor | https://ejournal.unp.ac.id/index.php/komposisi/about | 2026-10-12~13 |
| TR-RB-0015 | color_matches_bg | ejournal.unp.ac.id | cipit88 | https://ejournal.unp.ac.id/index.php/komposisi/about | 2026-10-12~13 |
| TR-RB-0016 | color_matches_bg | ejournal.unp.ac.id | parlay | https://ejournal.unp.ac.id/index.php/komposisi/about | 2026-10-12~13 |
| TR-RB-0017 | color_matches_bg | ejournal.unp.ac.id | badak178 | https://ejournal.unp.ac.id/index.php/komposisi/about | 2026-10-12~13 |
| TR-RB-0018 | color_matches_bg | ejournal.unp.ac.id | badak178 | https://ejournal.unp.ac.id/index.php/komposisi/about | 2026-10-12~13 |
| TR-RB-0019 | color_matches_bg | ejournal.unp.ac.id | badak178 | https://ejournal.unp.ac.id/index.php/komposisi/about | 2026-10-12~13 |
| TR-RB-0020 | color_matches_bg | ejournal.unp.ac.id | Badak178 | https://ejournal.unp.ac.id/index.php/komposisi/about | 2026-10-12~13 |
| TR-RB-0021 | color_matches_bg | ojs.stiem-bongaya.ac.id | situs togel | https://ojs.stiem-bongaya.ac.id/BJRA | 2026-10-12~13 |
| TR-RB-0022 | color_matches_bg | ojs.stiem-bongaya.ac.id | kampungbet | https://ojs.stiem-bongaya.ac.id/BJRA | 2026-10-12~13 |

## 부록 D. 전체판 샘플별 출처 (541건)

`transparent_real_test_full.yaml`의 모든 샘플. "기본셋" 열이 O이면 기본셋에도 들어 있다.

| id | subtype | 사이트 | 숨겨진 문구(evidence_text) | 원본 페이지 URL | 수집일 | 기본셋 |
|---|---|---|---|---|---|---|
| TR-RT-0001 | color_matches_bg | bestjournal.untad.ac.id | mahjong ways 2 | https://bestjournal.untad.ac.id/index.php/sciencetech | 2026-10-08 | O |
| TR-RT-0002 | color_matches_bg | bestjournal.untad.ac.id | yuantoto | https://bestjournal.untad.ac.id/index.php/sciencetech | 2026-10-08 | O |
| TR-RT-0003 | color_matches_bg | bestjournal.untad.ac.id | yuantoto | https://bestjournal.untad.ac.id/index.php/sciencetech | 2026-10-08 | O |
| TR-RT-0004 | color_matches_bg | bestjournal.untad.ac.id | yuantoto | https://bestjournal.untad.ac.id/index.php/sciencetech | 2026-10-08 | O |
| TR-RT-0005 | color_matches_bg | bestjournal.untad.ac.id | slot gacor | https://bestjournal.untad.ac.id/index.php/sciencetech | 2026-10-08 | O |
| TR-RT-0006 | color_matches_bg | bestjournal.untad.ac.id | slot 4D | https://bestjournal.untad.ac.id/index.php/sciencetech | 2026-10-08 | O |
| TR-RT-0007 | color_matches_bg | bestjournal.untad.ac.id | slot gacor | https://bestjournal.untad.ac.id/index.php/sciencetech | 2026-10-08 | O |
| TR-RT-0008 | color_matches_bg | bestjournal.untad.ac.id | SLOT GACOR | https://bestjournal.untad.ac.id/index.php/sciencetech | 2026-10-08 | O |
| TR-RT-0009 | color_matches_bg | bestjournal.untad.ac.id | parlay | https://bestjournal.untad.ac.id/index.php/sciencetech | 2026-10-08 | O |
| TR-RT-0010 | color_matches_bg | bestjournal.untad.ac.id | slot777 | https://bestjournal.untad.ac.id/index.php/sciencetech | 2026-10-08 | O |
| TR-RT-0011 | opacity_zero | dinkopumkm.endekab.go.id | kencang77 | https://dinkopumkm.endekab.go.id | 2026-10-08 | O |
| TR-RT-0012 | opacity_zero | dinkopumkm.endekab.go.id | situs slot gacor | https://dinkopumkm.endekab.go.id | 2026-10-08 | O |
| TR-RT-0013 | opacity_zero | dinkopumkm.endekab.go.id | kencang77 | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0014 | opacity_zero | dinkopumkm.endekab.go.id | Tinjauan Sosio Ekonomi Judi Online | https://dinkopumkm.endekab.go.id | 2026-10-08 | O |
| TR-RT-0015 | opacity_zero | dinkopumkm.endekab.go.id | Bahaya Game Digital Mirip Judi | https://dinkopumkm.endekab.go.id | 2026-10-08 | O |
| TR-RT-0016 | opacity_zero | dinkopumkm.endekab.go.id | Tanda Perilaku Adiktif Judi Online | https://dinkopumkm.endekab.go.id | 2026-10-08 | O |
| TR-RT-0017 | opacity_zero | dinkopumkm.endekab.go.id | Bahaya Mengejar Kekalahan Slot Online | https://dinkopumkm.endekab.go.id | 2026-10-08 | O |
| TR-RT-0018 | opacity_zero | dinkopumkm.endekab.go.id | Pandangan Syariat Dampak Hasil Judi | https://dinkopumkm.endekab.go.id | 2026-10-08 | O |
| TR-RT-0019 | opacity_zero | dinkopumkm.endekab.go.id | Analisis Kesehatan Mental Pelarian Slot | https://dinkopumkm.endekab.go.id | 2026-10-08 | O |
| TR-RT-0020 | opacity_zero | dinkopumkm.endekab.go.id | Bahaya Slot Online Merusak Keluarga | https://dinkopumkm.endekab.go.id | 2026-10-08 | O |
| TR-RT-0021 | opacity_zero | dinkopumkm.endekab.go.id | Efek Kecanduan Judi Pada Otak | https://dinkopumkm.endekab.go.id | 2026-10-08 | O |
| TR-RT-0022 | opacity_zero | dinkopumkm.endekab.go.id | Batas Etis Hukum Judi Islam | https://dinkopumkm.endekab.go.id | 2026-10-08 | O |
| TR-RT-0023 | opacity_zero | dinkopumkm.endekab.go.id | Langkah Awal Pemulihan Berhenti Judi | https://dinkopumkm.endekab.go.id | 2026-10-08 | O |
| TR-RT-0024 | opacity_zero | dinkopumkm.endekab.go.id | Bahaya Berjudi Berkedok Game Digital | https://dinkopumkm.endekab.go.id | 2026-10-08 | O |
| TR-RT-0025 | opacity_zero | dinkopumkm.endekab.go.id | Membangun Self Control Bebas Slot | https://dinkopumkm.endekab.go.id | 2026-10-08 | O |
| TR-RT-0026 | opacity_zero | dinkopumkm.endekab.go.id | Algoritma Slot Menang Jangka Panjang | https://dinkopumkm.endekab.go.id | 2026-10-08 | O |
| TR-RT-0027 | opacity_zero | dinkopumkm.endekab.go.id | Bahaya Chasing Losses Slot Online | https://dinkopumkm.endekab.go.id | 2026-10-08 | O |
| TR-RT-0028 | opacity_zero | dinkopumkm.endekab.go.id | Pengingat Prioritas Ibadah Bahaya Slot | https://dinkopumkm.endekab.go.id | 2026-10-08 | O |
| TR-RT-0029 | opacity_zero | dinkopumkm.endekab.go.id | Menghentikan Kebiasaan Mengejar Kekalahan Judi | https://dinkopumkm.endekab.go.id | 2026-10-08 | O |
| TR-RT-0030 | opacity_zero | dinkopumkm.endekab.go.id | Baccarat Poker Slot Digemari Anak Muda | https://dinkopumkm.endekab.go.id | 2026-10-08 | O |
| TR-RT-0031 | opacity_zero | dinkopumkm.endekab.go.id | Pinjol Modal Judi Ujungnya Jurang | https://dinkopumkm.endekab.go.id | 2026-10-08 | O |
| TR-RT-0032 | opacity_zero | dinkopumkm.endekab.go.id | Psikologi Hampir Jackpot Bikin Nagih | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0033 | opacity_zero | dinkopumkm.endekab.go.id | Sbobet ke Ruang Sidang: Kehancuran | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0034 | opacity_zero | dinkopumkm.endekab.go.id | Bonus Harian Judi Bikin Nagih | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0035 | opacity_zero | dinkopumkm.endekab.go.id | Judi Online di Grup WhatsApp Keluarga | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0036 | opacity_zero | dinkopumkm.endekab.go.id | Jackpot Palsu Hancurkan Ekonomi Rumah Tangga | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0037 | opacity_zero | dinkopumkm.endekab.go.id | Anak Kos dan Slot Online | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0038 | opacity_zero | dinkopumkm.endekab.go.id | Terapi Kognitif untuk Pecandu Judi | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0039 | opacity_zero | dinkopumkm.endekab.go.id | Masjid dan Kampus Lawan Judi | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0040 | opacity_zero | dinkopumkm.endekab.go.id | Judi Online vs Investasi: Mana Nyata? | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0041 | opacity_zero | dinkopumkm.endekab.go.id | AI Bandar Kuras Kantong Pemain | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0042 | opacity_zero | dinkopumkm.endekab.go.id | Mantan Pecandu Judi Menemukan Jati Diri | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0043 | opacity_zero | dinkopumkm.endekab.go.id | Korban Judi Sulit Cari Bantuan | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0044 | opacity_zero | dinkopumkm.endekab.go.id | Iklan Judi Racuni Generasi Muda | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0045 | opacity_zero | dinkopumkm.endekab.go.id | FOMO Bikin Orang Terjebak Judi | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0046 | opacity_zero | dinkopumkm.endekab.go.id | Maqashid Syariah vs Janji Jackpot | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0047 | opacity_zero | dinkopumkm.endekab.go.id | Gen Z Tolak Jalan Pintas Judi | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0048 | opacity_zero | dinkopumkm.endekab.go.id | Judi Pelarian Stres Pekerja Muda | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0049 | opacity_zero | dinkopumkm.endekab.go.id | Mahjong Ways dan Kemenangan Instan | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0050 | opacity_zero | dinkopumkm.endekab.go.id | Menang Slot Belum Tentu Untung | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0051 | opacity_zero | dinkopumkm.endekab.go.id | Deposit Slot Bukan Modal Usaha | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0052 | opacity_zero | dinkopumkm.endekab.go.id | Risiko Bonus Free Spin Slot | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0053 | opacity_zero | dinkopumkm.endekab.go.id | Promosi Judi dari Konten Maxwin | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0054 | opacity_zero | dinkopumkm.endekab.go.id | Mahjong Ways antara Hiburan Maysir | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0055 | opacity_zero | dinkopumkm.endekab.go.id | Kemenangan Slot Diputar Kembali Lagi | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0056 | opacity_zero | dinkopumkm.endekab.go.id | Judi Online Bukan Jalan Rezeki | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0057 | opacity_zero | dinkopumkm.endekab.go.id | Gaji Berubah Menjadi Saldo Slot | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0058 | opacity_zero | dinkopumkm.endekab.go.id | Penyebar Link Slot Punya Tanggungjawab | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0059 | opacity_zero | dinkopumkm.endekab.go.id | Penghasilan Referral dari Judi Online | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0060 | opacity_zero | dinkopumkm.endekab.go.id | Memahami Promosi Konten Kemenangan Slot | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0061 | opacity_zero | dinkopumkm.endekab.go.id | Deposit Slot Mengganggu Kepercayaan Keluarga | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0062 | opacity_zero | dinkopumkm.endekab.go.id | Literasi Istilah Scatter dan Maxwin | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0063 | opacity_zero | dinkopumkm.endekab.go.id | Konten Bisa Mengenalkan Judi Online | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0064 | opacity_zero | dinkopumkm.endekab.go.id | Bias Kemenangan Slot Media Sosial | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0065 | opacity_zero | dinkopumkm.endekab.go.id | Game Berbayar Tidak Selalu Judi | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0066 | opacity_zero | dinkopumkm.endekab.go.id | pola jam menang ilusi kendali slot | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0067 | opacity_zero | dinkopumkm.endekab.go.id | judi online mengubah pengambilan keputusan | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0068 | opacity_zero | dinkopumkm.endekab.go.id | tanda bahaya judi online mengganggu kehidupan | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0069 | opacity_zero | dinkopumkm.endekab.go.id | alasan ilmiah pemain slot sulit berhenti | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0070 | opacity_zero | dinkopumkm.endekab.go.id | efek suara animasi kemenangan slot | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0071 | opacity_zero | dinkopumkm.endekab.go.id | melindungi keuangan keluarga dari judi online | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0072 | opacity_zero | dinkopumkm.endekab.go.id | menyembunyikan deposit tanda judi online | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0073 | opacity_zero | dinkopumkm.endekab.go.id | istilah cuan dalam judi online | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0074 | opacity_zero | dinkopumkm.endekab.go.id | rasa bosan memicu bermain slot lagi | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0075 | opacity_zero | dinkopumkm.endekab.go.id | judi online merusak kepercayaan keluarga | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0076 | opacity_zero | dinkopumkm.endekab.go.id | gamblers fallacy menjebak pemain judi | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0077 | opacity_zero | dinkopumkm.endekab.go.id | tanda bahaya mengejar sensasi judi online | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0078 | opacity_zero | dinkopumkm.endekab.go.id | cara menolak ajakan bermain judi online | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0079 | opacity_zero | dinkopumkm.endekab.go.id | prediksi pola menang dan jam gacor | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0080 | opacity_zero | dinkopumkm.endekab.go.id | cara memutus akses judi online | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0081 | opacity_zero | dinkopumkm.endekab.go.id | cara membicarakan judi online kepada remaja | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0082 | opacity_zero | dinkopumkm.endekab.go.id | menjaga harta dengan menghindari judi online | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0083 | opacity_zero | dinkopumkm.endekab.go.id | kencang77 | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0084 | opacity_zero | dinkopumkm.endekab.go.id | situs slot gacor | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0085 | opacity_zero | dinkopumkm.endekab.go.id | kencang77 | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0086 | opacity_zero | dinkopumkm.endekab.go.id | Tinjauan Sosio Ekonomi Judi Online | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0087 | opacity_zero | dinkopumkm.endekab.go.id | Bahaya Game Digital Mirip Judi | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0088 | opacity_zero | dinkopumkm.endekab.go.id | Tanda Perilaku Adiktif Judi Online | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0089 | opacity_zero | dinkopumkm.endekab.go.id | Bahaya Mengejar Kekalahan Slot Online | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0090 | opacity_zero | dinkopumkm.endekab.go.id | Pandangan Syariat Dampak Hasil Judi | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0091 | opacity_zero | dinkopumkm.endekab.go.id | Analisis Kesehatan Mental Pelarian Slot | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0092 | opacity_zero | dinkopumkm.endekab.go.id | Bahaya Slot Online Merusak Keluarga | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0093 | opacity_zero | dinkopumkm.endekab.go.id | Efek Kecanduan Judi Pada Otak | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0094 | opacity_zero | dinkopumkm.endekab.go.id | Batas Etis Hukum Judi Islam | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0095 | opacity_zero | dinkopumkm.endekab.go.id | Langkah Awal Pemulihan Berhenti Judi | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0096 | opacity_zero | dinkopumkm.endekab.go.id | Bahaya Berjudi Berkedok Game Digital | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0097 | opacity_zero | dinkopumkm.endekab.go.id | Membangun Self Control Bebas Slot | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0098 | opacity_zero | dinkopumkm.endekab.go.id | Algoritma Slot Menang Jangka Panjang | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0099 | opacity_zero | dinkopumkm.endekab.go.id | Bahaya Chasing Losses Slot Online | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0100 | opacity_zero | dinkopumkm.endekab.go.id | Pengingat Prioritas Ibadah Bahaya Slot | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0101 | opacity_zero | dinkopumkm.endekab.go.id | Menghentikan Kebiasaan Mengejar Kekalahan Judi | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0102 | opacity_zero | dinkopumkm.endekab.go.id | Baccarat Poker Slot Digemari Anak Muda | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0103 | opacity_zero | dinkopumkm.endekab.go.id | Pinjol Modal Judi Ujungnya Jurang | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0104 | opacity_zero | dinkopumkm.endekab.go.id | Psikologi Hampir Jackpot Bikin Nagih | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0105 | opacity_zero | dinkopumkm.endekab.go.id | Sbobet ke Ruang Sidang: Kehancuran | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0106 | opacity_zero | dinkopumkm.endekab.go.id | Bonus Harian Judi Bikin Nagih | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0107 | opacity_zero | dinkopumkm.endekab.go.id | Judi Online di Grup WhatsApp Keluarga | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0108 | opacity_zero | dinkopumkm.endekab.go.id | Jackpot Palsu Hancurkan Ekonomi Rumah Tangga | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0109 | opacity_zero | dinkopumkm.endekab.go.id | Anak Kos dan Slot Online | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0110 | opacity_zero | dinkopumkm.endekab.go.id | Terapi Kognitif untuk Pecandu Judi | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0111 | opacity_zero | dinkopumkm.endekab.go.id | Masjid dan Kampus Lawan Judi | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0112 | opacity_zero | dinkopumkm.endekab.go.id | Judi Online vs Investasi: Mana Nyata? | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0113 | opacity_zero | dinkopumkm.endekab.go.id | AI Bandar Kuras Kantong Pemain | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0114 | opacity_zero | dinkopumkm.endekab.go.id | Mantan Pecandu Judi Menemukan Jati Diri | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0115 | opacity_zero | dinkopumkm.endekab.go.id | Korban Judi Sulit Cari Bantuan | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0116 | opacity_zero | dinkopumkm.endekab.go.id | Iklan Judi Racuni Generasi Muda | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0117 | opacity_zero | dinkopumkm.endekab.go.id | FOMO Bikin Orang Terjebak Judi | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0118 | opacity_zero | dinkopumkm.endekab.go.id | Maqashid Syariah vs Janji Jackpot | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0119 | opacity_zero | dinkopumkm.endekab.go.id | Gen Z Tolak Jalan Pintas Judi | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0120 | opacity_zero | dinkopumkm.endekab.go.id | Judi Pelarian Stres Pekerja Muda | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0121 | opacity_zero | dinkopumkm.endekab.go.id | Mahjong Ways dan Kemenangan Instan | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0122 | opacity_zero | dinkopumkm.endekab.go.id | Menang Slot Belum Tentu Untung | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0123 | opacity_zero | dinkopumkm.endekab.go.id | Deposit Slot Bukan Modal Usaha | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0124 | opacity_zero | dinkopumkm.endekab.go.id | Risiko Bonus Free Spin Slot | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0125 | opacity_zero | dinkopumkm.endekab.go.id | Promosi Judi dari Konten Maxwin | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0126 | opacity_zero | dinkopumkm.endekab.go.id | Mahjong Ways antara Hiburan Maysir | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0127 | opacity_zero | dinkopumkm.endekab.go.id | Kemenangan Slot Diputar Kembali Lagi | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0128 | opacity_zero | dinkopumkm.endekab.go.id | Judi Online Bukan Jalan Rezeki | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0129 | opacity_zero | dinkopumkm.endekab.go.id | Gaji Berubah Menjadi Saldo Slot | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0130 | opacity_zero | dinkopumkm.endekab.go.id | Penyebar Link Slot Punya Tanggungjawab | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0131 | opacity_zero | dinkopumkm.endekab.go.id | Penghasilan Referral dari Judi Online | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0132 | opacity_zero | dinkopumkm.endekab.go.id | Memahami Promosi Konten Kemenangan Slot | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0133 | opacity_zero | dinkopumkm.endekab.go.id | Deposit Slot Mengganggu Kepercayaan Keluarga | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0134 | opacity_zero | dinkopumkm.endekab.go.id | Literasi Istilah Scatter dan Maxwin | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0135 | opacity_zero | dinkopumkm.endekab.go.id | Konten Bisa Mengenalkan Judi Online | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0136 | opacity_zero | dinkopumkm.endekab.go.id | Bias Kemenangan Slot Media Sosial | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0137 | opacity_zero | dinkopumkm.endekab.go.id | Game Berbayar Tidak Selalu Judi | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0138 | opacity_zero | dinkopumkm.endekab.go.id | pola jam menang ilusi kendali slot | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0139 | opacity_zero | dinkopumkm.endekab.go.id | judi online mengubah pengambilan keputusan | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0140 | opacity_zero | dinkopumkm.endekab.go.id | tanda bahaya judi online mengganggu kehidupan | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0141 | opacity_zero | dinkopumkm.endekab.go.id | alasan ilmiah pemain slot sulit berhenti | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0142 | opacity_zero | dinkopumkm.endekab.go.id | efek suara animasi kemenangan slot | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0143 | opacity_zero | dinkopumkm.endekab.go.id | melindungi keuangan keluarga dari judi online | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0144 | opacity_zero | dinkopumkm.endekab.go.id | menyembunyikan deposit tanda judi online | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0145 | opacity_zero | dinkopumkm.endekab.go.id | istilah cuan dalam judi online | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0146 | opacity_zero | dinkopumkm.endekab.go.id | rasa bosan memicu bermain slot lagi | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0147 | opacity_zero | dinkopumkm.endekab.go.id | judi online merusak kepercayaan keluarga | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0148 | opacity_zero | dinkopumkm.endekab.go.id | gamblers fallacy menjebak pemain judi | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0149 | opacity_zero | dinkopumkm.endekab.go.id | tanda bahaya mengejar sensasi judi online | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0150 | opacity_zero | dinkopumkm.endekab.go.id | cara menolak ajakan bermain judi online | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0151 | opacity_zero | dinkopumkm.endekab.go.id | prediksi pola menang dan jam gacor | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0152 | opacity_zero | dinkopumkm.endekab.go.id | cara memutus akses judi online | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0153 | opacity_zero | dinkopumkm.endekab.go.id | cara membicarakan judi online kepada remaja | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0154 | opacity_zero | dinkopumkm.endekab.go.id | menjaga harta dengan menghindari judi online | https://dinkopumkm.endekab.go.id | 2026-10-08 |  |
| TR-RT-0155 | color_alpha_zero | e-journal.upr.ac.id | gacor | https://e-journal.upr.ac.id/index.php/JPTS | 2026-10-08 | O |
| TR-RT-0156 | color_alpha_zero | e-journal.upr.ac.id | ABC1131 | https://e-journal.upr.ac.id/index.php/JPTS | 2026-10-08 | O |
| TR-RT-0157 | color_matches_bg | ejurnal.unisri.ac.id | kampungbet | https://ejurnal.unisri.ac.id/index.php/jpaud | 2026-10-08 | O |
| TR-RT-0158 | color_matches_bg | ejurnal.unisri.ac.id | situs toto | https://ejurnal.unisri.ac.id/index.php/jpaud | 2026-10-08 | O |
| TR-RT-0159 | color_matches_bg | ejurnal.unisri.ac.id | susterslot | https://ejurnal.unisri.ac.id/index.php/jpaud | 2026-10-08 | O |
| TR-RT-0160 | color_matches_bg | ejurnal.unisri.ac.id | susterslot | https://ejurnal.unisri.ac.id/index.php/jpaud | 2026-10-08 | O |
| TR-RT-0161 | color_matches_bg | ejurnal.unisri.ac.id | susterslot | https://ejurnal.unisri.ac.id/index.php/jpaud | 2026-10-08 |  |
| TR-RT-0162 | color_matches_bg | ejurnal.unisri.ac.id | susterslot | https://ejurnal.unisri.ac.id/index.php/jpaud | 2026-10-08 | O |
| TR-RT-0163 | color_matches_bg | ejurnal.unisri.ac.id | Toto | https://ejurnal.unisri.ac.id/index.php/jpaud | 2026-10-08 | O |
| TR-RT-0164 | color_matches_bg | ejurnal.unisri.ac.id | 838win | https://ejurnal.unisri.ac.id/index.php/jpaud | 2026-10-08 | O |
| TR-RT-0165 | color_matches_bg | ejurnal.unisri.ac.id | tobrut888 | https://ejurnal.unisri.ac.id/index.php/jtpr | 2026-10-08 | O |
| TR-RT-0166 | color_matches_bg | ejurnal.unisri.ac.id | kokitoto | https://ejurnal.unisri.ac.id/index.php/jtpr | 2026-10-08 | O |
| TR-RT-0167 | color_matches_bg | ejurnal.unisri.ac.id | slot server thailand | https://ejurnal.unisri.ac.id/index.php/jtpr | 2026-10-08 | O |
| TR-RT-0168 | color_matches_bg | galuhvirtual.ciamiskab.go.id | situs toto | https://galuhvirtual.ciamiskab.go.id | 2026-10-08 | O |
| TR-RT-0169 | opacity_zero | jitekin-upiyptk.org | EROPA99 Slot | https://jitekin-upiyptk.org/ojs/index.php/Teknologi | 2026-10-08 | O |
| TR-RT-0170 | opacity_zero | jitekin-upiyptk.org | BEST 188 | https://jitekin-upiyptk.org/ojs/index.php/Teknologi | 2026-10-08 | O |
| TR-RT-0171 | opacity_zero | jitekin-upiyptk.org | geber88 | https://jitekin-upiyptk.org/ojs/index.php/Teknologi | 2026-10-08 | O |
| TR-RT-0172 | opacity_zero | journal.iaincurup.ac.id | deposit pulsa | https://journal.iaincurup.ac.id/index.php/disclosure | 2026-10-08 | O |
| TR-RT-0173 | opacity_zero | journal.iaincurup.ac.id | 7meter parlay | https://journal.iaincurup.ac.id/index.php/disclosure | 2026-10-08 | O |
| TR-RT-0174 | opacity_zero | journal.iaincurup.ac.id | 7meter sbobet | https://journal.iaincurup.ac.id/index.php/disclosure | 2026-10-08 | O |
| TR-RT-0175 | color_matches_bg | journal.ibrahimy.ac.id | Garuda888 | https://journal.ibrahimy.ac.id/index.php/JSAPI | 2026-10-08 | O |
| TR-RT-0176 | color_alpha_zero | journal.uinmataram.ac.id | slot online | https://journal.uinmataram.ac.id/index.php/schemata | 2026-10-08 | O |
| TR-RT-0177 | opacity_zero | journal.unucirebon.ac.id | slot gacor | https://journal.unucirebon.ac.id/index.php/ijpess/index | 2026-10-08 | O |
| TR-RT-0178 | opacity_zero | journal.unucirebon.ac.id | slot88 | https://journal.unucirebon.ac.id/index.php/ijpess/index | 2026-10-08 | O |
| TR-RT-0179 | opacity_zero | journal.unucirebon.ac.id | slot online | https://journal.unucirebon.ac.id/index.php/ijpess/index | 2026-10-08 | O |
| TR-RT-0180 | opacity_zero | journal.unucirebon.ac.id | slot indonesia | https://journal.unucirebon.ac.id/index.php/ijpess/index | 2026-10-08 | O |
| TR-RT-0181 | opacity_zero | journal.unucirebon.ac.id | idnslot | https://journal.unucirebon.ac.id/index.php/ijpess/index | 2026-10-08 | O |
| TR-RT-0182 | opacity_zero | journal.unucirebon.ac.id | slot thailand | https://journal.unucirebon.ac.id/index.php/ijpess/index | 2026-10-08 | O |
| TR-RT-0183 | opacity_zero | journal.unucirebon.ac.id | slot777 | https://journal.unucirebon.ac.id/index.php/ijpess/index | 2026-10-08 | O |
| TR-RT-0184 | opacity_zero | journal.unucirebon.ac.id | slot88 | https://journal.unucirebon.ac.id/index.php/ijpess/index | 2026-10-08 | O |
| TR-RT-0185 | color_matches_bg | jurnal.ulb.ac.id | HOKI138 | https://jurnal.ulb.ac.id/index.php/advokasi | 2026-10-08 | O |
| TR-RT-0186 | opacity_zero | jurnal.unigo.ac.id | toto slot | https://jurnal.unigo.ac.id/gjise | 2026-10-08 | O |
| TR-RT-0187 | opacity_zero | jurnal.unigo.ac.id | slot qris | https://jurnal.unigo.ac.id/gjise | 2026-10-08 | O |
| TR-RT-0188 | opacity_zero | jurnal.unigo.ac.id | OKESLOT | https://jurnal.unigo.ac.id/gjise | 2026-10-08 | O |
| TR-RT-0189 | opacity_zero | mibaida.sch.id | psk casino aplikacija | https://mibaida.sch.id | 2026-10-08 | O |
| TR-RT-0190 | opacity_zero | mibaida.sch.id | Le casino en ligne Stake s’est impose comme une reference in | https://mibaida.sch.id | 2026-10-08 | O |
| TR-RT-0191 | opacity_zero | mibaida.sch.id | stake code | https://mibaida.sch.id | 2026-10-08 | O |
| TR-RT-0192 | opacity_zero | mibaida.sch.id | mrbit rotiri fara depunere | https://mibaida.sch.id | 2026-10-08 | O |
| TR-RT-0193 | opacity_zero | mibaida.sch.id | Platforma se distinge prin interfata moderna si intuitiva, c | https://mibaida.sch.id | 2026-10-08 | O |
| TR-RT-0194 | opacity_zero | mibaida.sch.id | Dlaczego fireball casino przyciąga graczy z całej Polski? | https://mibaida.sch.id | 2026-10-08 | O |
| TR-RT-0195 | opacity_zero | mibaida.sch.id | fireball casino kod promocyjny bez depozytu | https://mibaida.sch.id | 2026-10-08 | O |
| TR-RT-0196 | opacity_zero | mibaida.sch.id | stake pba | https://mibaida.sch.id | 2026-10-08 | O |
| TR-RT-0197 | opacity_zero | mibaida.sch.id | juegos de casino | https://mibaida.sch.id | 2026-10-08 | O |
| TR-RT-0198 | opacity_zero | mibaida.sch.id | La ruleta es uno de los juegos más emblemáticos que existen  | https://mibaida.sch.id | 2026-10-08 | O |
| TR-RT-0199 | opacity_zero | mibaida.sch.id | Explorando la experiencia de juego en TodoSlots | https://mibaida.sch.id | 2026-10-08 | O |
| TR-RT-0200 | opacity_zero | mibaida.sch.id | El mercado de los casinos digitales ha crecido exponencialme | https://mibaida.sch.id | 2026-10-08 | O |
| TR-RT-0201 | opacity_zero | mibaida.sch.id | todoslots goldenpark gratis | https://mibaida.sch.id | 2026-10-08 | O |
| TR-RT-0202 | opacity_zero | mibaida.sch.id | gratogana casino | https://mibaida.sch.id | 2026-10-08 | O |
| TR-RT-0203 | opacity_zero | mibaida.sch.id | Wszystko co warto wiedzieć o Total Casino | https://mibaida.sch.id | 2026-10-08 | O |
| TR-RT-0204 | opacity_zero | mibaida.sch.id | casino total | https://mibaida.sch.id | 2026-10-08 | O |
| TR-RT-0205 | opacity_zero | mibaida.sch.id | nv casino bonus | https://mibaida.sch.id | 2026-10-08 | O |
| TR-RT-0206 | opacity_zero | mibaida.sch.id | Dlaczego Bison Casino przyciąga polskich graczy? | https://mibaida.sch.id | 2026-10-08 | O |
| TR-RT-0207 | opacity_zero | mibaida.sch.id | bison casino 2 | https://mibaida.sch.id | 2026-10-08 | O |
| TR-RT-0208 | opacity_zero | mibaida.sch.id | W kwestii bezpieczeństwa, Bison Casino stawia na zaawansowan | https://mibaida.sch.id | 2026-10-08 | O |
| TR-RT-0209 | opacity_zero | mibaida.sch.id | live casino parimatch | https://mibaida.sch.id | 2026-10-08 |  |
| TR-RT-0210 | opacity_zero | mibaida.sch.id | rtp slot –jackpot108) | https://mibaida.sch.id | 2026-10-08 |  |
| TR-RT-0211 | opacity_zero | mibaida.sch.id | Dlaczego warto sprawdzić ofertę Beep Beep Casino | https://mibaida.sch.id | 2026-10-08 |  |
| TR-RT-0212 | opacity_zero | mibaida.sch.id | beep beep casino 150 zł | https://mibaida.sch.id | 2026-10-08 |  |
| TR-RT-0213 | opacity_zero | mibaida.sch.id | Podsumowując, Beep Beep Casino prezentuje się jako solidna p | https://mibaida.sch.id | 2026-10-08 |  |
| TR-RT-0214 | opacity_zero | mibaida.sch.id | free casino games | https://mibaida.sch.id | 2026-10-08 |  |
| TR-RT-0215 | opacity_zero | mibaida.sch.id | Podczas poszukiwań warto zwrócić uwagę na wskaźnik zwrotu dl | https://mibaida.sch.id | 2026-10-08 |  |
| TR-RT-0216 | opacity_zero | mibaida.sch.id | L’art de calculer ses chances au casino | https://mibaida.sch.id | 2026-10-08 |  |
| TR-RT-0217 | opacity_zero | mibaida.sch.id | En somme, le succès au casino ne dépend pas de la chance pur | https://mibaida.sch.id | 2026-10-08 |  |
| TR-RT-0218 | opacity_zero | mibaida.sch.id | Les avantages de jouer dans un casino online | https://mibaida.sch.id | 2026-10-08 |  |
| TR-RT-0219 | opacity_zero | mibaida.sch.id | casino online | https://mibaida.sch.id | 2026-10-08 |  |
| TR-RT-0220 | opacity_zero | mibaida.sch.id | Le blackjack demeure sans conteste l’un des jeux de cartes l | https://mibaida.sch.id | 2026-10-08 |  |
| TR-RT-0221 | opacity_zero | mibaida.sch.id | Le marché des casinos en ligne ne cesse d’évoluer au fil des | https://mibaida.sch.id | 2026-10-08 |  |
| TR-RT-0222 | opacity_zero | mibaida.sch.id | Le secteur des casinos en ligne a considérablement évolué po | https://mibaida.sch.id | 2026-10-08 |  |
| TR-RT-0223 | opacity_zero | mibaida.sch.id | Lorsqu un utilisateur s inscrit, le casino lui demande génér | https://mibaida.sch.id | 2026-10-08 |  |
| TR-RT-0224 | opacity_zero | mibaida.sch.id | La sécurité des informations transmises est une priorité abs | https://mibaida.sch.id | 2026-10-08 |  |
| TR-RT-0225 | color_matches_bg | ojs.udb.ac.id | link slot gacor | https://ojs.udb.ac.id | 2026-10-08 | O |
| TR-RT-0226 | color_matches_bg | ojs.udb.ac.id | slot | https://ojs.udb.ac.id | 2026-10-08 | O |
| TR-RT-0227 | opacity_zero | ojs.uhnsugriwa.ac.id | LGO99 Deposit Qris | https://ojs.uhnsugriwa.ac.id/index.php/jpr | 2026-10-08 | O |
| TR-RT-0228 | opacity_zero | ojs.uhnsugriwa.ac.id | CARAWD88 | https://ojs.uhnsugriwa.ac.id/index.php/jpr | 2026-10-08 | O |
| TR-RT-0229 | opacity_zero | ojs.uhnsugriwa.ac.id | hemat138 slot | https://ojs.uhnsugriwa.ac.id/index.php/jpr | 2026-10-08 | O |
| TR-RT-0230 | opacity_zero | ojs.uhnsugriwa.ac.id | bandar togel online | https://ojs.uhnsugriwa.ac.id/index.php/jpr | 2026-10-08 | O |
| TR-RT-0231 | opacity_zero | ojs.uhnsugriwa.ac.id | toto togel online | https://ojs.uhnsugriwa.ac.id/index.php/jpr | 2026-10-08 | O |
| TR-RT-0232 | opacity_zero | ojs.uhnsugriwa.ac.id | slot | https://ojs.uhnsugriwa.ac.id/index.php/jpr | 2026-10-08 | O |
| TR-RT-0233 | opacity_zero | ojs.uhnsugriwa.ac.id | bolaslot99 | https://ojs.uhnsugriwa.ac.id/index.php/jpr | 2026-10-08 | O |
| TR-RT-0234 | opacity_zero | ojs.uhnsugriwa.ac.id | demo slot | https://ojs.uhnsugriwa.ac.id/index.php/jpr | 2026-10-08 | O |
| TR-RT-0235 | opacity_zero | ojs.uhnsugriwa.ac.id | slot pulsa | https://ojs.uhnsugriwa.ac.id/index.php/jpr | 2026-10-08 | O |
| TR-RT-0236 | color_matches_bg | oyostate.gov.ng | samudrabet | https://oyostate.gov.ng | 2026-10-08 | O |
| TR-RT-0237 | color_matches_bg | oyostate.gov.ng | officialbro138.com | https://oyostate.gov.ng | 2026-10-08 | O |
| TR-RT-0238 | color_matches_bg | oyostate.gov.ng | officialbosswin168.com | https://oyostate.gov.ng | 2026-10-08 | O |
| TR-RT-0239 | color_matches_bg | oyostate.gov.ng | officialjuraganslot.com | https://oyostate.gov.ng | 2026-10-08 | O |
| TR-RT-0240 | color_matches_bg | oyostate.gov.ng | officialalbaslot.com | https://oyostate.gov.ng | 2026-10-08 | O |
| TR-RT-0241 | color_matches_bg | oyostate.gov.ng | garasislotofficial.com | https://oyostate.gov.ng | 2026-10-08 | O |
| TR-RT-0242 | color_matches_bg | oyostate.gov.ng | officialsoju88.com | https://oyostate.gov.ng | 2026-10-08 | O |
| TR-RT-0243 | color_matches_bg | oyostate.gov.ng | officialsupraslot.com | https://oyostate.gov.ng | 2026-10-08 | O |
| TR-RT-0244 | color_matches_bg | oyostate.gov.ng | ajaib88resmi.com | https://oyostate.gov.ng | 2026-10-08 | O |
| TR-RT-0245 | color_matches_bg | oyostate.gov.ng | officialnusantara88.com | https://oyostate.gov.ng | 2026-10-08 | O |
| TR-RT-0246 | color_matches_bg | oyostate.gov.ng | usaha188resmi.com | https://oyostate.gov.ng | 2026-10-08 | O |
| TR-RT-0247 | color_matches_bg | oyostate.gov.ng | merdekawinofficial.com | https://oyostate.gov.ng | 2026-10-08 | O |
| TR-RT-0248 | color_matches_bg | oyostate.gov.ng | merdeka777alternatif.com | https://oyostate.gov.ng | 2026-10-08 | O |
| TR-RT-0249 | color_matches_bg | oyostate.gov.ng | mamibetofficial.com | https://oyostate.gov.ng | 2026-10-08 | O |
| TR-RT-0250 | color_matches_bg | oyostate.gov.ng | probet88loginresmi.com | https://oyostate.gov.ng | 2026-10-08 | O |
| TR-RT-0251 | color_matches_bg | oyostate.gov.ng | mahkotaslotlinklogin.com | https://oyostate.gov.ng | 2026-10-08 | O |
| TR-RT-0252 | color_matches_bg | oyostate.gov.ng | hbowinofficial.com | https://oyostate.gov.ng | 2026-10-08 | O |
| TR-RT-0253 | color_matches_bg | oyostate.gov.ng | area188official.com | https://oyostate.gov.ng | 2026-10-08 |  |
| TR-RT-0254 | color_matches_bg | oyostate.gov.ng | ibetslotasli.com | https://oyostate.gov.ng | 2026-10-08 | O |
| TR-RT-0255 | color_matches_bg | oyostate.gov.ng | linkboss88login.com | https://oyostate.gov.ng | 2026-10-08 |  |
| TR-RT-0256 | color_matches_bg | oyostate.gov.ng | sihokislotlogin.com | https://oyostate.gov.ng | 2026-10-08 | O |
| TR-RT-0257 | color_matches_bg | oyostate.gov.ng | dota88official.com | https://oyostate.gov.ng | 2026-10-08 |  |
| TR-RT-0258 | color_matches_bg | oyostate.gov.ng | cuan88official.com | https://oyostate.gov.ng | 2026-10-08 |  |
| TR-RT-0259 | color_matches_bg | oyostate.gov.ng | jago88official.com | https://oyostate.gov.ng | 2026-10-08 |  |
| TR-RT-0260 | color_matches_bg | oyostate.gov.ng | jitu77official.com | https://oyostate.gov.ng | 2026-10-08 |  |
| TR-RT-0261 | color_matches_bg | oyostate.gov.ng | lumbung88official.com | https://oyostate.gov.ng | 2026-10-08 |  |
| TR-RT-0262 | color_matches_bg | oyostate.gov.ng | pamanslotofficial.com | https://oyostate.gov.ng | 2026-10-08 | O |
| TR-RT-0263 | opacity_zero | revistas.ufrj.br | slot demo mahjong ways | https://revistas.ufrj.br/index.php/dilemas/index | 2026-10-08 | O |
| TR-RT-0264 | opacity_zero | revistas.ufrj.br | kenzobet | https://revistas.ufrj.br/index.php/dilemas/index | 2026-10-08 | O |
| TR-RT-0265 | opacity_zero | revistas.ufrj.br | OKESLOT | https://revistas.ufrj.br/index.php/dilemas/index | 2026-10-08 |  |
| TR-RT-0266 | opacity_zero | revistas.ufrj.br | kenzototo | https://revistas.ufrj.br/index.php/dilemas/index | 2026-10-08 | O |
| TR-RT-0267 | opacity_zero | revistas.ufrj.br | kenzototo | https://revistas.ufrj.br/index.php/dilemas/index | 2026-10-08 | O |
| TR-RT-0268 | opacity_zero | revistas.ufrj.br | slot gacor | https://revistas.ufrj.br/index.php/dilemas/index | 2026-10-08 | O |
| TR-RT-0269 | opacity_zero | revistas.ufrj.br | deposit pulsa | https://revistas.ufrj.br/index.php/dilemas/index | 2026-10-08 | O |
| TR-RT-0270 | opacity_zero | revistas.ufrj.br | kenzototo | https://revistas.ufrj.br/index.php/dilemas/index | 2026-10-08 | O |
| TR-RT-0271 | opacity_zero | revistas.ufrj.br | Slot Demo | https://revistas.ufrj.br/index.php/dilemas/index | 2026-10-08 | O |
| TR-RT-0272 | opacity_zero | revistas.ufrj.br | slot pulsa | https://revistas.ufrj.br/index.php/dilemas/index | 2026-10-08 | O |
| TR-RT-0273 | opacity_zero | revistas.ufrj.br | nagacor181 | https://revistas.ufrj.br/index.php/dilemas/index | 2026-10-08 | O |
| TR-RT-0274 | opacity_zero | revistas.ufrj.br | roma77 | https://revistas.ufrj.br/index.php/dilemas/index | 2026-10-08 | O |
| TR-RT-0275 | opacity_zero | revistas.ufrj.br | roma77 | https://revistas.ufrj.br/index.php/dilemas/index | 2026-10-08 | O |
| TR-RT-0276 | opacity_zero | revistas.ufrj.br | toto slot gacor | https://revistas.ufrj.br/index.php/dilemas/index | 2026-10-08 | O |
| TR-RT-0277 | opacity_zero | revistas.ufrj.br | hoki99 | https://revistas.ufrj.br/index.php/dilemas/index | 2026-10-08 | O |
| TR-RT-0278 | opacity_zero | revistas.ufrj.br | hoki99 | https://revistas.ufrj.br/index.php/dilemas/index | 2026-10-08 | O |
| TR-RT-0279 | opacity_zero | revistas.ufrj.br | hoki99 | https://revistas.ufrj.br/index.php/dilemas/index | 2026-10-08 | O |
| TR-RT-0280 | opacity_zero | revistas.ufrj.br | hoki99 | https://revistas.ufrj.br/index.php/dilemas/index | 2026-10-08 | O |
| TR-RT-0281 | color_matches_bg | syekhnurjati.ac.id | pestotosalak.com | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 | O |
| TR-RT-0282 | color_matches_bg | syekhnurjati.ac.id | hokiraja | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 | O |
| TR-RT-0283 | color_matches_bg | syekhnurjati.ac.id | hoki raja | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 | O |
| TR-RT-0284 | color_matches_bg | syekhnurjati.ac.id | angsa11 | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 | O |
| TR-RT-0285 | color_matches_bg | syekhnurjati.ac.id | Bmw777 | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 | O |
| TR-RT-0286 | color_matches_bg | syekhnurjati.ac.id | toto slot | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 | O |
| TR-RT-0287 | color_matches_bg | syekhnurjati.ac.id | toto slot | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 |  |
| TR-RT-0288 | color_matches_bg | syekhnurjati.ac.id | link gacor | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 | O |
| TR-RT-0289 | color_matches_bg | syekhnurjati.ac.id | slot gacor malam ini | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 | O |
| TR-RT-0290 | color_matches_bg | syekhnurjati.ac.id | Pg slot | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 | O |
| TR-RT-0291 | color_matches_bg | syekhnurjati.ac.id | slot88 | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 | O |
| TR-RT-0292 | color_matches_bg | syekhnurjati.ac.id | situs slot777 | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 | O |
| TR-RT-0293 | color_matches_bg | syekhnurjati.ac.id | slot88 | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 |  |
| TR-RT-0294 | color_matches_bg | syekhnurjati.ac.id | pgslot | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 | O |
| TR-RT-0295 | color_matches_bg | syekhnurjati.ac.id | slot gacor | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 | O |
| TR-RT-0296 | color_matches_bg | syekhnurjati.ac.id | Slot gacor | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 |  |
| TR-RT-0297 | color_matches_bg | syekhnurjati.ac.id | situs slot gacor | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 | O |
| TR-RT-0298 | color_matches_bg | syekhnurjati.ac.id | slot gacor | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 |  |
| TR-RT-0299 | color_matches_bg | syekhnurjati.ac.id | toto slot | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 |  |
| TR-RT-0300 | color_matches_bg | syekhnurjati.ac.id | slot gacor | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 |  |
| TR-RT-0301 | color_matches_bg | syekhnurjati.ac.id | cipit88 | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 | O |
| TR-RT-0302 | color_matches_bg | syekhnurjati.ac.id | toto slot | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 |  |
| TR-RT-0303 | color_matches_bg | syekhnurjati.ac.id | yuantoto | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 | O |
| TR-RT-0304 | color_matches_bg | syekhnurjati.ac.id | slot gacor | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 |  |
| TR-RT-0305 | color_matches_bg | syekhnurjati.ac.id | slot gacor | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 |  |
| TR-RT-0306 | color_matches_bg | syekhnurjati.ac.id | slot depo 5k | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 | O |
| TR-RT-0307 | color_matches_bg | syekhnurjati.ac.id | bosgacor | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 | O |
| TR-RT-0308 | color_matches_bg | syekhnurjati.ac.id | bosgacor | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 |  |
| TR-RT-0309 | color_matches_bg | syekhnurjati.ac.id | slot gacor | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 |  |
| TR-RT-0310 | color_matches_bg | syekhnurjati.ac.id | slot gacor | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 |  |
| TR-RT-0311 | color_matches_bg | syekhnurjati.ac.id | sbobet | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 | O |
| TR-RT-0312 | color_matches_bg | syekhnurjati.ac.id | slot gacor | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 |  |
| TR-RT-0313 | color_matches_bg | syekhnurjati.ac.id | SLOT GACOR | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 |  |
| TR-RT-0314 | color_matches_bg | syekhnurjati.ac.id | slot gacor | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 |  |
| TR-RT-0315 | color_matches_bg | syekhnurjati.ac.id | situs toto | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 | O |
| TR-RT-0316 | color_matches_bg | syekhnurjati.ac.id | situs toto | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 |  |
| TR-RT-0317 | color_matches_bg | syekhnurjati.ac.id | situs toto | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 |  |
| TR-RT-0318 | color_matches_bg | syekhnurjati.ac.id | slot gacor | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 |  |
| TR-RT-0319 | color_matches_bg | syekhnurjati.ac.id | gading22 | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 |  |
| TR-RT-0320 | color_matches_bg | syekhnurjati.ac.id | slot gacor | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 |  |
| TR-RT-0321 | color_matches_bg | syekhnurjati.ac.id | slot gacor | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 |  |
| TR-RT-0322 | color_matches_bg | syekhnurjati.ac.id | slot gacor | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 |  |
| TR-RT-0323 | color_matches_bg | syekhnurjati.ac.id | slot gacor terbaru | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 |  |
| TR-RT-0324 | color_matches_bg | syekhnurjati.ac.id | slot gacor | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 |  |
| TR-RT-0325 | color_matches_bg | syekhnurjati.ac.id | yuantoto | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 |  |
| TR-RT-0326 | color_matches_bg | syekhnurjati.ac.id | slot gacor | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 |  |
| TR-RT-0327 | color_matches_bg | syekhnurjati.ac.id | slot 4D | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 |  |
| TR-RT-0328 | color_matches_bg | syekhnurjati.ac.id | slot gacor | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 |  |
| TR-RT-0329 | color_matches_bg | syekhnurjati.ac.id | slot gacor | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 |  |
| TR-RT-0330 | color_matches_bg | syekhnurjati.ac.id | slot gacor | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 |  |
| TR-RT-0331 | color_matches_bg | syekhnurjati.ac.id | rubahtoto | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 |  |
| TR-RT-0332 | color_matches_bg | syekhnurjati.ac.id | slot gacor | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 |  |
| TR-RT-0333 | color_matches_bg | syekhnurjati.ac.id | idn slot | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 |  |
| TR-RT-0334 | color_matches_bg | syekhnurjati.ac.id | yuantoto | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 |  |
| TR-RT-0335 | color_matches_bg | syekhnurjati.ac.id | slot deposit 1000 | https://syekhnurjati.ac.id/jurnal/index.php/eduma | 2026-10-08 |  |
| TR-RT-0336 | opacity_zero | periodicos.unimontes.br | kenzobet | https://www.periodicos.unimontes.br/index.php/caminhosdahistoria | 2026-10-08 | O |
| TR-RT-0337 | opacity_zero | periodicos.unimontes.br | kenzototo | https://www.periodicos.unimontes.br/index.php/caminhosdahistoria | 2026-10-08 | O |
| TR-RT-0338 | opacity_zero | periodicos.unimontes.br | kenzototo | https://www.periodicos.unimontes.br/index.php/caminhosdahistoria | 2026-10-08 | O |
| TR-RT-0339 | opacity_zero | journal.ar-raniry.ac.id | toto togel online | https://journal.ar-raniry.ac.id/index.php/ojs-training | 2026-10-12~13 |  |
| TR-RT-0340 | opacity_zero | journal.ar-raniry.ac.id | slot online | https://journal.ar-raniry.ac.id/index.php/ojs-training | 2026-10-12~13 | O |
| TR-RT-0341 | opacity_zero | journal.ar-raniry.ac.id | partaitogel | https://journal.ar-raniry.ac.id/index.php/ojs-training | 2026-10-12~13 | O |
| TR-RT-0342 | opacity_zero | journal.unucirebon.ac.id | slot gacor | https://journal.unucirebon.ac.id/index.php/asf | 2026-10-12~13 |  |
| TR-RT-0343 | opacity_zero | journal.unucirebon.ac.id | slot88 | https://journal.unucirebon.ac.id/index.php/asf | 2026-10-12~13 |  |
| TR-RT-0344 | opacity_zero | journal.unucirebon.ac.id | slot online | https://journal.unucirebon.ac.id/index.php/asf | 2026-10-12~13 |  |
| TR-RT-0345 | opacity_zero | journal.unucirebon.ac.id | slot indonesia | https://journal.unucirebon.ac.id/index.php/asf | 2026-10-12~13 |  |
| TR-RT-0346 | opacity_zero | journal.unucirebon.ac.id | idnslot | https://journal.unucirebon.ac.id/index.php/asf | 2026-10-12~13 |  |
| TR-RT-0347 | opacity_zero | journal.unucirebon.ac.id | slot thailand | https://journal.unucirebon.ac.id/index.php/asf | 2026-10-12~13 |  |
| TR-RT-0348 | opacity_zero | journal.unucirebon.ac.id | slot777 | https://journal.unucirebon.ac.id/index.php/asf | 2026-10-12~13 |  |
| TR-RT-0349 | opacity_zero | journal.unucirebon.ac.id | slot88 | https://journal.unucirebon.ac.id/index.php/asf | 2026-10-12~13 |  |
| TR-RT-0350 | opacity_zero | journal.unucirebon.ac.id | slot gacor | https://journal.unucirebon.ac.id/index.php/jakir | 2026-10-12~13 | O |
| TR-RT-0351 | opacity_zero | journal.unucirebon.ac.id | slot88 | https://journal.unucirebon.ac.id/index.php/jakir | 2026-10-12~13 | O |
| TR-RT-0352 | opacity_zero | journal.unucirebon.ac.id | slot online | https://journal.unucirebon.ac.id/index.php/jakir | 2026-10-12~13 | O |
| TR-RT-0353 | opacity_zero | journal.unucirebon.ac.id | slot indonesia | https://journal.unucirebon.ac.id/index.php/jakir | 2026-10-12~13 | O |
| TR-RT-0354 | opacity_zero | journal.unucirebon.ac.id | idnslot | https://journal.unucirebon.ac.id/index.php/jakir | 2026-10-12~13 | O |
| TR-RT-0355 | opacity_zero | journal.unucirebon.ac.id | slot thailand | https://journal.unucirebon.ac.id/index.php/jakir | 2026-10-12~13 | O |
| TR-RT-0356 | opacity_zero | journal.unucirebon.ac.id | slot777 | https://journal.unucirebon.ac.id/index.php/jakir | 2026-10-12~13 | O |
| TR-RT-0357 | opacity_zero | journal.unucirebon.ac.id | slot88 | https://journal.unucirebon.ac.id/index.php/jakir | 2026-10-12~13 | O |
| TR-RT-0358 | opacity_zero | journal.unucirebon.ac.id | slot gacor | https://journal.unucirebon.ac.id/index.php/judicial | 2026-10-12~13 |  |
| TR-RT-0359 | opacity_zero | journal.unucirebon.ac.id | slot88 | https://journal.unucirebon.ac.id/index.php/judicial | 2026-10-12~13 |  |
| TR-RT-0360 | opacity_zero | journal.unucirebon.ac.id | slot online | https://journal.unucirebon.ac.id/index.php/judicial | 2026-10-12~13 |  |
| TR-RT-0361 | opacity_zero | journal.unucirebon.ac.id | slot indonesia | https://journal.unucirebon.ac.id/index.php/judicial | 2026-10-12~13 |  |
| TR-RT-0362 | opacity_zero | journal.unucirebon.ac.id | idnslot | https://journal.unucirebon.ac.id/index.php/judicial | 2026-10-12~13 |  |
| TR-RT-0363 | opacity_zero | journal.unucirebon.ac.id | slot thailand | https://journal.unucirebon.ac.id/index.php/judicial | 2026-10-12~13 |  |
| TR-RT-0364 | opacity_zero | journal.unucirebon.ac.id | slot777 | https://journal.unucirebon.ac.id/index.php/judicial | 2026-10-12~13 |  |
| TR-RT-0365 | opacity_zero | journal.unucirebon.ac.id | slot88 | https://journal.unucirebon.ac.id/index.php/judicial | 2026-10-12~13 |  |
| TR-RT-0366 | color_matches_bg | jurnal.polteknaker.ac.id | slot maxwin | https://jurnal.polteknaker.ac.id/index.php/jpk | 2026-10-12~13 | O |
| TR-RT-0367 | color_matches_bg | jurnal.polteknaker.ac.id | slot gacor | https://jurnal.polteknaker.ac.id/index.php/jpk | 2026-10-12~13 | O |
| TR-RT-0368 | color_matches_bg | jurnal.polteknaker.ac.id | tiga333 | https://jurnal.polteknaker.ac.id/index.php/jpk | 2026-10-12~13 | O |
| TR-RT-0369 | opacity_zero | jurnal.unimed.ac.id | slot pulsa | https://jurnal.unimed.ac.id/2012/index.php/tgeo/manuscripttemplate | 2026-10-12~13 | O |
| TR-RT-0370 | opacity_zero | jurnal.unimed.ac.id | 7meter parlay | https://jurnal.unimed.ac.id/2012/index.php/tgeo/manuscripttemplate | 2026-10-12~13 | O |
| TR-RT-0371 | opacity_zero | jurnal.unimed.ac.id | 7meter sbobet | https://jurnal.unimed.ac.id/2012/index.php/tgeo/manuscripttemplate | 2026-10-12~13 | O |
| TR-RT-0372 | color_alpha_zero | jurnalkonstan.ac.id | maggiemakesitbetter.com | https://jurnalkonstan.ac.id | 2026-10-12~13 | O |
| TR-RT-0373 | color_alpha_zero | jurnalkonstan.ac.id | cyclowing.com | https://jurnalkonstan.ac.id | 2026-10-12~13 | O |
| TR-RT-0374 | color_alpha_zero | jurnalkonstan.ac.id | growing-years.net | https://jurnalkonstan.ac.id | 2026-10-12~13 | O |
| TR-RT-0375 | color_alpha_zero | jurnalkonstan.ac.id | dlja-windows.com | https://jurnalkonstan.ac.id | 2026-10-12~13 | O |
| TR-RT-0376 | color_alpha_zero | jurnalkonstan.ac.id | windowinstallationmidlandtx.com | https://jurnalkonstan.ac.id | 2026-10-12~13 | O |
| TR-RT-0377 | color_alpha_zero | jurnalkonstan.ac.id | betasetup.com | https://jurnalkonstan.ac.id | 2026-10-12~13 | O |
| TR-RT-0378 | color_alpha_zero | jurnalkonstan.ac.id | betflixpr.com | https://jurnalkonstan.ac.id | 2026-10-12~13 | O |
| TR-RT-0379 | color_alpha_zero | jurnalkonstan.ac.id | windowtintingtoday.com | https://jurnalkonstan.ac.id | 2026-10-12~13 | O |
| TR-RT-0380 | color_alpha_zero | jurnalkonstan.ac.id | wingsnbags.com | https://jurnalkonstan.ac.id | 2026-10-12~13 | O |
| TR-RT-0381 | color_alpha_zero | jurnalkonstan.ac.id | thehomewind.com | https://jurnalkonstan.ac.id | 2026-10-12~13 | O |
| TR-RT-0382 | color_alpha_zero | jurnalkonstan.ac.id | miso88vn.com | https://jurnalkonstan.ac.id | 2026-10-12~13 |  |
| TR-RT-0383 | color_alpha_zero | jurnalkonstan.ac.id | baldwinhillsclassroom.org | https://jurnalkonstan.ac.id | 2026-10-12~13 | O |
| TR-RT-0384 | color_alpha_zero | jurnalkonstan.ac.id | swindonlightningcheerleading.com | https://jurnalkonstan.ac.id | 2026-10-12~13 | O |
| TR-RT-0385 | color_alpha_zero | jurnalkonstan.ac.id | gocoastalrowing.com | https://jurnalkonstan.ac.id | 2026-10-12~13 | O |
| TR-RT-0386 | color_alpha_zero | jurnalkonstan.ac.id | crumpetsteaandsewing.com | https://jurnalkonstan.ac.id | 2026-10-12~13 | O |
| TR-RT-0387 | color_alpha_zero | jurnalkonstan.ac.id | amp-1tiara4d.xyz | https://jurnalkonstan.ac.id | 2026-10-12~13 | O |
| TR-RT-0388 | color_alpha_zero | jurnalkonstan.ac.id | lebah4d-amp.com | https://jurnalkonstan.ac.id | 2026-10-12~13 | O |
| TR-RT-0389 | color_alpha_zero | jurnalkonstan.ac.id | tiara4d-amp.com | https://jurnalkonstan.ac.id | 2026-10-12~13 | O |
| TR-RT-0390 | color_alpha_zero | jurnalkonstan.ac.id | laris4d-amp.com | https://jurnalkonstan.ac.id | 2026-10-12~13 | O |
| TR-RT-0391 | color_alpha_zero | jurnalkonstan.ac.id | lebah4d-alternatif.com | https://jurnalkonstan.ac.id | 2026-10-12~13 | O |
| TR-RT-0392 | color_alpha_zero | jurnalkonstan.ac.id | laris4d-alternatif.com | https://jurnalkonstan.ac.id | 2026-10-12~13 | O |
| TR-RT-0393 | color_alpha_zero | jurnalkonstan.ac.id | tiara4d-alternatif.com | https://jurnalkonstan.ac.id | 2026-10-12~13 |  |
| TR-RT-0394 | color_alpha_zero | jurnalkonstan.ac.id | tiara4d-alternatif.shop | https://jurnalkonstan.ac.id | 2026-10-12~13 |  |
| TR-RT-0395 | color_alpha_zero | jurnalkonstan.ac.id | amp-tiara4d.shop | https://jurnalkonstan.ac.id | 2026-10-12~13 |  |
| TR-RT-0396 | color_alpha_zero | jurnalkonstan.ac.id | amp-tiara4d.xyz | https://jurnalkonstan.ac.id | 2026-10-12~13 |  |
| TR-RT-0397 | color_alpha_zero | jurnalkonstan.ac.id | amp-lebah4d.shop | https://jurnalkonstan.ac.id | 2026-10-12~13 |  |
| TR-RT-0398 | color_alpha_zero | jurnalkonstan.ac.id | amp-lebah4d.site | https://jurnalkonstan.ac.id | 2026-10-12~13 |  |
| TR-RT-0399 | color_alpha_zero | jurnalkonstan.ac.id | tiara4d-xyz.shop | https://jurnalkonstan.ac.id | 2026-10-12~13 |  |
| TR-RT-0400 | color_alpha_zero | jurnalkonstan.ac.id | champion4d-amp.xyz | https://jurnalkonstan.ac.id | 2026-10-12~13 |  |
| TR-RT-0401 | color_alpha_zero | jurnalkonstan.ac.id | tiara4d-gacor.xyz | https://jurnalkonstan.ac.id | 2026-10-12~13 |  |
| TR-RT-0402 | color_alpha_zero | jurnalkonstan.ac.id | pastigacordilebah.xyz | https://jurnalkonstan.ac.id | 2026-10-12~13 |  |
| TR-RT-0403 | color_alpha_zero | jurnalkonstan.ac.id | scatterhitam-lebah4d.com | https://jurnalkonstan.ac.id | 2026-10-12~13 |  |
| TR-RT-0404 | color_alpha_zero | jurnalkonstan.ac.id | lebah4dtogel.com | https://jurnalkonstan.ac.id | 2026-10-12~13 |  |
| TR-RT-0405 | color_alpha_zero | jurnalkonstan.ac.id | ampforlebah4d.com | https://jurnalkonstan.ac.id | 2026-10-12~13 |  |
| TR-RT-0406 | color_alpha_zero | jurnalkonstan.ac.id | selalumenangditiara4d.xyz | https://jurnalkonstan.ac.id | 2026-10-12~13 |  |
| TR-RT-0407 | color_alpha_zero | jurnalkonstan.ac.id | tiara4dgacor.com | https://jurnalkonstan.ac.id | 2026-10-12~13 |  |
| TR-RT-0408 | color_alpha_zero | jurnalkonstan.ac.id | lebah4dgacornih.com | https://jurnalkonstan.ac.id | 2026-10-12~13 |  |
| TR-RT-0409 | color_alpha_zero | jurnalkonstan.ac.id | laris4damp.xyz | https://jurnalkonstan.ac.id | 2026-10-12~13 |  |
| TR-RT-0410 | color_alpha_zero | jurnalkonstan.ac.id | tiaragacor.xyz | https://jurnalkonstan.ac.id | 2026-10-12~13 |  |
| TR-RT-0411 | color_alpha_zero | jurnalkonstan.ac.id | lebah4donline.xyz | https://jurnalkonstan.ac.id | 2026-10-12~13 |  |
| TR-RT-0412 | color_alpha_zero | jurnalkonstan.ac.id | ampforlebah4d.xyz | https://jurnalkonstan.ac.id | 2026-10-12~13 |  |
| TR-RT-0413 | color_alpha_zero | jurnalkonstan.ac.id | situsbanyakmenangtiara4d.com | https://jurnalkonstan.ac.id | 2026-10-12~13 |  |
| TR-RT-0414 | color_alpha_zero | jurnalkonstan.ac.id | amplebah4d.xyz | https://jurnalkonstan.ac.id | 2026-10-12~13 |  |
| TR-RT-0415 | color_alpha_zero | jurnalkonstan.ac.id | bandartototiara.xyz | https://jurnalkonstan.ac.id | 2026-10-12~13 |  |
| TR-RT-0416 | color_alpha_zero | jurnalkonstan.ac.id | daftarsegeradilebah4d.com | https://jurnalkonstan.ac.id | 2026-10-12~13 |  |
| TR-RT-0417 | color_alpha_zero | jurnalkonstan.ac.id | selalumaxwindilebah.com | https://jurnalkonstan.ac.id | 2026-10-12~13 |  |
| TR-RT-0418 | color_alpha_zero | kma.ac.th | 1win online | https://kma.ac.th | 2026-10-12~13 | O |
| TR-RT-0419 | color_alpha_zero | kma.ac.th | pinup casino | https://kma.ac.th | 2026-10-12~13 | O |
| TR-RT-0420 | color_alpha_zero | kma.ac.th | mostbets | https://kma.ac.th | 2026-10-12~13 | O |
| TR-RT-0421 | color_alpha_zero | kma.ac.th | mostbet kz | https://kma.ac.th | 2026-10-12~13 | O |
| TR-RT-0422 | color_alpha_zero | kma.ac.th | mosbet casino | https://kma.ac.th | 2026-10-12~13 | O |
| TR-RT-0423 | color_alpha_zero | kma.ac.th | mosbet | https://kma.ac.th | 2026-10-12~13 | O |
| TR-RT-0424 | color_alpha_zero | kma.ac.th | pin up casino india | https://kma.ac.th | 2026-10-12~13 | O |
| TR-RT-0425 | color_alpha_zero | kma.ac.th | mostbet uz | https://kma.ac.th | 2026-10-12~13 | O |
| TR-RT-0426 | color_alpha_zero | kma.ac.th | mosbet | https://kma.ac.th | 2026-10-12~13 | O |
| TR-RT-0427 | color_alpha_zero | kma.ac.th | mosbet | https://kma.ac.th | 2026-10-12~13 | O |
| TR-RT-0428 | opacity_zero | ojs.stiem-bongaya.ac.id | บาคาร่า | https://ojs.stiem-bongaya.ac.id/BJRM | 2026-10-12~13 | O |
| TR-RT-0429 | opacity_zero | ojs.stiem-bongaya.ac.id | partaitogel | https://ojs.stiem-bongaya.ac.id/BJRM | 2026-10-12~13 | O |
| TR-RT-0430 | opacity_zero | ojs.stiem-bongaya.ac.id | partaitogel | https://ojs.stiem-bongaya.ac.id/BJRM | 2026-10-12~13 | O |
| TR-RT-0431 | opacity_zero | ojs.stiem-bongaya.ac.id | partaitogel | https://ojs.stiem-bongaya.ac.id/BJRM | 2026-10-12~13 | O |
| TR-RT-0432 | opacity_zero | ojs.stiem-bongaya.ac.id | ups4d | https://ojs.stiem-bongaya.ac.id/BJRM | 2026-10-12~13 | O |
| TR-RT-0433 | color_alpha_zero | ojs.stiem-bongaya.ac.id | slot gacor | https://ojs.stiem-bongaya.ac.id/BJRM | 2026-10-12~13 | O |
| TR-RT-0434 | color_matches_bg | ojs.udb.ac.id | link slot gacor | https://ojs.udb.ac.id/DJP | 2026-10-12~13 |  |
| TR-RT-0435 | color_matches_bg | ojs.udb.ac.id | slot | https://ojs.udb.ac.id/DJP | 2026-10-12~13 |  |
| TR-RT-0436 | opacity_zero | ojs.udb.ac.id | บาคาร่า | https://ojs.udb.ac.id/DJP | 2026-10-12~13 |  |
| TR-RT-0437 | opacity_zero | ojs.udb.ac.id | deposit pulsa | https://ojs.udb.ac.id/DJP | 2026-10-12~13 | O |
| TR-RT-0438 | opacity_zero | ojs.udb.ac.id | togel online | https://ojs.udb.ac.id/DJP | 2026-10-12~13 | O |
| TR-RT-0439 | opacity_zero | ojs.udb.ac.id | CARAWD88 gacor | https://ojs.udb.ac.id/DJP | 2026-10-12~13 | O |
| TR-RT-0440 | opacity_zero | ojs.udb.ac.id | slot gacor gampang menang | https://ojs.udb.ac.id/DJP | 2026-10-12~13 | O |
| TR-RT-0441 | opacity_zero | ojs.udb.ac.id | slot gacor | https://ojs.udb.ac.id/DJP | 2026-10-12~13 | O |
| TR-RT-0442 | opacity_zero | ojs.udb.ac.id | toto togel online | https://ojs.udb.ac.id/DJP | 2026-10-12~13 |  |
| TR-RT-0443 | opacity_zero | ojs.udb.ac.id | slot | https://ojs.udb.ac.id/DJP | 2026-10-12~13 | O |
| TR-RT-0444 | color_matches_bg | ejournal.um-sorong.ac.id | rubahtoto | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 | O |
| TR-RT-0445 | color_matches_bg | ejournal.um-sorong.ac.id | rubahtoto | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0446 | color_matches_bg | ejournal.um-sorong.ac.id | idn slot | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 | O |
| TR-RT-0447 | color_matches_bg | ejournal.um-sorong.ac.id | https://yuantoto.tech/ | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 | O |
| TR-RT-0448 | color_matches_bg | ejournal.um-sorong.ac.id | slot deposit 5000 | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 | O |
| TR-RT-0449 | color_matches_bg | ejournal.um-sorong.ac.id | yuantoto | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 | O |
| TR-RT-0450 | color_matches_bg | ejournal.um-sorong.ac.id | idn slot | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0451 | color_matches_bg | ejournal.um-sorong.ac.id | slot gacor | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 | O |
| TR-RT-0452 | color_matches_bg | ejournal.um-sorong.ac.id | slot deposit 1000 | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 | O |
| TR-RT-0453 | color_matches_bg | ejournal.um-sorong.ac.id | slot gacor | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0454 | color_matches_bg | ejournal.um-sorong.ac.id | slot online | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 | O |
| TR-RT-0455 | color_matches_bg | ejournal.um-sorong.ac.id | slot 4D | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 | O |
| TR-RT-0456 | color_matches_bg | ejournal.um-sorong.ac.id | slot 4D | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0457 | color_matches_bg | ejournal.um-sorong.ac.id | pestoto | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 | O |
| TR-RT-0458 | color_matches_bg | ejournal.um-sorong.ac.id | yuantoto | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0459 | color_matches_bg | ejournal.um-sorong.ac.id | slot gacor | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0460 | color_matches_bg | ejournal.um-sorong.ac.id | slot gacor | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0461 | color_matches_bg | ejournal.um-sorong.ac.id | slot gacor | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0462 | color_matches_bg | ejournal.um-sorong.ac.id | slot gacor | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0463 | color_matches_bg | ejournal.um-sorong.ac.id | gading22 | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 | O |
| TR-RT-0464 | color_matches_bg | ejournal.um-sorong.ac.id | mahjong | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 | O |
| TR-RT-0465 | color_matches_bg | ejournal.um-sorong.ac.id | slot gacor | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0466 | color_matches_bg | ejournal.um-sorong.ac.id | slot gacor | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0467 | color_matches_bg | ejournal.um-sorong.ac.id | toto slot | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 | O |
| TR-RT-0468 | color_matches_bg | ejournal.um-sorong.ac.id | situs toto | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 | O |
| TR-RT-0469 | color_matches_bg | ejournal.um-sorong.ac.id | situs toto | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0470 | color_matches_bg | ejournal.um-sorong.ac.id | slot gacor | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0471 | color_matches_bg | ejournal.um-sorong.ac.id | SLOT GACOR | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0472 | color_matches_bg | ejournal.um-sorong.ac.id | sbobet | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 | O |
| TR-RT-0473 | color_matches_bg | ejournal.um-sorong.ac.id | slot777 | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0474 | color_matches_bg | ejournal.um-sorong.ac.id | slot777 | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0475 | color_matches_bg | ejournal.um-sorong.ac.id | bosgacor | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 | O |
| TR-RT-0476 | color_matches_bg | ejournal.um-sorong.ac.id | slot gacor | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0477 | color_matches_bg | ejournal.um-sorong.ac.id | bosgacor | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0478 | color_matches_bg | ejournal.um-sorong.ac.id | slot depo 5k | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 | O |
| TR-RT-0479 | color_matches_bg | ejournal.um-sorong.ac.id | slot gacor | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0480 | color_matches_bg | ejournal.um-sorong.ac.id | slot gacor | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0481 | color_matches_bg | ejournal.um-sorong.ac.id | toto slot | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0482 | color_matches_bg | ejournal.um-sorong.ac.id | cipit88 | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 | O |
| TR-RT-0483 | color_matches_bg | ejournal.um-sorong.ac.id | slot gacor | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0484 | color_matches_bg | ejournal.um-sorong.ac.id | slot gacor | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0485 | color_matches_bg | ejournal.um-sorong.ac.id | medantoto | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 | O |
| TR-RT-0486 | color_matches_bg | ejournal.um-sorong.ac.id | situs slot gacor | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 | O |
| TR-RT-0487 | color_matches_bg | ejournal.um-sorong.ac.id | Slot gacor | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0488 | color_matches_bg | ejournal.um-sorong.ac.id | slot gacor | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0489 | color_matches_bg | ejournal.um-sorong.ac.id | https://pajaktoto8800.com | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0490 | color_matches_bg | ejournal.um-sorong.ac.id | slot dana | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0491 | color_matches_bg | ejournal.um-sorong.ac.id | slot gacor maxwin | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0492 | color_matches_bg | ejournal.um-sorong.ac.id | sbobet | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0493 | color_matches_bg | ejournal.um-sorong.ac.id | slot pulsa indosat | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0494 | color_matches_bg | ejournal.um-sorong.ac.id | slot gacor | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0495 | color_matches_bg | ejournal.um-sorong.ac.id | slot88 | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0496 | color_matches_bg | ejournal.um-sorong.ac.id | pgslot | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0497 | color_matches_bg | ejournal.um-sorong.ac.id | slot777 | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0498 | color_matches_bg | ejournal.um-sorong.ac.id | slot88 | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0499 | color_matches_bg | ejournal.um-sorong.ac.id | Pg slot | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0500 | color_matches_bg | ejournal.um-sorong.ac.id | slot gacor malam ini | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0501 | color_matches_bg | ejournal.um-sorong.ac.id | toto slot | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0502 | color_matches_bg | ejournal.um-sorong.ac.id | toto slot | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0503 | color_matches_bg | ejournal.um-sorong.ac.id | link gacor | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0504 | color_matches_bg | ejournal.um-sorong.ac.id | Bmw777 | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0505 | color_matches_bg | ejournal.um-sorong.ac.id | Slot 777 | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0506 | color_matches_bg | ejournal.um-sorong.ac.id | slot qris | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0507 | color_matches_bg | ejournal.um-sorong.ac.id | slot gacor malam ini | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0508 | color_matches_bg | ejournal.um-sorong.ac.id | DPRTOTO | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0509 | color_matches_bg | ejournal.um-sorong.ac.id | DPRTOTO | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0510 | color_matches_bg | ejournal.um-sorong.ac.id | DPRTOTO | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0511 | color_matches_bg | ejournal.um-sorong.ac.id | SLOT DANA | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0512 | color_matches_bg | ejournal.um-sorong.ac.id | VIA4D | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0513 | color_matches_bg | ejournal.um-sorong.ac.id | DPRTOTO | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0514 | color_matches_bg | ejournal.um-sorong.ac.id | dprtotoonlineterus.com | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0515 | color_matches_bg | ejournal.um-sorong.ac.id | DPRTOTO | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0516 | color_matches_bg | ejournal.um-sorong.ac.id | DPRTOTO | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0517 | color_matches_bg | ejournal.um-sorong.ac.id | dprtotoagendana.com | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0518 | color_matches_bg | ejournal.um-sorong.ac.id | slot88 | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0519 | color_matches_bg | ejournal.um-sorong.ac.id | slot pulsa indosat | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0520 | color_matches_bg | ejournal.um-sorong.ac.id | slot pulsa | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0521 | color_matches_bg | ejournal.um-sorong.ac.id | slot deposit 5k | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0522 | color_matches_bg | ejournal.um-sorong.ac.id | slot deposit pulsa | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0523 | color_matches_bg | ejournal.um-sorong.ac.id | slot dana | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0524 | color_matches_bg | ejournal.um-sorong.ac.id | slot qris | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0525 | color_matches_bg | ejournal.um-sorong.ac.id | slot pulsa | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0526 | color_matches_bg | ejournal.um-sorong.ac.id | slot pulsa indosat | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0527 | color_matches_bg | ejournal.um-sorong.ac.id | slot deposit pulsa | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0528 | color_matches_bg | ejournal.um-sorong.ac.id | Badak178 | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0529 | color_matches_bg | ejournal.um-sorong.ac.id | Badak178 | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0530 | color_matches_bg | ejournal.um-sorong.ac.id | Badak178 | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0531 | color_matches_bg | ejournal.um-sorong.ac.id | Badak178 | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0532 | color_matches_bg | ejournal.um-sorong.ac.id | Badak178 | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0533 | color_matches_bg | ejournal.um-sorong.ac.id | Badak178 | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0534 | color_matches_bg | ejournal.um-sorong.ac.id | Badak178 | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0535 | color_matches_bg | ejournal.um-sorong.ac.id | toto | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0536 | color_matches_bg | ejournal.um-sorong.ac.id | slot gacor | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0537 | color_matches_bg | ejournal.um-sorong.ac.id | slot777 | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0538 | color_matches_bg | ejournal.um-sorong.ac.id | petirtoto | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0539 | color_matches_bg | ejournal.um-sorong.ac.id | hokiraja | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0540 | color_matches_bg | ejournal.um-sorong.ac.id | hoki raja | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
| TR-RT-0541 | color_matches_bg | ejournal.um-sorong.ac.id | tiga333 | https://www.ejournal.um-sorong.ac.id/index.php/gl | 2026-10-12~13 |  |
