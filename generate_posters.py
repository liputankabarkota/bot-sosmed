#!/usr/bin/env python3
"""
Auto Poster Generator untuk Liputan KabarKota (Blogger -> GitHub Actions -> Telegram)
Otomatis mengambil artikel terbaru dari feed Blogger, membuat poster dari template.png,
menyimpan ke folder posters/, dan mengirim poster + judul + link Baca selengkapnya ke Telegram.
"""

import html
import json
import os
import re
import sys
from datetime import datetime
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps

# Konfigurasi default
BLOG_URL = os.environ.get("BLOG_URL", "https://www.liputankabarkota.com").rstrip("/")
ARTICLE_URL = os.environ.get("ARTICLE_URL", "").strip()
MAX_RESULTS = int(os.environ.get("MAX_RESULTS", "10"))
TEMPLATE_PATH = Path("template.png")
POSTERS_DIR = Path("posters")
PROCESSED_FILE = Path("processed.json")
GALLERY_FILE = POSTERS_DIR / "gallery.json"

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

# Koordinat presisi sesuai Liputan KabarKota News Template sosed.psd (941 x 1238)
CANVAS_W, CANVAS_H = 941, 1238
PHOTO_BOX = (0, 200, 941, 610)  # x, y, w, h
TITLE_CX, TITLE_CY = 466, 860
TITLE_MAX_W, TITLE_MAX_H = 740, 112

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

FONT_CANDIDATES = [
    "fonts/RobotoCondensed-Bold.ttf",
    "/usr/share/fonts/truetype/roboto/unhinted/RobotoCondensed-Bold.ttf",
    "/usr/share/fonts/truetype/roboto/RobotoCondensed-Bold.ttf",
    "/usr/share/fonts/truetype/roboto/unhinted/RobotoTTF/Roboto-Bold.ttf",
    "/usr/share/fonts/truetype/roboto/Roboto-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSansNarrow-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def find_font_path() -> str:
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            return path
    return ""


def load_font(font_path: str, size: int) -> ImageFont.FreeTypeFont:
    if font_path:
        return ImageFont.truetype(font_path, size=size)
    return ImageFont.load_default()


def slugify(text: str, max_len: int = 55) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (s or "berita")[:max_len].strip("-")


def extract_meta_tag(page: str, attr: str, val: str) -> str:
    m = re.search(rf'<meta[^>]+{attr}=["\']{val}["\'][^>]+content=["\']([^"\']+)["\']', page, re.I)
    if not m:
        m = re.search(rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+{attr}=["\']{val}["\']', page, re.I)
    return html.unescape(m.group(1)).strip() if m else ""


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_w: int) -> list[str]:
    words = text.strip().split()
    lines, current = [], ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if (bbox[2] - bbox[0]) <= max_w:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def render_poster(photo_img: Image.Image, title: str, output_path: Path, template_path: Path = TEMPLATE_PATH) -> Path:
    if not template_path.exists():
        raise FileNotFoundError(f"Template tidak ditemukan: {template_path}")

    canvas = Image.new("RGBA", (CANVAS_W, CANVAS_H), (20, 30, 48, 255))

    px, py, pw, ph = PHOTO_BOX
    photo_rgb = ImageOps.exif_transpose(photo_img).convert("RGBA")
    cropped = ImageOps.fit(photo_rgb, (pw, ph), method=Image.Resampling.LANCZOS, centering=(0.5, 0.30))
    canvas.paste(cropped, (px, py))

    template = Image.open(template_path).convert("RGBA")
    if template.size != (CANVAS_W, CANVAS_H):
        template = template.resize((CANVAS_W, CANVAS_H), Image.Resampling.LANCZOS)
    canvas.alpha_composite(template)

    draw = ImageDraw.Draw(canvas)
    font_path = find_font_path()
    clean_title = re.sub(r"\s+", " ", html.unescape(title)).strip()

    chosen_font = None
    chosen_lines = []
    line_height = 0

    for size in range(42, 18, -2):
        font = load_font(font_path, size)
        lines = wrap_text(draw, clean_title, font, TITLE_MAX_W)
        lh = int(size * 1.18)
        if len(lines) * lh <= TITLE_MAX_H:
            chosen_font = font
            chosen_lines = lines
            line_height = lh
            break

    if chosen_font is None:
        chosen_font = load_font(font_path, 20)
        chosen_lines = wrap_text(draw, clean_title, chosen_font, TITLE_MAX_W)[:4]
        line_height = 24

    total_h = len(chosen_lines) * line_height
    start_y = TITLE_CY - total_h / 2 + line_height / 2

    for idx, line in enumerate(chosen_lines):
        y = start_y + idx * line_height
        draw.text((TITLE_CX, y), line, font=chosen_font, fill=(15, 23, 42, 255), anchor="mm")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(output_path, "JPEG", quality=95, optimize=True)
    return output_path


def upgrade_blogger_image_url(url: str) -> str:
    if not url:
        return ""
    url = re.sub(r"/s\d+(-[a-z0-9-]+)?/", "/s1600/", url)
    url = re.sub(r"/w\d+-h\d+(-[a-z0-9-]+)?/", "/s1600/", url)
    return url


def fetch_article_from_url(article_url: str) -> dict | None:
    resp = requests.get(article_url, headers=HEADERS, timeout=25)
    resp.raise_for_status()
    page = resp.text

    title = extract_meta_tag(page, "property", "og:title")
    if not title:
        m = re.search(r"<title>(.*?)</title>", page, re.I | re.S)
        title = html.unescape(m.group(1)).strip() if m else ""
    title = re.sub(r"\s*[-|]\s*Liputan\s*KabarKota.*$", "", title, flags=re.I).strip()

    img_url = upgrade_blogger_image_url(extract_meta_tag(page, "property", "og:image"))
    if not title or not img_url:
        return None

    return {
        "id": article_url,
        "title": title,
        "link": article_url,
        "image": img_url,
        "published": datetime.now().strftime("%Y-%m-%d"),
    }


def fetch_blogger_posts(blog_url: str, max_results: int = 10) -> list[dict]:
    feed_url = f"{blog_url}/feeds/posts/default?alt=json&max-results={max_results}"
    resp = requests.get(feed_url, headers=HEADERS, timeout=25)
    resp.raise_for_status()
    data = resp.json()

    posts = []
    for entry in data.get("feed", {}).get("entry", []):
        post_id = entry.get("id", {}).get("$t", "")
        title = entry.get("title", {}).get("$t", "").strip()
        published = entry.get("published", {}).get("$t", "")[:10] or datetime.now().strftime("%Y-%m-%d")

        link = ""
        for l in entry.get("link", []):
            if l.get("rel") == "alternate":
                link = l.get("href", "")
                break

        raw_body = entry.get("content", {}).get("$t", "") or entry.get("summary", {}).get("$t", "")
        img_url = ""
        thumb = entry.get("media$thumbnail", {}).get("url", "")
        if thumb:
            img_url = upgrade_blogger_image_url(thumb)
        else:
            m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', raw_body, re.I)
            if m:
                img_url = upgrade_blogger_image_url(m.group(1))

        if post_id and title and img_url:
            posts.append({
                "id": post_id,
                "title": title,
                "link": link,
                "image": img_url,
                "published": published,
            })
    return posts


def download_image(url: str) -> Image.Image:
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return Image.open(BytesIO(resp.content))


def send_to_telegram(image_path: Path, title: str, link: str) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return

    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    clean_caption_title = re.sub(r"^Liputan\s+Kabar\s*Kota\s*[-–—:]\s*", "", title, flags=re.I).strip()
    caption = f"📰 Liputan Kabar Kota - {clean_caption_title}\n\n🔗 Baca selengkapnya:\n{link}"

    with open(image_path, "rb") as f:
        resp = requests.post(
            api_url,
            data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption[:1024]},
            files={"photo": f},
            timeout=30,
        )
    if resp.ok:
        print(f"  [Telegram] Terkirim: {image_path.name}")
    else:
        print(f"  [Telegram] Gagal ({resp.status_code}): {resp.text[:200]}")


