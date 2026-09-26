# -*- coding: utf-8 -*-
# 작성일: 2026-09-27 06:07 (KST)
"""
Pages_워크플로_전환.py
GitHub Pages 의 배포 방식을 'legacy'(브랜치 파일 그대로 서빙)에서
'workflow'(GitHub Actions) 로 바꾸고, 실제로 배포가 도는지 확인합니다.

하는 일
    1) .github/workflows/pages.yml 을 만들어 저장소에 올립니다
    2) Pages 배포 방식을 workflow 로 바꿉니다
    3) 워크플로를 실행하고 끝날 때까지 기다립니다
    4) 최종 설정을 보여 줍니다

사용법
    이 파일을 더블클릭하세요.
"""

import base64
import json
import subprocess
import sys
import time
from pathlib import Path

소유자 = "HYUN722"
저장소 = "Study01_MNIST"
워크플로_파일 = "pages.yml"
기준 = f"repos/{소유자}/{저장소}"
워크플로_경로 = ".github/workflows/pages.yml"

워크플로_내용 = r"""# 작성일: 2026-09-27 06:05 (KST)
# GitHub Actions 로 GitHub Pages 에 배포하는 워크플로입니다.
# 빌드 도구가 없는 정적 사이트라, 저장소 내용을 그대로 묶어 올립니다.

name: GitHub Pages 배포

on:
  push:
    branches: [main]      # main 에 올릴 때마다 자동 배포
  workflow_dispatch:      # 깃허브 화면이나 API 로 수동 실행도 가능

permissions:
  contents: read          # 저장소 내용 읽기
  pages: write            # Pages 에 배포
  id-token: write         # 배포 인증용 토큰

# 배포는 한 번에 하나만. 진행 중인 것을 취소하지 않고 순서대로 기다립니다.
concurrency:
  group: pages
  cancel-in-progress: false

jobs:
  deploy:
    name: 배포
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - name: 저장소 내려받기
        uses: actions/checkout@v4

      - name: Pages 설정 불러오기
        uses: actions/configure-pages@v5

      - name: 저장소 전체를 배포 꾸러미로 묶기
        uses: actions/upload-pages-artifact@v3
        with:
          # 루트를 그대로 올립니다. 그래야 기존 주소
          # (/Study01_MNIST/web_version/) 가 바뀌지 않습니다.
          path: '.'

      - name: Pages 에 배포
        id: deployment
        uses: actions/deploy-pages@v4
"""



