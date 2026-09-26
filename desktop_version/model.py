# -*- coding: utf-8 -*-
"""
model.py
MNIST 손글씨 숫자 인식을 위한 합성곱 신경망(CNN) 모델 정의 파일입니다.

구조 요약
    입력 (1, 28, 28)
      → 합성곱 3x3, 채널 32  + ReLU
      → 합성곱 3x3, 채널 64  + ReLU
      → 최대 풀링 2x2        (크기 24x24 → 12x12)
      → 드롭아웃 25%
      → 펼치기(Flatten)      (64 * 12 * 12 = 9216)
      → 완전연결 9216 → 128  + ReLU
      → 드롭아웃 50%
      → 완전연결 128 → 10    (숫자 0~9에 대한 점수)
"""

import torch.nn as nn
import torch.nn.functional as F


class MnistCNN(nn.Module):
    """손글씨 숫자(0~9)를 분류하는 CNN 모델."""

    def __init__(self):
        super().__init__()

        # 첫 번째 합성곱 층: 흑백 1채널을 32채널 특징 지도로 변환합니다.
        self.conv1 = nn.Conv2d(in_channels=1, out_channels=32, kernel_size=3)
        # 두 번째 합성곱 층: 32채널을 64채널로 늘려 더 복잡한 모양을 학습합니다.
        self.conv2 = nn.Conv2d(in_channels=32, out_channels=64, kernel_size=3)

        # 드롭아웃: 학습 중 일부 뉴런을 무작위로 끊어 과적합을 줄입니다.
        self.dropout1 = nn.Dropout(0.25)
        self.dropout2 = nn.Dropout(0.5)

        # 완전연결 층: 추출된 특징을 최종 10개 숫자 점수로 바꿉니다.
        self.fc1 = nn.Linear(64 * 12 * 12, 128)
        self.fc2 = nn.Linear(128, 10)

    def forward(self, x):
        """
        순전파 계산.

        매개변수
            x : (배치 크기, 1, 28, 28) 모양의 텐서
        반환값
            (배치 크기, 10) 모양의 로그 확률 텐서
        """
        x = self.conv1(x)          # (N, 32, 26, 26)
        x = F.relu(x)              # 음수를 0으로 만들어 비선형성을 줍니다.

        x = self.conv2(x)          # (N, 64, 24, 24)
        x = F.relu(x)

        x = F.max_pool2d(x, 2)     # (N, 64, 12, 12) 크기를 절반으로 줄입니다.
        x = self.dropout1(x)

        x = x.flatten(1)           # (N, 9216) 1차원으로 펼칩니다.
        x = self.fc1(x)            # (N, 128)
        x = F.relu(x)
        x = self.dropout2(x)

        x = self.fc2(x)            # (N, 10)

        # 로그 소프트맥스: 확률의 로그값을 반환합니다(NLLLoss와 함께 사용).
        return F.log_softmax(x, dim=1)
