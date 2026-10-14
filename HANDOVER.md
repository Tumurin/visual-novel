# 交接文件（Handover）

> 專案：古典小說書庫 — 重視閱讀體驗的中國古典小說閱讀網站
> 狀態：已完成並驗證（2026-10-15）。`npm run build` 通過、`impeccable detect` 零告警、桌機/手機/三主題/廣告模式截圖目檢通過。
> 本文件給接下來維護的人：環境怎麼裝、東西放哪、pipeline 怎麼跑、坑在哪。

---

## 1. 專案總覽

- **位置**：`/home/user/Developer/visual-novel`
- **技術棧**：Astro 7（全靜態輸出）+ Tailwind CSS 4 + 原生 TypeScript（無前端框架）+ Python 3 資料 pipeline（僅標準庫 + opencc）
- **內容**：40 部公共領域古典小說，約 2000 萬字，2,354 個 AI 插畫場景（目前為水墨風佔位 SVG）
- **功能**：書庫搜尋、三主題（紙白/書卷米/墨夜）、五級字級、目錄抽屜、進度記憶、鍵盤翻回、名場面插畫、廣告模式（插畫槽替換為贊助內容）
- **版權界線**：只收公共領域文本。金庸（2018 歿）、古龍（1985 歿）、黃易（2017 歿）等仍在保護期內，**一律不收**；pipeline 保留匯入管道供合法取得的文本使用。這是硬性原則，不要在書源清單加入仍在保護期的作品。

## 2. 環境需求

| 需求 | 位置/安裝方式 | 備註 |
| --- | --- | --- |
| Node.js 22 | `~/.local/node`（手動解官方 tarball 安裝） | 已寫入 `~/.bashrc` 與 `~/.profile` 的 PATH；非互動 shell 需手動 `export PATH="$HOME/.local/node/bin:$PATH"` |
| Python 3.12 | 系統內建 `/usr/bin/python3` | 無 venv |
| pip 套件 | `opencc-python-reimplemented`（`pip install --user --break-system-packages`） | 僅殆知閣簡體來源轉繁體用；沒裝的話 PG 來源照跑、GH 來源會報錯 |
| 無頭瀏覽器（驗證用） | `brave-browser` | 截圖/ dump-dom 驗證前端用 |
| impeccable CLI（設計稽核） | `~/.kimi-code/skill-repos/impeccable/skill/scripts/impeccable` | 自包含 binary，直接執行 |

**沒有其他系統依賴**。`node_modules` 由 `npm install` 重建（lockfile 已存在）。

## 3. 快速上手

```bash
export PATH="$HOME/.local/node/bin:$PATH"
cd /home/user/Developer/visual-novel
npm install          # 首次或刪過 node_modules
npm run build        # → dist/
python3 -m http.server 8000 -d dist   # 或 npm run preview
```

開發：`npm run dev`（AGENTS.md 指示背景模式用 `astro dev --background`）。

## 4. 架構與資料流

```
Project Gutenberg ─┐
                   ├─→ scripts/download_novels.py ─→ data/raw/<slug>.txt（原文快取）
殆知閣 (GitHub) ───┘        │（切章、段落接合、OpenCC s2t）
                            ├─→ public/novels/<slug>/meta.json
                            ├─→ public/novels/<slug>/chapters/NNNN.json
                            └─→ public/novels/catalog.json
                                   │
scripts/detect_scenes.py ──────────┴─→ public/novels/<slug>/scenes.json
scripts/generate_illustrations.py ─────→ public/novels/<slug>/illust/*.svg|png
public/ads/（手維護）──────────────────→ ads.json + 創意 SVG
                                   │
                 Astro build（純靜態；前端 client-side fetch 上述 JSON）
                                   ↓
                    index.astro 書庫 / read.astro 閱讀器（+廣告模式）
```

**重要**：`public/novels/` 與 `public/ads/` 的 JSON/SVG 是 pipeline 產物，**不要手改**；改 scripts 重跑。刪掉 `public/novels/<slug>/` 後重跑 `download_novels.py` 只重建該書（原文有快取，不會重新下載）。

### 前端檔案

