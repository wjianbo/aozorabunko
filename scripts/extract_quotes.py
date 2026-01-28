from pathlib import Path
import json
import re
from datetime import datetime

ROOT = Path("cards")
OUTPUT = Path("preview/quotes.json")
MAX_FILES = 20000000  # 开发时

MAIN_TEXT_START = '<div class="main_text">'
MAIN_TEXT_END = '</div>'

TITLE_RE = re.compile(r'<h1 class="title">(.+?)</h1>')
AUTHOR_RE = re.compile(r'<h2 class="author">(.+?)</h2>')

TAG_RE = re.compile(r"<[^>]+>")


def extract_first_sentence_fast(html: str):
    start = html.find(MAIN_TEXT_START)
    if start == -1:
        return None

    end = html.find(MAIN_TEXT_END, start)
    if end == -1:
        return None

    body = html[start + len(MAIN_TEXT_START): end]
    body = TAG_RE.sub("", body)
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


def main():
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

    OUTPUT.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
