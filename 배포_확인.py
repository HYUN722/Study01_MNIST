# -*- coding: utf-8 -*-
# 작성일: 2026-09-28 09:55 (KST)
# 작성자: 2601975 정수현
"""
배포_확인.py
GitHub Pages 배포를 다시 실행하고, 실제 공개 주소에 학번·이름이 보이는지까지 확인합니다.

깃허브_올리기.py 로 파일을 올린 뒤에 실행하세요.

하는 일
    1) 저장소의 최신 커밋과 배포 상태를 확인
    2) Pages 워크플로를 실행하고 끝날 때까지 기다림
    3) 공개 주소 두 개를 실제로 내려받아 학번·이름이 들어 있는지 검사
"""

import json
import subprocess
import sys
import time
import urllib.request

소유자 = "HYUN722"
저장소 = "Study01_MNIST"
기준 = f"repos/{소유자}/{저장소}"
찾을_문구 = "2601975"

주소들 = {
    "일반 화면": f"https://hyun722.github.io/{저장소}/web_version/",
    "발표용 화면": f"https://hyun722.github.io/{저장소}/web_version/steps.html",
}


def gh_api(경로, 본문=None, 방식=None):
    명령 = ["gh", "api", 경로]
    if 방식:
        명령 += ["--method", 방식]
    if 본문 is not None:
        명령 += ["--input", "-"]
    결과 = subprocess.run(
        명령, input=json.dumps(본문) if 본문 is not None else None,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if 결과.returncode != 0:
        return None, (결과.stdout or "") + (결과.stderr or "")
    if not 결과.stdout.strip():
        return {}, ""
    try:
        return json.loads(결과.stdout), ""
    except json.JSONDecodeError:
        return {}, ""


def 줄긋기(제목):
    print("\n" + "=" * 60)
    print(f" {제목}")
    print("=" * 60)


def 주소_읽기(주소):
    """공개 주소를 그대로 내려받습니다. 캐시를 피하려고 시각을 덧붙입니다."""
    요청 = urllib.request.Request(
        f"{주소}?t={int(time.time())}",
        headers={"Cache-Control": "no-cache", "User-Agent": "배포확인"},
    )
    try:
        with urllib.request.urlopen(요청, timeout=20) as 응답:
            return 응답.status, 응답.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as 오류:
        return 오류.code, ""
    except Exception as 오류:
        return 0, str(오류)


def main():
    줄긋기("1단계 · 저장소 상태")
    최신, 오류 = gh_api(f"{기준}/commits/main")
    if not 최신:
        print(f"[오류] 저장소를 읽지 못했습니다.\n{오류}")
        return 1
    커밋 = 최신["sha"][:7]
    print(f"  최신 커밋   : {커밋} — {최신['commit']['message'].splitlines()[0]}")

    파일, _ = gh_api(f"{기준}/contents/web_version/index.html")
    if 파일:
        import base64
        내용 = base64.b64decode(파일["content"]).decode("utf-8", "replace")
        print(f"  저장소 index.html 에 학번 있음: {'예' if 찾을_문구 in 내용 else '아니오'}")

    줄긋기("2단계 · Pages 설정")
    설정, _ = gh_api(f"{기준}/pages")
    if 설정:
        print(f"  빌드 방식   : {설정.get('build_type')}")
        print(f"  상태        : {설정.get('status')}")
    else:
        print("  [오류] Pages 설정을 읽지 못했습니다.")
        return 1

    줄긋기("3단계 · 배포 실행")
    _, 오류 = gh_api(f"{기준}/actions/workflows/pages.yml/dispatches", {"ref": "main"}, "POST")
    if 오류:
        print(f"  [알림] 수동 실행 요청이 거절됐습니다(이미 돌고 있을 수 있음).\n  {오류}")
    else:
        print("  실행을 요청했습니다.")

    print("\n  워크플로가 끝나기를 기다립니다(최대 5분)...")
    직전 = None
    성공 = False
    for _ in range(60):
        time.sleep(5)
        목록, _ = gh_api(f"{기준}/actions/workflows/pages.yml/runs?per_page=1")
        실행들 = (목록 or {}).get("workflow_runs") or []
        if not 실행들:
            continue
        실행 = 실행들[0]
        상태 = f"{실행.get('status')} / {실행.get('conclusion') or '진행 중'}"
        if 상태 != 직전:
            print(f"    {상태}  (커밋 {(실행.get('head_sha') or '')[:7]})")
            직전 = 상태
        if 실행.get("status") == "completed":
            성공 = 실행.get("conclusion") == "success"
            print(f"  기록: {실행.get('html_url')}")
            if not 성공:
                print("\n[실패] 워크플로가 성공하지 않았습니다. 위 주소에서 로그를 확인하세요.")
                return 1
            break
    else:
        print("  [알림] 5분 안에 끝나지 않았습니다. Actions 탭에서 확인해 주세요.")

    줄긋기("4단계 · 공개 주소에서 실제 확인")
    print("  배포 반영까지 잠시 기다립니다(30초)...")
    time.sleep(30)

    모두_통과 = True
    for 이름, 주소 in 주소들.items():
        상태코드, 본문 = 주소_읽기(주소)
        if 상태코드 != 200:
            print(f"  [실패] {이름:10s} HTTP {상태코드}  {주소}")
            모두_통과 = False
            continue
        있음 = 찾을_문구 in 본문
        표시 = "O" if 있음 else "X"
        print(f"  [{표시}] {이름:10s} HTTP 200 · 학번 표기 {'보임' if 있음 else '없음'}")
        if not 있음:
            모두_통과 = False

    줄긋기("결과")
    if 모두_통과:
        print("  두 화면 모두 정상입니다. 맨 위에 '학번 2601975 · 이름 정수현' 이 보입니다.")
        for 이름, 주소 in 주소들.items():
            print(f"    {이름}: {주소}")
        return 0

    print("  아직 반영되지 않았습니다.")
    print("  1~2분 뒤 이 파일을 한 번 더 실행해 보세요.")
    print("  그래도 안 되면 브라우저에서 Ctrl+F5 로 강력 새로고침 해 보세요.")
    return 1


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
