# B. 탐지 엔진

A 가 넘긴 텍스트 요소에서 불법광고를 찾아 요강 4종(HOMOGLYPH · JAMO · TRANSPARENT · OFFSCREEN)과 추가 유형(ETC)으로 분류한다.

| 산출물 | 내용 |
|---|---|
| `normalize.py` | NFKC · 닮은꼴 글자 폴딩 · 자모 재결합 · 제로폭 제거 |
| `detectors/` | 4종 탐지기 + 추가 유형 플러그인 |
| `lexicon/` | 불법광고 키워드 사전 · 가중치 · 예외 목록 |
| `gate.py` | 내용 판정(선택적으로 LLM) |
| `fusion.py` | 같은 요소·같은 기법 병합 · 신뢰도 · 임계값 |
