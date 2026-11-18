"""금자 카드: 캐릭터·이름·대사·스탯·버튼을 배경 카드 하나로 그린 뒤,
버튼마다 따로 누를 수 있게 세로로 세 조각(움직이는 GIF)으로 잘라 저장한다."""
import glob, hashlib, re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
PARTS, FRAMES, OUT_DIR = HERE / "parts", HERE / "frames", HERE / "panel"
S = 2
INK = (58, 35, 80, 255)
WHITE = (255, 255, 255, 255)
KEY = (1, 2, 3)

W = 250
FEET = 100
BTN_Y, STAT_Y, TEXT_Y = 190, 124, 106
H = BTN_Y + 24 + 2 + 7
BTNS = ["feed", "play", "sleep"]
GAP = 6
SPARKS = [(18, 16), (226, 22), (30, 78), (214, 84), (74, 10), (180, 52)]

GLYPH = {
    "z": ["1111", "0010", "0100", "1111"],
    "Z": ["11111", "00010", "00100", "01000", "11111"],
    "heart": [".11.11.", "1111111", "1111111", ".11111.", "..111..", "...1..."],
    "spark": ["..1..", "..1..", "11111", "..1..", "..1.."],
    "dot": ["11", "11"],
}


def _mask(w, h, r):
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], r, fill=255)
    return m.point(lambda v: 255 if v > 127 else 0)


def _put(img, g, x, y, col, outline=None):
    rows = GLYPH[g]
    on = {(i, j) for j, r in enumerate(rows) for i, c in enumerate(r) if c == "1"}
    if outline:
        for (i, j) in on:
            for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                if (i + a, j + b) not in on:
                    img.putpixel((x + i + a, y + j + b), outline)
    for (i, j) in on:
        img.putpixel((x + i, y + j), col)


