# -*- coding: utf-8 -*-
# 작성일: 2026-09-27 04:57 (KST)
# 수정일: 2026-09-27 05:29 (KST) — 최종 리뷰 반영: 내부 리뷰 표기 제거,
#   마지막 단계에서 다음단추 비활성화 확인, 1280×800 화면 scrollHeight <= 800 단언 추가
"""
발표화면검증.py
web_version/steps.html (발표용 "단계별 시각화" 화면)을 실제 정적 서버로 띄우고
headless Chromium 으로 검증하는 종단(E2E) 테스트입니다. tests/e2e/웹검증.py 의
정적 서버 띄우기·숫자 그리기·playwright 사용법을 그대로 따릅니다.

확인하는 것:
- 모델이 실려 "준비 완료" 문구가 뜬다.
- 아무것도 그리지 않은 채로 "다음" 을 눌러도 안내 문구("먼저 그려")가 보이고
  캔버스가 아니라 그 문구가 뜬다(빈 상태 처리).
- 숫자를 하나 그린 뒤 1단계부터 6단계까지 "다음" 으로 넘기면서, 각 단계의
  제목이 기대한 문구를 담고 있고 #단계화면 안에 캔버스가 하나 이상 있다.
- "이전" 으로 다시 되돌아갈 수 있다(점 네비게이션이 아니라 단추로 확인).
- 마지막(6단계)에서는 다음단추가 비활성화된다(이전단추와 대칭).
- 단계 점(#단계점들)을 직접 클릭해도 해당 단계로 바로 이동한다.
- 1280×800 뷰포트에서 여섯 단계 전부 document.documentElement.scrollHeight 가
  800 이하다(프로젝터 화면에서 스크롤 없이 들어와야 합니다).
- 브라우저에서 pageerror 가 하나도 나지 않는다.

실행:
    python3 tests/e2e/발표화면검증.py
"""

import http.server
import socket
import sys
import threading
from functools import partial
from pathlib import Path

from playwright.sync_api import sync_playwright

저장소_루트 = Path(__file__).resolve().parent.parent.parent
WEB_VERSION_경로 = 저장소_루트 / "web_version"

# 캔버스(280x280) 기준 숫자 "1" 획. 웹검증.py 의 획모음과 같은 형식입니다.
숫자_1_획 = [[(140, 60), (140, 225)]]

등분_수 = 20
상태_대기_최대초 = 30.0

기대_단계제목들 = [
    "1. 입력",
    "2. 합성곱 1",
    "3. 합성곱 2",
    "4. 최대 풀링",
    "5. 완전연결",
    "6. 출력",
]


def 빈_포트_찾기():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def 정적서버_띄우기(폴더, 포트):
    핸들러 = partial(http.server.SimpleHTTPRequestHandler, directory=str(폴더))
    서버 = http.server.ThreadingHTTPServer(("127.0.0.1", 포트), 핸들러)
    서버.allow_reuse_address = True
    스레드 = threading.Thread(target=서버.serve_forever, daemon=True)
    스레드.start()
    return 서버, 스레드


def 캔버스_안_좌표를_페이지_좌표로(상자, x, y):
    """캔버스 내부(280x280) 좌표를 실제 화면(페이지) 좌표로 바꿉니다."""
    return (
        상자["x"] + (x / 280) * 상자["width"],
        상자["y"] + (y / 280) * 상자["height"],
    )


def 숫자_그리기(페이지, 스트로크모음):
    상자 = 페이지.locator("#그림판").bounding_box()
    for 스트로크 in 스트로크모음:
        시작x, 시작y = 캔버스_안_좌표를_페이지_좌표로(상자, *스트로크[0])
        페이지.mouse.move(시작x, 시작y)
        페이지.mouse.down()
        for i in range(len(스트로크) - 1):
            x0, y0 = 스트로크[i]
            x1, y1 = 스트로크[i + 1]
            for 단계 in range(1, 등분_수 + 1):
                t = 단계 / 등분_수
                x = x0 + (x1 - x0) * t
                y = y0 + (y1 - y0) * t
                px, py = 캔버스_안_좌표를_페이지_좌표로(상자, x, y)
                페이지.mouse.move(px, py)
        페이지.mouse.up()


