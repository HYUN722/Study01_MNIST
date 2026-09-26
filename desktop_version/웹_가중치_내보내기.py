# -*- coding: utf-8 -*-
# 작성일: 2026-09-27 04:05 (KST)
"""
웹_가중치_내보내기.py
학습된 mnist_cnn.pt 를 웹 버전이 읽을 수 있는 model.bin 으로 변환합니다.

사용법
    이 파일을 더블클릭하거나
    py 웹_가중치_내보내기.py

만들어지는 파일
    ../web_version/model.bin
        float32(리틀엔디언) 값들이 아래 순서로 빈틈없이 이어진 단순 바이너리입니다.
        웹 쪽 model.js 의 `가중치_목록` 과 순서·모양이 정확히 같아야 합니다.

            conv1.weight (32,1,3,3)   conv1.bias (32,)
            conv2.weight (64,32,3,3)  conv2.bias (64,)
            fc1.weight   (128,9216)   fc1.bias   (128,)
            fc2.weight   (10,128)     fc2.bias   (10,)

        총 1,199,882개 = 4,799,528바이트 (약 4.6MB)

재학습을 했다면 이 스크립트를 다시 실행해 model.bin 을 갱신해야
웹 버전에도 새 가중치가 반영됩니다.
"""

import sys
from pathlib import Path

import numpy as np
import torch

기준_폴더 = Path(__file__).resolve().parent
가중치_파일 = 기준_폴더 / "mnist_cnn.pt"
내보낼_파일 = 기준_폴더.parent / "web_version" / "model.bin"

# 웹의 model.js 와 반드시 같아야 하는 순서와 모양
내보내기_순서 = [
    ("conv1.weight", (32, 1, 3, 3)),
    ("conv1.bias", (32,)),
    ("conv2.weight", (64, 32, 3, 3)),
    ("conv2.bias", (64,)),
    ("fc1.weight", (128, 9216)),
    ("fc1.bias", (128,)),
    ("fc2.weight", (10, 128)),
    ("fc2.bias", (10,)),
]


def main():
    print("웹 버전용 가중치 내보내기")
    print(f"  입력: {가중치_파일}")
    print(f"  출력: {내보낼_파일}\n")

    if not 가중치_파일.exists():
        print(f"[오류] '{가중치_파일.name}' 이 없습니다. 먼저 py train.py 로 학습해 주세요.")
        return 1

    상태 = torch.load(가중치_파일, map_location="cpu")

    # 모양이 예상과 같은지 먼저 확인합니다(구조를 바꿨다면 여기서 걸립니다).
    for 이름, 모양 in 내보내기_순서:
        if 이름 not in 상태:
            print(f"[오류] 가중치에 '{이름}' 이 없습니다. model.py 구조가 바뀌었나요?")
            return 1
        실제 = tuple(상태[이름].shape)
        if 실제 != 모양:
            print(f"[오류] '{이름}' 모양이 다릅니다. 기대 {모양}, 실제 {실제}")
            print("      model.py 를 바꿨다면 web_version/model.js 의 가중치_목록 도 함께 고쳐야 합니다.")
            return 1

    내보낼_파일.parent.mkdir(parents=True, exist_ok=True)

    총_개수 = 0
    with open(내보낼_파일, "wb") as 파일:
        for 이름, _ in 내보내기_순서:
            값 = 상태[이름].detach().cpu().numpy().astype("<f4")   # 리틀엔디언 float32
            파일.write(np.ascontiguousarray(값).tobytes())
            총_개수 += 값.size
            print(f"  기록: {이름:14s} {값.size:>9,}개")

    크기 = 내보낼_파일.stat().st_size
    print(f"\n완료! 총 {총_개수:,}개 실수, {크기:,} 바이트 ({크기/1024/1024:.2f} MB)")
    print("이제 web_version 폴더를 그대로 웹에 올리면 됩니다.")
    return 0


if __name__ == "__main__":
    코드 = 1
    try:
        코드 = main()
    except Exception:
        import traceback
        print("\n[예상치 못한 오류]")
        traceback.print_exc()
    finally:
        try:
            input("\n계속하려면 Enter 키를 누르세요...")
        except (EOFError, KeyboardInterrupt):
            pass
    sys.exit(코드)
