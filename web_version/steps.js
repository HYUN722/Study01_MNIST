// 작성일: 2026-09-27 04:57 (KST)
// 수정일: 2026-09-27 05:29 (KST) — 최종 리뷰 반영: 막대 대비, 모델 적재 실패 안내,
// 작성자: 2601975 정수현
//   3단계 설명 오타, 마지막 단계 다음단추 비활성화, 캔버스 접근성(role/aria-label)
//
// steps.js
// 발표용 "단계별 시각화" 화면의 동작을 맡습니다: 그림판 연결, 모델 불러오기,
// 여섯 단계 사이의 이동과 각 단계의 그리기를 연결합니다.
// model.js(추론)·preprocess.js(전처리)·시각화.js(특징지도_그리기) 가
// 이 파일보다 먼저 읽혀 있어야 합니다.
//
// 계산(합성곱·풀링·완전연결)은 여기서 다시 하지 않습니다. 추론_단계별() 을
// 손을 뗄 때 한 번만 부르고, 단계 전환은 그 결과를 다시 그리기만 합니다.

const 캔버스 = document.getElementById("그림판");
const 맥락 = 캔버스.getContext("2d", { willReadFrequently: true });
const 지우기단추 = document.getElementById("지우기단추");
const 이전단추 = document.getElementById("이전단추");
const 다음단추 = document.getElementById("다음단추");
const 단계점들칸 = document.getElementById("단계점들");
const 단계제목 = document.getElementById("단계제목");
const 단계설명 = document.getElementById("단계설명");
const 단계크기 = document.getElementById("단계크기");
const 단계화면 = document.getElementById("단계화면");
const 상태글 = document.getElementById("상태");

const 캔버스크기 = 280;      // index.html 의 그림판과 같은 내부 해상도
const 펜_굵기 = 20;          // index.html 의 그림판과 같은 굵기라야 인식 결과가 같습니다.

let 가중치 = null;
let 적재_실패 = false;        // model.bin 을 못 읽었으면 true (인식()/단계_그리기() 의 안내문에 씁니다)
let 그리는중 = false;
let 직전좌표 = null;
let 마지막결과 = null;        // 추론_단계별() 의 반환값({확률, 단계})
let 마지막전처리 = null;      // 전처리() 의 반환값(미리보기 포함)
let 현재단계 = 0;

/* ── 캔버스 준비(index.html/app.js 와 같은 방식) ─────────────── */

캔버스.width = 캔버스크기;
캔버스.height = 캔버스크기;
맥락.lineCap = "round";
맥락.lineJoin = "round";
맥락.lineWidth = 펜_굵기;
맥락.strokeStyle = "#ffffff";
맥락.fillStyle = "#ffffff";

function 캔버스_지우기() {
  맥락.save();
  맥락.fillStyle = "#000000";
  맥락.fillRect(0, 0, 캔버스크기, 캔버스크기);
  맥락.restore();
}

/** 화면 좌표를 캔버스 내부 좌표로 바꿉니다(확대/축소 대응). app.js 의 좌표() 와 동일합니다. */
function 좌표(사건) {
  const 영역 = 캔버스.getBoundingClientRect();
  return {
    x: ((사건.clientX - 영역.left) / 영역.width) * 캔버스크기,
    y: ((사건.clientY - 영역.top) / 영역.height) * 캔버스크기,
  };
}

function 그리기시작(사건) {
  사건.preventDefault();
  그리는중 = true;
  직전좌표 = 좌표(사건);
  맥락.beginPath();
  맥락.arc(직전좌표.x, 직전좌표.y, 펜_굵기 / 2, 0, Math.PI * 2);
  맥락.fill();
  캔버스.setPointerCapture(사건.pointerId);
}

function 그리는중처리(사건) {
  if (!그리는중) return;
  사건.preventDefault();
  const 현재 = 좌표(사건);
  맥락.beginPath();
  맥락.moveTo(직전좌표.x, 직전좌표.y);
  맥락.lineTo(현재.x, 현재.y);
  맥락.stroke();
  직전좌표 = 현재;
}