def gh_api(경로, 본문=None, 방식=None):
    """gh api 를 호출해 (결과dict, 오류문자열) 을 돌려줍니다."""
    명령 = ["gh", "api", 경로]
    if 방식:
        명령 += ["--method", 방식]
    if 본문 is not None:
        명령 += ["--input", "-"]

    결과 = subprocess.run(
        명령,
        input=json.dumps(본문) if 본문 is not None else None,
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
    print("\n" + "=" * 56)
    print(f" {제목}")
    print("=" * 56)


def 워크플로_파일_올리기():
    """워크플로 파일을 로컬에 쓰고 저장소에도 올립니다. 이미 같은 내용이면 건너뜁니다."""
    # 로컬 폴더에도 같은 파일을 둡니다(저장소와 내용을 맞추기 위해).
    지역_경로 = Path(__file__).resolve().parent / ".github" / "workflows" / "pages.yml"
    지역_경로.parent.mkdir(parents=True, exist_ok=True)
    지역_경로.write_text(워크플로_내용, encoding="utf-8")
    print(f"  로컬에 작성: {지역_경로}")

    내용_base64 = base64.b64encode(워크플로_내용.encode("utf-8")).decode("ascii")
    기존, _ = gh_api(f"{기준}/contents/{워크플로_경로}")

    if 기존 and 기존.get("content", "").replace("\n", "") == 내용_base64:
        print("  저장소에 같은 내용이 이미 있습니다.")
        return True

    본문 = {"message": "ci: GitHub Pages 배포 워크플로 추가", "content": 내용_base64}
    if 기존:
        본문["sha"] = 기존["sha"]
        본문["message"] = "ci: GitHub Pages 배포 워크플로 갱신"

    결과, 오류 = gh_api(f"{기준}/contents/{워크플로_경로}", 본문, "PUT")
    if not 결과:
        print(f"[오류] 워크플로 파일을 올리지 못했습니다.\n{오류}")
        print("      gh 로그인에 workflow 권한이 있는지 확인하세요(gh auth status).")
        return False
    print("  저장소에 올렸습니다.")
    return True


def main():
    줄긋기("1단계 · 워크플로 파일 준비")
    if not 워크플로_파일_올리기():
        return 1

    줄긋기("2단계 · Pages 배포 방식 전환")
    현재, _ = gh_api(f"{기준}/pages")
    if 현재:
        print(f"  현재 방식: {현재.get('build_type', '-')}")
        if 현재.get("build_type") == "workflow":
            print("  이미 workflow 방식입니다. 전환을 건너뜁니다.")
        else:
            _, 오류 = gh_api(f"{기준}/pages", {"build_type": "workflow"}, "PUT")
            if 오류:
                print(f"[오류] 전환에 실패했습니다.\n{오류}")
                return 1
            print("  workflow 방식으로 바꿨습니다.")
    else:
        # Pages 자체가 꺼져 있으면 workflow 방식으로 새로 켭니다.
        _, 오류 = gh_api(f"{기준}/pages", {"build_type": "workflow"}, "POST")
        if 오류:
            print(f"[오류] Pages 를 켜지 못했습니다.\n{오류}")
            return 1
        print("  Pages 를 workflow 방식으로 켰습니다.")

    줄긋기("3단계 · 워크플로 실행")
    _, 오류 = gh_api(f"{기준}/actions/workflows/{워크플로_파일}/dispatches",
                    {"ref": "main"}, "POST")
    if 오류:
        print(f"[알림] 수동 실행 요청이 거절됐습니다. 직전 push 로 이미 돌고 있을 수 있습니다.\n{오류}")
    else:
        print("  실행을 요청했습니다.")

    print("\n  진행 상황을 기다립니다(최대 4분)...")
    마지막_상태 = None
    for _ in range(48):                      # 5초 × 48 = 4분
        time.sleep(5)
        목록, _ = gh_api(f"{기준}/actions/workflows/{워크플로_파일}/runs?per_page=1")
        실행들 = (목록 or {}).get("workflow_runs") or []
        if not 실행들:
            continue
        실행 = 실행들[0]
        상태 = f"{실행.get('status')} / {실행.get('conclusion') or '진행 중'}"
        if 상태 != 마지막_상태:
            print(f"    {상태}")
            마지막_상태 = 상태
        if 실행.get("status") == "completed":
            if 실행.get("conclusion") != "success":
                print(f"\n[실패] 워크플로가 성공하지 않았습니다: {실행.get('conclusion')}")
                print(f"  자세한 내용: {실행.get('html_url')}")
                return 1
            print(f"  성공! 실행 기록: {실행.get('html_url')}")
            break
    else:
        print("  [알림] 4분 안에 끝나지 않았습니다. 깃허브 Actions 탭에서 확인해 주세요.")

    줄긋기("4단계 · 최종 설정 확인")
    설정, _ = gh_api(f"{기준}/pages")
    if 설정:
        출처 = 설정.get("source") or {}
        for 이름, 값 in [
            ("공개 주소", 설정.get("html_url", "-")),
            ("상태", 설정.get("status", "-")),
            ("빌드 방식", 설정.get("build_type", "-")),
            ("소스 브랜치", 출처.get("branch", "-")),
            ("HTTPS 적용", "예" if 설정.get("https_enforced") else "아니오"),
        ]:
            print(f"  {이름:12s}: {값}")

    print("\n끝났습니다. 아래 주소를 열어 확인해 보세요.")
    print(f"  일반 화면   : https://hyun722.github.io/{저장소}/web_version/")
    print(f"  발표용 화면 : https://hyun722.github.io/{저장소}/web_version/steps.html")
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
