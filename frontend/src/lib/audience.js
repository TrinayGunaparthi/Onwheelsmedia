// Privacy-first audience sampler. Emits ANONYMOUS aggregated stats every 30s.
// In production, replace `simulate()` with face-api.js / MediaPipe running locally on the device.
// No raw frames, no identity data — only counts and buckets.

const AGE_BUCKETS = ["under18", "18-24", "25-34", "35-44", "45-54", "55+"];
const GENDERS = ["male", "female"];

function pickWeighted(items, weights) {
  const total = weights.reduce((a,b)=>a+b, 0);
  let r = Math.random() * total;
  for (let i=0;i<items.length;i++) { r -= weights[i]; if (r <= 0) return items[i]; }
  return items[items.length-1];
}

export function simulate() {
  // Simulate 0-4 anonymous viewers with plausible urban Indian auto passenger distribution
  const viewers = Math.random() < 0.25 ? 0 : 1 + Math.floor(Math.random() * 3);
  const age_distribution = {};
  const gender_distribution = {};
  let looking = 0;
  for (let i=0; i<viewers; i++) {
    const age = pickWeighted(AGE_BUCKETS, [1, 4, 6, 5, 3, 2]); // peak 25-34
    const gender = pickWeighted(GENDERS, [55, 45]);
    age_distribution[age] = (age_distribution[age] || 0) + 1;
    gender_distribution[gender] = (gender_distribution[gender] || 0) + 1;
    if (Math.random() < 0.6) looking++;
  }
  const attention = viewers === 0 ? 0 : Math.max(0, Math.min(100, Math.round(30 + (looking / viewers) * 60 + (Math.random()*10 - 5))));
  return {
    viewers,
    people_present: viewers > 0,
    age_distribution,
    gender_distribution,
    attention_score: attention,
    looking_at_screen: looking,
    avg_view_duration_sec: viewers ? Math.round(3 + Math.random() * 8) : 0,
    source: "simulator"
  };
}

export function topKey(dist) {
  let best = null, bestV = -1;
  for (const [k, v] of Object.entries(dist || {})) {
    if (v > bestV) { best = k; bestV = v; }
  }
  return best || "";
}