def _base(level, line):
    img = Image.new("RGBA", (W, H))
    body_h = H - 2
    m = _mask(W, body_h, 10)
    img.paste(Image.new("RGBA", (W, body_h), INK), (0, 2), m)
    img.paste(Image.new("RGBA", (W, body_h), INK), (0, 0), m)
    grad = Image.new("RGBA", (W - 2, body_h - 2))
    gd = ImageDraw.Draw(grad)
    top, bot = (241, 230, 255), (255, 224, 240)
    for y in range(body_h - 2):
        t = y / (body_h - 3)
        gd.line([(0, y), (W, y)], fill=tuple(round(top[k] + (bot[k] - top[k]) * t) for k in range(3)) + (255,))
    gd.line([(8, 1), (W - 12, 1)], fill=WHITE)                       # gloss
    img.paste(grad, (1, 1), _mask(W - 2, body_h - 2, 9))
    d = ImageDraw.Draw(img)
    # floor shadow
    sh = Image.new("RGBA", (W, H))
    ImageDraw.Draw(sh).ellipse([W // 2 - 22, FEET - 3, W // 2 + 22, FEET + 3], fill=(120, 80, 160, 60))
    img.alpha_composite(sh)
    # name + speech
    fb = ImageFont.truetype(str(HERE / "fonts" / "Galmuri11-Bold.ttf"), 12)
    fr = ImageFont.truetype(str(HERE / "fonts" / "Galmuri11.ttf"), 12)
    d.fontmode = "1"
    name, lv = "정금자", f" Lv.{level}"
    speech = "“" + re.sub(r"[\U00010000-\U0010ffff✨️]", "", line).strip() + "”"
    total = fb.getlength(name) + fr.getlength(lv) + 8 + fr.getlength(speech)
    x = (W - total) / 2
    d.text((x, TEXT_Y), name, font=fb, fill=INK); x += fb.getlength(name)
    d.text((x, TEXT_Y), lv, font=fr, fill=(150, 120, 180, 255)); x += fr.getlength(lv) + 8
    d.text((x, TEXT_Y), speech, font=fr, fill=(200, 70, 140, 255))
    return img


def _sprite_frames(name):
    fs = [Image.open(f).convert("RGBA") for f in sorted(glob.glob(str(FRAMES / name / "*.png")))]
    b = fs[0].getbbox()
    return fs, W // 2 - (b[0] + b[2]) // 2, FEET - b[3]


def _darken(im, a):
    ov = Image.new("RGBA", im.size, (40, 30, 90, 0))
    ov.putalpha(im.getchannel("A").point(lambda v: a if v else 0))
    return Image.alpha_composite(im, ov)


def _frames(mood, base):
    """(frames, duration_ms) — every frame is a full card."""
    def card(sprite, ox, oy, i, spark_col=WHITE):
        im = base.copy()
        for k, (sx, sy) in enumerate(SPARKS):
            if (i + k) % 3:
                _put(im, "spark", sx, sy, spark_col)
        im.alpha_composite(sprite, (ox, oy)) if ox >= 0 and oy >= 0 else im.paste(sprite, (ox, oy), sprite)
        return im

    cx = W // 2
    if mood == "happy":
        fs, ox, oy = _sprite_frames("happy")
        out = []
        for i, f in enumerate(fs + fs[:1]):
            im = card(f, ox, oy, i)
            for k, hx in enumerate((cx - 40, cx + 30, cx - 20)):
                _put(im, "heart", hx, 40 - ((i * 5 + k * 12) % 32), (255, 92, 160, 255), WHITE)
            out.append(im)
        return out, 110
    if mood == "hungry":
        fs, ox, oy = _sprite_frames("hungry")
        out = []
        for i, f in enumerate(fs + fs[-2:0:-1]):
            im = card(f, ox, oy, i)
            if i % 8 < 6:
                d = ImageDraw.Draw(im)
                bx, by = cx + 22, 10
                d.ellipse([bx, by, bx + 32, by + 26], fill=WHITE, outline=INK)
                d.ellipse([bx - 4, by + 29, bx + 1, by + 34], fill=WHITE, outline=INK)
                d.polygon([(bx + 16, by + 5), (bx + 8, by + 21), (bx + 24, by + 21)], fill=WHITE, outline=INK)
                d.rectangle([bx + 13, by + 16, bx + 19, by + 21], fill=(40, 52, 50))
            out.append(im)
        return out, 170
    fs, ox, oy = _sprite_frames("idle")
    seq = fs + fs[-2:0:-1]
    if mood == "sleepy":
        out = []
        for i in range(12):
            im = card(_darken(seq[i % len(seq)], 70), ox, oy, i, (255, 236, 170, 255))
            for k, (zx, g) in enumerate(((cx + 18, "z"), (cx + 26, "Z"), (cx + 36, "Z"))):
                _put(im, g, zx + (i + k) % 2, 34 - ((i * 2 + k * 8) % 24), WHITE, (90, 70, 150, 255))
            out.append(im)
        return out, 260
    if mood == "bored":
        out = []
        for i in range(12):
            im = card(fs[(i // 3) % len(fs)], ox, oy, i)
            for k in range(min(3, i % 6)):
                _put(im, "dot", cx + 16 + k * 6, 22, (110, 95, 130, 255))
            out.append(im)
        return out, 300
    return [card(f, ox, oy, i) for i, f in enumerate(seq)], 220


def _cuts():
    widths = [Image.open(PARTS / f"btn_{b}.png").width for b in BTNS]
    x0 = (W - (sum(widths) + GAP * 2)) // 2
    xs, x = [], x0
    for w in widths:
        xs.append(x); x += w + GAP
    c1 = xs[0] + widths[0] + GAP // 2
    c2 = xs[1] + widths[1] + GAP // 2
    return xs, [(0, c1), (c1, c2), (c2, W)]


def _to_gif_frame(im):
    big = im.resize((im.width * S, im.height * S), Image.NEAREST)
    alpha = big.getchannel("A")
    rgb = Image.new("RGB", big.size, KEY)
    rgb.paste(big, (0, 0), alpha)
    p = rgb.quantize(colors=255, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    pal = p.getpalette()[: 255 * 3] + list(KEY)
    p.putpalette(pal)
    p.paste(255, (0, 0), alpha.point(lambda v: 255 if v < 128 else 0))
    return p


def write(mood, line, level, stats):
    """카드를 그려 세 조각 GIF 로 저장하고 [(경로, 폭px), ...] 를 돌려준다."""
    base = _base(level, line)
    xs, cuts = _cuts()
    for k, key in enumerate(("hunger", "fun", "energy")):
        part = Image.open(PARTS / f"{key}_{round(stats[key] / 10)}.png").convert("RGBA")
        base.alpha_composite(part, ((W - part.width) // 2, STAT_Y + k * 21))
    for b, x in zip(BTNS, xs):
        base.alpha_composite(Image.open(PARTS / f"btn_{b}.png").convert("RGBA"), (x, BTN_Y))
    frames, dur = _frames(mood, base)

    OUT_DIR.mkdir(exist_ok=True)
    tag = hashlib.sha1(repr((mood, line, level, stats)).encode()).hexdigest()[:10]
    keep = set()
    result = []
    for n, (a, b) in enumerate(cuts):
        name = f"p_{tag}_{n}.gif"
        keep.add(name)
        gif = [_to_gif_frame(f.crop((a, 0, b, H))) for f in frames]
        gif[0].save(OUT_DIR / name, save_all=True, append_images=gif[1:], duration=dur, loop=0,
                    disposal=2, transparency=255, optimize=False)
        result.append((f"./pet/panel/{name}", (b - a) * S))
    for old in OUT_DIR.glob("p_*.gif"):
        if old.name not in keep:
            old.unlink()
    return result
