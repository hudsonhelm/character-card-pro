# Project Notes

## Upstream Baseline

- Upstream: <https://github.com/linnnn89/chub-png-card-editor>
- Clean baseline: commit `c7ea9bd` / tag `v1.0.0`
- License: MIT; the upstream copyright and license text remain unchanged in `LICENSE`.
- Baseline verification: the two upstream unit tests passed under Python 3.12 before feature work began.

## Phase 1 Findings

- The application is a dependency-free Python/Tkinter desktop program. The GUI and metadata core currently live in `chub_card_editor.py`.
- PNG files are parsed and written as raw chunks with CRC validation. Saving replaces character-card text chunks immediately before `IEND`; it does not decode or re-encode image pixels.
- Character data is UTF-8 JSON encoded as Base64 in PNG text chunks. `ccv3` takes priority over `chara` when both exist.
- V2 and V3 cards use their native envelope (`spec`, `spec_version`, and `data`) internally. Legacy flat data is normalized to a V2 envelope for editing.
- Loaded cards are deep-copied. Unrecognized `data` and top-level fields remain in the model and are exposed in the Advanced JSON tab, so they survive a normal edit/save cycle.
- The GUI is a single Tkinter window with tabs for core fields, prompts, metadata, advanced JSON, and a full JSON preview.
- The upstream repository contains no PyInstaller spec, build script, workflow, or dependency manifest. The derivative now provides `build.ps1` and a pinned `requirements-build.txt`; generated build output and transient spec files remain ignored.

## MVP Decisions

- One-click creation defaults to Character Card V3 because the current V3 specification defines `ccv3` as the PNG chunk and requires `group_only_greetings`; the File menu also provides V2 creation for broader compatibility.
- A PNG that already contains `chara` or `ccv3` data is rejected by the new-card workflow and must be opened normally, preventing accidental metadata replacement.
- A new card has no current output path, so its first Save opens Save As and proposes `<source>_card.png` beside the source image.
- Empty optional `character_book` data is omitted rather than serialized as JSON `null`.

## Validation

- Unit coverage checks existing cards, V2/V3 creation, V3 priority, unknown-field survival, source-file immutability, and preservation of all non-card PNG chunks.
- A generated V3 card was decoded independently using the same `png-chunks-extract` and `png-chunk-text` packages used by SillyTavern's current character-card parser.
- The bundled automation Python had an unusable Tcl/Tk library, but the user later confirmed the source application launches under a normal Windows Python/Tk installation.
- The portable EXE was built with Python 3.14.7 and PyInstaller 6.22.2. It remained running through a five-second packaged-application startup smoke test, confirming that the bundled Tcl/Tk runtime initialized.

Specification references:

- Character Card V2: <https://github.com/malfoyslastname/character-card-spec-v2/blob/main/spec_v2.md>
- Character Card V3: <https://github.com/kwaroran/character-card-spec-v3/blob/main/SPEC_V3.md>
- SillyTavern parser: <https://github.com/SillyTavern/SillyTavern/blob/release/src/character-card-parser.js>
