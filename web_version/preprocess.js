// 작성일: 2026-09-27 03:52 (KST)
//
// preprocess.js
// 캔버스에 그린 그림을 MNIST 형식(28x28)으로 바꿉니다.
// 데스크톱 버전 utils.py 의 `이미지를_28x28로_전처리` 와 같은 순서로 처리하며,
// 상수(20px, 무게중심, 0.1307/0.3081)도 동일해야 인식률이 유지됩니다.
//
//   1) 흑백으로 바꾸고, 배경이 밝으면 색을 반전 (검정 배경 + 흰 글씨로 통일)
//   2) 글씨가 있는 영역만 잘라내기
//   3) 비율을 유지하며 긴 변을 20px 로 축소
//   4) 28x28 캔버스 가운데에 넣고 무게중심을 정중앙으로 이동
//   5) 평균 0.1307, 표준편차 0.3081 로 정규화

const MNIST_평균 = 0.1307;
const MNIST_표준편차 = 0.3081;
const 밝기_임계값 = 30;     // 이 값보다 밝으면 '글씨가 있다'고 봅니다.

/** RGBA 이미지 데이터를 밝기(0~255) 1채널 배열로 바꿉니다. */
function 흑백으로(이미지데이터) {
  const { width: 너비, height: 높이, data: 화소 } = 이미지데이터;
  const 밝기 = new Uint8ClampedArray(너비 * 높이);
  for (let i = 0; i < 밝기.length; i++) {
    // 사람 눈의 민감도를 반영한 표준 가중치입니다.
    밝기[i] = 0.299 * 화소[i * 4] + 0.587 * 화소[i * 4 + 1] + 0.114 * 화소[i * 4 + 2];
  }
  return { 밝기, 너비, 높이 };
}

/** 테두리가 밝으면 흰 배경으로 보고 색을 반전합니다. */
function 배경을_검정으로(밝기, 너비, 높이) {
  let 합 = 0;
  let 개수 = 0;
  for (let x = 0; x < 너비; x++) {
    합 += 밝기[x] + 밝기[(높이 - 1) * 너비 + x];
    개수 += 2;
  }
  for (let y = 0; y < 높이; y++) {
    합 += 밝기[y * 너비] + 밝기[y * 너비 + (너비 - 1)];
    개수 += 2;
  }
  if (합 / 개수 > 127) {
    for (let i = 0; i < 밝기.length; i++) 밝기[i] = 255 - 밝기[i];
  }
  return 밝기;
}

/** 글씨가 있는 최소 사각형을 찾습니다. 글씨가 없으면 null 을 돌려줍니다. */
function 글씨_영역_찾기(밝기, 너비, 높이) {
  let 상 = 높이, 하 = -1, 좌 = 너비, 우 = -1;
  for (let y = 0; y < 높이; y++) {
    for (let x = 0; x < 너비; x++) {
      if (밝기[y * 너비 + x] > 밝기_임계값) {
        if (y < 상) 상 = y;
        if (y > 하) 하 = y;
        if (x < 좌) 좌 = x;
        if (x > 우) 우 = x;
      }
    }
  }
  if (하 < 0) return null;
  return { 좌, 상, 너비: 우 - 좌 + 1, 높이: 하 - 상 + 1 };
}

/** 무게중심이 28x28 의 정중앙(13.5, 13.5)에 오도록 평행이동합니다. */
function 무게중심_맞추기(격자) {
  let 전체 = 0, 행합 = 0, 열합 = 0;
  for (let y = 0; y < 28; y++) {
    for (let x = 0; x < 28; x++) {
      const 값 = 격자[y * 28 + x];
      전체 += 값;
      행합 += y * 값;
      열합 += x * 값;
    }
  }
  if (전체 === 0) return 격자;

  const 이동y = Math.round(13.5 - 행합 / 전체);
  const 이동x = Math.round(13.5 - 열합 / 전체);
  if (이동y === 0 && 이동x === 0) return 격자;

  const 결과 = new Float32Array(784);
  for (let y = 0; y < 28; y++) {
    const 새y = y + 이동y;
    if (새y < 0 || 새y >= 28) continue;
    for (let x = 0; x < 28; x++) {
      const 새x = x + 이동x;
      if (새x < 0 || 새x >= 28) continue;
      결과[새y * 28 + 새x] = 격자[y * 28 + x];
    }
  }
  return 결과;
}