- `src/styles/global.css` — 三主題 CSS 變數（`--bg-page/--fg/--muted/--line/--soft/--accent`）、`.reader-body` 排版、focus-visible、skip-link、reduced-motion
- `src/layouts/Base.astro` — 共用 head、主題/字級防閃爍還原腳本
- `src/pages/index.astro` — 書庫（client-side fetch catalog，即時搜尋）
- `src/pages/read.astro` — 閱讀器全部邏輯（約 500 行原生 TS）

### 資料合約（前端只認這些）

| 端點 | 格式 |
| --- | --- |
| `/novels/catalog.json` | meta 陣列 |
| `/novels/<slug>/meta.json` | `{slug,title,author,dynasty,description,source,license,chapterCount,totalChars,chapters:[{n,title,chars}]}` |
| `/novels/<slug>/chapters/NNNN.json` | `{n,title,paragraphs[]}`，四位數補零 |
| `/novels/<slug>/scenes.json`（可 404） | `{chapters:{"1":[{para,score,excerpt,image,prompt}]}}`；`para` 是 **0-based** 段落索引，插在第 `para` 段之後；`image` 相對於 `/novels/<slug>/` |
| `/ads/ads.json` | `[{id,brand,slogan,image,cta,url}]` |

### URL 參數（read.astro）

- `?n=<slug>&c=<回次>` — 指定書與回；無 `c` 時自動接續上次進度
- `?ads=1|0` — 廣告模式（**會**寫入 localStorage）
- `?theme=paper|rice|ink` — 主題預覽（**不**寫入 localStorage）

## 5. 資料 pipeline 細節

### `download_novels.py`

書目在 `NOVELS` 清單（slug, 書名, 作者, 朝代, 簡介, 來源）。來源兩種：

- `("pg", "<ebook_id>")` — Project Gutenberg，繁體 UTF-8
- `("gh", "集藏/...txt")` — 殆知閣 `garychowcmu/daizhigev20`，簡體，OpenCC `s2t` 轉繁體

切章規則（`split_chapters`），依序處理過這些真實格式：

1. 行首回目 `第X回/卷/章`（數字含 `〇零○一…十百千兩` 與全形數字；`○` 是西遊記的「第一○回」）
2. 行內回目：`……且聽下回分解。第三回　標題` 同段黏在一起 → 句讀後補換行（排除「回合/回來」等誤判）
3. 回目帶項目符號前綴（`●第一回`，野叟曝言）→ 剝除
4. 回目與正文同行的超長行 → 拆標題（取到第一個句讀或 24 字），**多出來的字還給正文，不丟內容**
5. 目錄頁過濾：開頭一連串 body 極短的標記視為目錄；目錄殘留與正文同標題時丟掉先出現者；第一章標題含兩個回目（合併型目錄）時丟掉
6. 退路：無回目文本按 4000 字切塊

段落接合（`make_paragraphs`）：原文是 ~30 字硬換行。規則：空行分段；段內多數行有縮排（`　` 或兩空格）則各自成段；全為 ≤16 字短行視為詩詞保留換行；其餘接成一段（CJK 不加空格）。

### `detect_scenes.py`

關鍵詞加權（大戰/舌戰/借東風/空城/打虎…）對每段評分，每回取前 2 名（間距 ≥6 段、門檻 ≥4 分）。產出含送給圖像模型的 `prompt`（水墨風、無文字）。要改風格或名場面定義就改這支。

### `generate_illustrations.py`

`ILLUST_BACKEND`：

| 值 | 需要 | 產出 |
| --- | --- | --- |
| `mock`（預設） | 無 | 水墨風佔位 SVG（確定性 seed，重跑不變） |
| `openai` | `OPENAI_API_KEY`（可選 `OPENAI_BASE_URL`、`ILLUST_MODEL`，預設 gpt-image-1） | PNG，scenes.json 的 image 路徑自動改副檔名 |
| `gemini` | `GEMINI_API_KEY`（可選 `ILLUST_MODEL`） | 同上 |

換真實後端：`ILLUST_BACKEND=openai python3 scripts/generate_illustrations.py --force`（`--force` 覆蓋 mock 產物；不加則只補缺的）。2,354 張圖要跑很久且要花錢，先用 `--only sanguo` 試一冊。

## 6. 廣告系統

