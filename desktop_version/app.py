# -*- coding: utf-8 -*-
# 작성일: 2026-09-27 03:08 (KST)
# 작성자: 2601975 정수현
"""
app.py
손글씨 숫자 인식기의 통합 실행 파일입니다.
이 파일 하나만 실행하면 아래 과정을 순서대로 자동으로 처리합니다.

    1) 필요한 패키지(torch, torchvision, numpy, pillow)가 있는지 확인하고 없으면 설치
    2) 학습된 가중치 mnist_cnn.pt 가 없으면 train.py 로 학습
    3) 마우스로 숫자를 그려 인식하는 GUI 창 실행

실행 방법
    · 폴더에서 이 파일(app.py)을 그냥 더블클릭        ← 가장 간단합니다
    · 또는 터미널에서
        py app.py                 # 기본값(3 에폭)으로 자동 진행
        py app.py --에폭 5        # 학습 에폭 수 지정
        py app.py --재학습        # 가중치가 있어도 다시 학습
        py app.py --학습생략      # 학습은 건너뛰고 GUI 만 실행
      (맥/리눅스에서는 py 대신 python3)
"""

import argparse
import importlib
import subprocess
import sys
import traceback
from pathlib import Path

# 이 파일이 있는 폴더를 기준 폴더로 삼습니다.
기준_폴더 = Path(__file__).resolve().parent
가중치_이름 = "mnist_cnn.pt"

# (파이썬에서 부르는 이름, pip 로 설치할 때 쓰는 이름)
필요_패키지 = [
    ("numpy", "numpy"),
    ("PIL", "pillow"),
    ("torch", "torch"),
    ("torchvision", "torchvision"),
]


def 줄긋기(제목=""):
    """터미널 출력을 보기 좋게 구분해 줍니다."""
    print("\n" + "=" * 56)
    if 제목:
        print(f" {제목}")
        print("=" * 56)


def 빠진_패키지_찾기():
    """설치되어 있지 않은 패키지의 pip 이름 목록을 돌려줍니다."""
    빠진_것 = []
    for 부르는_이름, 설치_이름 in 필요_패키지:
        try:
            importlib.import_module(부르는_이름)
        except ImportError:
            빠진_것.append(설치_이름)
    return 빠진_것


def 패키지_설치(설치_목록):
    """빠진 패키지를 pip 으로 설치합니다. PyTorch 는 용량이 작은 CPU 판을 먼저 시도합니다."""
    줄긋기("1단계 · 필요한 패키지 설치")
    print("설치할 패키지:", ", ".join(설치_목록))
    print("(처음 한 번만 받으면 되며, 인터넷 속도에 따라 몇 분 걸릴 수 있습니다)\n")

    토치_목록 = [이름 for 이름 in 설치_목록 if 이름 in ("torch", "torchvision")]
    기타_목록 = [이름 for 이름 in 설치_목록 if 이름 not in ("torch", "torchvision")]

    if 기타_목록:
        결과 = subprocess.run([sys.executable, "-m", "pip", "install", *기타_목록])
        if 결과.returncode != 0:
            return False

    if 토치_목록:
        # CPU 전용 저장소가 용량이 훨씬 작아 먼저 시도합니다.
        결과 = subprocess.run([sys.executable, "-m", "pip", "install", *토치_목록,
                              "--index-url", "https://download.pytorch.org/whl/cpu"])
        if 결과.returncode != 0:
            print("\n[알림] CPU 전용 저장소 설치에 실패해 기본 저장소로 다시 시도합니다.")
            결과 = subprocess.run([sys.executable, "-m", "pip", "install", *토치_목록])
        if 결과.returncode != 0:
            return False

    return True


def 학습_실행(에폭: int) -> bool:
    """train.py 를 별도 프로세스로 실행해 학습을 진행합니다."""
    줄긋기(f"2단계 · MNIST 학습 ({에폭} 에폭)")
    print("처음 실행하면 MNIST 데이터(약 11MB)를 먼저 내려받습니다.")
    print("CPU 기준으로 에폭당 몇 분 걸립니다. 진행 상황이 아래에 표시됩니다.\n")

    결과 = subprocess.run(
        [sys.executable, "-u", str(기준_폴더 / "train.py"), "--에폭", str(에폭)],
        cwd=str(기준_폴더),
    )
    return 결과.returncode == 0


