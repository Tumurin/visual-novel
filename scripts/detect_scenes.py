#!/usr/bin/env python3
"""掃描章回文本，找出關鍵場面（戰鬥、名場面），產生插畫清單 scenes.json。

輸出: public/novels/<slug>/scenes.json
格式: {"chapters": {"1": [{"para": 12, "excerpt": "...", "image": "illust/c0001-s1.svg", "prompt": "..."}]}}
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOVELS_DIR = ROOT / "public" / "novels"

# 名場面關鍵詞與權重
KEYWORDS = {
    "大戰": 5, "交鋒": 4, "決鬥": 4, "舌戰": 5, "比武": 4, "大鬧": 5,
    "火燒": 4, "水淹": 4, "打虎": 5, "借東風": 6, "空城": 5, "三打": 4,
    "埋伏": 3, "劫": 2, "斬": 3, "廝殺": 4, "衝殺": 4, "殺入": 4,
    "戰不": 3, "鬥": 1, "陣": 1, "大敗": 3, "大勝": 3, "單刀": 4,
    "拔劍": 3, "揮刀": 3, "大怒": 2, "喝道": 2, "罵": 1, "哭了": 2,
    "結義": 5, "借箭": 5, "過關": 3, "會": 1,
}
TOP_K = 2          # 每回最多插畫數
MIN_GAP = 6        # 場景段落最小間距
MIN_SCORE = 4      # 入選門檻


def score_paragraph(text: str) -> int:
    score = 0
    for kw, w in KEYWORDS.items():
        if kw in text:
            score += w
    return score


def detect(slug: str) -> dict:
    meta = json.loads((NOVELS_DIR / slug / "meta.json").read_text(encoding="utf-8"))
    result: dict[str, list] = {}
    for ch in meta["chapters"]:
        n = ch["n"]
        data = json.loads(
            (NOVELS_DIR / slug / "chapters" / f"{n:04d}.json").read_text(encoding="utf-8")
        )
        candidates = []
        for i, para in enumerate(data["paragraphs"]):
            s = score_paragraph(para)
            if s >= MIN_SCORE:
                candidates.append((s, i, para))
        candidates.sort(key=lambda c: -c[0])
        picked = []
        for s, i, para in candidates:
            if all(abs(i - p["para"]) >= MIN_GAP for p in picked):
                excerpt = para[:60] + ("…" if len(para) > 60 else "")
                picked.append({
                    "para": i,
                    "score": s,
                    "excerpt": excerpt,
                    "image": f"illust/c{n:04d}-s{len(picked) + 1}.svg",
                    "prompt": (
                        f"《{meta['title']}》{data['title']} 場景插畫：{excerpt}"
                        "中國水墨畫風，寫意與工筆結合，留白構圖，淡彩，無文字。"
                    ),
                })
            if len(picked) >= TOP_K:
                break
        if picked:
            picked.sort(key=lambda p: p["para"])
            result[str(n)] = picked
    return {"chapters": result}


def main() -> None:
    only = None
    if "--only" in sys.argv:
        only = set(sys.argv[sys.argv.index("--only") + 1].split(","))
    total = 0
    for meta_path in sorted(NOVELS_DIR.glob("*/meta.json")):
        slug = meta_path.parent.name
        if only and slug not in only:
            continue
        scenes = detect(slug)
        count = sum(len(v) for v in scenes["chapters"].values())
        (meta_path.parent / "scenes.json").write_text(
            json.dumps(scenes, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        total += count
        print(f"[ ok ] {slug}: {count} 個場景")
    print(f"\n共偵測 {total} 個插畫場景")


if __name__ == "__main__":
    main()
