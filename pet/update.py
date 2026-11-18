"""정금자 키우기: 이슈 제목으로 들어온 행동을 반영하고 README 를 다시 그린다.

사용법:
  python pet/update.py action <feed|play|sleep> <github-login>
  python pet/update.py tick            # 시간이 지나면 수치가 조금씩 줄어든다
"""
import json, re, sys, datetime as dt
from urllib.parse import quote
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "pet" / "state.json"
README = ROOT / "README.md"
REPO = "saeodixx/saeodixx"
CARE_URL = "https://geumja-care.vercel.app/api/care"

ACTIONS = {
    #          배부름 재미  에너지
    "feed":  {"hunger": 25, "fun": 0,   "energy": 0,   "msg": "🍙 밥을 줬어요",   "title": "🍙 금자 밥 주기"},
    "play":  {"hunger": -5, "fun": 25,  "energy": -10, "msg": "🎀 같이 놀았어요", "title": "🎀 금자랑 놀아주기"},
    "sleep": {"hunger": -5, "fun": 0,   "energy": 35,  "msg": "💤 재워줬어요",   "title": "🌙 금자 재우기"},
}


def action_from_title(title):
    title = title.strip()
    for k, v in ACTIONS.items():
        if title == v["title"] or title == f"pet|{k}":
            return k
    return None
DECAY = {"hunger": -4, "fun": -3, "energy": -2}


def clamp(v):
    return max(0, min(100, v))


def now():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def load():
    return json.loads(STATE.read_text(encoding="utf-8"))


def save(s):
    STATE.write_text(json.dumps(s, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def mood(s):
    if s["energy"] < 25:
        return "sleepy", "꾸벅꾸벅 졸려요…"
    if s["hunger"] < 30:
        return "hungry", "배고파요… 밥 주세요 🥺"
    if s["fun"] < 30:
        return "bored", "심심해요… 놀아줘요"
    if min(s["hunger"], s["fun"], s["energy"]) >= 70:
        return "happy", "최고로 행복해요 ✨"
    return "idle", "기분 좋아요 ♡"


def bar(v):
    n = round(v / 10)
    return "▰" * n + "▱" * (10 - n)


def button(action, label):
    url = f"{CARE_URL}?a={action}"
    return f'<a href="{url}"><img src="./pet/btn_{action}.png" height="44" alt="{label}" /></a>'


def stat(key, v):
    return f'<img src="./pet/stats/{key}_{round(v / 10)}.png" height="36" alt="{key} {v}" />'


def render(s):
    key, line = mood(s)
    hist = "".join(f"<sub>{h}</sub><br/>\n" for h in s["history"][:5]) or "<sub>아직 아무도 안 왔어요</sub>\n"
    return f"""<!-- PET:START -->
<div align="center">

<img src="./pet/{key}.gif" width="200" alt="정금자 ({key})" />

**정금자** · Lv.{s['level']} &nbsp;—&nbsp; {line}

{stat('hunger', s['hunger'])}<br/>
{stat('fun', s['fun'])}<br/>
{stat('energy', s['energy'])}

{button('feed', '🍙 밥 주기')} &nbsp; {button('play', '🎀 놀아주기')} &nbsp; {button('sleep', '💤 재우기')}

<sub>버튼 한 번이면 끝! 1분 뒤 금자가 반응해요 · 지금까지 {s['care_count']}번 돌봐줬어요</sub>

{hist}
</div>
<!-- PET:END -->"""


def write_readme(s):
    text = README.read_text(encoding="utf-8")
    new = re.sub(r"<!-- PET:START -->.*?<!-- PET:END -->", lambda _: render(s), text, flags=re.S)
    README.write_text(new, encoding="utf-8")


NICK_A = ["딸기", "별사탕", "말랑", "반짝", "솜사탕", "젤리", "복숭아", "구름", "버블", "체리"]
NICK_B = ["토끼", "고양이", "곰돌이", "병아리", "햄스터", "강아지", "펭귄", "다람쥐"]
COOLDOWN_MIN = 10


def nickname(visitor):
    h = int(visitor[:8], 16)
    return f"{NICK_A[h % len(NICK_A)]} {NICK_B[(h // 7) % len(NICK_B)]}"


def apply(s, action, who):
    eff = ACTIONS[action]
    for k in ("hunger", "fun", "energy"):
        s[k] = clamp(s[k] + eff[k])
    s["care_count"] += 1
    s["level"] = 1 + s["care_count"] // 10
    s["history"].insert(0, f"{eff['msg']} — {who}")
    s["history"] = s["history"][:5]


def main(argv):
    s = load()
    if argv[:1] == ["action"]:
        action, login = action_from_title(argv[1]), argv[2]
        if action is None or not re.fullmatch(r"[A-Za-z0-9-]{1,39}", login):
            print("ignored"); return 1
        apply(s, action, f"@{login}")
    elif argv[:1] == ["care"]:
        action, visitor = argv[1], argv[2]
        if action not in ACTIONS or not re.fullmatch(r"[0-9a-f]{16}", visitor):
            print("ignored"); return 1
        t = dt.datetime.now(dt.timezone.utc)
        recent = {v: ts for v, ts in s.get("recent", {}).items()
                  if t - dt.datetime.fromisoformat(ts) < dt.timedelta(minutes=COOLDOWN_MIN)}
        if visitor in recent:
            print("ignored"); return 1
        recent[visitor] = now()
        s["recent"] = recent
        apply(s, action, nickname(visitor))
    elif argv[:1] == ["tick"]:
        for k, d in DECAY.items():
            s[k] = clamp(s[k] + d)
    elif argv[:1] != ["render"]:
        print(__doc__); return 2
    s["updated_at"] = now()
    save(s)
    write_readme(s)
    print(mood(s)[0])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
