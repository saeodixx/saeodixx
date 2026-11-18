// 금자 원클릭 돌보기: 버튼 링크 → GitHub repository_dispatch → 워크플로가 README 갱신
const crypto = require("crypto");

const REPO = "saeodixx/saeodixx";
const PROFILE = "https://github.com/saeodixx";
const RAW = `https://raw.githubusercontent.com/${REPO}/main/pet`;
const ACTIONS = {
  feed: { text: "금자에게 밥을 줬어요!", gif: "happy" },
  play: { text: "금자랑 신나게 놀았어요!", gif: "happy" },
  sleep: { text: "금자를 재워줬어요… 쉿", gif: "sleepy" },
};

function page(title, sub, gif) {
  return `<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="4;url=${PROFILE}">
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

  let ok = false;
  try {
    const r = await fetch(`https://api.github.com/repos/${REPO}/dispatches`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${process.env.GITHUB_TOKEN}`,
        Accept: "application/vnd.github+json",
        "User-Agent": "geumja-care",
      },
      body: JSON.stringify({ event_type: "care", client_payload: { action: a, visitor } }),
    });
    ok = r.status === 204;
  } catch (e) {}

  if (!ok) {
    res.statusCode = 502;
    return res.end(page("앗, 금자가 잠깐 자리를 비웠어요", "조금 있다가 다시 눌러주세요", "bored"));
  }
  res.end(page(act.text, "1분쯤 뒤 프로필에 반영돼요 · 4초 뒤 돌아가요", act.gif));
};
