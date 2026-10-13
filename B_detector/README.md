# B. 탐지 엔진

A 가 넘긴 텍스트 요소에서 불법광고를 찾아 요강 4종(HOMOGLYPH · JAMO · TRANSPARENT · OFFSCREEN)과 추가 유형(ETC)으로 분류한다.

| 산출물 | 내용 |
|---|---|
| `normalize.py` | NFKC · 닮은꼴 글자 폴딩 · 자모 재결합 · 제로폭 제거 |
| `detectors/` | 4종 탐지기 + 추가 유형 플러그인 |
| `lexicon/` | 불법광고 키워드 사전 · 가중치 · 예외 목록 |

사람 4 가 모은 사전(624개, 모두 검수 완료)은 데이터 폴더에 카테고리별로 둔다: `C_data/data/lexicon/seed.yaml`. 분류별 weight 와 고친 내역은 `C_data/data/JAMO_LEXICON_변경요약_20261005.md` 에 있다. `gambling_weak`(0.1~0.2)·adult 의 weight 0.3 어휘는 단독 출현으로 판정하지 않는다.

HOMOGLYPH 정규화에 쓰는 Unicode 17.0.0 표(confusables·Scripts·IdentifierType)는 `C_data/data/unicode/` 에 있다. 쓸 때 주의할 점(매핑 방향, 집합 필드, 기본값)은 그 폴더 README 에 있다.
| `gate.py` | 내용 판정(선택적으로 LLM) |
| `fusion.py` | 같은 요소·같은 기법 병합 · 신뢰도 · 임계값 |히히
