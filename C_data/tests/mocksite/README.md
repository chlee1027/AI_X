# 모의 사이트 (페이지 단위 채점용)

실측 조각을 한 페이지에 하나씩 심어, 요강대로 **페이지 단위**로 채점되게 하는 평가용 장치다.

## 왜 필요한가

정답셋(`data/answers/`)의 `url` 은 조각을 잘라 온 실제 페이지다. 한 페이지에서 조각을 여러 개 뜯어 오면
`(url + location + technique)` 가 겹쳐 채점기 안에서 하나로 합쳐진다(학습·검증 몫 기준 641 -> 441). 조각마다
제 페이지를 주면 `url` 이 달라져 겹치지 않는다. 채점기는 실제 사이트에 요청하지 않도록 `127.0.0.1` 만 연다.

## 폴더

이 폴더의 `site/` · `answers/` · `index.html` 은 **생성물이라 git 에 올리지 않는다**(`C_data/.gitignore`).
`build_mocksite.py` 로 언제든 다시 만든다. 커밋하는 것은 빌더와 이 설명뿐이다.

## 만들고 채점하기

```sh
cd C_data

# 1) 모의 사이트와 페이지 단위 정답셋 만들기 (저장소 학습·검증 몫)
python tools/build/build_mocksite.py
#   -> tests/mocksite/site/<샘플id>.html (한 조각당 한 장)
#      tests/mocksite/answers/{answer_result,answer_result_extra,negatives}.json

# 2) 로컬 http 로 띄우기 (정답 url 의 포트 8000 과 맞춘다)
python -m http.server 8000 --directory tests/mocksite --bind 127.0.0.1
#      -> http://127.0.0.1:8000/site/<샘플id>.html 로 열린다

# 3) 다른 터미널에서 채점
python tests/scorer.py 제출.json tests/mocksite/answers/answer_result.json --resolve dom
python tests/scorer.py 제출.json tests/mocksite/answers/answer_result_extra.json --resolve dom --extra
```

봉인한 테스트 몫은 `--data`·`--out` 으로 따로 만든다(포트는 다르게).

```sh
python tools/build/build_mocksite.py --data "<봉인폴더>/data" --out "<봉인폴더>/mocksite" --base http://127.0.0.1:8001/
python -m http.server 8001 --directory "<봉인폴더>/mocksite" --bind 127.0.0.1
```

## 확인한 것 (2026-10-07)

- 학습·검증 몫으로 페이지 1,039장. 정답 `answer_result.json` 641 · `answer_result_extra.json` 525 · `negatives.json` 160.
- 빌드 때 `(url+location+기법)` 겹침이 주요 4종·추가 유형 모두 **0**.
- 띄워서 자기 채점(`--resolve dom`)하면 중복 합침 0, F1 1.0. 조각 단위(같은 파일을 그냥 채점)에서 생기던 합침이 사라졌다.

## 한계

- 각 페이지는 조각 하나만 담은 최소 HTML 이다. 실제 공공 사이트의 전체 마크업·스크립트는 없다. 숨김·난독화 판정에 필요한 요소와 그 CSS 는 조각에 그대로 들어 있다.
- 한 조합 조각에 수법이 여럿이면 같은 페이지·같은 선택자에 `technique`(또는 `extra_finding`)만 다른 정답이 되어 요강대로 따로 센다.
- 생성 데이터는 넣지 않았다(테스트·평가는 실측만).
