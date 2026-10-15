#!/usr/bin/env python3
"""Adds a visitor to the README guestbook wall.

Called by .github/workflows/guestbook.yml when someone opens a "guestbook|hi" issue.
Only the issue author's GitHub login is used — never the issue title or body.

Usage:  python scripts/guestbook.py <github-login>
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "guestbook.json")
README = os.path.join(ROOT, "README.md")
START, END = "<!-- GUESTBOOK:START -->", "<!-- GUESTBOOK:END -->"
MAX_SHOWN = 24
LOGIN_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9]|-(?=[A-Za-z0-9])){0,38}$")  # GitHub's username rules


def render(book):
    shown = book["visitors"][:MAX_SHOWN]
    if not shown:
        return "<p align=\"center\"><sub>No signatures yet. Be the first!</sub></p>"
    avatars = "\n".join(f'  <a href="https://github.com/{u}"><img src="https://github.com/{u}.png?size=88" width="44" height="44" alt="{u}" title="{u}"/></a>'
                        for u in shown)
    total = book["total"]
    return (f'<p align="center">\n{avatars}\n</p>\n'
            f'<p align="center"><sub>{total} {"person has" if total == 1 else "people have"} signed · newest first</sub></p>')


def main():
    login = sys.argv[1] if len(sys.argv) > 1 else ""
    if not LOGIN_RE.match(login) or login.endswith("[bot]"):
        sys.exit(f"Refusing invalid login: {login!r}")
    book = json.load(open(DATA, encoding="utf-8")) if os.path.exists(DATA) else {"total": 0, "visitors": []}
    if login.lower() not in (v.lower() for v in book["visitors"]):
        book["total"] += 1
    book["visitors"] = [login] + [v for v in book["visitors"] if v.lower() != login.lower()]
    book["visitors"] = book["visitors"][:200]
    with open(DATA, "w", encoding="utf-8") as fh:
        json.dump(book, fh, indent=1)

    text = open(README, encoding="utf-8").read()
    pre, rest = text.split(START, 1)
    _, post = rest.split(END, 1)
    with open(README, "w", encoding="utf-8") as fh:
        fh.write(f"{pre}{START}\n{render(book)}\n{END}{post}")
    print(f"signed: {login} (total {book['total']})")


if __name__ == "__main__":
    main()
