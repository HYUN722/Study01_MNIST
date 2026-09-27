# -*- coding: utf-8 -*-
# 작성일: 2026-09-27 02:50 (KST)
# 작성자: 2601975 정수현
"""
predict.py
저장된 이미지 파일(PNG, JPG 등) 속 손글씨 숫자를 인식합니다.
GUI 없이 결과만 빠르게 확인하고 싶을 때 사용합니다.

사용법
    python predict.py 그림.png
    python predict.py 그림1.png 그림2.png --보여주기
"""

import argparse
import sys
from pathlib import Path

import torch
from PIL import Image

from model import MnistCNN
from utils import 이미지를_28x28로_전처리, 배열을_텐서로, 배열을_문자그림으로


def main():
    파서 = argparse.ArgumentParser(description="이미지 파일의 손글씨 숫자 인식")
    파서.add_argument("이미지들", nargs="+", help="인식할 이미지 파일 경로(여러 개 가능)")
    파서.add_argument("--가중치", type=str, default="mnist_cnn.pt", help="학습된 가중치 파일")
    파서.add_argument("--보여주기", action="store_true", help="전처리 결과를 문자 그림으로 출력")
    설정 = 파서.parse_args()

    가중치_경로 = Path(설정.가중치)
    if not 가중치_경로.exists():
        print(f"[오류] 가중치 파일 '{가중치_경로}' 이 없습니다. 먼저 train.py 를 실행하세요.")
        sys.exit(1)

    장치 = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    모델 = MnistCNN().to(장치)
    모델.load_state_dict(torch.load(가중치_경로, map_location=장치))
    모델.eval()

    for 경로_문자열 in 설정.이미지들:
        경로 = Path(경로_문자열)
        if not 경로.exists():
            print(f"[건너뜀] '{경로}' 파일이 없습니다.")
            continue

        전처리_결과 = 이미지를_28x28로_전처리(Image.open(경로))
        if 전처리_결과 is None:
            print(f"[건너뜀] '{경로}' 에서 글씨를 찾지 못했습니다.")
            continue

        with torch.no_grad():
            확률 = torch.exp(모델(배열을_텐서로(전처리_결과).to(장치)))[0]

        예측_숫자 = int(확률.argmax())
        print(f"\n{경로.name} → 인식 결과: {예측_숫자} (확신도 {확률[예측_숫자] * 100:.1f}%)")

        # 확률이 높은 순서로 상위 3개를 함께 보여 줍니다.
        상위값, 상위번호 = torch.topk(확률, 3)
        순위_문자열 = ", ".join(f"{int(번호)}={값 * 100:.1f}%" for 값, 번호 in zip(상위값, 상위번호))
        print(f"  상위 3개: {순위_문자열}")

        if 설정.보여주기:
            print(배열을_문자그림으로(전처리_결과))


if __name__ == "__main__":
    main()