def GUI_실행():
    """draw_gui.py 의 창을 띄웁니다."""
    줄긋기("3단계 · 손글씨 인식 창 실행")
    print("검은 칸에 마우스로 숫자를 크게 그려 보세요. 창을 닫으면 종료됩니다.\n")

    sys.path.insert(0, str(기준_폴더))
    sys.argv = ["draw_gui.py", "--가중치", str(기준_폴더 / 가중치_이름)]

    import draw_gui                      # 패키지 설치가 끝난 뒤에 불러옵니다.
    draw_gui.main()


def main():
    파서 = argparse.ArgumentParser(description="손글씨 숫자 인식기 통합 실행")
    파서.add_argument("--에폭", type=int, default=3, help="학습 에폭 수 (기본 3)")
    파서.add_argument("--재학습", action="store_true", help="가중치가 있어도 다시 학습")
    파서.add_argument("--학습생략", action="store_true", help="학습 없이 GUI 만 실행")
    설정 = 파서.parse_args()

    print("손글씨 숫자 인식기 (MNIST · PyTorch CNN)")
    print(f"작업 폴더: {기준_폴더}")
    print(f"파이썬: {sys.version.split()[0]}")

    # ── 1단계: 패키지 확인 ─────────────────────────────────────────
    빠진_것 = 빠진_패키지_찾기()
    if 빠진_것:
        if not 패키지_설치(빠진_것):
            print("\n[오류] 패키지 설치에 실패했습니다. 위 메시지를 확인해 주세요.")
            print("      직접 설치하려면: pip install torch torchvision numpy pillow")
            return 1
        # 설치 직후에도 제대로 불러와지는지 다시 확인합니다.
        importlib.invalidate_caches()
        남은_것 = 빠진_패키지_찾기()
        if 남은_것:
            print(f"\n[오류] 아직 불러올 수 없는 패키지가 있습니다: {', '.join(남은_것)}")
            return 1
        print("\n패키지 준비 완료!")
    else:
        print("\n필요한 패키지가 모두 설치되어 있습니다.")

    # ── 2단계: 학습 ────────────────────────────────────────────────
    가중치_경로 = 기준_폴더 / 가중치_이름
    if 설정.학습생략:
        if not 가중치_경로.exists():
            print(f"\n[오류] '{가중치_이름}' 이 없어 GUI 를 띄울 수 없습니다. --학습생략 없이 실행해 주세요.")
            return 1
        print(f"\n학습을 건너뜁니다. 기존 가중치를 사용합니다: {가중치_이름}")
    elif 가중치_경로.exists() and not 설정.재학습:
        크기 = 가중치_경로.stat().st_size / (1024 * 1024)
        print(f"\n이미 학습된 가중치가 있습니다: {가중치_이름} ({크기:.2f} MB)")
        print("다시 학습하려면 --재학습 옵션을 붙여 실행하세요.")
    else:
        if not 학습_실행(설정.에폭):
            print("\n[오류] 학습이 정상적으로 끝나지 않았습니다.")
            return 1
        if not 가중치_경로.exists():
            print(f"\n[오류] 학습은 끝났지만 '{가중치_이름}' 파일을 찾을 수 없습니다.")
            return 1

    # ── 3단계: GUI ─────────────────────────────────────────────────
    GUI_실행()
    print("\n프로그램을 종료합니다. 수고하셨습니다!")
    return 0


def 창_닫히기_전에_멈추기():
    """
    더블클릭으로 실행했을 때 검은 창이 곧바로 사라지지 않도록 붙잡아 둡니다.
    (터미널에서 실행한 경우에는 굳이 멈출 필요가 없지만, 구분이 어려우므로 항상 멈춥니다.)
    """
    try:
        input("\n계속하려면 Enter 키를 누르세요...")
    except (EOFError, KeyboardInterrupt):
        pass


if __name__ == "__main__":
    종료_코드 = 1
    try:
        종료_코드 = main()
    except KeyboardInterrupt:
        print("\n\n사용자가 중단했습니다.")
    except Exception:
        # 오류가 나도 창이 바로 닫히지 않도록 내용을 보여 준 뒤 멈춥니다.
        print("\n[예상치 못한 오류가 발생했습니다]")
        traceback.print_exc()
        print("\n위 내용을 그대로 복사해서 알려 주시면 원인을 찾을 수 있습니다.")
    finally:
        창_닫히기_전에_멈추기()
    sys.exit(종료_코드)
