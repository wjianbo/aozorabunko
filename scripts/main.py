from pathlib import Path
import json
import re
from datetime import datetime, date
import argparse
import hashlib

ROOT = Path("cards")
QUOTES_OUTPUT = Path("preview/quotes.json")
DAILY_OUTPUT = Path("preview/daily.json")

MAX_FILES = 20000000  # 开发时

MAIN_TEXT_START = '<div class="main_text">'
MAIN_TEXT_END = '</div>'

TITLE_RE = re.compile(r'<h1 class="title">(.+?)</h1>')
AUTHOR_RE = re.compile(r'<h2 class="author">(.+?)</h2>')

TAG_RE = re.compile(r"<[^>]+>")
# 允许保留的标签
ALLOWED_TAGS = ("ruby", "rb", "rt", "rp")

TAG_STRIP_RE = re.compile(
    r"</?(?!(" + "|".join(ALLOWED_TAGS) + r")\b)[^>]+>",
    re.IGNORECASE,
)

def extract_first_sentence_fast(html: str):
    start = html.find(MAIN_TEXT_START)
    if start == -1:
        return None

    end = html.find(MAIN_TEXT_END, start)
    if end == -1:
        return None

    body = html[start + len(MAIN_TEXT_START): end]
    body = TAG_STRIP_RE.sub("", body)
    body = body.replace("&nbsp;", "").strip()
    body = body.lstrip("　")

    idx = body.find("。")
    if idx == -1:
        return None

    return body[: idx + 1]


def extract_title_and_author(html: str):
    title = None
    author = None

    m = TITLE_RE.search(html)
    if m:
        title = m.group(1).strip()

    m = AUTHOR_RE.search(html)
    if m:
        author = m.group(1).strip()

    return title, author


def build_quote_item(sentence: str, path: Path, title: str, author_name: str):
    card_id = path.parts[1]
    file_id = path.stem.split("_")[0]
    quote_id = f"aob-{card_id}-{file_id}"

    return {
        "id": quote_id,
        "text": sentence,
        "author": {
            "name": author_name,
            "id": None
        },
        "work": {
            "title": title,
            "id": None,
            "year": None
        },
        "source": {
            "path": str(path),
            "aozora_url": f"https://www.aozora.gr.jp/cards/{card_id}/files/{path.name}"
        },
        "metrics": {
            "length": len(sentence)
        }
    }


# -------------------------
# 1️⃣ 低频：构建 quotes.json
# -------------------------
def build_quotes():
    quotes = []
    scanned = 0

    for path in ROOT.rglob("files/*.html"):
        if scanned >= MAX_FILES:
            break

        scanned += 1
        html = path.read_text(encoding="shift_jis", errors="ignore")
        sentence = extract_first_sentence_fast(html)
        if not sentence:
            continue

        title, author_name = extract_title_and_author(html)

        quotes.append(
            build_quote_item(
                sentence=sentence,
                path=path,
                title=title,
                author_name=author_name
            )
        )

    output = {
        "meta": {
            "schema_version": 1,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "source": "aozorabunko",
            "count": len(quotes)
        },
        "quotes": quotes
    }

    print(f"Scanned html files: {scanned}")
    print(f"Collected candidates: {len(quotes)}")

    QUOTES_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    QUOTES_OUTPUT.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# -------------------------
# 2️⃣ 高频：每日生成 daily.json
# -------------------------
def generate_daily():
    data = json.loads(QUOTES_OUTPUT.read_text(encoding="utf-8"))
    quotes = data["quotes"]

    if not quotes:
        raise RuntimeError("quotes.json is empty")

    today = date.today().isoformat()
    h = hashlib.sha256(today.encode()).hexdigest()
    index = int(h, 16) % len(quotes)

    q = quotes[index]

    daily = {
        "date": today,
        "quote": {
            "id": q["id"],
            "text": q["text"],
            "author": q["author"]["name"],
            "title": q["work"]["title"],
        }
    }

    DAILY_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    DAILY_OUTPUT.write_text(
        json.dumps(daily, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# -------------------------
# 3️⃣ 入口：用参数控制
# -------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--build",
        action="store_true",
        help="Rebuild quotes.json from HTML files"
    )
    args = parser.parse_args()

    if args.build or not QUOTES_OUTPUT.exists():
        build_quotes()

    generate_daily()


if __name__ == "__main__":
    main()
