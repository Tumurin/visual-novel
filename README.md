# 古典小說書庫（Visual Novel Reader）

> 維護交接請看 **[HANDOVER.md](HANDOVER.md)**（環境、架構、pipeline 細節、已知問題、驗證 SOP）。

以閱讀體驗為核心的中國古典小說閱讀網站。Astro 7 + Tailwind CSS 4，全靜態輸出。

## 功能

- **書庫**：40 部公共領域古典長篇，約 2000 萬字（三國演義、水滸傳、西遊記、紅樓夢、金瓶梅詞話、儒林外史、聊齋誌異、封神演義、三俠五義、施公案、說岳全傳……完整書目見 `public/novels/catalog.json`）
- **閱讀器**：襯線字體、寬行距、三主題（紙白／書卷米／墨夜）、五級字級、目錄抽屜、進度記憶、鍵盤翻回（←/→）、桌機手機響應式
- **AI 插畫**：自動偵測名場面（戰鬥、舌戰、名場景關鍵詞評分），每回最多 2 幅插畫，插在對應段落之後
- **廣告模式**：開啟「廣告版」後，插畫槽位替換為贊助商內容（示範：青龍牌菜刀、臥龍茶、及時雨運動飲料），附「廣告」標章，免重整切換，支援 `?ads=1` 網址參數

## 常用指令

```bash
export PATH="$HOME/.local/node/bin:$PATH"   # Node 22 装在 ~/.local/node
npm run build                               # 建置到 dist/
npm run preview                             # 預覽建置結果
python3 -m http.server 8000 -d dist         # 或用任何靜態伺服器
```

## 資料 pipeline（scripts/）

```bash
python3 scripts/download_novels.py          # 下載+切章+產生 JSON（原文快取 data/raw/）
python3 scripts/detect_scenes.py            # 關鍵場面偵測 → scenes.json
python3 scripts/generate_illustrations.py   # 產生插畫
```

- 書源：Project Gutenberg（繁體）＋ 殆知閣 daizhigev20（簡體，OpenCC 自動轉繁體）。只收公共領域作品；金庸、古龍、黃易等仍在著作權保護期內，不收錄。欲匯入合法取得的文本，在 `download_novels.py` 的 `NOVELS` 清單加一筆即可。
- `--only slug1,slug2` 可只處理指定書；刪掉 `public/novels/<slug>/` 重跑即重建該書（原文有快取，不會重抓）。

## 插畫後端

環境變數 `ILLUST_BACKEND`：

| 值 | 說明 |
| --- | --- |
| `mock`（預設） | 離線產生水墨風佔位 SVG，用來打通 pipeline |
| `openai` | 需 `OPENAI_API_KEY`，可選 `OPENAI_BASE_URL`、`ILLUST_MODEL`（預設 gpt-image-1），產 PNG |
| `gemini` | 需 `GEMINI_API_KEY`，可選 `ILLUST_MODEL`，產 PNG |

換真實後端後執行 `python3 scripts/generate_illustrations.py --force` 重新產生全部插畫（scenes.json 的 prompt 欄位即為送給模型的提示詞）。

## 廣告

廣告素材在 `public/ads/`（`ads.json` 清單 + SVG 創意）。上新廣告：放 SVG、在 ads.json 加一筆 `{id, brand, slogan, image, cta, url}` 即可，前端自動輪播。

## 資料格式

- `public/novels/catalog.json`：全書目錄
- `public/novels/<slug>/meta.json`：單書 meta（含章回清單）
- `public/novels/<slug>/chapters/NNNN.json`：`{n, title, paragraphs[]}`
- `public/novels/<slug>/scenes.json`：`{chapters: {"1": [{para, excerpt, image, prompt}]}}`
- `public/novels/<slug>/illust/`：插畫檔
