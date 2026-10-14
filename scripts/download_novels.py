#!/usr/bin/env python3
"""下載公共領域中國古典小說，切分章回，輸出 JSON 到 public/novels/。

書源：
  pg  Project Gutenberg（繁體 UTF-8 全文）
  gh  殆知閣（github.com/garychowcmu/daizhigev20，簡體，自動以 OpenCC 轉繁體）

僅收錄已進入公共領域的作品。原文快取於 data/raw/，重跑不會重複下載。
用法: python3 scripts/download_novels.py [--only slug1,slug2]
"""
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "public" / "novels"
RAW = ROOT / "data" / "raw"
UA = {"User-Agent": "visual-novel-reader/0.1 (public-domain text pipeline)"}
GH_BASE = "https://raw.githubusercontent.com/garychowcmu/daizhigev20/master/"

try:
    import opencc
    S2T = opencc.OpenCC("s2t").convert
except Exception:  # noqa: BLE001
    S2T = None

# (slug, 書名, 作者, 朝代, 簡介, (來源, 參照))
NOVELS = [
    ("sanguo", "三國演義", "羅貫中", "明",
     "東漢末年群雄並起，魏蜀吳三分天下的歷史演義。", ("pg", "23950")),
    ("shuihu", "水滸傳", "施耐庵", "元末明初",
     "一百零八條好漢聚義梁山泊，替天行道。（金聖嘆七十回本）", ("pg", "23863")),
    ("xiyou", "西遊記", "吳承恩", "明",
     "唐僧師徒四人西天取經，歷經九九八十一難。", ("pg", "23962")),
    ("hongloumeng", "紅樓夢", "曹雪芹", "清",
     "賈寶玉與金陵十二釵的悲歡離合，封建家族的興衰史詩。", ("pg", "24264")),
    ("jinpingmei", "金瓶梅詞話", "蘭陵笑笑生", "明",
     "以西門慶一家為中心的明代世情小說。", ("pg", "52200")),
    ("rulin", "儒林外史", "吳敬梓", "清",
     "諷刺科舉制度下讀書人百態的長篇小說。", ("pg", "24032")),
    ("liaozhai", "聊齋誌異", "蒲松齡", "清",
     "狐鬼花妖的短篇志怪故事集。", ("pg", "51828")),
    ("fengshen", "封神演義", "許仲琳", "明",
     "武王伐紂，姜子牙封神的神魔小說。", ("pg", "23910")),
    ("jinghuayuan", "鏡花緣", "李汝珍", "清",
     "唐敖海外遊歷奇國，百花仙子謫凡的奇幻小說。", ("pg", "23818")),
    ("laocan", "老殘遊記", "劉鶚", "清末",
     "走方郎中老殘遊歷山東所見的官場與民生。", ("pg", "23850")),
    ("guanchang", "官場現形記", "李伯元", "清末",
     "清末官場群醜圖，譴責小說代表作。", ("pg", "54756")),
    ("niehaihua", "孽海花", "曾樸", "清末",
     "以賽金花一生串起清末三十年政局與士林百態。", ("pg", "25128")),
    ("dongzhou", "東周列國志", "馮夢龍", "明",
     "春秋戰國五百年的諸侯興亡演義。", ("gh", "集藏/演义/东周列国志.txt")),
    ("suitang", "隋唐演義", "褚人穫", "清",
     "隋末唐初英雄傳奇與宮闈故事。", ("pg", "23835")),
    ("shuoyue", "說岳全傳", "錢彩", "清",
     "岳飛精忠報國、抗金衛宋的英雄演義。", ("gh", "集藏/话本/说岳全传.txt")),
    ("sanxiawuyi", "三俠五義", "石玉崑", "清",
     "包拯斷案，南俠展昭與五鼠的俠義公案小說（俞樾改編本稱《七俠五義》）。", ("pg", "25376")),
    ("xiaowuyi", "小五義", "佚名", "清",
     "《三俠五義》續書，小五義出世的故事。", ("gh", "集藏/话本/小五义.txt")),
    ("yangjiajiang", "楊家將傳", "熊大木", "明",
     "楊家將滿門忠烈、抗遼衛國的故事。", ("gh", "集藏/话本/杨家将传.txt")),
    ("jigong", "濟公全傳", "郭小亭", "清",
     "濟顛和尚懲惡揚善的神魔俠義小說。", ("gh", "集藏/小说/济公全传.txt")),
    ("yushi", "喻世明言", "馮夢龍", "明",
     "三言之一，明代白話短篇小說集。", ("pg", "27582")),
    ("jingshi", "警世通言", "馮夢龍", "明",
     "三言之二，明代白話短篇小說集。", ("pg", "24141")),
    ("xingshi", "醒世恆言", "馮夢龍", "明",
     "三言之三，明代白話短篇小說集。", ("pg", "24239")),
    ("chuke", "初刻拍案驚奇", "凌濛初", "明",
     "二拍之一，明代擬話本短篇小說集。", ("pg", "57248")),
    ("erke", "二刻拍案驚奇", "凌濛初", "明",
     "二拍之二，明代擬話本短篇小說集。", ("pg", "26729")),
    ("jinguqiguan", "今古奇觀", "抱甕老人", "明",
     "從三言二拍精選四十篇的明代話本選集。", ("gh", "集藏/小说/今古奇观.txt")),
    ("ernv", "兒女英雄傳", "文康", "清",
     "十三妹何玉鳳與安驥的俠義言情小說。", ("pg", "25327")),
    ("xingshiyinyuan", "醒世姻緣傳", "西周生", "明末清初",
     "晁家兩世婚姻因果，百回世情小說。", ("gh", "集藏/小说/醒世姻缘传.txt")),
    ("lvyexianzong", "綠野仙蹤", "李百川", "清",
     "冷于冰修道成仙、濟世度人的神怪世情小說。", ("gh", "集藏/小说/绿野仙踪.txt")),
    ("yesoupuyan", "野叟曝言", "夏敬渠", "清",
     "文素臣文治武功的清代才學小說。", ("gh", "集藏/小说/野叟曝言.txt")),
    ("qiludeng", "歧路燈", "李綠園", "清",
     "浪子回頭的清代河南世情教育小說。", ("gh", "集藏/小说/歧路灯.txt")),
    ("huayuehen", "花月痕", "魏秀仁", "清",
     "才子佳人與戰亂離合的清代狹邪小說。", ("gh", "集藏/小说/花月痕.txt")),
    ("qingloumeng", "青樓夢", "俞達", "清",
     "金挹香與三十六釵的清代狹邪小說。", ("gh", "集藏/小说/青楼梦.txt")),
    ("jiuweigui", "九尾龜", "張春帆", "清末",
     "描寫清末上海青樓生態的狹邪小說。", ("gh", "集藏/小说/九尾龟.txt")),
    ("henhai", "恨海", "吳趼人", "清末",
     "庚子之亂中兩對兒女離散悲歡的寫情小說。", ("gh", "集藏/小说/恨海.txt")),
    ("tongshi", "痛史", "吳趼人", "清末",
     "南宋亡國之痛，借古諷今的歷史小說。", ("gh", "集藏/小说/痛史.txt")),
    ("ershinian", "二十年目睹之怪現狀", "吳趼人", "清末",
     "九死一生所見清末社會百態，譴責小說代表作。", ("gh", "集藏/小说/二十年目睹之怪现状.txt")),
    ("shigongan", "施公案", "佚名", "清",
     "施仕綸斷案、黃天霸行俠的公案俠義小說。", ("gh", "集藏/话本/施公案.txt")),
    ("penggongan", "彭公案", "貪夢道人", "清",
     "彭朋斷案的公案俠義小說。", ("gh", "集藏/话本/彭公案.txt")),
    ("baogongan", "包公案", "安遇時", "明",
     "包拯明鏡高懸斷奇案的公案小說集。", ("gh", "集藏/话本/包公案.txt")),
    ("hedian", "何典", "張南莊", "清",
     "鬼話連篇、滑稽諷世的清代吳語小說。", ("gh", "集藏/小说/何典.txt")),
]

