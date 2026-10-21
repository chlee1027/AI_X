# 공공 웹사이트 불법광고 탐지 도구

행정안전부·NIA 「공공 웹사이트 불법광고 탐지 도구 개발 공모전」 팀 저장소. 접수 마감 2026-10-23(금) 18시.

점검할 웹사이트 URL 하나를 넣으면 하위 페이지·게시글·댓글·iframe 안에 게시되거나 숨겨진 불법광고를 찾아, 유형과 위치를 화면과 `result.json` 으로 알려 주는 Windows 11 도구를 만든다.

## 최종판 (v9n + API v2x, 2026-10-21)

사이트 주소 하나를 받아 최대 2,000쪽 또는 20분 동안 실제 브라우저(Edge)로 돌아다니며 숨기거나 위장한 불법광고를 찾아
`result.json`(4종)과 `result_extra.json`(추가 유형)을 쓴다. 규칙과 학습 판정기로 후보를 고르고, 애매한 것만 Claude API(claude-haiku-5-5)에 2차로 묻는다.
키가 없으면 API 없이 끝까지 돈다. 이전 시험판(`A_crawler`·`B_detector`·`D_ui_docs`)은 이 판으로 바꾸며 지웠다(git 이력에 남아 있음).

- 성능·한계·요강 해석: `인계문서_보고서팀.md`
- 빌드: `빌드방법.txt` (Windows, Python 3.12.7, `package/requirements.txt`)
- 사용법: `package/사용설명서.txt`
- 결과 형식 점검: `python model2/요강점검.py <결과 폴더>`
- 실행 파일은 레포에 올리지 않는다(약 300 MB). 제출 zip 으로 따로 전달한다.

## 폴더

| 위치 | 내용 |
|---|---|
| `model/`, `model2/` | 탐지 코드. 진입점은 `model2/scan4.py`(크롤러·판정) |
| `package/detect.py` | 실행 파일 진입점, `package/build.py` 로 빌드 |
| `package/model_v9n/` | 학습된 판정 모델 |
| `model2/채점.py`, `score_key.py`, `score_extra.py` | 사이트 채점(정답 파일과 비교, 집계만 출력) |
| `model2/score_test_etc.py` | 봉인 시험셋 추가 유형 채점(집계만 출력) |
| `C_data/` | 실측 샘플(DECOY · ETC · 난독화 조합 · JAMO · OFFSCREEN), 키워드 사전, 요강 스키마 정답셋, 모의 사이트, 채점기 |

## 요강에서 정한 탐지 유형

적격평가는 아래 4종만 본다. 그 밖의 유형은 `technique: "ETC"` 와 `extra_finding` 으로 `result_extra.json` 에 따로 적는다.

| 코드 | 유형 | 예 |
|---|---|---|
| `HOMOGLYPH` | 닮은꼴 글자 위장 | 키릴·전각 문자, 숫자를 섞음 |
| `JAMO` | 자모 분해 | 음절을 자모로 쪼갬 |
| `TRANSPARENT` | 투명 텍스트 | 배경과 같은 색, `opacity:0`, `color:transparent` |
| `OFFSCREEN` | 화면 밖 은닉 | `font-size:0~1px`, `left:-9999px`, `display:none` |

## 저장소 규칙

- `.env`(API 키)와 `**/data/raw/`(수집 원문)는 올리지 않는다.
- 결과 발표 전까지 비공개로 둔다(요강: 접수 이후 공개된 아이디어는 보호받지 못한다).