function 그리기끝(사건) {
  if (!그리는중) return;
  사건.preventDefault();
  그리는중 = false;
  직전좌표 = null;
  인식();                       // 손을 떼면 바로 인식합니다.
}

캔버스.addEventListener("pointerdown", 그리기시작);
캔버스.addEventListener("pointermove", 그리는중처리);
캔버스.addEventListener("pointerup", 그리기끝);
캔버스.addEventListener("pointercancel", 그리기끝);
캔버스.addEventListener("contextmenu", (사건) => {
  사건.preventDefault();
  지우기();
});

function 지우기() {
  캔버스_지우기();
  마지막결과 = null;
  마지막전처리 = null;
  단계_그리기();
}

지우기단추.addEventListener("click", 지우기);

/* ── 단계화면을 채우는 그리기 함수들 ───────────────────────────
   추론 계산은 절대 다시 하지 않습니다. model.js 의 추론_단계별() 이
   돌려준 결과와 시각화.js 의 특징지도_그리기() 만 씁니다. */

/** 무대 캔버스를 하나 만듭니다(붙이지는 않습니다). 스크린 리더가 "그림이 통째로
 *  바뀌었다"만 알고 내용을 모르는 일이 없도록 role="img" 와, 그 단계 설명을 그대로
 *  재사용한 aria-label 을 넣습니다. */
function 무대_캔버스_만들기(설명 = "") {
  const 캔 = document.createElement("canvas");
  캔.className = "무대캔버스";
  if (설명) {
    캔.setAttribute("role", "img");
    캔.setAttribute("aria-label", 설명);
  }
  return 캔;
}

/** #단계화면 안에 캔버스를 하나 만들어 붙이고 돌려줍니다. */
function 무대캔버스(설명 = "") {
  const 캔 = 무대_캔버스_만들기(설명);
  단계화면.appendChild(캔);
  return 캔;
}

/** 단계 1: 원본 그림(280×280)과 전처리 결과(28×28, 확대)를 나란히 보여줍니다. */
function 입력_그리기() {
  const 감싸개 = document.createElement("div");
  감싸개.className = "입력비교";

  const 원본칸 = document.createElement("div");
  원본칸.className = "입력비교_칸";
  const 원본라벨 = document.createElement("p");
  원본라벨.className = "입력비교_라벨";
  원본라벨.textContent = "원본 (280×280)";
  const 원본캔버스 = document.createElement("canvas");
  원본캔버스.width = 캔버스크기;
  원본캔버스.height = 캔버스크기;
  원본캔버스.setAttribute("role", "img");
  원본캔버스.setAttribute("aria-label", 원본라벨.textContent);
  원본캔버스.getContext("2d").drawImage(캔버스, 0, 0);   // 그림판을 그대로 옮겨 찍습니다.
  원본칸.append(원본라벨, 원본캔버스);

  const 결과칸 = document.createElement("div");
  결과칸.className = "입력비교_칸";
  const 결과라벨 = document.createElement("p");
  결과라벨.className = "입력비교_라벨";
  결과라벨.textContent = "전처리 후 (28×28)";
  const 결과캔버스 = document.createElement("canvas");
  결과캔버스.className = "확대캔버스";
  결과캔버스.width = 28;
  결과캔버스.height = 28;
  결과캔버스.setAttribute("role", "img");
  결과캔버스.setAttribute("aria-label", 결과라벨.textContent);
  const 맥락2 = 결과캔버스.getContext("2d");
  const 이미지 = 맥락2.createImageData(28, 28);
  for (let i = 0; i < 784; i++) {
    const 값 = 마지막전처리.미리보기[i];
    이미지.data[i * 4] = 이미지.data[i * 4 + 1] = 이미지.data[i * 4 + 2] = 값;
    이미지.data[i * 4 + 3] = 255;
  }
  맥락2.putImageData(이미지, 0, 0);
  결과칸.append(결과라벨, 결과캔버스);

  감싸개.append(원본칸, 결과칸);
  단계화면.appendChild(감싸개);
}

