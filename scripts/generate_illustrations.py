#!/usr/bin/env python3
"""依 scenes.json 產生插畫。

後端以環境變數 ILLUST_BACKEND 選擇：
  mock   （預設）離線產生水墨風佔位 SVG，用來打通整條 pipeline
  openai  需 OPENAI_API_KEY（可選 OPENAI_BASE_URL、ILLUST_MODEL，預設 gpt-image-1）
  gemini  需 GEMINI_API_KEY（可選 ILLUST_MODEL，預設 gemini-2.0-flash-preview-image-generation）

用法: python3 scripts/generate_illustrations.py [--only slug1,slug2] [--force]
"""
import base64
import hashlib
import json
import os
import random
import sys
import time
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
NOVELS_DIR = ROOT / "public" / "novels"
W, H = 1200, 675


# ---------------------------------------------------------------- mock 後端
def mock_svg(title: str, chapter: str, excerpt: str, seed: str) -> str:
    rnd = random.Random(int(hashlib.sha256(seed.encode()).hexdigest(), 16))
    # 山巒剪影
    layers = []
    for depth, (base, amp, opacity) in enumerate([(430, 130, 0.18), (500, 170, 0.30), (580, 200, 0.45)]):
        pts = [(0, base + rnd.randint(-30, 30))]
        x = 0
        while x < W:
            x += rnd.randint(140, 260)
            pts.append((min(x, W), base - rnd.randint(20, amp)))
        path = f"M0,{H} L0,{pts[0][1]} " + " ".join(f"L{x},{y}" for x, y in pts) + f" L{W},{H} Z"
        layers.append(f'<path d="{path}" fill="#2b3440" opacity="{opacity}"/>')
    sun_x, sun_y, sun_r = rnd.randint(700, 1050), rnd.randint(120, 240), rnd.randint(46, 70)
    mist_y = rnd.randint(380, 470)
    excerpt_lines = [excerpt[i:i + 22] for i in range(0, min(len(excerpt), 44), 22)]
    excerpt_tspans = "".join(
        f'<tspan x="90" dy="{0 if i == 0 else 34}">{escape(line)}</tspan>'
        for i, line in enumerate(excerpt_lines)
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" aria-label="{escape(title)}">
<defs>
  <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#f7f2e7"/><stop offset="1" stop-color="#e6dcc6"/>
  </linearGradient>
</defs>
<rect width="{W}" height="{H}" fill="url(#sky)"/>
<circle cx="{sun_x}" cy="{sun_y}" r="{sun_r}" fill="#b3402a" opacity="0.75"/>
{''.join(layers)}
<ellipse cx="{W / 2:.0f}" cy="{mist_y}" rx="{W * 0.55:.0f}" ry="60" fill="#f7f2e7" opacity="0.55"/>
<text x="90" y="120" font-family="serif" font-size="54" fill="#222">{escape(title)}</text>
<text x="90" y="180" font-family="serif" font-size="30" fill="#555">{escape(chapter)}</text>
<text x="90" y="{mist_y + 130}" font-family="serif" font-size="24" fill="#444">{excerpt_tspans}</text>
<g transform="translate({W - 130},{H - 130})">
  <rect width="86" height="86" fill="#b3402a" rx="6"/>
  <text x="43" y="40" text-anchor="middle" font-family="serif" font-size="30" fill="#f7f2e7">插畫</text>
  <text x="43" y="72" text-anchor="middle" font-family="serif" font-size="22" fill="#f7f2e7">占位</text>
</g>
</svg>"""


# ------------------------------------------------------------ openai 後端
def openai_image(prompt: str, dest: Path) -> None:
    key = os.environ["OPENAI_API_KEY"]
    base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model = os.environ.get("ILLUST_MODEL", "gpt-image-1")
    body = json.dumps({"model": model, "prompt": prompt, "size": "1536x1024", "n": 1}).encode()
    req = urllib.request.Request(
        f"{base}/images/generations", data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        payload = json.loads(resp.read())
    item = payload["data"][0]
    if item.get("b64_json"):
        dest.write_bytes(base64.b64decode(item["b64_json"]))
    else:
        with urllib.request.urlopen(item["url"], timeout=120) as resp:
            dest.write_bytes(resp.read())


# ------------------------------------------------------------ gemini 後端
def gemini_image(prompt: str, dest: Path) -> None:
    key = os.environ["GEMINI_API_KEY"]
    model = os.environ.get("ILLUST_MODEL", "gemini-2.0-flash-preview-image-generation")
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/{model}"
           f":generateContent?key={key}")
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
    }).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        payload = json.loads(resp.read())
    for part in payload["candidates"][0]["content"]["parts"]:
        if "inlineData" in part:
            dest.write_bytes(base64.b64decode(part["inlineData"]["data"]))
            return
    raise RuntimeError("Gemini 回應中沒有圖片")


def main() -> None:
    backend = os.environ.get("ILLUST_BACKEND", "mock")
    force = "--force" in sys.argv
    only = None
    if "--only" in sys.argv:
        only = set(sys.argv[sys.argv.index("--only") + 1].split(","))
    made = skipped = failed = 0
    for scenes_path in sorted(NOVELS_DIR.glob("*/scenes.json")):
        slug = scenes_path.parent.name
        if only and slug not in only:
            continue
        meta = json.loads((scenes_path.parent / "meta.json").read_text(encoding="utf-8"))
        scenes = json.loads(scenes_path.read_text(encoding="utf-8"))
        illust_dir = scenes_path.parent / "illust"
        illust_dir.mkdir(exist_ok=True)
        for ch_n, items in scenes["chapters"].items():
            ch_title = meta["chapters"][int(ch_n) - 1]["title"]
            for item in items:
                rel = item["image"]
                dest = scenes_path.parent / rel
                if dest.exists() and not force:
                    skipped += 1
                    continue
                try:
                    if backend == "mock":
                        dest.write_text(
                            mock_svg(meta["title"], ch_title, item["excerpt"],
                                     seed=f"{slug}-{rel}"),
                            encoding="utf-8",
                        )
                    elif backend == "openai":
                        dest = dest.with_suffix(".png")
                        item["image"] = rel.replace(".svg", ".png")
                        openai_image(item["prompt"], dest)
                        time.sleep(1)
                    elif backend == "gemini":
                        dest = dest.with_suffix(".png")
                        item["image"] = rel.replace(".svg", ".png")
                        gemini_image(item["prompt"], dest)
                        time.sleep(1)
                    else:
                        raise RuntimeError(f"未知後端: {backend}")
                    made += 1
                except Exception as exc:  # noqa: BLE001
                    failed += 1
                    print(f"[fail] {slug}/{rel}: {exc}")
        scenes_path.write_text(
            json.dumps(scenes, ensure_ascii=False, indent=1), encoding="utf-8"
        )
    print(f"後端={backend} 產生={made} 略過={skipped} 失敗={failed}")


if __name__ == "__main__":
    main()
