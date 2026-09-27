// 작성일: 2026-09-27 03:56 (KST)
// 작성자: 2601975 정수현
//
// app.js
// 화면(캔버스, 단추, 결과 표시)과 추론 엔진을 연결합니다.
// model.js(추론)와 preprocess.js(전처리)가 먼저 읽혀 있어야 합니다.

const 캔버스 = document.getElementById("그림판");
const 맥락 = 캔버스.getContext("2d", { willReadFrequently: true });
const 미리보기캔버스 = document.getElementById("미리보기");
const 결과숫자 = document.getElementById("결과숫자");
const 확신도글 = document.getElementById("확신도");
const 상태글 = document.getElementById("상태");
const 인식단추 = document.getElementById("인식단추");
const 지우기단추 = document.getElementById("지우기단추");

const 캔버스크기 = 280;          // 내부 해상도(화면 표시 크기와 별개)
const 펜_굵기 = 20;              // 28x28 로 줄였을 때 2px 안팎이 되도록 정했습니다.

let 가중치 = null;
let 그리는중 = false;
let 직전좌표 = null;
let 뭔가그렸다 = false;

/* ── 캔버스 준비 ───────────────────────────────────────────── */

캔버스.width = 캔버스크기;
캔버스.height = 캔버스크기;
맥락.lineCap = "round";
맥락.lineJoin = "round";
맥락.lineWidth = 펜_굵기;
맥락.strokeStyle = "#ffffff";
맥락.fillStyle = "#ffffff";

function 지우기() {
  맥락.save();
  맥락.fillStyle = "#000000";
  맥락.fillRect(0, 0, 캔버스크기, 캔버스크기);
  맥락.restore();

  뭔가그렸다 = false;
  결과숫자.textContent = "?";
  확신도글.textContent = "숫자를 그려 주세요";
  확률_그리기(new Float32Array(10));
  미리보기_지우기();
}

/** 화면 좌표를 캔버스 내부 좌표로 바꿉니다(확대/축소 대응). */
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
  뭔가그렸다 = true;
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

지우기단추.addEventListener("click", 지우기);
인식단추.addEventListener("click", 인식);

/* ── 결과 표시 ─────────────────────────────────────────────── */

/** 0~9 확률 막대를 만듭니다(처음 한 번). */
function 확률표_만들기() {
  const 표 = document.getElementById("확률표");
  for (let 숫자 = 0; 숫자 < 10; 숫자++) {
    const 줄 = document.createElement("div");
    줄.className = "확률줄";
    줄.id = `확률줄${숫자}`;
    줄.innerHTML =
      `<span>${숫자}</span><div class="막대"><span id="막대${숫자}"></span></div>` +
      `<span class="수치" id="수치${숫자}">0.0%</span>`;
    표.appendChild(줄);
  }
}

function 확률_그리기(확률) {
  let 으뜸 = -1;
  let 최대 = 0;
  for (let i = 0; i < 10; i++) {
    if (확률[i] > 최대) { 최대 = 확률[i]; 으뜸 = i; }
  }
  for (let 숫자 = 0; 숫자 < 10; 숫자++) {
    document.getElementById(`막대${숫자}`).style.width = `${확률[숫자] * 100}%`;
    document.getElementById(`수치${숫자}`).textContent = `${(확률[숫자] * 100).toFixed(1)}%`;
    document.getElementById(`확률줄${숫자}`).classList.toggle("으뜸", 숫자 === 으뜸 && 최대 > 0);
  }
}

function 미리보기_그리기(미리보기) {
  const 맥락2 = 미리보기캔버스.getContext("2d");
  const 이미지 = 맥락2.createImageData(28, 28);
  for (let i = 0; i < 784; i++) {
    const 값 = 미리보기[i];
    이미지.data[i * 4] = 이미지.data[i * 4 + 1] = 이미지.data[i * 4 + 2] = 값;
    이미지.data[i * 4 + 3] = 255;
  }
  맥락2.putImageData(이미지, 0, 0);
}

function 미리보기_지우기() {
  const 맥락2 = 미리보기캔버스.getContext("2d");
  맥락2.fillStyle = "#000000";
  맥락2.fillRect(0, 0, 28, 28);
}

/* ── 인식 ──────────────────────────────────────────────────── */

function 인식() {
  if (!가중치) {
    상태글.textContent = "모델을 아직 불러오는 중입니다...";
    return;
  }
  if (!뭔가그렸다) {
    확신도글.textContent = "그림이 비어 있습니다";
    return;
  }

  const 결과 = 전처리(캔버스);
  if (!결과) {
    확신도글.textContent = "그림이 비어 있습니다";
    return;
  }

  const 시작 = performance.now();
  const 확률 = 추론(가중치, 결과.입력);
  const 걸린시간 = performance.now() - 시작;

  let 예측 = 0;
  for (let i = 1; i < 10; i++) if (확률[i] > 확률[예측]) 예측 = i;

  결과숫자.textContent = String(예측);
  확신도글.textContent = `확신도 ${(확률[예측] * 100).toFixed(1)}%`;
  확률_그리기(확률);
  미리보기_그리기(결과.미리보기);
  상태글.textContent = `추론 시간 ${걸린시간.toFixed(0)}ms (브라우저에서 계산)`;
}

/* ── 시작 ──────────────────────────────────────────────────── */

async function 시작하기() {
  확률표_만들기();
  지우기();
  인식단추.disabled = true;
  상태글.textContent = "모델 가중치를 불러오는 중입니다... (약 4.6MB, 처음 한 번만)";

  try {
    가중치 = await 가중치_불러오기("model.bin");
    인식단추.disabled = false;
    상태글.textContent = "준비 완료! 왼쪽 칸에 숫자를 그려 보세요.";
  } catch (오류) {
    상태글.textContent =
      `모델을 불러오지 못했습니다: ${오류.message} ` +
      "(model.bin 파일이 같은 폴더에 있는지 확인해 주세요)";
  }
}

시작하기();
