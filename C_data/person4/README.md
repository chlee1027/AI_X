# 사람 4 (JAMO · LEXICON) 산출물

데이터 수집 계획의 사람 4 몫(JAMO 100 · LEXICON 500)이다. 2026-10-05 에 역할 C 가 점검하고 고친 판을 이 저장소에 넣었다.

| 저장소 위치 | 내용 |
|---|---|
| `C_data/data/samples/jamo.yaml` | JAMO 실측 샘플 142건 (compat_full 12 · partial_mix 58 · conjoining_u1100 20 · mixed_technique 52), 35개 사이트 |
| `B_detector/lexicon/seed.yaml` | 사전 624개 (gambling_core·lure·contact·adult 각 100, whitelist 130, gambling_weak 94), 모두 `reviewed: true` |
| `B_detector/lexicon/review_20261005.csv` | 2026-10-05 에 바뀌거나 새로 들어간 어휘 401개 검수 목록 |
| `C_data/person4/변경요약_20261005.md` | 무엇을 왜 바꿨는지 한눈에 보는 표 |
| `C_data/person4/사람4_작업결과.md` | 사람 4 작업 노트 원문 + 끝에 「2026-10-05 점검 뒤 고친 것」 |
| `C_data/person4/tools/` | 점검·수정 스크립트 (`fix_jamo.py`, `fix_lexicon.py`, `find_jamo.py`, `find_jamo_diverse.py`, `mine_terms.py`, `build_corpus.py`) |

- 노트 안의 경로(`data/samples/jamo_dataset.csv`, `data/lexicon/review.csv`, `scripts/…` 등)는 사람 4 의 원래 작업 폴더 기준이다. 그 파일들은 이 저장소에 없고, 숫자도 고치기 전(JAMO 130 · 사전 500) 기준이다. **이 저장소에서는 위 표의 두 파일이 정본이다.**
- 남은 것: 호환자모 전체 분해 12/40. 공개 게시판 원문 3,638쪽에서 실례 0건이라 더 찾거나 생성으로 채워야 한다.
- 근거 자료로 쓴 원문 색인(`corpus.jsonl`, 약 150MB)은 스팸 원문 글자라 올리지 않았다.