/**
 * 캔버스를 MNIST 형식으로 전처리합니다.
 * @param {HTMLCanvasElement} 캔버스 그림이 그려진 캔버스
 * @returns {{입력: Float32Array, 미리보기: Uint8ClampedArray}|null}
 *          입력은 정규화된 784개 값, 미리보기는 0~255 의 28x28 값.
 *          글씨가 없으면 null.
 */
function 전처리(캔버스) {
  const 맥락 = 캔버스.getContext("2d", { willReadFrequently: true });
  const { 밝기, 너비, 높이 } = 흑백으로(맥락.getImageData(0, 0, 캔버스.width, 캔버스.height));
  배경을_검정으로(밝기, 너비, 높이);

  const 영역 = 글씨_영역_찾기(밝기, 너비, 높이);
  if (!영역) return null;

  // 잘라낸 영역을 임시 캔버스에 옮깁니다(밝기값을 회색조 RGBA 로 되돌립니다).
  const 원본캔버스 = document.createElement("canvas");
  원본캔버스.width = 영역.너비;
  원본캔버스.height = 영역.높이;
  const 원본맥락 = 원본캔버스.getContext("2d");
  const 잘린이미지 = 원본맥락.createImageData(영역.너비, 영역.높이);
  for (let y = 0; y < 영역.높이; y++) {
    for (let x = 0; x < 영역.너비; x++) {
      const 값 = 밝기[(영역.상 + y) * 너비 + (영역.좌 + x)];
      const i = (y * 영역.너비 + x) * 4;
      잘린이미지.data[i] = 잘린이미지.data[i + 1] = 잘린이미지.data[i + 2] = 값;
      잘린이미지.data[i + 3] = 255;
    }
  }
  원본맥락.putImageData(잘린이미지, 0, 0);

  // 비율을 유지하며 긴 변을 20px 로 줄입니다.
  let 새너비, 새높이;
  if (영역.높이 > 영역.너비) {
    새높이 = 20;
    새너비 = Math.max(1, Math.round((영역.너비 * 20) / 영역.높이));
  } else {
    새너비 = 20;
    새높이 = Math.max(1, Math.round((영역.높이 * 20) / 영역.너비));
  }

  // 28x28 검정 캔버스 가운데에 붙입니다.
  const 작은캔버스 = document.createElement("canvas");
  작은캔버스.width = 28;
  작은캔버스.height = 28;
  const 작은맥락 = 작은캔버스.getContext("2d", { willReadFrequently: true });
  작은맥락.fillStyle = "black";
  작은맥락.fillRect(0, 0, 28, 28);
  작은맥락.imageSmoothingEnabled = true;
  작은맥락.imageSmoothingQuality = "high";
  작은맥락.drawImage(
    원본캔버스,
    Math.floor((28 - 새너비) / 2),
    Math.floor((28 - 새높이) / 2),
    새너비,
    새높이
  );

  const 축소자료 = 작은맥락.getImageData(0, 0, 28, 28).data;
  let 격자 = new Float32Array(784);
  for (let i = 0; i < 784; i++) 격자[i] = 축소자료[i * 4];   // 회색조라 R 값만 써도 됩니다.

  격자 = 무게중심_맞추기(격자);

  // 미리보기용 0~255 값과, 모델에 넣을 정규화 값을 함께 돌려줍니다.
  const 미리보기 = new Uint8ClampedArray(784);
  const 입력 = new Float32Array(784);
  for (let i = 0; i < 784; i++) {
    미리보기[i] = 격자[i];
    입력[i] = (격자[i] / 255 - MNIST_평균) / MNIST_표준편차;
  }
  return { 입력, 미리보기 };
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { MNIST_평균, MNIST_표준편차, 무게중심_맞추기, 글씨_영역_찾기, 배경을_검정으로 };
}
