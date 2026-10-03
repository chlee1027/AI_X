# A. 크롤러 · 렌더링 · 성능

입력 URL 하나에서 하위 페이지·게시글·댓글·iframe 까지 렌더링하며 훑고, 탐지기에 넘길 텍스트 요소와 그 위치(CSS 선택자)를 뽑는다. `result.json` 기록과 스키마 검증도 여기서 맡는다.

| 산출물 | 내용 |
|---|---|
| `frontier.py` | URL 정규화(요강 붙임4 비교 규칙과 같게) · 큐 · 범위 · 무한 URL 방지 |
| `renderer.py` | Playwright 병렬 렌더링 · iframe 순회 · 「더보기」 펼치기 · 브라우저 대체 경로 |
| `probe.js` | 페이지 안 요소·계산 스타일 수집 + 유일 선택자 생성·검증 |
| `budget.py` | 30분 상한 안의 시간 예산 · 24분 강제 기록 |
| `emitter.py` · `schema.py` | `result.json` / `result_extra.json` 기록(UTF-8, BOM 없음)과 스키마 검증 |
