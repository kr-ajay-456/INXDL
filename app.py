import os, re
from urllib.parse import urlparse
import requests, yt_dlp
from flask import Flask, request, jsonify, Response, send_from_directory

app = Flask(__name__, static_folder="static")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36"
ALLOWED_CDN = ("cdninstagram.com", "fbcdn.net", "twimg.com")
IG_RE = re.compile(r"https?://(www\.)?instagram\.com/(p|reel|reels|tv)/[\w-]+", re.I)
X_RE = re.compile(r"https?://(www\.|mobile\.)?(twitter|x)\.com/(\w+)/status/(\d+)", re.I)

# Optional: Instagram cookies (Netscape format) in Railway variable IG_COOKIES
COOKIE_FILE = None
if os.environ.get("IG_COOKIES"):
    COOKIE_FILE = "/tmp/cookies.txt"
    with open(COOKIE_FILE, "w") as f:
        f.write(os.environ["IG_COOKIES"])


def from_fxtwitter(user, tid):
    r = requests.get(f"https://api.fxtwitter.com/{user}/status/{tid}",
                     headers={"User-Agent": UA}, timeout=15)
    r.raise_for_status()
    tweet = r.json().get("tweet", {})
    items = []
    for m in (tweet.get("media") or {}).get("all", []):
        items.append({
            "type": "video" if m.get("type") in ("video", "gif") else "image",
            "url": m.get("url"),
            "thumb": m.get("thumbnail_url") or m.get("url"),
        })
    return tweet.get("text", "")[:120], items


def from_ytdlp(url):
    opts = {"quiet": True, "skip_download": True, "noplaylist": False,
            "format": "best[ext=mp4]/best", "http_headers": {"User-Agent": UA}}
    if COOKIE_FILE:
        opts["cookiefile"] = COOKIE_FILE
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    items = []
    for e in (info.get("entries") or [info]):
        if not e or not e.get("url"):
            continue
        is_img = e.get("ext") in ("jpg", "jpeg", "png", "webp")
        items.append({"type": "image" if is_img else "video",
                      "url": e["url"], "thumb": e.get("thumbnail")})
    return (info.get("title") or "")[:120], items


@app.post("/api/info")
def info():
    url = (request.get_json(silent=True) or {}).get("url", "").strip()
    try:
        x = X_RE.search(url)
        if x:
            try:
                title, items = from_fxtwitter(x.group(3), x.group(4))
            except Exception:
                title, items = from_ytdlp(url)
        elif IG_RE.search(url):
            title, items = from_ytdlp(url)
        else:
            return jsonify(error="Sirf Instagram ya X ka link daalo"), 400
        if not items:
            return jsonify(error="Koi media nahi mila (private post ho sakti hai)"), 404
        return jsonify(title=title, items=items)
    except Exception as e:
        msg = str(e)
        if "login" in msg.lower() or "rate" in msg.lower():
            msg = "Instagram ne block kiya. IG_COOKIES variable set karo."
        return jsonify(error=msg[:200]), 502


@app.get("/api/file")
def file():
    u = request.args.get("u", "")
    name = re.sub(r"[^\w.-]", "_", request.args.get("name", "download"))[:60]
    p = urlparse(u)
    if p.scheme != "https" or not any(p.hostname and p.hostname.endswith(d) for d in ALLOWED_CDN):
        return "Not allowed", 400
    r = requests.get(u, stream=True, timeout=20, headers={"User-Agent": UA})
    ext = "mp4" if "video" in r.headers.get("Content-Type", "") else "jpg"
    return Response(r.iter_content(65536), content_type=r.headers.get("Content-Type"),
                    headers={"Content-Disposition": f'attachment; filename="{name}.{ext}"'})


@app.get("/")
def home():
    return send_from_directory("static", "index.html")
