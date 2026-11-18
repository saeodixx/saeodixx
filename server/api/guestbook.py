"""실시간 방명록 그림: 열 때마다 pet/guestbook.json 을 읽어 PNG 로 그린다."""
import io, json, os, sys, urllib.request
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "_gb"))
import guestbook  # noqa: E402  (pet/guestbook.py 와 같은 그림 코드)

REPO = "saeodixx/saeodixx"


def load():
    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/contents/pet/guestbook.json",
        headers={
            "Authorization": f"Bearer {os.environ.get('GITHUB_TOKEN', '')}",
            "Accept": "application/vnd.github.raw+json",
            "User-Agent": "geumja-guestbook",
        },
    )
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.loads(r.read().decode("utf-8"))


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            g = load()
            img = guestbook.draw(g.get("entries", []), g.get("count", 0))
        except Exception as e:  # 읽기 실패해도 빈 방명록은 보여준다
            print("guestbook error:", repr(e))
            img = guestbook.draw([], 0)
        buf = io.BytesIO()
        img.save(buf, "PNG", optimize=True)
        body = buf.getvalue()
        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate, max-age=0")
        self.send_header("Expires", "0")
        self.end_headers()
        self.wfile.write(body)
