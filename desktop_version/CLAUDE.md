# CLAUDE.md — 데스크톱 버전

<!-- 작성일: 2026-09-27 04:12 (KST) -->

PyTorch로 학습하고, tkinter 창에서 마우스로 그린 숫자를 인식하는 부분입니다.
공통 규칙과 웹 버전과의 관계는 상위 폴더의 `CLAUDE.md` 를 먼저 읽으세요.

## 실행 명령

```powershell
py app.py                 # 통합 실행 (패키지 확인 → 필요 시 학습 → GUI). app.py 더블클릭과 동일
py app.py --에폭 5        # 학습 에폭 수 지정 (기본 3)
py app.py --재학습        # 가중치가 있어도 다시 학습
py app.py --학습생략      # 학습 없이 GUI만

py train.py --에폭 3      # 학습만 (mnist_cnn.pt 저장)
py draw_gui.py            # GUI만 (mnist_cnn.pt 필요)
py predict.py 그림.png --보여주기   # 이미지 파일 인식

py 웹_가중치_내보내기.py   # 학습 결과를 ../web_version/model.bin 으로 변환
py 바로가기_만들기.py      # 바탕 화면 바로가기 생성 (한 번만)
```

## 파일 구조

| 파일 | 역할 |
|------|------|
| `app.py` | 진입점. 패키지 확인·설치 → 학습 → GUI 실행 |
| `model.py` | `MnistCNN` 정의 (Conv 2층 + FC 2층, LogSoftmax 출력) |
| `utils.py` | 전처리. **torch 없이 numpy/Pillow 만 사용** (단독 검증 가능) |
| `train.py` | 학습 루프, 평가, 가중치 저장 |
| `draw_gui.py` | tkinter 캔버스 GUI |
| `predict.py` | 이미지 파일 추론 (CLI) |
| `웹_가중치_내보내기.py` | `mnist_cnn.pt` → `../web_version/model.bin` |
| `바로가기_만들기.py` | PowerShell COM으로 바탕 화면 `.lnk` 생성 |
| `app_icon.ico` | 창·바로가기 아이콘 |
| `mnist_cnn.pt` | 학습된 가중치 (커밋함) |
| `data/`, `__pycache__/` | 생성물. 커밋하지 않음 |

## 주의할 점

### 전처리와 학습 정규화는 반드시 짝을 이룹니다

`utils.이미지를_28x28로_전처리()` 의 5단계 — ①배경을 검정으로 통일 ②글씨 영역만 잘라내기
③비율 유지하며 긴 변 20px ④28×28에 넣고 무게중심을 (13.5, 13.5)로 이동 ⑤평균 0.1307,
표준편차 0.3081로 정규화 — 에서 쓰는 상수는 `train.py` 의 `transforms.Normalize` 및
웹의 `preprocess.js` 와 **모두 같아야 합니다**.

### GUI는 화면과 PIL 이미지를 이중으로 그립니다

`draw_gui.py` 는 tkinter Canvas 에 그리는 동시에 같은 좌표를 `PIL.ImageDraw` 에도 그립니다.
화면 캡처(postscript)보다 정확하고 OS 의존성이 없기 때문입니다.
획을 그리는 코드를 고칠 때는 `그리기_시작`, `그리는_중` **두 곳을 같이** 고쳐야 합니다.

### 모델 구조를 바꾸면 웹도 함께

`model.py` 를 수정하면 재학습 후 `웹_가중치_내보내기.py` 의 `내보내기_순서` 와
`web_version/model.js` 의 `가중치_목록` 을 같이 고쳐야 합니다. 상위 `CLAUDE.md` 의 표를 참고하세요.

### 학습 설정

* 데이터 증강: 회전 ±10°, 이동 ±10%, 확대축소 0.9~1.1배 (마우스 글씨 대응)
* 최적화: Adadelta(lr=1.0) + StepLR(gamma=0.7)
* `train.py` 는 **시험 정확도가 최고인 에폭에서만** `mnist_cnn.pt` 를 덮어씁니다
* 3에폭이면 보통 99% 안팎

## 환경

* 윈도우 + Python 3.14 (`C:\Users\suhye\AppData\Local\Python\pythoncore-3.14-64`)
* CPU 전용 PyTorch(`torch`, `torchvision`), `numpy`, `pillow`
* tkinter 는 파이썬 기본 포함
* 바탕 화면 바로가기는 콘솔 창이 뜨지 않도록 `pythonw.exe` 로 실행됩니다