def load_json_file(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default
    return default


def main() -> int:
    processed = set(load_json_file(PROCESSED_FILE, []))
    gallery = load_json_file(GALLERY_FILE, [])

    if ARTICLE_URL:
        print(f"Mode artikel tunggal: {ARTICLE_URL}")
        post = fetch_article_from_url(ARTICLE_URL)
        posts = [post] if post else []
        force_process = True
    else:
        print(f"Mengambil feed terbaru dari {BLOG_URL}...")
        posts = fetch_blogger_posts(BLOG_URL, MAX_RESULTS)
        force_process = False

    if not posts:
        print("Tidak ada artikel yang bisa diproses.")
        return 0

    created_count = 0
    for post in posts:
        if not force_process and post["id"] in processed:
            continue

        print(f"Memproses: {post['title']}")
        try:
            photo = download_image(post["image"])
            filename = f"{post['published']}-{slugify(post['title'])}.jpg"
            out_path = POSTERS_DIR / filename
            render_poster(photo, post["title"], out_path)
            print(f"  [OK] Tersimpan: {out_path}")

            processed.add(post["id"])
            gallery = [g for g in gallery if g.get("file") != f"posters/{filename}"]
            gallery.insert(0, {
                "title": post["title"],
                "link": post["link"],
                "published": post["published"],
                "file": f"posters/{filename}",
            })
            gallery = gallery[:50]

            send_to_telegram(out_path, post["title"], post["link"])
            created_count += 1
        except Exception as exc:
            print(f"  [ERROR] Gagal memproses '{post['title']}': {exc}")

    POSTERS_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_FILE.write_text(json.dumps(sorted(processed), indent=2), encoding="utf-8")
    GALLERY_FILE.write_text(json.dumps(gallery, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Selesai. Poster baru dibuat: {created_count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
