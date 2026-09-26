// 작성일: 2026-09-27 04:18 (KST)
//
// 검증.js
// web_version/model.js 를 그대로 require 해서, tests/js/기준구현.py 가 만들어 둔
// 임시 가중치·입력으로 추론한 뒤 numpy 로 계산한 기준 확률과 비교합니다.
//
// 실행 순서(먼저 기준구현.py 로 임시 파일을 만들어야 합니다):
//   python3 tests/js/기준구현.py && node tests/js/검증.js

const fs = require("fs");
const path = require("path");

const 모델 = require("../../web_version/model.js");

const 임시_폴더 = path.join(__dirname, "_임시");
const MODEL_BIN_경로 = path.join(임시_폴더, "model.bin");
const INPUT_BIN_경로 = path.join(임시_폴더, "input.bin");
const 기준_확률_경로 = path.join(임시_폴더, "기준_확률.txt");

const 허용_오차 = 1e-5;

function 파일을_버퍼로(경로) {
  const b = fs.readFileSync(경로);
  const 버퍼 = b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength);
  return 버퍼;
}

function main() {
  for (const 경로 of [MODEL_BIN_경로, INPUT_BIN_경로, 기준_확률_경로]) {
    if (!fs.existsSync(경로)) {
      console.error(
        `[오류] ${경로} 가 없습니다. 먼저 'python3 tests/js/기준구현.py' 를 실행하세요.`
      );
      process.exit(1);
    }
  }

  const 가중치_버퍼 = 파일을_버퍼로(MODEL_BIN_경로);
  const 가중치 = 모델.가중치_해석(가중치_버퍼);

  const 입력_버퍼 = 파일을_버퍼로(INPUT_BIN_경로);
  const 입력 = new Float32Array(입력_버퍼);

  const 기준_확률 = fs
    .readFileSync(기준_확률_경로, "utf-8")
    .trim()
    .split(/\s+/)
    .map(Number);

  const 시작 = process.hrtime.bigint();
  const 확률 = 모델.추론(가중치, 입력);
  const 끝 = process.hrtime.bigint();
  const 걸린_밀리초 = Number(끝 - 시작) / 1e6;

  if (확률.length !== 기준_확률.length) {
    console.error(
      `[오류] 확률 배열 길이가 다릅니다. js=${확률.length}, 기준=${기준_확률.length}`
    );
    process.exit(1);
  }

  let 최대_오차 = 0;
  for (let i = 0; i < 확률.length; i++) {
    const 오차 = Math.abs(확률[i] - 기준_확률[i]);
    if (오차 > 최대_오차) 최대_오차 = 오차;
  }

  console.log(`추론 시간: ${걸린_밀리초.toFixed(3)}ms`);
  console.log(`js 확률:   [${Array.from(확률).map((v) => v.toFixed(8)).join(", ")}]`);
  console.log(`기준 확률: [${기준_확률.map((v) => v.toFixed(8)).join(", ")}]`);
  console.log(`최대 오차: ${최대_오차}`);

  if (최대_오차 < 허용_오차) {
    console.log("검증 통과");
    process.exit(0);
  } else {
    console.error(`검증 실패: 최대 오차 ${최대_오차} >= 허용 오차 ${허용_오차}`);
    process.exit(1);
  }
}

main();
