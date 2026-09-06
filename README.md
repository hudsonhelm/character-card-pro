# Character Card Pro

A simple Windows desktop utility for creating and editing PNG character cards. It runs completely locally: no account, browser, server, telemetry, or network connection is used at runtime.

> **Download:** Get the latest portable Windows build from this repository's [Releases page](../../releases/latest). Until the first derivative release is published, run the application from source as described below.

## English

Character Card Pro is a derivative of the Chub PNG Character Card Editor for reading, creating, and editing chub.ai / SillyTavern-compatible PNG character cards.

It reads character metadata embedded in PNG text chunks, edits the card fields in separate text boxes, and writes the updated metadata back into the PNG without re-encoding the image pixels.

### Features

- Create a new Character Card V3 from any ordinary PNG with one click, or choose V2 from the File menu.
- Open PNG character cards that store base64 JSON in `chara` or `ccv3` text chunks.
- Edit common Character Card V2/V3 fields, including name, description, personality, scenario, first message, example dialogues, creator notes, system prompt, post-history instructions, tags, alternate greetings, character book JSON, and extensions JSON.
- Supports UTF-8 content, including English, Chinese, Japanese, and other languages inside the card data.
- Provides Open, Save, and Save As.
- Keeps unknown `data` fields and top-level extra fields so platform-specific extensions are not silently discarded.
- Replaces only the card metadata chunk and does not re-compress or redraw the PNG image.

### Quick Start

1. Choose **New Card from PNG** to turn an ordinary PNG into a new V3 card, or use **File → New Card from PNG → Character Card V2** when V2 is required.
2. Choose the source PNG, fill in the character fields, and select **Save** or **Save As**.
3. The first save of a new card always asks for a destination so the source artwork is not overwritten accidentally.

To edit an existing V2 or V3 card, choose **Open**, make the changes, then use **Save** or **Save As**.

### Download

For normal Windows use, download the portable EXE from the [GitHub Releases page](../../releases/latest).

### Run From Source

```powershell
python .\chub_card_editor.py
```

Requirements: Python 3.10+ with `tkinter`.

### Test

```powershell
python -m unittest .\test_card_editor_core.py
```

### Build the Portable Windows EXE

Python 3.10+ with `tkinter` is required on the build machine. From PowerShell:

```powershell
.\build.ps1
```

The script creates an isolated `.venv`, installs the pinned PyInstaller version, and writes the portable application to `dist\Character Card Pro.exe`. Python is bundled into the EXE and is not required on the end user's computer.

### Format and Safety Notes

- New cards default to Character Card V3 (`ccv3`, specification version `3.0`). V2 (`chara`, version `2.0`) remains available for compatibility.
- Existing unknown/custom top-level and `data` fields are retained when a card is edited and saved.
- PNG chunks are copied directly; image pixels are not decoded or recompressed.
- Normal use is fully offline and makes no network requests.

### Attribution and License

This project is derived from [linnnn89/chub-png-card-editor](https://github.com/linnnn89/chub-png-card-editor), originally copyright © 2026 linnnn89. The upstream MIT license and copyright notice are preserved in [LICENSE](LICENSE).

## 中文

Chub PNG Character Card Editor 是一个本地桌面小工具，用于读取和编辑 chub.ai / SillyTavern 的 PNG 角色卡。

它会读取 PNG 文本 chunk 中嵌入的角色卡元数据，在独立文本框中编辑各个模块，然后把更新后的元数据写回 PNG；图片像素本身不会被重新编码。

### 功能

- 打开使用 `chara` 或 `ccv3` 文本 chunk 保存 base64 JSON 的 PNG 角色卡。
- 可编辑 Character Card V2/V3 常用字段，包括名称、描述、性格、场景、开场白、示例对话、作者备注、系统提示词、后历史指令、标签、备用开场白、世界书 JSON 和扩展 JSON。
- 角色卡内容支持 UTF-8，可保存英文、中文、日文等语言。
- 提供 Open、Save、Save As 功能。
- 保留未知的 `data` 字段和顶层额外字段，避免丢弃平台私有扩展。
- 只替换角色卡元数据 chunk，不重压缩、不重绘 PNG 图片。

### 下载

Windows 普通用户可从 GitHub Releases 页面下载英文版 EXE。

### 从源码运行

```powershell
python .\chub_card_editor.py
```

依赖：Python 3.10+，并需要 `tkinter`。

### 测试

```powershell
python -m unittest .\test_card_editor_core.py
```

## 日本語

Chub PNG Character Card Editor は、chub.ai / SillyTavern の PNG キャラクターカードをローカルで読み書きするための小さなデスクトップツールです。

PNG のテキスト chunk に埋め込まれたキャラクターカードのメタデータを読み取り、各項目を専用のテキストボックスで編集し、画像ピクセルを再エンコードせずにメタデータだけを書き戻します。

### 機能

- `chara` または `ccv3` のテキスト chunk に base64 JSON を保存した PNG キャラクターカードを開けます。
- Character Card V2/V3 の主要項目を編集できます。名前、説明、性格、シナリオ、最初のメッセージ、会話例、作成者メモ、システムプロンプト、履歴後指示、タグ、代替挨拶、キャラクターブック JSON、拡張 JSON などに対応します。
- カード内のデータは UTF-8 に対応し、英語、中国語、日本語などを保存できます。
- Open、Save、Save As を提供します。
- 未知の `data` フィールドとトップレベルの追加フィールドを保持し、プラットフォーム固有の拡張を不用意に削除しません。
- キャラクターカードのメタデータ chunk だけを置き換え、PNG 画像は再圧縮・再描画しません。

### ダウンロード

通常の Windows 利用では、GitHub Releases ページから英語版 EXE をダウンロードしてください。

### ソースから実行

```powershell
python .\chub_card_editor.py
```

要件：Python 3.10+ と `tkinter`。

### テスト

```powershell
python -m unittest .\test_card_editor_core.py
```
