# -*- coding: utf-8 -*-
# 작성일: 2026-09-27 02:50 (KST)
# 작성자: 2601975 정수현
"""
draw_gui.py
마우스로 숫자를 그리면 학습된 CNN 이 그 숫자를 인식해 주는 프로그램입니다.

사용법
    python draw_gui.py
    python draw_gui.py --가중치 mnist_cnn.pt

조작 방법
    · 왼쪽 검은 칸에 마우스를 끌어서 숫자 하나를 크게 그립니다.
    · 마우스 버튼을 놓으면 자동으로 인식합니다.
    · [지우기] 버튼 또는 마우스 오른쪽 버튼으로 캔버스를 비웁니다.
"""

import argparse
import sys
import tkinter as tk
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageDraw

from model import MnistCNN
from utils import 이미지를_28x28로_전처리, 배열을_텐서로

# 캔버스 설정값
캔버스_크기 = 280          # 화면에 보이는 그림판 한 변의 픽셀 수 (28의 10배)
펜_굵기 = 20               # 붓 굵기. 28x28 로 줄였을 때 2픽셀 정도가 되도록 정했습니다.

try:
    from PIL import ImageTk           # 전처리 결과 미리보기에 사용합니다.
    미리보기_가능 = True
except Exception:                     # 환경에 따라 없을 수 있으므로 없으면 생략합니다.
    미리보기_가능 = False