/**
 * 값들을 세로 막대로 그립니다(5단계 완전연결1의 128개, 6단계 확률 10개에 씁니다).
 * @param {HTMLCanvasElement} 캔버스대상
 * @param {ArrayLike<number>} 값들
 * @param {{라벨?: boolean, 강조?: number, 최대값?: number}} [옵션]
 */
function 막대그래프_그리기(캔버스대상, 값들, 옵션 = {}) {
  const { 라벨 = false, 강조 = -1, 최대값 = null } = 옵션;
  const 너비 = 720;
  const 높이 = 300;
  캔버스대상.width = 너비;
  캔버스대상.height = 높이;
  const 맥락2 = 캔버스대상.getContext("2d");

  // 화면(라이트/다크) 색상과 맞추기 위해 CSS 변수를 그대로 읽어 씁니다.
  const 스타일 = getComputedStyle(document.documentElement);
  const 강조색 = 스타일.getPropertyValue("--강조").trim() || "#1a5fb4";
  const 바탕색 = 스타일.getPropertyValue("--막대바탕").trim() || "#e9edf2";
  const 글자색 = 스타일.getPropertyValue("--글자").trim() || "#1b1f24";

  맥락2.clearRect(0, 0, 너비, 높이);

  const 개수 = 값들.length;
  const 라벨높이 = 라벨 ? 26 : 0;
  const 그림높이 = 높이 - 라벨높이;
  const 여백 = 개수 > 32 ? 1 : 6;                      // 128개는 촘촘하게, 10개는 여유 있게
  const 막대너비 = (너비 - 여백 * (개수 + 1)) / 개수;

  let 실제최대값 = 최대값;
  if (실제최대값 === null) {
    실제최대값 = 0;
    for (let i = 0; i < 개수; i++) if (값들[i] > 실제최대값) 실제최대값 = 값들[i];
    if (실제최대값 === 0) 실제최대값 = 1;               // 전부 0 이면 0 으로 나누지 않습니다.
  }

  // index.html 의 확률표(.막대)와 같은 방식입니다: 막대는 항상 강조색으로 그리고,
  // 강조되지 않은 막대는 투명도만 낮춥니다. --막대바탕 은 "여기까지 갈 수 있다"를
  // 보여주는 트랙(배경)으로만 씁니다 — 막대 색 자체로 쓰면 흰 카드 위 대비가
  // 1.18:1 밖에 안 나와(WCAG 비텍스트 최소 3:1) 128개 막대가 전부 안 보이게 됩니다.
  for (let i = 0; i < 개수; i++) {
    const 막대높이 = Math.max(1, (값들[i] / 실제최대값) * (그림높이 - 4));
    const x = 여백 + i * (막대너비 + 여백);
    const y = 그림높이 - 막대높이;

    맥락2.fillStyle = 바탕색;
    맥락2.fillRect(x, 0, 막대너비, 그림높이);

    맥락2.globalAlpha = i === 강조 ? 1 : 0.35;
    맥락2.fillStyle = 강조색;
    맥락2.fillRect(x, y, 막대너비, 막대높이);
    맥락2.globalAlpha = 1;
  }

  if (라벨) {
    맥락2.fillStyle = 글자색;
    맥락2.font = "16px sans-serif";
    맥락2.textAlign = "center";
    for (let i = 0; i < 개수; i++) {
      const x = 여백 + i * (막대너비 + 여백) + 막대너비 / 2;
      맥락2.fillText(String(i), x, 그림높이 + 20);
    }
  }
}

