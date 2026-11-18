// 프로필 구분선 그림. 누가 프로필을 볼 때마다 불리니까, 이 김에
// "마지막으로 스탯을 줄인 지 1시간 넘었나?"를 보고 넘었으면 워크플로에 tick 을 요청한다.
// (GitHub 예약 실행은 자주 늦거나 건너뛰어서, 보는 사람이 있을 때 확실히 줄어들게)
const fs = require("fs");
const path = require("path");

const REPO = "saeodixx/saeodixx";
const PNG = fs.readFileSync(path.join(__dirname, "_assets", "divider.png"));
const HOUR = 60 * 60 * 1000;

const gh = (p, init = {}) =>
  fetch(`https://api.github.com/repos/${REPO}/${p}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${process.env.GITHUB_TOKEN}`,
      Accept: "application/vnd.github+json",
      "User-Agent": "geumja-tick",
      ...(init.headers || {}),
    },
  });

async function maybeTick() {
  const r = await gh("contents/pet/state.json", { headers: { Accept: "application/vnd.github.raw+json" } });
  if (!r.ok) return;
  const s = await r.json();
  const last = Date.parse(s.decayed_at || s.updated_at || 0);
  if (Date.now() - last < HOUR) return;
  const d = await gh("dispatches", { method: "POST", body: JSON.stringify({ event_type: "tick" }) });
  if (d.status !== 204) console.error("tick dispatch", d.status);
}

module.exports = async (req, res) => {
  try {
    await Promise.race([maybeTick(), new Promise((ok) => setTimeout(ok, 3000))]);
  } catch (e) {
    console.error("tick error", String(e));
  }
  res.setHeader("Content-Type", "image/png");
  res.setHeader("Cache-Control", "no-cache, no-store, must-revalidate, max-age=0");
  res.end(PNG);
};
