# -*- coding: utf-8 -*-
# 작성일: 2026-09-27 02:50 (KST)
# 작성자: 2601975 정수현
"""
train.py
MNIST 데이터셋으로 CNN 을 학습하고, 학습된 가중치를 mnist_cnn.pt 로 저장합니다.

사용법
    python train.py                 # 기본값(5 에폭)으로 학습
    python train.py --에폭 3        # 에폭 수 바꾸기
    python train.py --저장경로 my.pt
"""

import argparse
import time
from pathlib import Path

import torch
import torch.nn.functional as F
from torch import optim
from torch.optim.lr_scheduler import StepLR
from torch.utils.data import DataLoader
from torchvision import datasets, transforms

from model import MnistCNN


def 인자_읽기():
    """명령줄 옵션을 정의하고 읽어 옵니다."""
    파서 = argparse.ArgumentParser(description="MNIST 손글씨 숫자 인식 CNN 학습")
    파서.add_argument("--에폭", type=int, default=5, help="전체 데이터를 몇 번 반복 학습할지 (기본 5)")
    파서.add_argument("--배치크기", type=int, default=128, help="한 번에 학습할 이미지 수 (기본 128)")
    파서.add_argument("--학습률", type=float, default=1.0, help="Adadelta 학습률 (기본 1.0)")
    파서.add_argument("--데이터폴더", type=str, default="./data", help="MNIST 데이터를 내려받을 폴더")
    파서.add_argument("--저장경로", type=str, default="mnist_cnn.pt", help="가중치를 저장할 파일 이름")
    파서.add_argument("--시드", type=int, default=42, help="재현성을 위한 난수 시드")
    return 파서.parse_args()


def 데이터_준비(데이터폴더: str, 배치크기: int):
    """MNIST 학습/시험 데이터를 내려받아 데이터로더로 만듭니다."""
    # 학습용 변환: 약간의 회전·이동·확대축소를 무작위로 주어(데이터 증강)
    #             마우스로 그린 삐뚤삐뚤한 글씨에도 잘 대응하도록 합니다.
    학습_변환 = transforms.Compose([
        transforms.RandomAffine(degrees=10, translate=(0.1, 0.1), scale=(0.9, 1.1)),
        transforms.ToTensor(),
        transforms.Normalize((0.1307,), (0.3081,)),
    ])
    # 시험용 변환: 증강 없이 정규화만 합니다.
    시험_변환 = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.1307,), (0.3081,)),
    ])

    print("MNIST 데이터셋을 준비합니다...")
    학습_데이터 = datasets.MNIST(데이터폴더, train=True, download=True, transform=학습_변환)
    시험_데이터 = datasets.MNIST(데이터폴더, train=False, download=True, transform=시험_변환)
    print(f"  학습 이미지 {len(학습_데이터):,}장, 시험 이미지 {len(시험_데이터):,}장")

    학습_로더 = DataLoader(학습_데이터, batch_size=배치크기, shuffle=True)
    시험_로더 = DataLoader(시험_데이터, batch_size=1000, shuffle=False)
    return 학습_로더, 시험_로더


def 한_에폭_학습(모델, 장치, 학습_로더, 최적화기, 에폭번호):
    """한 에폭 동안 모델을 학습시키고 평균 손실을 반환합니다."""
    모델.train()                       # 드롭아웃을 켜는 학습 모드
    손실_합계 = 0.0
    전체_배치 = len(학습_로더)

    for 배치번호, (이미지, 정답) in enumerate(학습_로더, start=1):
        이미지, 정답 = 이미지.to(장치), 정답.to(장치)

        최적화기.zero_grad()           # 이전 기울기를 초기화
        예측 = 모델(이미지)             # 순전파
        손실 = F.nll_loss(예측, 정답)   # 로그 소프트맥스와 짝을 이루는 손실 함수
        손실.backward()                # 역전파로 기울기 계산
        최적화기.step()                # 가중치 갱신

        손실_합계 += 손실.item()

        # 진행 상황을 10% 단위로 출력합니다.
        if 배치번호 % max(1, 전체_배치 // 10) == 0 or 배치번호 == 전체_배치:
            진행률 = 100.0 * 배치번호 / 전체_배치
            print(f"  [에폭 {에폭번호}] {진행률:5.1f}% 진행  손실 {손실.item():.4f}")

    return 손실_합계 / 전체_배치


def 평가(모델, 장치, 시험_로더):
    """시험 데이터로 평균 손실과 정확도를 계산합니다."""
    모델.eval()                        # 드롭아웃을 끄는 평가 모드
    손실_합계 = 0.0
    맞춘_개수 = 0

    with torch.no_grad():              # 평가 때는 기울기를 계산하지 않습니다.
        for 이미지, 정답 in 시험_로더:
            이미지, 정답 = 이미지.to(장치), 정답.to(장치)
            예측 = 모델(이미지)
            손실_합계 += F.nll_loss(예측, 정답, reduction="sum").item()
            맞춘_개수 += 예측.argmax(dim=1).eq(정답).sum().item()

    전체 = len(시험_로더.dataset)
    return 손실_합계 / 전체, 100.0 * 맞춘_개수 / 전체


def main():
    설정 = 인자_읽기()
    torch.manual_seed(설정.시드)

    # GPU(CUDA)가 있으면 쓰고, 없으면 CPU 를 사용합니다.
    장치 = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"사용 장치: {장치}")

    학습_로더, 시험_로더 = 데이터_준비(설정.데이터폴더, 설정.배치크기)

    모델 = MnistCNN().to(장치)
    매개변수_수 = sum(p.numel() for p in 모델.parameters())
    print(f"모델 매개변수 개수: {매개변수_수:,}")

    최적화기 = optim.Adadelta(모델.parameters(), lr=설정.학습률)
    # 에폭이 지날수록 학습률을 0.7배씩 줄여 안정적으로 수렴시킵니다.
    스케줄러 = StepLR(최적화기, step_size=1, gamma=0.7)

    시작_시각 = time.time()
    최고_정확도 = 0.0

    for 에폭번호 in range(1, 설정.에폭 + 1):
        print(f"\n===== 에폭 {에폭번호}/{설정.에폭} =====")
        평균_손실 = 한_에폭_학습(모델, 장치, 학습_로더, 최적화기, 에폭번호)
        시험_손실, 정확도 = 평가(모델, 장치, 시험_로더)
        스케줄러.step()

        print(f"  학습 평균 손실 {평균_손실:.4f} | 시험 손실 {시험_손실:.4f} | 시험 정확도 {정확도:.2f}%")

        # 정확도가 가장 좋았던 순간의 가중치를 저장합니다.
        if 정확도 > 최고_정확도:
            최고_정확도 = 정확도
            torch.save(모델.state_dict(), 설정.저장경로)
            print(f"  → 최고 성적 갱신, '{설정.저장경로}' 에 저장했습니다.")

    걸린_시간 = time.time() - 시작_시각
    파일_크기 = Path(설정.저장경로).stat().st_size / (1024 * 1024)
    print(f"\n학습 완료! 총 {걸린_시간/60:.1f}분 소요")
    print(f"최고 시험 정확도: {최고_정확도:.2f}%")
    print(f"저장된 가중치: {설정.저장경로} ({파일_크기:.2f} MB)")
    print("이제 'python draw_gui.py' 를 실행해 마우스로 숫자를 그려 보세요.")


if __name__ == "__main__":
    main()