NUM = r"〇零○一二三四五六七八九十百千兩\d０-９"
CHAPTER_RE = re.compile(rf"^第\s*[{NUM}]{{1,7}}\s*[回卷章]\s*[：:、．.]?[^\n]{{0,55}}$")
JUAN_RE = re.compile(rf"^卷之?\s*[{NUM}]{{1,5}}[^\n]{{0,40}}$")
# 行首回目（不限行長；回目與正文同行的長行會再切開）
HEAD_RE = re.compile(rf"^第\s*[{NUM}]{{1,7}}\s*[回卷][ 　\xa0]{{0,4}}")


def fetch(url: str, retries: int = 3) -> bytes:
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.read()
        except Exception:  # noqa: BLE001
            if attempt == retries - 1:
                raise
            time.sleep(2 * (attempt + 1))
    return b""


def source_url(kind: str, ref: str) -> str:
    if kind == "pg":
        return f"https://www.gutenberg.org/cache/epub/{ref}/pg{ref}.txt"
    return GH_BASE + urllib.parse.quote(ref)


def download(kind: str, ref: str) -> str:
    url = source_url(kind, ref)
    raw = fetch(url)
    if len(raw) < 2000 and kind == "pg":
        # 退路：舊式 utf8 命名與 .txt.utf-8 端點
        for alt in (f"https://www.gutenberg.org/cache/epub/{ref}/pg{ref}.txt.utf8",
                    f"https://www.gutenberg.org/ebooks/{ref}.txt.utf-8"):
            try:
                raw = fetch(alt)
            except Exception:  # noqa: BLE001
                continue
            if len(raw) >= 2000:
                break
    if len(raw) < 2000:
        raise RuntimeError(f"下載內容過短 ({url})")
    for enc in ("utf-8", "gb18030", "big5"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    raise RuntimeError(f"無法解碼 ({url})")


def strip_boilerplate(text: str) -> str:
    start = re.search(r"\*\*\*\s*START OF (THE|THIS) PROJECT GUTENBERG EBOOK[^\n]*\*\*\*", text)
    if start:
        text = text[start.end():]
    end = re.search(r"\*\*\*\s*END OF (THE|THIS) PROJECT GUTENBERG EBOOK", text)
    if end:
        text = text[:end.start()]
    return text.strip()


# 行內回目：「……且聽下回分解。第三回　　姬昌解圍進妲己」同一行的情況，
# 在句讀後、形如「第X回(空格)標題」的位置補換行。
# 分隔空白含 \xa0；亦允許無空白（「第二回小俠…」），但排除「回合/回來」等誤判。
INLINE_RE = re.compile(
    rf"(?<=[。！？])(?=第\s*[{NUM}]{{1,7}}\s*回(?!合|來|頭|家|見|去|覆|答|報|轉|心|聲|信|味)[ 　\xa0]{{0,4}}\S)")
BULLET_RE = re.compile(r"^[●○◇◎※▲▽■□☆★·．]\s*")
DOUBLE_MARK_RE = re.compile(rf"第[{NUM}]{{1,7}}\s*[回卷].*第[{NUM}]{{1,7}}\s*[回卷]")


def normalize_title(title: str) -> str:
    return re.sub(r"[\s　]", "", title)


def filter_marks(marks: list[int], lines: list[str], clean: list[str]) -> list[int]:
    """去掉目錄區的回目：開頭一連串 body 極短的標記視為目錄；
    之後若某標題在後面再次出現（目錄殘留與正文重複），丟掉先前者。"""
    if len(marks) < 8:
        return marks
    run = 0
    while run < len(marks):
        m = marks[run]
        stop = marks[run + 1] if run + 1 < len(marks) else len(lines)
        body_len = sum(len(ln) for ln in lines[m + 1:stop])
        if body_len >= 200:
            break
        run += 1
    if run >= 5:
        marks = marks[run:]
    # 目錄殘留：標題在後面再次出現時，丟掉先出現的（目錄列），保留正文
    last: dict[str, int] = {}
    for pos, m in enumerate(marks):
        last[normalize_title(clean[m])] = pos
    return [m for pos, m in enumerate(marks) if last[normalize_title(clean[m])] == pos]


def split_title_line(line: str, pattern: re.Pattern) -> tuple[str, str]:
    """回目與正文同行的長行：拆出標題，多出來的部分還給正文，不丟字。"""
    if len(line) <= 60:
        return line, ""
    m = pattern.match(line)
    if not m:
        return line, ""
    rest = line[m.end():]
    p = re.search(r"[，。！？；：]", rest)
    if p and 6 <= p.start() <= 40:
        cut = m.end() + p.start()
    else:
        cut = m.end() + 24
    return line[:cut].rstrip("，。！？；： "), line[cut:].strip()


def split_chapters(text: str) -> list[tuple[str, str]]:
    text = INLINE_RE.sub("\n", text)
    lines = text.splitlines()
    clean = [BULLET_RE.sub("", ln.strip()).strip() for ln in lines]
    for pattern in (HEAD_RE, JUAN_RE):
        marks = [i for i, ln in enumerate(clean) if ln and pattern.match(ln)]
        marks = filter_marks(marks, lines, clean)
        if len(marks) >= 3:
            chapters = []
            for idx, start in enumerate(marks):
                stop = marks[idx + 1] if idx + 1 < len(marks) else len(lines)
                title, overflow = split_title_line(clean[start], pattern)
                body = ((overflow + "\n") if overflow else "") + "\n".join(lines[start + 1:stop])
                body = body.strip()
                if body:
                    chapters.append((title, body))
            if len(chapters) >= 3:
                # 合併型目錄殘留：第一章標題含兩個回目（「第三十九卷…第四十 卷…」）
                if DOUBLE_MARK_RE.search(chapters[0][0]):
                    chapters = chapters[1:]
                return chapters
    # 退路：依長度切塊（適用短篇集或無回目文本）
    chunk_size = 4000
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chapters, buf, n = [], [], 1
    size = 0
    for p in paras:
        buf.append(p)
        size += len(p)
        if size >= chunk_size:
            chapters.append((f"節 {n}", "\n\n".join(buf)))
            buf, size, n = [], 0, n + 1
    if buf:
        chapters.append((f"節 {n}", "\n\n".join(buf)))
    return chapters


def make_paragraphs(body: str) -> list[str]:
    """把硬換行接回段落：空行分段；段內若多數行有縮排則各自成段；
    全為短行視為詩詞保留換行；其餘視為硬換行散文，接成一段。"""
    paras: list[str] = []
    for block in re.split(r"\n[　\s]*\n", body):
        lines = [ln for ln in block.splitlines() if ln.strip()]
        if not lines:
            continue
        if len(lines) == 1:
            paras.append(lines[0].strip())
            continue
        indented = sum(1 for ln in lines if ln.startswith(("　", "  ")))
        if indented >= max(2, len(lines) * 0.6):
            cur = ""
            for ln in lines:
                if ln.startswith(("　", "  ")):
                    if cur:
                        paras.append(cur)
                    cur = ln.strip()
                else:
                    cur += ln.strip()
            if cur:
                paras.append(cur)
        elif all(len(ln.strip()) <= 16 for ln in lines):
            paras.extend(ln.strip() for ln in lines)
        else:
            paras.append("".join(ln.strip() for ln in lines))
    return paras


def process(slug: str, title: str, author: str, dynasty: str, desc: str,
            kind: str, ref: str) -> dict:
    RAW.mkdir(parents=True, exist_ok=True)
    raw_path = RAW / f"{slug}.txt"
    if raw_path.exists():
        text = raw_path.read_text(encoding="utf-8")
    else:
        text = download(kind, ref)
        if kind == "gh":
            if S2T is None:
                raise RuntimeError("需要 opencc（pip install opencc-python-reimplemented）")
            text = S2T(text)
        text = strip_boilerplate(text)
        raw_path.write_text(text, encoding="utf-8")
        time.sleep(1)
    chapters = split_chapters(text)
    if not chapters:
        raise RuntimeError("章回切分失敗")
    dest = OUT / slug
    (dest / "chapters").mkdir(parents=True, exist_ok=True)
    chapter_metas = []
    for n, (ctitle, body) in enumerate(chapters, start=1):
        paras = make_paragraphs(body)
        payload = {"n": n, "title": ctitle, "paragraphs": paras}
        (dest / "chapters" / f"{n:04d}.json").write_text(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        chapter_metas.append({"n": n, "title": ctitle, "chars": len(body)})
    src_label = ("https://www.gutenberg.org/ebooks/" + ref) if kind == "pg" \
        else ("https://github.com/garychowcmu/daizhigev20 (殆知閣): " + ref)
    meta = {
        "slug": slug, "title": title, "author": author, "dynasty": dynasty,
        "description": desc, "source": src_label,
        "license": "Public Domain",
        "chapterCount": len(chapters),
        "totalChars": sum(c["chars"] for c in chapter_metas),
        "chapters": chapter_metas,
    }
    (dest / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return meta


def main() -> None:
    only = None
    if "--only" in sys.argv:
        only = set(sys.argv[sys.argv.index("--only") + 1].split(","))
    OUT.mkdir(parents=True, exist_ok=True)
    catalog = []
    for slug, title, author, dynasty, desc, (kind, ref) in NOVELS:
        if only and slug not in only:
            mp = OUT / slug / "meta.json"
            if mp.exists():
                catalog.append(json.loads(mp.read_text(encoding="utf-8")))
            continue
        if (OUT / slug / "meta.json").exists():
            print(f"[skip] {slug} 已存在")
            catalog.append(json.loads((OUT / slug / "meta.json").read_text(encoding="utf-8")))
            continue
        print(f"[...] {title} ({kind}:{ref})", flush=True)
        try:
            meta = process(slug, title, author, dynasty, desc, kind, ref)
            catalog.append(meta)
            first = meta["chapters"][0]["title"][:26]
            print(f"[ ok ] {title}: {meta['chapterCount']} 回  首回「{first}」", flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"[fail] {title}: {exc}", flush=True)
    catalog.sort(key=lambda m: m["slug"])
    (OUT / "catalog.json").write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n完成: {len(catalog)} 部小說 → {OUT}")


if __name__ == "__main__":
    main()
