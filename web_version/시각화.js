// 작성일: 2026-09-27 04:51 (KST)
//
// 시각화.js
// model.js 의 추론_단계별() 이 돌려주는 중간 결과({값, 채널, 크기})를
// 사람이 볼 수 있는 격자 이미지(특징 지도)로 그립니다.
//
// 값 은 (채널, 높이, 너비) 순서로 평탄화돼 있습니다.
// 채널 c 의 (행 r, 열 l) 은 값[c*크기*크기 + r*크기 + l] 입니다.
// ReLU 를 거친 값이라 음수가 없고, 채널에 따라서는 전부 0 일 수 있습니다.
//
// 순수 계산 함수(지도를_0_255로_펴기, 타일_배치)와 캔버스를 쓰는 그리기 함수
// (특징지도_그리기)를 분리했습니다. 계산 함수만 node 에서 테스트합니다.

/**
 * 한 채널의 값 개수개를 0~255 범위로 선형으로 펴서 밝기로 바꿉니다.
 * 최솟값·최댓값이 같으면(예: ReLU 로 전부 0) 0 으로 나누지 않고 전부 0 을 돌려줍니다.
 * @param {Float32Array} 값 전체 값 배열
 * @param {number} 시작 이 채널이 시작하는 인덱스
 * @param {number} 개수 이 채널의 원소 수(크기*크기)
 * @returns {Uint8ClampedArray} 길이 개수 인 0~255 밝기 배열
 */
function 지도를_0_255로_펴기(값, 시작, 개수) {
  let 최소 = Infinity, 최대 = -Infinity;
  for (let i = 0; i < 개수; i++) {
    const v = 값[시작 + i];
    if (v < 최소) 최소 = v;
    if (v > 최대) 최대 = v;
  }
  const 폭 = 최대 - 최소;
  const 결과 = new Uint8ClampedArray(개수);
  if (폭 === 0) return 결과;              // 전부 같은 값이면 검정. 0 으로 나누지 않는다.
  for (let i = 0; i < 개수; i++) {
    결과[i] = ((값[시작 + i] - 최소) / 폭) * 255;
  }
  return 결과;
}

/**
 * 채널수개의 크기x크기 타일을 열수 개씩 격자로 배치했을 때
 * 전체 캔버스 크기와 각 타일의 좌상단 좌표를 계산합니다.
 * @param {number} 채널수
 * @param {number} 크기 타일 한 변의 픽셀 수
 * @param {number} 열수 한 줄에 놓을 타일 수
 * @param {number} 여백 타일 사이·테두리 여백(픽셀)
 * @returns {{너비: number, 높이: number, 위치들: {x: number, y: number}[]}}
 */
function 타일_배치(채널수, 크기, 열수, 여백) {
  const 줄수 = Math.ceil(채널수 / 열수);
  const 위치들 = [];
  for (let i = 0; i < 채널수; i++) {
    위치들.push({
      x: 여백 + (i % 열수) * (크기 + 여백),
      y: 여백 + Math.floor(i / 열수) * (크기 + 여백),
    });
  }
  return { 너비: 열수 * 크기 + (열수 + 1) * 여백, 높이: 줄수 * 크기 + (줄수 + 1) * 여백, 위치들 };
}

/**
 * 추론_단계별() 의 한 단계({값, 채널, 크기})를 캔버스에 격자 타일로 그립니다.
 * 채널마다 지도를_0_255로_펴기 로 밝기를 구하고 타일_배치 로 위치를 구한 뒤,
 * 오프스크린 ImageData 한 장에 전부 찍고 마지막에 한 번만 putImageData 합니다.
 * @param {HTMLCanvasElement} 캔버스
 * @param {{값: Float32Array, 채널: number, 크기: number}} 묶음
 * @param {number} 열수
 * @param {number} 여백
 */
function 특징지도_그리기(캔버스, 묶음, 열수 = 8, 여백 = 2) {
  const { 값, 채널, 크기 } = 묶음;
  const 배치 = 타일_배치(채널, 크기, 열수, 여백);
  캔버스.width = 배치.너비;
  캔버스.height = 배치.높이;
  const 맥락 = 캔버스.getContext("2d");
  const 이미지 = 맥락.createImageData(배치.너비, 배치.높이);
  const 면 = 크기 * 크기;
  for (let 채 = 0; 채 < 채널; 채++) {
    const 편값 = 지도를_0_255로_펴기(값, 채 * 면, 면);
    const { x: 왼, y: 위 } = 배치.위치들[채];
    for (let 행 = 0; 행 < 크기; 행++) {
      for (let 열 = 0; 열 < 크기; 열++) {
        const 밝기 = 편값[행 * 크기 + 열];
        const 자리 = ((위 + 행) * 배치.너비 + (왼 + 열)) * 4;
        이미지.data[자리] = 이미지.data[자리 + 1] = 이미지.data[자리 + 2] = 밝기;
        이미지.data[자리 + 3] = 255;
      }
    }
  }
  맥락.putImageData(이미지, 0, 0);
}

// node 환경(검증 스크립트)에서도 쓸 수 있도록 내보냅니다. 브라우저에서는 무시됩니다.
if (typeof module !== "undefined" && module.exports) {
  module.exports = { 지도를_0_255로_펴기, 타일_배치, 특징지도_그리기 };
}
