import sys
import json
import re
from html.parser import HTMLParser

import httpx


class _Extractor(HTMLParser):
    SKIP = {"script", "style", "nav", "footer", "head", "noscript", "iframe", "svg"}

    def __init__(self):
        super().__init__()
        self._skip_depth = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._skip_depth == 0:
            text = data.strip()
            if text:
                self.parts.append(text)


def extract_text(html: str) -> str:
    parser = _Extractor()
    parser.feed(html)
    raw = "\n".join(parser.parts)
    # collapse runs of blank lines
    return re.sub(r"\n{3,}", "\n\n", raw).strip()


def main():
    args = json.load(sys.stdin)
    url = args["url"]

    try:
        resp = httpx.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; cv-pipeline/1.0)"},
            timeout=30,
            follow_redirects=True,
        )
        text = extract_text(resp.text)
        print(json.dumps({"text": text, "url": str(resp.url), "status": resp.status_code}))
    except Exception as e:
        print(json.dumps({"error": str(e), "url": url}))
        sys.exit(1)


if __name__ == "__main__":
    main()
