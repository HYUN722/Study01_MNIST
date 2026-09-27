# -*- coding: utf-8 -*-
# 작성일: 2026-09-27 03:13 (KST)
# 작성자: 2601975 정수현
"""
바로가기_만들기.py
바탕 화면에 '손글씨 숫자 인식기' 바로가기(.lnk)를 만듭니다.

만들어지는 바로가기의 특징
    · 더블클릭하면 검은 콘솔 창 없이 인식 창만 뜹니다 (pythonw.exe 로 실행)
    · app_icon.ico 아이콘이 적용됩니다
    · 마우스 오른쪽 버튼 → '작업 표시줄에 고정' 으로 고정할 수 있습니다

사용법
    이 파일을 한 번만 더블클릭하면 됩니다.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

기준_폴더 = Path(__file__).resolve().parent
바로가기_이름 = "손글씨 숫자 인식기.lnk"


def 콘솔없는_파이썬_찾기() -> Path:
    """
    콘솔 창을 띄우지 않는 pythonw.exe 경로를 찾습니다.
    찾지 못하면 일반 python.exe 를 그대로 사용합니다(이 경우 검은 창이 함께 뜹니다).
    """
    현재 = Path(sys.executable)
    후보 = [현재.with_name("pythonw.exe"), 현재.parent / "Scripts" / "pythonw.exe"]
    for 경로 in 후보:
        if 경로.exists():
            return 경로
    print("[알림] pythonw.exe 를 찾지 못해 python.exe 로 만듭니다(검은 창이 함께 뜹니다).")
    return 현재


def 바로가기_생성():
    """PowerShell 의 WScript.Shell 로 바탕 화면에 .lnk 파일을 만듭니다."""
    파이썬 = 콘솔없는_파이썬_찾기()
    대상_스크립트 = 기준_폴더 / "draw_gui.py"
    아이콘 = 기준_폴더 / "app_icon.ico"

    if not 대상_스크립트.exists():
        print(f"[오류] {대상_스크립트} 를 찾을 수 없습니다.")
        return None

    # PowerShell 스크립트를 임시 파일로 만들어 실행합니다(따옴표 문제를 피하기 위함).
    아이콘_줄 = f"$링크.IconLocation = '{아이콘},0'" if 아이콘.exists() else "# 아이콘 파일 없음"
    파워셸_내용 = f"""
$쉘 = New-Object -ComObject WScript.Shell
$바탕화면 = [Environment]::GetFolderPath('Desktop')
$링크경로 = Join-Path $바탕화면 '{바로가기_이름}'
$링크 = $쉘.CreateShortcut($링크경로)
$링크.TargetPath = '{파이썬}'
$링크.Arguments = '"{대상_스크립트}"'
$링크.WorkingDirectory = '{기준_폴더}'
$링크.Description = '마우스로 그린 손글씨 숫자를 인식하는 프로그램 (MNIST CNN)'
$링크.WindowStyle = 1
{아이콘_줄}
$링크.Save()
Write-Output $링크경로
"""

    임시_파일 = Path(tempfile.gettempdir()) / "_바로가기_만들기.ps1"
    # PowerShell 5.1 이 한글을 제대로 읽도록 BOM 이 있는 UTF-8 로 저장합니다.
    임시_파일.write_text(파워셸_내용, encoding="utf-8-sig")

    try:
        결과 = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(임시_파일)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
    finally:
        try:
            os.remove(임시_파일)
        except OSError:
            pass

    if 결과.returncode != 0:
        print("[오류] 바로가기 생성에 실패했습니다.")
        print(결과.stdout)
        print(결과.stderr)
        return None

    return 결과.stdout.strip().splitlines()[-1] if 결과.stdout.strip() else None


def main():
    print("바탕 화면 바로가기를 만듭니다...")
    print(f"  대상   : {기준_폴더 / 'draw_gui.py'}")
    print(f"  실행기 : {콘솔없는_파이썬_찾기()}")

    만들어진_경로 = 바로가기_생성()
    if not 만들어진_경로:
        return 1

    print(f"\n완료! 바로가기가 만들어졌습니다:\n  {만들어진_경로}")
    print("\n[작업 표시줄에 고정하는 방법]")
    print("  바탕 화면의 바로가기에 마우스 오른쪽 버튼 → '작업 표시줄에 고정'")
    print("  (메뉴에 없으면 '추가 옵션 표시' 를 먼저 누르세요)")
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
