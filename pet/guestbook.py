"""금자 방명록 이미지: 공책 종이 위에 최근 돌봐준 사람들을 적는다."""
import datetime as dt
import hashlib
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
FONTS = HERE / "fonts"
OUT_DIR = HERE / "guestbook"
S = 2
INK = (58, 35, 80, 255)
WHITE = (255, 255, 255, 255)
MUTED = (150, 125, 175, 255)
PAPER = (255, 251, 242, 255)
RULE = (214, 228, 248, 255)
MARGIN = (255, 170, 200, 255)
KST = dt.timezone(dt.timedelta(hours=9))

ICONS = {
    "feed": (["...###...", "..#WWW#..", ".#WWWWW#.", "#WWWWWWW#", "#W#####W#", "#W#NNN#W#", ".#######."],
             {"W": WHITE, "N": (40, 70, 60, 255)}),
    "play": (["##.....##", "#P#...#P#", "#PP###PP#", "#PP#R#PP#", "#PP###PP#", "#P#...#P#", "##.....##"],
             {"P": (255, 150, 200, 255), "R": (230, 70, 140, 255)}),
    "sleep": (["..####...", ".#YYY#...", "#YYY#....", "#YYY#....", "#YYYY####", ".#YYYYYY#", "..######."],
              {"Y": (255, 220, 110, 255)}),
}
MSG = {"feed": "밥을 줬어요", "play": "같이 놀았어요", "sleep": "재워줬어요"}
NAME_COL = {"feed": (214, 70, 140, 255), "play": (130, 90, 220, 255), "sleep": (60, 120, 210, 255)}

W, PAD, ROW, ROWS = 300, 10, 20, 5
TOP = 30
H = TOP + ROW * ROWS + 22


def _mask(w, h, r):
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], r, fill=255)
    return m.point(lambda v: 255 if v > 127 else 0)


def _icon(img, key, x, y):
    rows, pal = ICONS[key]
    for j, r in enumerate(rows):
        for i, c in enumerate(r):
            if c == "#":
                img.putpixel((x + i, y + j), INK)
            elif c in pal:
                img.putpixel((x + i, y + j), pal[c])


def _when(iso):
    try:
        return dt.datetime.fromisoformat(iso).astimezone(KST).strftime("%m.%d %H:%M")
    except Exception:
        return ""


def draw(entries, care_count):
    fb = ImageFont.truetype(str(FONTS / "Galmuri11-Bold.ttf"), 12)
    fr = ImageFont.truetype(str(FONTS / "Galmuri11.ttf"), 12)
    img = Image.new("RGBA", (W, H + 2))
    m = _mask(W, H, 8)
    img.paste(Image.new("RGBA", (W, H), INK), (0, 2), m)
    img.paste(Image.new("RGBA", (W, H), INK), (0, 0), m)
    img.paste(Image.new("RGBA", (W - 2, H - 2), PAPER), (1, 1), _mask(W - 2, H - 2, 7))
    d = ImageDraw.Draw(img)
    d.fontmode = "1"

    # ruled lines + pink margin, like a notebook page
    for i in range(ROWS + 1):
        y = TOP + i * ROW - 1
        d.line([(2, y), (W - 3, y)], fill=RULE)
    d.line([(28, TOP - 6), (28, H - 3)], fill=MARGIN)

    # washi tape on the corners
    for (x, col) in ((14, (255, 200, 225, 255)), (W - 46, (205, 225, 255, 255))):
        d.rectangle([x, -1, x + 32, 7], fill=col)
        for k in range(x + 2, x + 32, 4):
            d.point((k, 3), fill=WHITE)

    d.text((PAD + 24, 10), "♡ 금자 방명록", font=fb, fill=INK)
    tw = int(fr.getlength(f"총 {care_count}번 돌봐줬어요"))
    d.text((W - PAD - tw, 10), f"총 {care_count}번 돌봐줬어요", font=fr, fill=MUTED)

    if not entries:
        msg = "아직 아무도 안 왔어요… 첫 손님이 되어줘!"
        d.text(((W - fr.getlength(msg)) // 2, TOP + ROW * 2 + 3), msg, font=fr, fill=MUTED)
    for i, e in enumerate(entries[:ROWS]):
        y = TOP + i * ROW
        _icon(img, e["action"], 12, y + 6)
        x = 36
        d.text((x, y + 3), e["who"], font=fb, fill=NAME_COL[e["action"]])
        x += int(fb.getlength(e["who"])) + 6
        d.text((x, y + 3), MSG[e["action"]], font=fr, fill=INK)
        t = _when(e.get("at", ""))
        d.text((W - PAD - fr.getlength(t), y + 3), t, font=fr, fill=MUTED)

    d.text((PAD + 24, H - 18), "버튼으로 금자를 돌봐주면 이름이 남아요", font=fr, fill=MUTED)
    return img.resize((W * S, (H + 2) * S), Image.NEAREST)


def write(entries, care_count):
    """방명록을 새 파일 이름으로 저장하고(이미지 캐시 회피) 예전 파일은 지운다. README 용 경로를 돌려준다."""
    img = draw(entries, care_count)
    OUT_DIR.mkdir(exist_ok=True)
    key = hashlib.sha1(repr((entries, care_count)).encode()).hexdigest()[:10]
    name = f"gb_{key}.png"
    for old in OUT_DIR.glob("gb_*.png"):
        if old.name != name:
            old.unlink()
    img.save(OUT_DIR / name, optimize=True)
    return f"./pet/guestbook/{name}"