class 숫자인식창:
    """tkinter 로 만든 손글씨 숫자 인식 창."""

    def __init__(self, 루트: tk.Tk, 모델, 장치):
        self.루트 = 루트
        self.모델 = 모델
        self.장치 = 장치
        self.직전_좌표 = None                       # 선을 이어 그리기 위한 이전 마우스 위치

        루트.title("손글씨 숫자 인식기 (MNIST CNN)")
        루트.resizable(False, False)

        # 창과 작업 표시줄에 표시될 아이콘을 지정합니다(app_icon.ico 가 있을 때만).
        아이콘_경로 = Path(__file__).resolve().parent / "app_icon.ico"
        if 아이콘_경로.exists():
            try:
                루트.iconbitmap(default=str(아이콘_경로))
            except Exception:
                pass                          # 아이콘을 못 읽어도 프로그램은 계속 동작합니다.

        # ── 왼쪽: 그림판 ────────────────────────────────────────────
        왼쪽 = tk.Frame(루트, padx=10, pady=10)
        왼쪽.grid(row=0, column=0)

        tk.Label(왼쪽, text="여기에 숫자를 그리세요", font=("맑은 고딕", 11)).pack(pady=(0, 6))

        self.캔버스 = tk.Canvas(왼쪽, width=캔버스_크기, height=캔버스_크기,
                                bg="black", highlightthickness=1,
                                highlightbackground="#888888", cursor="cross")
        self.캔버스.pack()

        # 화면의 캔버스와 똑같은 내용을 PIL 이미지에도 그려 둡니다.
        # (화면을 캡처하는 방식보다 정확하고 운영체제에 상관없이 동작합니다.)
        self.그림 = Image.new("L", (캔버스_크기, 캔버스_크기), color=0)
        self.붓 = ImageDraw.Draw(self.그림)

        # 마우스 사건 연결
        self.캔버스.bind("<Button-1>", self.그리기_시작)
        self.캔버스.bind("<B1-Motion>", self.그리는_중)
        self.캔버스.bind("<ButtonRelease-1>", self.그리기_끝)
        self.캔버스.bind("<Button-3>", lambda 사건: self.지우기())

        단추칸 = tk.Frame(왼쪽, pady=8)
        단추칸.pack(fill="x")
        tk.Button(단추칸, text="인식하기", width=12, command=self.인식).pack(side="left", padx=4)
        tk.Button(단추칸, text="지우기", width=12, command=self.지우기).pack(side="left", padx=4)

        # ── 오른쪽: 결과 표시 ───────────────────────────────────────
        오른쪽 = tk.Frame(루트, padx=10, pady=10)
        오른쪽.grid(row=0, column=1, sticky="n")

        tk.Label(오른쪽, text="인식 결과", font=("맑은 고딕", 11)).pack()
        self.결과_글자 = tk.Label(오른쪽, text="?", font=("맑은 고딕", 72, "bold"), fg="#1a5fb4")
        self.결과_글자.pack()
        self.확신도_글자 = tk.Label(오른쪽, text="숫자를 그려 주세요", font=("맑은 고딕", 10))
        self.확신도_글자.pack(pady=(0, 8))

        # 0~9 각각의 확률을 막대로 보여 줍니다.
        tk.Label(오른쪽, text="숫자별 확률", font=("맑은 고딕", 10)).pack(anchor="w")
        self.막대_캔버스 = tk.Canvas(오른쪽, width=220, height=210,
                                    bg="white", highlightthickness=1,
                                    highlightbackground="#cccccc")
        self.막대_캔버스.pack(pady=(2, 8))
        self.확률_그리기([0.0] * 10)

        # 모델이 실제로 보는 28x28 이미지를 확대해 보여 줍니다(학습용 확인).
        if 미리보기_가능:
            tk.Label(오른쪽, text="모델이 보는 28x28 이미지", font=("맑은 고딕", 10)).pack(anchor="w")
            self.미리보기 = tk.Label(오른쪽, bd=1, relief="solid")
            self.미리보기.pack(pady=2)
            self.미리보기_이미지 = None       # 가비지 컬렉션 방지용 보관 변수

    # ── 그리기 관련 ────────────────────────────────────────────────
    def 그리기_시작(self, 사건):
        self.직전_좌표 = (사건.x, 사건.y)
        # 점 하나만 찍어도 표시되도록 원을 그립니다.
        반지름 = 펜_굵기 // 2
        self.캔버스.create_oval(사건.x - 반지름, 사건.y - 반지름,
                                사건.x + 반지름, 사건.y + 반지름,
                                fill="white", outline="white")
        self.붓.ellipse([사건.x - 반지름, 사건.y - 반지름,
                         사건.x + 반지름, 사건.y + 반지름], fill=255)

    def 그리는_중(self, 사건):
        if self.직전_좌표 is None:
            self.직전_좌표 = (사건.x, 사건.y)
            return
        x0, y0 = self.직전_좌표
        # 화면과 PIL 이미지에 같은 선을 그립니다.
        self.캔버스.create_line(x0, y0, 사건.x, 사건.y, fill="white",
                                width=펜_굵기, capstyle=tk.ROUND, smooth=True)
        self.붓.line([x0, y0, 사건.x, 사건.y], fill=255, width=펜_굵기, joint="curve")
        반지름 = 펜_굵기 // 2
        self.붓.ellipse([사건.x - 반지름, 사건.y - 반지름,
                         사건.x + 반지름, 사건.y + 반지름], fill=255)
        self.직전_좌표 = (사건.x, 사건.y)

    def 그리기_끝(self, 사건):
        self.직전_좌표 = None
        self.인식()                      # 손을 떼면 바로 인식합니다.

    def 지우기(self):
        self.캔버스.delete("all")
        self.붓.rectangle([0, 0, 캔버스_크기, 캔버스_크기], fill=0)
        self.결과_글자.config(text="?")
        self.확신도_글자.config(text="숫자를 그려 주세요")
        self.확률_그리기([0.0] * 10)
        if 미리보기_가능:
            self.미리보기.config(image="")
            self.미리보기_이미지 = None

    # ── 인식 관련 ──────────────────────────────────────────────────
    def 인식(self):
        """현재 그림을 전처리한 뒤 모델에 넣어 숫자를 맞춥니다."""
        전처리_결과 = 이미지를_28x28로_전처리(self.그림)
        if 전처리_결과 is None:
            self.확신도_글자.config(text="그림이 비어 있습니다")
            return

        입력_텐서 = 배열을_텐서로(전처리_결과).to(self.장치)

        self.모델.eval()
        with torch.no_grad():
            로그확률 = self.모델(입력_텐서)
            확률 = torch.exp(로그확률)[0].cpu().numpy()

        예측_숫자 = int(확률.argmax())
        확신도 = float(확률[예측_숫자]) * 100

        self.결과_글자.config(text=str(예측_숫자))
        self.확신도_글자.config(text=f"확신도 {확신도:.1f}%")
        self.확률_그리기(확률)
        self.미리보기_갱신(전처리_결과)

    def 확률_그리기(self, 확률):
        """0~9 숫자별 확률을 가로 막대로 그립니다."""
        self.막대_캔버스.delete("all")
        최대_숫자 = int(np.argmax(확률)) if max(확률) > 0 else -1

        for 숫자 in range(10):
            y = 6 + 숫자 * 20
            self.막대_캔버스.create_text(14, y + 7, text=str(숫자), font=("맑은 고딕", 10))
            막대_길이 = max(1, int(확률[숫자] * 150))
            색 = "#1a5fb4" if 숫자 == 최대_숫자 else "#b5c6da"
            self.막대_캔버스.create_rectangle(28, y, 28 + 막대_길이, y + 14,
                                             fill=색, outline="")
            self.막대_캔버스.create_text(190, y + 7, anchor="w",
                                        text=f"{확률[숫자] * 100:4.1f}%",
                                        font=("맑은 고딕", 8))

    def 미리보기_갱신(self, 전처리_결과):
        """전처리된 28x28 이미지를 140x140 으로 확대해 보여 줍니다."""
        if not 미리보기_가능:
            return
        from utils import MNIST_평균, MNIST_표준편차
        원본값 = np.clip(전처리_결과 * MNIST_표준편차 + MNIST_평균, 0, 1)
        이미지 = Image.fromarray((원본값 * 255).astype(np.uint8), mode="L")
        이미지 = 이미지.resize((140, 140), Image.NEAREST)
        self.미리보기_이미지 = ImageTk.PhotoImage(이미지)
        self.미리보기.config(image=self.미리보기_이미지)


def main():
    파서 = argparse.ArgumentParser(description="손글씨 숫자 인식 GUI")
    파서.add_argument("--가중치", type=str, default="mnist_cnn.pt", help="학습된 가중치 파일 경로")
    설정 = 파서.parse_args()

    가중치_경로 = Path(설정.가중치)
    if not 가중치_경로.exists():
        print(f"[오류] 가중치 파일 '{가중치_경로}' 을 찾을 수 없습니다.")
        print("      먼저 'python train.py' 를 실행해 모델을 학습해 주세요.")
        sys.exit(1)

    장치 = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    모델 = MnistCNN().to(장치)
    모델.load_state_dict(torch.load(가중치_경로, map_location=장치))
    print(f"가중치를 불러왔습니다: {가중치_경로} (장치: {장치})")

    루트 = tk.Tk()
    숫자인식창(루트, 모델, 장치)
    루트.mainloop()


if __name__ == "__main__":
    main()