- 素材手維護在 `public/ads/`：`ads.json` + 創意 SVG。目前三則示範：青龍牌菜刀、臥龍茶、及時雨。
- 讀者行為：廣告模式開時，每個插畫 figure 依序輪播廣告（起點 `chapterNum % ads.length`，避免同頁相鄰重複），圖右上「廣告」標章，caption 顯示品牌｜slogan＋CTA；關閉即還原插畫，免重整。
- **上新廣告**：放 SVG → ads.json 加一筆 → 不用改程式。

## 7. 設計系統（前端）

- 字體：Noto Serif TC（Google Fonts，離線 fallback Songti TC/PMingLiU/serif）
- 三主題對比皆過 WCAG AA（muted：紙白 5.2:1 / 米 4.7:1 / 墨夜 6.0:1）——**改主題色後務必重跑 detect**（見 §9）
- 墨夜主題有淺字深底補償（行高 2.05、字距 +0.01em）
- 動效全部包在 `prefers-reduced-motion: no-preference`
- 書卷米主題的 `cream-palette` detector 警告是刻意保留（人工指定主題）

## 8. 已安裝的 AI 技能（使用者層級）

- 位置：`~/.kimi-code/skill-repos/`（5 個 git clone，保留 .git）→ 個別技能 symlink 到 `~/.kimi-code/skills/`（共 37 個）
- 來源：Leonxlnx/taste-skill、nextlevelbuilder/ui-ux-pro-max-skill、pbakaus/impeccable、vercel-labs/web-interface-guidelines、emilkowalski/skills
- **更新**：`cd ~/.kimi-code/skill-repos/<repo> && git pull` 即可（symlink 不用動）
- impeccable 的 `SKILL.md` 是由 `SKILL.src.md` 手動渲染的（佔位符已替換）；上游若大改 `SKILL.src.md` 需重渲
- 新 session 才會載入新技能

## 9. 驗證 SOP

```bash
export PATH="$HOME/.local/node/bin:$PATH"
npm run build
python3 -m http.server 8471 --bind 127.0.0.1 -d dist &   # 起測試伺服器

# 設計/無障礙稽核（乾淨時無輸出、exit 0）
~/.kimi-code/skill-repos/impeccable/skill/scripts/impeccable detect \
  http://127.0.0.1:8471/ \
  "http://127.0.0.1:8471/read/?n=sanguo&c=5" \
  "http://127.0.0.1:8471/read/?n=sanguo&c=5&theme=ink"

# 截圖目檢
brave-browser --headless --disable-gpu --no-sandbox \
  --window-size=1280,1400 --screenshot=/tmp/check.png \
  "http://127.0.0.1:8471/read/?n=sanguo&c=5"

pkill -f "http.server 8471"
```

## 10. 已知問題（不影響使用，按優先級排）

1. **回目編號與 n 不一致**（包公案、九尾龜等）：原文分卷重新計數，`n` 是流水號、標題是原書回數，頂 bar「第 N / M 回」以 `n` 為準。要一致的話改 `download_novels.py` 的章節命名邏輯。
2. **來源文本本身缺回目**：儒林外史（PG 版缺約 10 個回目標記，章節合併在鄰回）、官場現形記缺第十三回標記、痛史缺第六/二十回、封神演義 PG 版缺第一百回內容。屬上游文本缺陷，換版本才能解。
3. **聊齋誌異只有 12 個大章**（按卷切，每卷約 4 萬字）：可再加一層按篇名切分。
4. **二刻拍案驚奇 39 卷**：原書卷四十「宋公明鬧元宵」為雜劇，許多版本不收，現狀合理。
5. 佔位插畫是 SVG mock，等接上真實圖像模型後整批重生（§5）。
6. Google Fonts 是外部依賴；要完全離線可下載字型自託管。

## 11. 後續工作建議

- 接真實插畫後端並重生全量插畫（§5，先單書試跑控制成本）
- 佈署：`dist/` 純靜態，任何靜態託管（Cloudflare Pages / Netlify / nginx）皆可，無環境變數需求
- 真實廣告主接入：把 ads.json 換成真素材與落地頁 URL，或接廣告聯播網（前端槽位邏輯已就緒）
- 合法文本匯入：使用者自購電子書轉純文字放 `data/raw/<slug>.txt`，在 `NOVELS` 加一筆即可走同一 pipeline
- 聊齋篇名切分、包公案回目正規化（見 §10）

---

其他參考：`README.md`（使用者向說明）、`AGENTS.md`（給 AI agent 的專案守則）。