/** 단계 6: 최종 예측 숫자·확신도를 크게 보여주고, 그 아래 10개 확률 막대를 그립니다. */
function 출력_그리기(결과, 설명) {
  let 예측 = 0;
  for (let i = 1; i < 10; i++) if (결과.확률[i] > 결과.확률[예측]) 예측 = i;

  const 감싸개 = document.createElement("div");
  감싸개.className = "출력칸";

  const 예측표시 = document.createElement("div");
  예측표시.className = "예측표시";
  const 예측숫자 = document.createElement("span");
  예측숫자.className = "예측숫자";
  예측숫자.textContent = String(예측);
  const 예측확신도 = document.createElement("span");
  예측확신도.className = "예측확신도";
  예측확신도.textContent = `확신도 ${(결과.확률[예측] * 100).toFixed(1)}%`;
  예측표시.append(예측숫자, 예측확신도);

  const 캔버스대상 = 무대_캔버스_만들기(설명);
  막대그래프_그리기(캔버스대상, 결과.확률, { 라벨: true, 강조: 예측, 최대값: 1 });

  감싸개.append(예측표시, 캔버스대상);
  단계화면.appendChild(감싸개);
}

/* ── 여섯 단계 정의: 설명 문구를 배열 하나에 모아, 발표 전에 고치기 쉽게 합니다. ── */

const 단계들 = [
  {
    제목: "1. 입력 전처리", 크기: "280×280 → 28×28",
    설명: "그린 그림을 잘라내고 20픽셀로 줄인 뒤, 무게중심을 한가운데로 옮겨 MNIST 와 같은 형태로 맞춥니다.",
    그리기: () => 입력_그리기(),
  },
  {
    제목: "2. 합성곱 1", 크기: "28×28 → 26×26 × 32",
    설명: "3×3 필터 32개가 각각 선·모서리 같은 단순한 무늬에 반응합니다. 밝은 곳이 강하게 반응한 자리입니다.",
    그리기: (결과, 단계) => 특징지도_그리기(무대캔버스(단계.설명), 결과.단계.합성곱1, 8),
  },
  {
    제목: "3. 합성곱 2", 크기: "26×26 → 24×24 × 64",
    설명: "2단계의 무늬들을 다시 조합해 곡선·꼭짓점처럼 더 복잡한 모양에 반응하는 64개 특징 지도를 만듭니다.",
    그리기: (결과, 단계) => 특징지도_그리기(무대캔버스(단계.설명), 결과.단계.합성곱2, 8),
  },
  {
    제목: "4. 최대 풀링", 크기: "24×24 → 12×12 × 64",
    설명: "2×2 구역마다 가장 강하게 반응한 값만 남겨 크기를 절반으로 줄입니다. 위치가 조금 달라져도 잘 인식하게 해 줍니다.",
    그리기: (결과, 단계) => 특징지도_그리기(무대캔버스(단계.설명), 결과.단계.최대풀링, 8),
  },
  {
    제목: "5. 완전연결 1 (128개)", 크기: "9216 → 128",
    설명: "풀링 결과를 한 줄로 펼친 9216개 값을 128개 값으로 압축합니다. 막대 하나가 뉴런 하나의 활성값입니다.",
    그리기: (결과, 단계) => 막대그래프_그리기(무대캔버스(단계.설명), 결과.단계.완전연결1),
  },
  {
    제목: "6. 출력 (확률)", 크기: "128 → 10",
    설명: "마지막으로 0~9 각 숫자일 확률을 계산합니다. 가장 높은 막대가 최종 예측입니다.",
    그리기: (결과, 단계) => 출력_그리기(결과, 단계.설명),
  },
];

/* ── 단계 전환 ─────────────────────────────────────────────── */

/** #단계점들 안에 단계 수만큼 점(단추)을 한 번만 만듭니다. */
function 점들_만들기() {
  단계점들칸.replaceChildren();
  단계들.forEach((단계, i) => {
    const 점 = document.createElement("button");
    점.type = "button";
    점.className = "점";
    점.setAttribute("aria-label", 단계.제목);
    점.addEventListener("click", () => 단계로_이동(i));
    단계점들칸.appendChild(점);
  });
}

function 점들_갱신() {
  [...단계점들칸.children].forEach((점, i) => {
    점.classList.toggle("현재", i === 현재단계);
    점.setAttribute("aria-current", i === 현재단계 ? "step" : "false");
  });
}

