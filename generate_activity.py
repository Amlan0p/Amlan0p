import json
import os
import urllib.request
from datetime import date, timedelta

USERNAME = os.environ.get("GITHUB_USER", "Amlan0p")
TOKEN = os.environ["GITHUB_TOKEN"]
END = date.today()
START = END - timedelta(days=364)

query = """
query($login:String!, $from:DateTime!, $to:DateTime!) {
  user(login:$login) {
    contributionsCollection(from:$from, to:$to) {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""

data = json.dumps({"query": query, "variables": {
    "login": USERNAME,
    "from": START.isoformat() + "T00:00:00Z",
    "to": END.isoformat() + "T23:59:59Z",
}}).encode()
req = urllib.request.Request("https://api.github.com/graphql", data=data, method="POST")
req.add_header("Authorization", f"bearer {TOKEN}")
req.add_header("Content-Type", "application/json")
req.add_header("User-Agent", "Amlan0p-contribution-activity")

with urllib.request.urlopen(req, timeout=30) as r:
    payload = json.load(r)

if payload.get("errors"):
    raise RuntimeError(payload["errors"])

calendar = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]
days = [d for w in calendar["weeks"] for d in w["contributionDays"]]

# Aggregate into 53 weekly buckets for a compact activity chart.
weeks = [days[i:i+7] for i in range(0, len(days), 7)]
weekly = [sum(d["contributionCount"] for d in w) for w in weeks]
if len(weekly) > 53:
    weekly = weekly[-53:]

W, H = 1000, 300
left, right, top, bottom = 55, 25, 50, 55
chart_w = W - left - right
chart_h = H - top - bottom
maxv = max(weekly or [1])
step = chart_w / max(1, len(weekly)-1)
points = []
for i, v in enumerate(weekly):
    x = left + i * step
    y = top + chart_h - (v / maxv) * chart_h
    points.append((x, y))

line = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
area = f"{left},{top+chart_h} " + line + f" {points[-1][0]:.1f},{top+chart_h}"

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<rect width="100%" height="100%" rx="14" fill="#161b22"/>
<text x="55" y="30" fill="#c9d1d9" font-family="Arial,sans-serif" font-size="18" font-weight="600">Contribution Activity — {USERNAME}</text>
<text x="945" y="30" text-anchor="end" fill="#8b949e" font-family="Arial,sans-serif" font-size="13">{calendar['totalContributions']} contributions</text>
<line x1="55" y1="245" x2="975" y2="245" stroke="#30363d"/>
<line x1="55" y1="170" x2="975" y2="170" stroke="#21262d"/>
<line x1="55" y1="95" x2="975" y2="95" stroke="#21262d"/>
<polygon points="{area}" fill="#238636" opacity="0.18"/>
<polyline points="{line}" fill="none" stroke="#39d353" stroke-width="3" stroke-linejoin="round" stroke-linecap="round"/>
<text x="55" y="268" fill="#8b949e" font-family="Arial,sans-serif" font-size="12">{START.strftime('%b %d, %Y')}</text>
<text x="975" y="268" text-anchor="end" fill="#8b949e" font-family="Arial,sans-serif" font-size="12">{END.strftime('%b %d, %Y')}</text>
<text x="55" y="289" fill="#8b949e" font-family="Arial,sans-serif" font-size="11">Weekly contribution totals • generated automatically by GitHub Actions</text>
</svg>'''

os.makedirs("dist", exist_ok=True)
with open("dist/contribution-activity.svg", "w", encoding="utf-8") as f:
    f.write(svg)
