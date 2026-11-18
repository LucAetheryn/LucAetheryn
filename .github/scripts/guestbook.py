import json, os, subprocess, re, html
issue = os.environ["ISSUE_NUMBER"]
repo = os.environ["REPO"]
token = os.environ["GH_TOKEN"]
raw = subprocess.check_output([
    "gh", "api", f"repos/{repo}/issues/{issue}"
], env={**os.environ, "GH_TOKEN": token}, text=True)
data = json.loads(raw)
title = data.get("title", "")
body = data.get("body") or ""
if not title.startswith("[Guestbook]"):
    raise SystemExit("Not a guestbook issue")
message = re.sub(r"\s+", " ", body).strip()
if not message or len(message) > 240:
    raise SystemExit("Message is empty or exceeds 240 characters")
# Markdown table-safe escaping; remove pipes and control characters.
message = message.replace("|", "¦").replace("<", "&lt;").replace(">", "&gt;")
message = message.replace("\n", " ")
user = data["user"]["login"]
date = data["created_at"][:10]
row = f"| [{user}](https://github.com/{user}) | {message} | {date} |"
path = "README.md"
text = open(path, encoding="utf-8").read()
start, end = "<!-- GUESTBOOK:START -->", "<!-- GUESTBOOK:END -->"
if start not in text or end not in text:
    raise SystemExit("Guestbook markers not found")
before, rest = text.split(start, 1)
_, after = rest.split(end, 1)
table = rest.split(end, 1)[0]
lines = [line for line in table.splitlines() if line.strip()]
if row not in lines:
    lines.append(row)
new_table = "\n" + "\n".join(lines) + "\n"
open(path, "w", encoding="utf-8").write(before + start + new_table + end + after)
