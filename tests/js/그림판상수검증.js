// 작성일: 2026-09-27 05:29 (KST)
//
// 그림판상수검증.js
// web_version/steps.js 와 web_version/app.js 는 그림판(캔버스) 코드가 60여 줄 중복돼
// 있습니다. 컨트롤러 판정으로 코드 추출은 하지 않고(양쪽 화면 회귀 위험이 이득보다
// 큼), 대신 두 파일에서 정규식으로 핵심 상수(캔버스크기, 펜_굵기)를 뽑아 값이
// 같은지만 단언합니다. 스펙 성공 기준 1(두 화면의 확률이 같다)을 실제로 깨뜨릴
// 다음 후보가 이 두 상수라, 값이 벌어지면 이 테스트가 바로 실패해야 합니다.
//
// 실행: node tests/js/그림판상수검증.js

const fs = require("fs");
const path = require("path");

const STEPS_경로 = path.join(__dirname, "../../web_version/steps.js");
const APP_경로 = path.join(__dirname, "../../web_version/app.js");

/** 소스 코드 텍스트에서 `const 이름 = 숫자;` 형태의 상수 값을 뽑습니다. */
function 상수_뽑기(파일경로, 이름) {
  const 내용 = fs.readFileSync(파일경로, "utf8");
  const 정규식 = new RegExp(`const\\s+${이름}\\s*=\\s*(\\d+)`);
  const 일치 = 내용.match(정규식);
  if (!일치) {
    console.error(`[오류] ${path.basename(파일경로)} 에서 상수 ${이름} 을 찾지 못했습니다.`);
    process.exit(1);
  }
  return Number(일치[1]);
}

function 실패하면종료(조건, 메시지) {
  if (!조건) {
    console.error(`[실패] ${메시지}`);
    process.exit(1);
  }
  console.log(`통과: ${메시지}`);
}

function main() {
  const steps_캔버스크기 = 상수_뽑기(STEPS_경로, "캔버스크기");
  const app_캔버스크기 = 상수_뽑기(APP_경로, "캔버스크기");
  const steps_펜굵기 = 상수_뽑기(STEPS_경로, "펜_굵기");
  const app_펜굵기 = 상수_뽑기(APP_경로, "펜_굵기");

  실패하면종료(
    steps_캔버스크기 === app_캔버스크기,
    `캔버스크기 가 steps.js(${steps_캔버스크기})와 app.js(${app_캔버스크기})에서 같습니다`
  );
  실패하면종료(
    steps_펜굵기 === app_펜굵기,
    `펜_굵기 가 steps.js(${steps_펜굵기})와 app.js(${app_펜굵기})에서 같습니다`
  );

  console.log("모든 단언 통과");
}

main();
