"""정금자 키우기: 이슈 제목으로 들어온 행동을 반영하고 README 를 다시 그린다.

사용법:
  python pet/update.py action <feed|play|sleep> <github-login>
  python pet/update.py tick            # 시간이 지나면 수치가 조금씩 줄어든다
"""
import json, re, sys, datetime as dt
from urllib.parse import quote
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "pet" / "state.json"
README = ROOT / "README.md"
REPO = "saeodixx/saeodixx"
CARE_URL = "https://geumja-care.vercel.app/api/care"
GUESTBOOK_URL = "https://geumja-care.vercel.app/api/guestbook"
GUESTBOOK = ROOT / "pet" / "guestbook.json"

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
        return "sleepy", "으음… 5분만 더 잘게…"
    if s["hunger"] < 30:
        return "hungry", "배고파… 밥 줄 거지? 🥺"
    if s["fun"] < 30:
        return "bored", "심심해~ 나랑 놀아줘!"
    if min(s["hunger"], s["fun"], s["energy"]) >= 70:
        return "happy", "오늘 최고로 행복해! ✨"
    return "idle", "놀러 와줘서 고마워 ♡"


def bar(v):
    n = round(v / 10)
    return "▰" * n + "▱" * (10 - n)


def button(action, label):
    url = f"{CARE_URL}?a={action}"
    return f'<a href="{url}"><img src="./pet/btn_{action}.png" height="44" alt="{label}" /></a>'


def stat(key, v):
    return f'<img src="./pet/stats/{key}_{round(v / 10)}.png" height="36" alt="{key} {v}" />'


def history_block(s):
    # 방명록은 Vercel 이 열 때마다 최신 기록으로 그려준다 (pet/guestbook.json)
    return f'<img src="{GUESTBOOK_URL}" width="400" alt="금자 방명록" />'


def guestbook_msg(action):
    return {"feed": "밥을 줬어요", "play": "같이 놀았어요", "sleep": "재워줬어요"}[action]


def card_block(s, key, line):
    """배경 카드 하나로 감싼 금자. 세 조각이 붙어서 한 장처럼 보이고, 조각마다 버튼 하나."""
    try:
        import panel
        parts = panel.write(key, line, s["level"], {k: s[k] for k in ("hunger", "fun", "energy")})
    except ImportError:
        return None
    labels = {"feed": "밥 주기", "play": "놀아주기", "sleep": "재우기"}
    alts = [f"정금자 — {line} · 배부름 {s['hunger']} 재미 {s['fun']} 에너지 {s['energy']}", "", ""]
    return "".join(
        f'<a href="{CARE_URL}?a={a}"><img src="{p}" width="{w}" alt="{alt or labels[a]}" /></a>'
        for (p, w), a, alt in zip(parts, ("feed", "play", "sleep"), alts))


def render(s):
    key, line = mood(s)
    hist = history_block(s)
    card = card_block(s, key, line)
    if card is None:  # Pillow 가 없을 때의 예전 모양
        card = f"""<img src="./pet/{key}.gif" width="200" alt="정금자 ({key})" />

**정금자** · Lv.{s['level']} &nbsp; 💬 “{line}”

{stat('hunger', s['hunger'])}<br/>
{stat('fun', s['fun'])}<br/>
{stat('energy', s['energy'])}

{button('feed', '🍙 밥 주기')} &nbsp; {button('play', '🎀 놀아주기')} &nbsp; {button('sleep', '💤 재우기')}"""
    return f"""<!-- PET:START -->
<div align="center">

<p>{card}</p>

<br/>

<img src="./pet/divider.png" width="600" alt="" />

<br/>

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


def guestbook_add(action, who):
    """이슈로 들어온 돌봄을 방명록에 적는다. (원클릭은 Vercel 함수가 직접 적는다)"""
    g = json.loads(GUESTBOOK.read_text(encoding="utf-8"))
    g["entries"].insert(0, {"action": action, "who": who, "at": now()})
    g["entries"] = g["entries"][:5]
    g["count"] += 1
    GUESTBOOK.write_text(json.dumps(g, ensure_ascii=False, indent=2) + chr(10), encoding="utf-8")


def main(argv):
    s = load()
    if argv[:1] == ["action"]:
        action, login = action_from_title(argv[1]), argv[2]
        if action is None or not re.fullmatch(r"[A-Za-z0-9-]{1,39}", login):
            print("ignored"); return 1
        apply(s, action, f"@{login}")
        guestbook_add(action, f"@{login}")
    elif argv[:1] == ["care"]:
        action, visitor = argv[1], argv[2]
        if action not in ACTIONS or not re.fullmatch(r"[0-9a-f]{16}", visitor):
            print("ignored"); return 1
        # 도배 방지와 방명록 기록은 Vercel 함수가 이미 했다. 여기선 스탯만.
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
