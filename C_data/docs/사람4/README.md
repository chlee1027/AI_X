# 사람 4 담당 데이터: JAMO · LEXICON (2026-10-12)

바탕화면 `data_4-20261012T141828Z-1-001.zip` 을 풀어 모았다. 파일 내용은 ZIP 원본과 같다. 맥에서 만든 ZIP 이라 `.DS_Store` 둘은 뺐고, 깨져 보이던 md 파일 이름은 `사람4_작업결과.md` 로 바로잡았다. 설명은 그 md 를 따른다.

| 파일 | 건수 | 내용 |
|---|---:|---|
| `samples/jamo.yaml` | 130 | JAMO 실제 공개 원문 광고(JM-001~JM-130). 전부 양성. partial_mix 43 · mixed_technique 55 · conjoining_u1100 20 · compat_full 12 |
| `lexicon/seed.yaml` | 500 | 어휘 사전. gambling_core · gambling_lure · contact · adult · whitelist 각 100. 전부 `reviewed: true` |
| `사람4_작업결과.md` | - | 사람 4 작업 설명서 |
| `tools/validate.py` | - | 팀 공통 양식 검사기(사람 2·3 폴더의 것과 같다) |

- JAMO 목표는 100건이다. 목표 수량까지만 세면 72/100 이고 compat_full(호환자모 전체 분해)이 28건 모자란다. 남는 건수는 partial_mix(13건)와 mixed_technique(45건)에서 나왔고, 이것으로 모자란 몫을 채운 것으로 세지 않았다(md 표 그대로).
- `html` 은 원문 문자열을 `<span id="jm-NNN">` 로 감싼 것이고 `css` 는 130건 모두 빈 문자열이다. 원문에서 CSS 를 수집한 데이터가 아니기 때문이다.

## 확인한 것 (2026-10-12)

- `tools/validate.py` 를 `samples/jamo.yaml` 에 돌려 통과했다(130건, 오류 0). 건수와 하위 유형 분포는 md 표와 같다.
- `lexicon/seed.yaml` 은 500개이고 다섯 분류가 100개씩이다.
- JAMO 출처는 20개 호스트다. www.emk.kr 한 곳이 49건(38%)이다. 그다음은 ygen.kr 20, toi-l.co.kr 11, bizk.co.kr 10, fusidyne.com 10 이다.

## 넣지 않은 것

md 가 설명하는 아래 파일은 ZIP 에 없다. md 가 이 파일들을 「현재 산출물」이라고 적고 있지만, 이번에 받은 것은 `jamo.yaml` 과 `seed.yaml` 둘뿐이다.

- JAMO: `jamo_dataset.csv`(원천 130건) · `jamo_partial_mix.csv` · `jamo_metadata.json` · `jamo_findings.jsonl` · `jamo_dataset_report.json` · 재생성·검증 스크립트
- LEXICON: `initial_100.yaml` · `review_metadata.json` · `review.csv` · `reviewed.yaml` · `approval_audit.json` · `human_approval.json` · `ygen_public_title_corpus.csv`(제목 7,498개) · `non_ygen_evidence.csv`(근거 244개) · 재생성·검증 스크립트

## 주의

- 원문 문자열에 도박 사이트 주소·연락처가 그대로 들어 있다. 공개 저장소에 올릴 때 주의한다.
