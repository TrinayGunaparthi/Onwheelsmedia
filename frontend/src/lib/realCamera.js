// Real Camera integration via face-api.js loaded from CDN as UMD script.
// Graceful fallback to the anonymous simulator when: camera denied, model load fails, no faces detected.
// STILL privacy-first: we NEVER send raw frames, only aggregated bucket counts.

import { simulate } from "@/lib/audience";

const SCRIPT_URL = "https://cdn.jsdelivr.net/npm/@vladmandic/face-api@1.7.13/dist/face-api.js";
const MODEL_URL = "https://cdn.jsdelivr.net/npm/@vladmandic/face-api@1.7.13/model";
let modelsReady = false;
let stream = null;
let videoEl = null;
let unavailable = false;

function loadScript(url) {
  return new Promise((resolve, reject) => {
    if (window.faceapi) return resolve(window.faceapi);
    const s = document.createElement("script");
    s.src = url;
    s.async = true;
    s.onload = () => resolve(window.faceapi);
    s.onerror = reject;
    document.head.appendChild(s);
  });
}

function bucketAge(age) {
  if (age < 18) return "under18";
  if (age < 25) return "18-24";
  if (age < 35) return "25-34";
  if (age < 45) return "35-44";
  if (age < 55) return "45-54";
  return "55+";
}

export async function initCamera() {
  if (unavailable) return false;
  try {
    const faceapi = await loadScript(SCRIPT_URL);
    if (!faceapi) throw new Error("face-api not loaded");
    if (!modelsReady) {
      await faceapi.nets.tinyFaceDetector.loadFromUri(MODEL_URL);
      await faceapi.nets.ageGenderNet.loadFromUri(MODEL_URL);
      modelsReady = true;
    }
    if (!stream) {
      stream = await navigator.mediaDevices.getUserMedia({ video: { width: 320, height: 240, facingMode: "user" }, audio: false });
      videoEl = document.createElement("video");
      videoEl.srcObject = stream;
      videoEl.muted = true;
      videoEl.playsInline = true;
      await videoEl.play();
    }
    return true;
  } catch (e) {
    console.warn("Camera unavailable; using simulator fallback.", (e && e.message) || e);
    unavailable = true;
    return false;
  }
}

export async function detectSample() {
  const ok = await initCamera();
  if (!ok) return simulate();
  const faceapi = window.faceapi;
  try {
    const detections = await faceapi
      .detectAllFaces(videoEl, new faceapi.TinyFaceDetectorOptions({ inputSize: 224, scoreThreshold: 0.5 }))
      .withAgeAndGender();
    const viewers = detections.length;
    const age_distribution = {};
    const gender_distribution = {};
    let attention_sum = 0;
    let looking = 0;
    detections.forEach((d) => {
      const b = bucketAge(d.age);
      age_distribution[b] = (age_distribution[b] || 0) + 1;
      const g = d.gender;
      gender_distribution[g] = (gender_distribution[g] || 0) + 1;
      const bx = d.detection.box;
      const cx = bx.x + bx.width / 2;
      const cy = bx.y + bx.height / 2;
      const nx = Math.abs(cx / videoEl.videoWidth - 0.5);
      const ny = Math.abs(cy / videoEl.videoHeight - 0.5);
      const looked = nx < 0.25 && ny < 0.35;
      if (looked) looking++;
      attention_sum += Math.max(0, 100 - Math.round((nx + ny) * 100));
    });
    const attention_score = viewers ? Math.round(attention_sum / viewers) : 0;
    return {
      viewers,
      people_present: viewers > 0,
      age_distribution,
      gender_distribution,
      attention_score,
      looking_at_screen: looking,
      avg_view_duration_sec: viewers ? 5 : 0,
      source: "face_api",
    };
  } catch (e) {
    console.warn("detect failed; simulator fallback", e);
    return simulate();
  }
}
