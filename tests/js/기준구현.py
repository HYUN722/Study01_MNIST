# -*- coding: utf-8 -*-
# 작성일: 2026-09-27 04:18 (KST)
# 작성자: 2601975 정수현
"""
기준구현.py
numpy 만으로 CNN 순전파를 직접 구현해 웹 버전(model.js)을 검증할 "정답지"를 만듭니다.
torch 를 쓰지 않습니다(이 환경에는 torch 가 없습니다).

고정 시드 20260927 로 임의의 가중치와 입력을 만들고, model.js 와 완전히 같은 순서로
순전파(conv → ReLU → conv → ReLU → 2x2 최대풀링 → reshape → fc → ReLU → fc → 소프트맥스)
를 계산해, 아래 세 파일을 tests/js/_임시/ 아래에 남깁니다.

    model.bin       가중치를 계약 순서대로 float32 리틀엔디언으로 이어 붙인 것
    input.bin       28x28 정규화 입력(float32 리틀엔디언, 784개)
    기준_확률.txt   소프트맥스 결과 10개 ("%.10f" 서식, 줄바꿈으로 구분)

실행:
    python3 tests/js/기준구현.py
"""

from pathlib import Path

import numpy as np

시드 = 20260927
난수 = np.random.RandomState(시드)

이_파일 = Path(__file__).resolve()
임시_폴더 = 이_파일.parent / "_임시"
임시_폴더.mkdir(parents=True, exist_ok=True)

# desktop_version/웹_가중치_내보내기.py 의 내보내기_순서 및 web_version/model.js 의
# 가중치_목록과 반드시 같은 이름·순서·모양이어야 합니다.
가중치_모양 = [
    ("conv1_가중치", (32, 1, 3, 3)),
    ("conv1_편향", (32,)),
    ("conv2_가중치", (64, 32, 3, 3)),
    ("conv2_편향", (64,)),
    ("fc1_가중치", (128, 9216)),
    ("fc1_편향", (128,)),
    ("fc2_가중치", (10, 128)),
    ("fc2_편향", (10,)),
]


def 임의값(모양):
    # 값이 너무 크면 ReLU 이후 소프트맥스가 원-핫처럼 굳어 오차 비교가 무의미해지므로
    # 작은 표준편차로 만듭니다.
    return 난수.normal(loc=0.0, scale=0.1, size=모양).astype("<f4")


가중치 = {이름: 임의값(모양) for 이름, 모양 in 가중치_모양}
입력 = 임의값((28, 28))  # 이미 정규화됐다고 가정한 28x28 입력


def 합성곱(입력, 가중치, 편향):
    """입력 (입력채널, H, W), 가중치 (출력채널, 입력채널, kh, kw) → (출력채널, H-kh+1, W-kw+1)"""
    출력채널수, 입력채널수, 커널행, 커널열 = 가중치.shape
    _, 높이, 너비 = 입력.shape
    출력높이 = 높이 - 커널행 + 1
    출력너비 = 너비 - 커널열 + 1
    출력 = np.zeros((출력채널수, 출력높이, 출력너비), dtype=np.float64)

    for 출채널 in range(출력채널수):
        합 = np.zeros((출력높이, 출력너비), dtype=np.float64)
        for 입채널 in range(입력채널수):
            for 커행 in range(커널행):
                for 커열 in range(커널열):
                    합 += (
                        입력[입채널, 커행 : 커행 + 출력높이, 커열 : 커열 + 출력너비]
                        * 가중치[출채널, 입채널, 커행, 커열]
                    )
        출력[출채널] = 합 + 편향[출채널]
    return 출력


def 렐루(배열):
    return np.maximum(배열, 0)


def 최대풀링(입력):
    """(채널, H, W) → (채널, H//2, W//2)"""
    채널수, 높이, 너비 = 입력.shape
    출력높이, 출력너비 = 높이 // 2, 너비 // 2
    입력잘림 = 입력[:, : 출력높이 * 2, : 출력너비 * 2]
    재구성 = 입력잘림.reshape(채널수, 출력높이, 2, 출력너비, 2)
    return 재구성.max(axis=(2, 4))


def 완전연결(입력, 가중치, 편향):
    return 가중치 @ 입력 + 편향


def 소프트맥스(점수):
    최대 = np.max(점수)
    지수 = np.exp(점수 - 최대)
    return 지수 / np.sum(지수)


def 순전파(가중치, 입력28x28):
    특징 = 합성곱(입력28x28[np.newaxis, :, :], 가중치["conv1_가중치"], 가중치["conv1_편향"])
    특징 = 렐루(특징)  # (32, 26, 26)

    특징 = 합성곱(특징, 가중치["conv2_가중치"], 가중치["conv2_편향"])
    특징 = 렐루(특징)  # (64, 24, 24)

    특징 = 최대풀링(특징)  # (64, 12, 12)

    펼침 = 특징.reshape(-1)  # (채널, 높이, 너비) 순서로 펼칩니다 → 9216
    특징 = 완전연결(펼침, 가중치["fc1_가중치"], 가중치["fc1_편향"])
    특징 = 렐루(특징)

    점수 = 완전연결(특징, 가중치["fc2_가중치"], 가중치["fc2_편향"])
    return 소프트맥스(점수)


def main():
    확률 = 순전파(가중치, 입력)

    model_bin_경로 = 임시_폴더 / "model.bin"
    with open(model_bin_경로, "wb") as 파일:
        for 이름, _ in 가중치_모양:
            파일.write(np.ascontiguousarray(가중치[이름]).astype("<f4").tobytes())

    input_bin_경로 = 임시_폴더 / "input.bin"
    with open(input_bin_경로, "wb") as 파일:
        파일.write(np.ascontiguousarray(입력).astype("<f4").tobytes())

    확률_경로 = 임시_폴더 / "기준_확률.txt"
    np.savetxt(확률_경로, 확률.astype(np.float64), fmt="%.10f")

    print("기준 구현 완료")
    print(f"  {model_bin_경로} ({model_bin_경로.stat().st_size:,} 바이트)")
    print(f"  {input_bin_경로} ({input_bin_경로.stat().st_size:,} 바이트)")
    print(f"  {확률_경로}")
    print(f"  기준 확률: {np.array2string(확률, precision=6)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
