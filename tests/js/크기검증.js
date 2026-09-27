// 작성일: 2026-09-27 04:18 (KST)
// 작성자: 2601975 정수현
//
// 크기검증.js
// model.js 의 가중치_해석 이 잘못된 크기의 버퍼를 받으면 예외를 던지는지 확인합니다.
//
// 실행: node tests/js/크기검증.js

const fs = require("fs");
const path = require("path");

const 모델 = require("../../web_version/model.js");

const MODEL_BIN_경로 = path.join(__dirname, "..", "..", "web_version", "model.bin");

function main() {
  // 실제 model.bin 을 읽어 앞 1000바이트만 남기고 자릅니다.
  const b = fs.readFileSync(MODEL_BIN_경로);
  const 원본_버퍼 = b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength);
  const 잘린_버퍼 = 원본_버퍼.slice(0, 1000);

  try {
    모델.가중치_해석(잘린_버퍼);
  } catch (오류) {
    console.log(`통과 (예외 메시지: ${오류.message})`);
    process.exit(0);
  }

  console.error("[실패] 잘린 버퍼를 넣었는데 예외가 나지 않았습니다.");
  process.exit(1);
}

main();
