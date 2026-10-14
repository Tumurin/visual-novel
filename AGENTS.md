## Project

古典小說閱讀網站。Node 22 在 `~/.local/node/bin`（每個 shell 先 `export PATH="$HOME/.local/node/bin:$PATH"`）。

- 書籍資料由 `scripts/` 的 Python pipeline 產生到 `public/novels/`（下載 → 切章 → 場景偵測 → 插畫），不要手改 `public/novels/` 與 `public/ads/` 的產物，改 scripts 重跑；原文快取在 `data/raw/`
- 資料格式與 pipeline 用法見 README.md；完整交接文件（環境、架構、已知問題、驗證 SOP）見 HANDOVER.md
- 只收公共領域文本；仍在著作權保護期內的作者（金庸、古龍、黃易等）一律不收

## Development

When starting the dev server, use background mode:

```
astro dev --background
```

Manage the background server with `astro dev stop`, `astro dev status`, and `astro dev logs`.

## Documentation

Full documentation: https://docs.astro.build

Consult these guides before working on related tasks:

- [Adding pages, dynamic routes, or middleware](https://docs.astro.build/en/guides/routing/)
- [Working with Astro components](https://docs.astro.build/en/basics/astro-components/)
- [Using React, Vue, Svelte, or other framework components](https://docs.astro.build/en/guides/framework-components/)
- [Adding or managing content](https://docs.astro.build/en/guides/content-collections/)
- [Adding styles or using Tailwind](https://docs.astro.build/en/guides/styling/)
- [Supporting multiple languages](https://docs.astro.build/en/guides/internationalization/)
