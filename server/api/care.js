// 금자 원클릭 돌보기
// 1) 방명록(pet/guestbook.json)에 바로 기록 + 10분 도배 방지  → 프로필 방명록에 즉시 보임
// 2) repository_dispatch → 워크플로가 스탯·카드를 갱신 (1분쯤)
const crypto = require("crypto");

const REPO = "saeodixx/saeodixx";
const PROFILE = "https://github.com/saeodixx";
const RAW = `https://raw.githubusercontent.com/${REPO}/main/pet`;
const GB_PATH = "pet/guestbook.json";
const COOLDOWN_MS = 10 * 60 * 1000;
const ACTIONS = {
  feed: { text: "금자에게 밥을 줬어요!", gif: "happy" },
  play: { text: "금자랑 신나게 놀았어요!", gif: "happy" },
  sleep: { text: "금자를 재워줬어요… 쉿", gif: "sleepy" },
};
const NICK_A = ["딸기", "별사탕", "말랑", "반짝", "솜사탕", "젤리", "복숭아", "구름", "버블", "체리"];
const NICK_B = ["토끼", "고양이", "곰돌이", "병아리", "햄스터", "강아지", "펭귄", "다람쥐"];

const nickname = (v) => {
  const h = parseInt(v.slice(0, 8), 16);
  return `${NICK_A[h % NICK_A.length]} ${NICK_B[Math.floor(h / 7) % NICK_B.length]}`;
};
const nowIso = () => new Date().toISOString().replace(/\.\d{3}Z$/, "+00:00");
const gh = (path, init = {}) =>
  fetch(`https://api.github.com/repos/${REPO}/${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${process.env.GITHUB_TOKEN}`,
      Accept: "application/vnd.github+json",
      "User-Agent": "geumja-care",
      ...(init.headers || {}),
    },
  });

function page(title, sub, gif) {
  return `<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="3;url=${PROFILE}">
<meta name="robots" content="noindex">
<title>정금자</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/galmuri@2.39.3/dist/galmuri.css">
<style>
  body{margin:0;min-height:100vh;display:grid;place-items:center;background:linear-gradient(160deg,#ecdeff,#ffd6ec);
       font-family:Galmuri11,system-ui,sans-serif;color:#3a2350;text-align:center}
  .card{background:#fffafd;border:3px solid #3a2350;border-radius:18px;box-shadow:0 6px 0 #3a2350;padding:28px 34px;max-width:320px;margin:16px}
  img{width:180px;image-rendering:pixelated}
  h1{font-size:20px;margin:12px 0 6px} p{font-size:13px;margin:0;opacity:.8}
  a{color:#d1458f}
</style></head><body><div class="card">
<img src="${RAW}/${gif}.gif" alt="">
<h1>${title}</h1><p>${sub}</p>
<p style="margin-top:14px"><a href="${PROFILE}">← 프로필로 돌아가기</a></p>
</div></body></html>`;
}

// 방명록에 기록. 반환: "ok" | "cooldown" | "error"
async function writeGuestbook(action, visitor) {
  for (let attempt = 0; attempt < 3; attempt++) {
    const r = await gh(`contents/${GB_PATH}`);
    if (!r.ok) { console.error("gb read", r.status); return "error"; }
    const file = await r.json();
    const g = JSON.parse(Buffer.from(file.content, "base64").toString("utf8"));
    const now = Date.now();
    g.recent = Object.fromEntries(
      Object.entries(g.recent || {}).filter(([, ts]) => now - Date.parse(ts) < COOLDOWN_MS));
    if (g.recent[visitor]) return "cooldown";
    const at = nowIso();
    g.recent[visitor] = at;
    g.entries = [{ action, who: nickname(visitor), at }, ...(g.entries || [])].slice(0, 5);
    g.count = (g.count || 0) + 1;
    const put = await gh(`contents/${GB_PATH}`, {
      method: "PUT",
      body: JSON.stringify({
        message: `💌 방명록: ${nickname(visitor)} ${action}`,
        content: Buffer.from(JSON.stringify(g, null, 2) + "\n", "utf8").toString("base64"),
        sha: file.sha,
      }),
    });
    if (put.ok) return "ok";
    if (put.status !== 409 && put.status !== 422) { console.error("gb write", put.status, (await put.text()).slice(0, 200)); return "error"; }
  }
  return "error";
}

module.exports = async (req, res) => {
  res.setHeader("Content-Type", "text/html; charset=utf-8");
  res.setHeader("Cache-Control", "no-store");
  const a = String((req.query && req.query.a) || "");
  const act = ACTIONS[a];
  if (!act) {
    res.statusCode = 400;
    return res.end(page("음… 뭘 하려던 거예요?", "프로필의 버튼으로 다시 와주세요", "bored"));
  }
  const ip = String(req.headers["x-forwarded-for"] || "").split(",")[0].trim() || "unknown";
  const visitor = crypto.createHmac("sha256", process.env.SALT || "geumja").update(ip).digest("hex").slice(0, 16);

  let result = "error";
  try {
    result = await writeGuestbook(a, visitor);
  } catch (e) {
    console.error("gb error", String(e));
  }
  if (result === "cooldown") {
    return res.end(page("금자가 아직 쉬는 중이에요", "10분에 한 번씩 돌봐줄 수 있어요 ♡", "idle"));
  }
  if (result === "ok") {
    try {
      const r = await gh("dispatches", {
        method: "POST",
        body: JSON.stringify({ event_type: "care", client_payload: { action: a, visitor } }),
      });
      if (r.status !== 204) console.error("dispatch failed", r.status, (await r.text()).slice(0, 200));
    } catch (e) {
      console.error("dispatch error", String(e));
    }
    return res.end(page(act.text, `방명록에 ${nickname(visitor)}(으)로 남았어요 · 프로필로 돌아가요`, act.gif));
  }
  res.statusCode = 502;
  res.end(page("앗, 금자가 잠깐 자리를 비웠어요", "조금 있다가 다시 눌러주세요", "bored"));
};
