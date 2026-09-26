# -*- coding: utf-8 -*-
# 작성일: 2026-09-27 06:00 (KST)
# 수정일: 2026-09-27 06:12 (KST)
"""
Pages설정_확인.py
깃허브 저장소의 GitHub Pages 설정과 최근 빌드 상태를 읽어 보여 줍니다.

읽기만 하며 아무것도 바꾸지 않습니다.
깃허브 CLI(gh) 로그인이 되어 있어야 합니다.

사용법
    이 파일을 더블클릭하세요.
"""

import json
import subprocess
import sys
from pathlib import Path

소유자 = "HYUN722"
저장소 = "Study01_MNIST"

# 창을 찾기 어려울 때를 대비해 결과를 파일로도 남깁니다.
결과_파일 = Path(__file__).resolve().parent / "Pages설정_결과.txt"
_모은_줄 = []


def 적기(내용=""):
    """화면과 결과 파일에 같은 내용을 남깁니다."""
    print(내용)
    _모은_줄.append(내용)


def 결과_저장():
    결과_파일.write_text("\n".join(_모은_줄) + "\n", encoding="utf-8")


def gh_api(경로):
    """gh api 를 호출해 결과를 dict 로 돌려줍니다. 실패하면 (None, 오류문자열)."""
    결과 = subprocess.run(
        ["gh", "api", 경로],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if 결과.returncode != 0:
        return None, (결과.stdout or "") + (결과.stderr or "")
    try:
        return json.loads(결과.stdout), ""
    except json.JSONDecodeError:
        return None, "응답을 해석하지 못했습니다"


def 줄긋기(제목):
    적기("\n" + "=" * 56)
    적기(f" {제목}")
    적기("=" * 56)


def main():
    기준 = f"repos/{소유자}/{저장소}"

    줄긋기("Pages 설정")
    설정, 오류 = gh_api(f"{기준}/pages")
    if not 설정:
        적기("[오류] Pages 설정을 읽지 못했습니다. Pages 가 꺼져 있거나 권한이 부족할 수 있습니다.")
        적기(오류)
        return 1

    출처 = 설정.get("source") or {}
    표 = [
        ("공개 주소", 설정.get("html_url", "-")),
        ("상태", 설정.get("status", "-")),
        ("빌드 방식", 설정.get("build_type", "-")),
        ("소스 브랜치", 출처.get("branch", "-")),
        ("소스 경로", 출처.get("path", "-")),
        ("HTTPS 적용", "예" if 설정.get("https_enforced") else "아니오"),
        ("사용자 도메인", 설정.get("cname") or "없음"),
        ("공개 여부", "공개" if 설정.get("public") else "비공개"),
    ]
    for 이름, 값 in 표:
        적기(f"  {이름:12s}: {값}")

    줄긋기("최근 빌드 (legacy 방식 기록 — workflow 전환 전의 것일 수 있음)")
    빌드, 오류 = gh_api(f"{기준}/pages/builds/latest")
    if 빌드:
        적기(f"  결과        : {빌드.get('status', '-')}")
        오류내용 = (빌드.get("error") or {}).get("message")
        적기(f"  오류        : {오류내용 or '없음'}")
        적기(f"  커밋        : {(빌드.get('commit') or '-')[:7]}")
        적기(f"  걸린 시간   : {빌드.get('duration', 0)} ms")
        적기(f"  생성 시각   : {빌드.get('created_at', '-')}")
    else:
        적기("  (빌드 정보를 읽지 못했습니다)")
        적기(오류)

    # workflow 방식이면 배포는 Actions 가 합니다. 그 실행 기록을 봅니다.
    if 설정.get("build_type") == "workflow":
        줄긋기("최근 워크플로 실행 (실제 배포)")
        목록, _ = gh_api(f"{기준}/actions/workflows/pages.yml/runs?per_page=1")
        실행들 = (목록 or {}).get("workflow_runs") or []
        if 실행들:
            실행 = 실행들[0]
            적기(f"  결과        : {실행.get('status')} / {실행.get('conclusion')}")
            적기(f"  커밋        : {(실행.get('head_sha') or '-')[:7]}")
            적기(f"  실행 번호   : #{실행.get('run_number')}")
            적기(f"  시작 시각   : {실행.get('created_at', '-')}")
            적기(f"  기록 주소   : {실행.get('html_url', '-')}")
        else:
            적기("  (워크플로 실행 기록이 없습니다)")

    줄긋기("저장소")
    저장소정보, _ = gh_api(기준)
    if 저장소정보:
        적기(f"  공개 여부   : {'공개' if not 저장소정보.get('private') else '비공개'}")
        적기(f"  기본 브랜치 : {저장소정보.get('default_branch', '-')}")
        적기(f"  마지막 갱신 : {저장소정보.get('pushed_at', '-')}")

    적기("\n확인이 끝났습니다. 아무것도 바꾸지 않았습니다.")
    결과_저장()
    적기(f"같은 내용을 파일로도 남겼습니다: {결과_파일.name}")
    return 0


if __name__ == "__main__":
    코드 = 1
    try:
        코드 = main()
    except Exception:
        import traceback
        적기("\n[예상치 못한 오류]")
        traceback.print_exc()
    finally:
        try:
            input("\n계속하려면 Enter 키를 누르세요...")
        except (EOFError, KeyboardInterrupt):
            pass
    sys.exit(코드)
