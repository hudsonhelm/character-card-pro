# Character Card Pro

Character Card Pro is a lightweight, completely offline Windows desktop utility for PNG character cards. It can create a new Character Card V3 or V2 from an ordinary PNG, open and edit existing cards, and save the finished card without re-encoding the artwork or silently discarding unknown metadata.

There are no accounts, browser components, hosted services, telemetry, or runtime network requests.

> **Download:** Get the latest portable Windows EXE from the [Releases page](../../releases/latest).

## English

Character Card Pro is a derivative of the Chub PNG Character Card Editor for reading, creating, and editing chub.ai / SillyTavern-compatible PNG character cards.

It reads character metadata embedded in PNG text chunks, edits the card fields in separate text boxes, and writes the updated metadata back into the PNG without re-encoding the image pixels.

### Features

- Create a new Character Card V3 from any ordinary PNG with one click, or choose V2 from the File menu.
- Open PNG character cards that store base64 JSON in `chara` or `ccv3` text chunks.
- Open an existing character-card PNG directly from Windows by associating `.png` files with Character Card Pro or using **Open with**.
- Edit common Character Card V2/V3 fields, including name, description, personality, scenario, first message, example dialogues, creator notes, system prompt, post-history instructions, tags, alternate greetings, character book JSON, and extensions JSON.
- Supports UTF-8 content, including English, Chinese, Japanese, and other languages inside the card data.
- Provides Open, Save, and Save As.
- Keeps unknown `data` fields and top-level extra fields so platform-specific extensions are not silently discarded.
- Replaces only the card metadata chunk and does not re-compress or redraw the PNG image.

### Quick Start

1. Choose **New V3 Card from PNG** to turn an ordinary PNG into a new V3 card, or use **File → New Card from PNG → Character Card V2** when V2 is required.
2. Choose the source PNG, fill in the character fields, and select **Save** or **Save As**.
3. The first save of a new card always asks for a destination so the source artwork is not overwritten accidentally.

To edit an existing V2 or V3 card, choose **Open**, make the changes, then use **Save** or **Save As**.

You can also right-click an existing character-card PNG in Windows, choose **Open with**, and select `Character Card Pro.exe`. Ordinary PNGs without card metadata should still be opened through **New V3 Card from PNG** (or the V2 option in the File menu).

### Download

For normal Windows use, download the portable EXE from the [GitHub Releases page](../../releases/latest).

The current build is not digitally signed, so Windows may display an Unknown Publisher or SmartScreen warning.

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

### Credits and License

Character Card Pro is based on the original [Chub PNG Character Card Editor](https://github.com/linnnn89/chub-png-card-editor) created by [linnnn89](https://github.com/linnnn89). Their compact Tkinter application and direct PNG metadata-preservation approach provided the foundation for this derivative.

The original project is MIT-licensed and copyright © 2026 linnnn89. Its copyright notice and license terms are preserved in [LICENSE](LICENSE), as required. This derivative is not presented as an official release of or endorsement by the upstream author.
