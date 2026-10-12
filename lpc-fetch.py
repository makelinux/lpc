#!/usr/bin/env python3
"""Fetch an LPC schedule and generate an HTML file named after the event."""

import html as H
import json
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import urlopen


class PlainText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


code = sys.argv[1] if len(sys.argv) == 2 else ""
if not (code.isascii() and code.isdigit()):
    print(f"Usage: {sys.argv[0]} EVENT_CODE", file=sys.stderr)
    sys.exit(2)
url = f"https://lpc.events/event/{code}"

with urlopen(f"https://lpc.events/export/event/{code}.json?detail=contributions", timeout=30) as response:
    event = json.load(response)["results"][0]
contribs = event["contributions"]

# build session -> [(title, contrib_url, description, authors, pdf_url|None)]
sessions = {}
for c in sorted(contribs, key=lambda x: (x.get("startDate") or {}).get("date", "")):
    s = c.get("session")
    if not s:
        continue
    sname = s.get("title", "Other") if isinstance(s, dict) else s
    title = c.get("title", "").strip()
    if not title or title.lower() in ("introduction", "wrap up",
        "wrap up and next steps", "discussion", "introduction and kickoff"):
        continue
    cid = c["db_id"]
    curl = f"{url}/contributions/{cid}/"
    text = PlainText()
    text.feed(c.get("description", ""))
    text.close()
    desc = " ".join(" ".join(text.parts).split())
    people = c.get("primaryauthors", []) + c.get("coauthors", []) or c.get("speakers", [])
    authors = ", ".join(
        " ".join((p["first_name"], p["last_name"]))
        + " " + p["affiliation"]
        for p in people
    )
    pdf = None
    for f in c.get("folders", []):
        for att in f.get("attachments", []):
            dl = att.get("download_url", "")
            if dl.lower().endswith(".pdf"):
                pdf = dl
                break
        if pdf:
            break
    sessions.setdefault(sname, []).append((title, curl, desc, authors, pdf))

if not sessions:
    print(f'No presentations for {event["title"]}')
    sys.exit(0)

lines = [f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{H.escape(event["title"])} - presentations</title>
<style>
body {{ font-family: sans-serif; max-width: 900px; margin: 2em auto; line-height: 1.5; }}
h1 {{ font-size: 1.4em; }}
h2 {{ font-size: 1.1em; margin-top: 1.5em; border-bottom: 1px solid #ccc; padding-bottom: 0.2em; }}
ul {{ padding-left: 1.2em; }}
li {{ margin: 0.2em 0; }}
a {{ color: #1a0dab; text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
</style>
</head>
<body>
<h1>{H.escape(event["title"])}</h1>"""]

pdfs = 0
for sname in sessions:
    items = sessions[sname]
    lines.extend((f"\n<h2>{H.escape(sname)}</h2>", "<ul>"))
    for title, curl, desc, authors, pdf in items:
        t = H.escape(title)
        tip = f" title=\"{H.escape(desc)}\"" if desc else ""
        line = f"<li><a href=\"{H.escape(curl)}\"{tip}>{t}</a>"
        if authors:
            line += f" - {H.escape(authors)}"
        if pdf:
            line += f" <a href=\"{H.escape(pdf)}\">pdf</a>"
            pdfs += 1
        line += "</li>"
        lines.append(line)
    lines.append("</ul>")

lines.append("\n</body>\n</html>")
output = Path(__file__).resolve().parent / f'{event["title"].replace("/", "-")}.html'
output.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"Generated {output.name} ({pdfs} PDFs)")