def 준비완료_기다리기(페이지):
    페이지.wait_for_function(
        "document.getElementById('상태').textContent.includes('준비 완료')",
        timeout=상태_대기_최대초 * 1000,
    )


def main():
    포트 = 빈_포트_찾기()
    서버, 스레드 = 정적서버_띄우기(WEB_VERSION_경로, 포트)
    print(f"정적 서버 시작: http://127.0.0.1:{포트}/ (경로: {WEB_VERSION_경로})")

    페이지오류들 = []
    실패 = []

    try:
        with sync_playwright() as p:
            브라우저 = p.chromium.launch()
            페이지 = 브라우저.new_page(viewport={"width": 1280, "height": 800})
            페이지.on("pageerror", lambda 오류: 페이지오류들.append(str(오류)))

            페이지.goto(f"http://127.0.0.1:{포트}/steps.html")
            print("페이지 로딩 완료, '준비 완료' 대기 중...")
            준비완료_기다리기(페이지)
            print("모델 준비 완료.")

            # ── 빈 상태: 아무것도 안 그린 채로 넘겨도 안내 문구가 보인다 ──
            if "1. 입력" not in 페이지.text_content("#단계제목"):
                실패.append("시작 단계 제목이 기대와 다릅니다: " + 페이지.text_content("#단계제목"))

            페이지.click("#다음단추")
            화면글 = 페이지.text_content("#단계화면")
            if "먼저 그려" not in 화면글:
                실패.append(f"빈 상태 안내 문구가 보이지 않습니다: {화면글!r}")
            if 페이지.locator("#단계화면 canvas").count() != 0:
                실패.append("빈 상태인데도 #단계화면 에 캔버스가 있습니다.")

            페이지.click("#이전단추")  # 그리기 전 상태(1단계)로 되돌립니다.
            if "1. 입력" not in 페이지.text_content("#단계제목"):
                실패.append("이전단추로 1단계로 되돌아가지 못했습니다.")

            # ── 숫자를 그린 뒤 1~6단계를 순서대로 확인 ──
            print("숫자 '1' 을(를) 그리는 중...")
            숫자_그리기(페이지, 숫자_1_획)
            페이지.wait_for_function(
                "document.getElementById('상태').textContent.includes('인식 완료')",
                timeout=5000,
            )

            단계별_scrollHeight = {}
            for i, 기대제목 in enumerate(기대_단계제목들):
                실제제목 = 페이지.text_content("#단계제목")
                if 기대제목 not in 실제제목:
                    실패.append(f"단계 제목이 기대와 다릅니다: 기대={기대제목!r} 실제={실제제목!r}")

                캔버스_개수 = 페이지.locator("#단계화면 canvas").count()
                if 캔버스_개수 < 1:
                    실패.append(f"'{실제제목}' 단계에서 #단계화면 에 캔버스가 없습니다.")

                크기글 = 페이지.text_content("#단계크기")
                if not 크기글.strip():
                    실패.append(f"'{실제제목}' 단계의 #단계크기 가 비어 있습니다.")

                # 1280×800 화면에서 스크롤 없이 들어와야 합니다(프로젝터 발표 기준).
                scrollHeight = 페이지.evaluate("document.documentElement.scrollHeight")
                단계별_scrollHeight[기대제목] = scrollHeight
                if scrollHeight > 800:
                    실패.append(
                        f"'{실제제목}' 단계의 scrollHeight 가 {scrollHeight} 로 800 을 넘습니다."
                    )

                print(f"  확인: {실제제목}  ({크기글})  캔버스 {캔버스_개수}개  scrollHeight={scrollHeight}")

                마지막_단계인가 = i == len(기대_단계제목들) - 1
                if not 마지막_단계인가:
                    페이지.click("#다음단추")

            print("\n1280×800 화면의 단계별 scrollHeight:")
            for 제목, 값 in 단계별_scrollHeight.items():
                print(f"  {제목}: {값}")

            # 6단계(마지막)에서는 다음단추가 비활성화되어 있어야 합니다(이전단추와 대칭).
            마지막제목 = 페이지.text_content("#단계제목")
            if "6. 출력" not in 마지막제목:
                실패.append(f"마지막 단계에서 더 이상 넘어가면 안 되는데 넘어갔습니다: {마지막제목!r}")
            if not 페이지.is_disabled("#다음단추"):
                실패.append("마지막 단계에서 다음단추가 비활성화되어 있지 않습니다.")

            # 비활성화된 단추를 강제로 눌러도(예외 없이) 단계가 그대로여야 합니다.
            페이지.click("#다음단추", force=True)
            마지막제목2 = 페이지.text_content("#단계제목")
            if "6. 출력" not in 마지막제목2:
                실패.append(
                    f"비활성화된 다음단추를 강제로 눌렀는데 단계가 바뀌었습니다: {마지막제목2!r}"
                )

            # 6단계 출력 화면에는 예측 숫자가 크게 보여야 합니다.
            if 페이지.locator(".예측숫자").count() != 1:
                실패.append("6단계에 예측 숫자(.예측숫자)가 보이지 않습니다.")
            else:
                예측값 = 페이지.text_content(".예측숫자").strip()
                if 예측값 != "1":
                    실패.append(f"'1'을 그렸는데 예측이 {예측값!r} 로 나왔습니다.")

            # ── 단계 점(#단계점들) 클릭으로 바로 이동 ──
            점들 = 페이지.locator("#단계점들 .점")
            if 점들.count() != 6:
                실패.append(f"단계 점 개수가 6이 아닙니다: {점들.count()}")
            else:
                점들.nth(0).click()
                if "1. 입력" not in 페이지.text_content("#단계제목"):
                    실패.append("단계 점 클릭으로 1단계로 이동하지 못했습니다.")
                점들.nth(3).click()
                if "4. 최대 풀링" not in 페이지.text_content("#단계제목"):
                    실패.append("단계 점 클릭으로 4단계로 이동하지 못했습니다.")

            # ── 키보드 화살표로도 이동한다 ──
            페이지.keyboard.press("ArrowLeft")
            if "3. 합성곱 2" not in 페이지.text_content("#단계제목"):
                실패.append("ArrowLeft 로 이전 단계로 이동하지 못했습니다.")
            페이지.keyboard.press("ArrowRight")
            if "4. 최대 풀링" not in 페이지.text_content("#단계제목"):
                실패.append("ArrowRight 로 다음 단계로 이동하지 못했습니다.")

            # ── 지우기 → 다시 빈 상태로 돌아간다 ──
            페이지.click("#지우기단추")
            화면글 = 페이지.text_content("#단계화면")
            if "먼저 그려" not in 화면글:
                실패.append(f"지운 뒤에도 안내 문구가 아닌 다른 내용이 보입니다: {화면글!r}")

            브라우저.close()
    finally:
        서버.shutdown()
        스레드.join(timeout=5)

    if 페이지오류들:
        print("\n[오류] 브라우저에서 pageerror 가 발생했습니다:")
        for 오류 in 페이지오류들:
            print(f"  - {오류}")

    if 실패:
        print("\n[오류] 검증에 실패한 항목이 있습니다:")
        for 항목 in 실패:
            print(f"  - {항목}")

    if not 페이지오류들 and not 실패:
        print("\n발표화면검증 통과: 여섯 단계 모두 정상 동작했고 오류가 없습니다.")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
