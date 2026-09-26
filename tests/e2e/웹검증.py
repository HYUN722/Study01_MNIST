# -*- coding: utf-8 -*-
# 작성일: 2026-09-27 04:18 (KST)
"""
웹검증.py
web_version 을 실제 정적 서버로 띄우고 headless Chromium 으로 숫자를 그려
브라우저 안에서 동작하는 인식기가 실제로 맞게 인식하는지 확인하는 종단(E2E) 테스트입니다.

- 빈 포트를 골라 `http.server` 를 백그라운드 스레드로 띄웁니다(`file://` 로 열면
  fetch("model.bin") 이 막히므로 반드시 서버로 띄워야 합니다).
- `#상태` 글에 "준비 완료" 가 나타날 때까지 최대 30초 기다립니다.
- 획모음에 정의된 4개 숫자를 각각 그려(획을 20등분해 부드럽게 이어 그림) `#결과숫자` 를 읽습니다.
- 브라우저의 `pageerror` 를 모두 모아, 하나라도 있으면 실패로 봅니다.
- 4개 모두 맞고 오류가 없으면 종료 코드 0, 아니면 1.

실행:
    python3 tests/e2e/웹검증.py
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

# 캔버스(280x280) 기준 획 좌표. 각 숫자는 여러 획(스트로크)의 목록이고,
# 각 획은 마우스를 누른 채 지나가는 점들의 목록입니다.
획모음 = {
    "1": [[(140, 60), (140, 225)]],
    "7": [[(75, 60), (205, 60)], [(205, 60), (120, 230)]],
    "4": [[(170, 55), (75, 165)], [(75, 165), (215, 165)], [(170, 100), (170, 235)]],
    "3": [[(85, 70), (180, 60), (170, 130), (110, 142)],
          [(110, 142), (190, 155), (175, 225), (85, 220)]],
}

등분_수 = 20
상태_대기_최대초 = 30.0


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
    결과 = {}

    try:
        with sync_playwright() as p:
            브라우저 = p.chromium.launch()
            페이지 = 브라우저.new_page()
            페이지.on("pageerror", lambda 오류: 페이지오류들.append(str(오류)))

            페이지.goto(f"http://127.0.0.1:{포트}/index.html")
            print("페이지 로딩 완료, '준비 완료' 대기 중...")
            준비완료_기다리기(페이지)
            print("모델 준비 완료.")

            for 숫자, 스트로크모음 in 획모음.items():
                페이지.locator("#지우기단추").click()
                숫자_그리기(페이지, 스트로크모음)
                # 손을 떼면 app.js 가 자동으로 인식하므로 결과가 반영될 시간을 조금 줍니다.
                페이지.wait_for_function(
                    "document.getElementById('결과숫자').textContent !== '?'",
                    timeout=5000,
                )
                인식결과 = 페이지.locator("#결과숫자").text_content()
                확신도 = 페이지.locator("#확신도").text_content()
                결과[숫자] = 인식결과
                print(f"  기대={숫자}  인식={인식결과}  ({확신도})")

            브라우저.close()
    finally:
        서버.shutdown()
        스레드.join(timeout=5)

    실패 = []
    for 숫자, 인식결과 in 결과.items():
        if 인식결과 != 숫자:
            실패.append(f"{숫자} 을(를) 그렸는데 {인식결과} 로 인식됨")

    if 페이지오류들:
        print("\n[오류] 브라우저에서 pageerror 가 발생했습니다:")
        for 오류 in 페이지오류들:
            print(f"  - {오류}")

    if 실패:
        print("\n[오류] 인식이 틀린 숫자가 있습니다:")
        for 항목 in 실패:
            print(f"  - {항목}")

    if not 페이지오류들 and not 실패:
        print("\n웹검증 통과: 4개 숫자 모두 정확히 인식됐고 오류가 없습니다.")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