/** 처음(0단계)에서는 "이전" 을, 마지막 단계에서는 "다음" 을 누를 수 없게 합니다
 *  (서로 대칭). 그렇지 않으면 마지막 단계에서 "다음" 이 활성 상태인데 눌러도
 *  아무 반응이 없는 것처럼 보입니다. */
function 단추_갱신() {
  이전단추.disabled = 현재단계 === 0;
  다음단추.disabled = 현재단계 === 단계들.length - 1;
}

/** 현재 단계의 제목·설명을 쓰고, 단계화면을 다시 그립니다.
 *  결과가 없으면(아직 안 그렸거나 지웠으면) 캔버스 대신 안내 문구만 보여줍니다. */
function 단계_그리기() {
  const 단계 = 단계들[현재단계];
  단계제목.textContent = 단계.제목;
  단계크기.textContent = 단계.크기;
  단계설명.textContent = 단계.설명;
  단계화면.replaceChildren();

  if (!마지막결과) {
    const 안내 = document.createElement("p");
    안내.className = "빈안내";
    // 모델을 못 불러온 상황에서까지 "먼저 그려 달라"고 하면 방금 그린 사람에게
    // 거짓말을 하는 셈입니다(그림은 있는데 계산할 모델이 없는 것뿐이므로).
    안내.textContent = 적재_실패
      ? "모델을 불러오지 못해 단계를 보여줄 수 없습니다."
      : "왼쪽 칸에 숫자를 먼저 그려 주세요.";
    단계화면.appendChild(안내);
    점들_갱신();
    단추_갱신();
    return;
  }
  단계.그리기(마지막결과, 단계);
  점들_갱신();
  단추_갱신();
}

function 단계로_이동(번호) {
  if (번호 < 0 || 번호 >= 단계들.length) return;
  현재단계 = 번호;
  단계_그리기();
}

function 단계_이동(델타) {
  단계로_이동(현재단계 + 델타);
}

이전단추.addEventListener("click", () => 단계_이동(-1));
다음단추.addEventListener("click", () => 단계_이동(1));

document.addEventListener("keydown", (사건) => {
  if (사건.key === "ArrowLeft") 단계_이동(-1);
  if (사건.key === "ArrowRight") 단계_이동(1);
});

/* ── 인식: 계산은 한 번만, 단계 전환은 보관한 결과에서 다시 그리기만 ─────── */

function 인식() {
  if (!가중치) {
    // app.js 와 같은 방식: 상황(불러오는 중/적재 실패)을 상태줄에 알리고,
    // 단계화면 안내문도 상황에 맞게 다시 그립니다(적재 실패 분기는 단계_그리기() 가 처리).
    상태글.textContent = 적재_실패
      ? "모델을 불러오지 못해 인식할 수 없습니다."
      : "모델을 아직 불러오는 중입니다...";
    단계_그리기();
    return;
  }

  const 전처리결과 = 전처리(캔버스);
  if (!전처리결과) {
    상태글.textContent = "그림이 비어 있습니다";
    마지막결과 = null;
    마지막전처리 = null;
    단계_그리기();
    return;
  }

  마지막전처리 = 전처리결과;
  마지막결과 = 추론_단계별(가중치, 전처리결과.입력);
  상태글.textContent = "인식 완료! 단계를 넘겨 과정을 살펴보세요.";
  단계_그리기();
}

/* ── 시작 ──────────────────────────────────────────────────── */

async function 시작하기() {
  캔버스_지우기();
  점들_만들기();
  단계_그리기();
  상태글.textContent = "모델 가중치를 불러오는 중입니다... (약 4.6MB, 처음 한 번만)";

  try {
    가중치 = await 가중치_불러오기("model.bin");
    상태글.textContent = "준비 완료! 왼쪽 칸에 숫자를 그린 뒤 단계를 넘겨 보세요.";
  } catch (오류) {
    적재_실패 = true;
    상태글.textContent = `모델을 불러오지 못했습니다: ${오류.message}`;
    단계_그리기();          // 이미 그려 둔 사람이 있어도 "먼저 그려라"가 아니라 적재 실패로 안내합니다.
  }
}

시작하기();
