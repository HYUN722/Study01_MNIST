# 테스트

<!-- 작성일: 2026-09-27 04:18 (KST) -->
<!-- 수정일: 2026-09-27 05:29 (KST) — 단계별 시각화(steps.html) 관련 테스트 4개 추가 -->

`계획(docs/superpowers/plans/2026-09-27-웹-데스크톱-분리.md)` 이 명시한 검증들을
자동화한 것입니다. 데스크톱(PyTorch)과 웹(순수 자바스크립트) 두 구현이 같은 결과를
내는지, 그리고 실제 웹 페이지가 브라우저에서 정상 동작하는지를 확인합니다.

이 환경에는 **torch 가 설치돼 있지 않습니다.** 아래 테스트들은 모두 torch 를
import 하지 않고, 이미 만들어져 있는 `web_version/model.bin` 과 소스 코드 텍스트만
가지고 검사합니다.

모든 명령은 **저장소 루트**에서 실행하는 것을 기준으로 적었지만, 각 파일은
`Path(__file__)` 기준으로 경로를 계산하므로 다른 디렉터리에서 실행해도 동작합니다.

| 파일 | 목적 | 실행 명령 |
|------|------|-----------|
| `tests/test_내보내기_계약.py` | `desktop_version/웹_가중치_내보내기.py` 의 `내보내기_순서` 와 `web_version/model.js` 의 `가중치_목록` 이 같은 모양(shape) 순서를 쓰는지, `model.bin` 크기가 계약(4,799,528바이트)과 맞는지 검사 | `pytest tests/test_내보내기_계약.py -v` (환경에 따라 `python3 -m pytest tests/test_내보내기_계약.py -v` 가 pytest 를 못 찾으면 `pytest` 명령을 직접 씁니다) |
| `tests/js/기준구현.py` | numpy 로 CNN 순전파를 직접 구현해, 고정 시드(20260927)의 임의 가중치·입력으로 "정답" 확률을 만들고 `tests/js/_임시/` 에 저장 | `python3 tests/js/기준구현.py` |
| `tests/js/검증.js` | `web_version/model.js` 를 node 에서 `require` 해 위 정답과 비교(허용 오차 1e-5) | `python3 tests/js/기준구현.py && node tests/js/검증.js` |
| `tests/js/크기검증.js` | `model.js` 의 `가중치_해석` 이 잘린(1000바이트) 가중치 버퍼를 받으면 예외를 던지는지 확인 | `node tests/js/크기검증.js` |
| `tests/js/전처리검증.js` | `web_version/preprocess.js` 의 DOM 없이 쓸 수 있는 함수(`무게중심_맞추기`, `배경을_검정으로`, `글씨_영역_찾기`)를 단위 검증 | `node tests/js/전처리검증.js` |
| `tests/js/단계별검증.js` | `web_version/model.js` 의 `추론_단계별()` 이 돌려주는 각 단계(합성곱1·합성곱2·최대풀링·완전연결1)의 크기가 맞고 음수가 없는지, 그리고 중간값을 `최대풀링()`·`완전연결()`로 직접 재계산한 값과 실제로 일치하는지 확인 | `python3 tests/js/기준구현.py && node tests/js/단계별검증.js` |
| `tests/js/시각화검증.js` | `web_version/시각화.js` 의 순수 계산 함수(`지도를_0_255로_펴기`, `타일_배치`)를 단위 검증(전부 같은 값이어도 NaN 이 안 나오는지, 채널 수가 열 수로 나누어떨어지지 않는 경계 포함) | `node tests/js/시각화검증.js` |
| `tests/js/그림판상수검증.js` | `web_version/steps.js` 와 `app.js` 의 그림판 상수(`캔버스크기`, `펜_굵기`)가 같은 값인지 정규식으로 뽑아 비교(코드는 추출하지 않고 값이 벌어지면 테스트가 실패하도록 고정) | `node tests/js/그림판상수검증.js` |
| `tests/e2e/웹검증.py` | `web_version` 을 `http.server` 로 띄우고 headless Chromium 으로 숫자(1, 7, 4, 3)를 그려 실제로 인식되는지, 페이지 오류(`pageerror`)가 없는지 확인 | `python3 tests/e2e/웹검증.py` |
| `tests/e2e/발표화면검증.py` | `web_version/steps.html`(발표용 단계별 시각화 화면)을 headless Chromium 으로 띄워, 빈 상태 안내·1~6단계 이동(다음/이전/점 클릭/키보드)·마지막 단계 예측·1280×800 화면의 `scrollHeight` 가 800 이하인지 확인 | `python3 tests/e2e/발표화면검증.py` |

## 한 번에 모두 실행

```bash
pytest tests/test_내보내기_계약.py -v
python3 tests/js/기준구현.py && node tests/js/검증.js
node tests/js/크기검증.js
node tests/js/전처리검증.js
node tests/js/단계별검증.js
node tests/js/시각화검증.js
node tests/js/그림판상수검증.js
python3 tests/e2e/웹검증.py
python3 tests/e2e/발표화면검증.py
```

## 참고

- `tests/js/_임시/` 는 `기준구현.py` 가 실행할 때마다 새로 만드는 산출물이라
  커밋하지 않습니다(`.gitignore` 참고).
- `tests/e2e/웹검증.py` 는 빈 포트를 스스로 찾아 서버를 띄우므로 다른 서버와
  충돌하지 않습니다. playwright 브라우저는 이미 설치돼 있어야 하며
  (`playwright install` 을 다시 실행할 필요 없음), headless Chromium 으로 동작합니다.
- `test_내보내기_계약.py` 는 이름 표기(`conv1.weight` ↔ `conv1_가중치`)가 언어마다
  다르므로 이름은 비교하지 않고 **모양(shape) 순서열**만 비교합니다.
