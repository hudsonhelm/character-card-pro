from __future__ import annotations

import base64
import copy
import json
import os
import struct
import tempfile
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
CARD_CHUNK_PRIORITY = ("ccv3", "chara")
CARD_CHUNK_NAMES = frozenset(CARD_CHUNK_PRIORITY)

TEXT_FIELDS = (
    "name",
    "description",
    "personality",
    "scenario",
    "first_mes",
    "mes_example",
    "creator_notes",
    "system_prompt",
    "post_history_instructions",
)

JSON_FIELDS = ("alternate_greetings", "character_book", "extensions")
LINE_LIST_FIELDS = ("tags",)
METADATA_FIELDS = ("creator", "character_version")
KNOWN_DATA_FIELDS = set(TEXT_FIELDS) | set(JSON_FIELDS) | set(LINE_LIST_FIELDS) | set(METADATA_FIELDS)


class CardFormatError(ValueError):
    """Raised when a PNG or embedded character-card payload is malformed."""


@dataclass
class PngChunk:
    kind: bytes
    data: bytes


@dataclass
class LoadedCard:
    path: Path
    chunk_keyword: str
    card: dict[str, Any]
    raw_json_text: str


def _crc(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


def _pack_chunk(chunk: PngChunk) -> bytes:
    return struct.pack(">I", len(chunk.data)) + chunk.kind + chunk.data + _crc(chunk.kind, chunk.data)


def read_png_chunks(path: os.PathLike[str] | str) -> list[PngChunk]:
    data = Path(path).read_bytes()
    if not data.startswith(PNG_SIGNATURE):
        raise CardFormatError("Not a PNG file: PNG signature is missing.")

    chunks: list[PngChunk] = []
    offset = len(PNG_SIGNATURE)
    while offset < len(data):
        if offset + 8 > len(data):
            raise CardFormatError("Invalid PNG: truncated chunk header.")
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        kind = data[offset + 4 : offset + 8]
        start = offset + 8
        end = start + length
        crc_end = end + 4
        if crc_end > len(data):
            raise CardFormatError(f"Invalid PNG: truncated {kind.decode('latin-1', 'replace')} chunk.")
        chunk_data = data[start:end]
        stored_crc = data[end:crc_end]
        if stored_crc != _crc(kind, chunk_data):
            raise CardFormatError(f"Invalid PNG: CRC check failed for {kind.decode('latin-1', 'replace')}.")
        chunks.append(PngChunk(kind, chunk_data))
        offset = crc_end
        if kind == b"IEND":
            break

    if not chunks or chunks[-1].kind != b"IEND":
        raise CardFormatError("Invalid PNG: IEND chunk is missing.")
    return chunks


def write_png_chunks(path: os.PathLike[str] | str, chunks: list[PngChunk]) -> None:
    payload = PNG_SIGNATURE + b"".join(_pack_chunk(chunk) for chunk in chunks)
    Path(path).write_bytes(payload)


def _decode_possible_text(kind: bytes, data: bytes) -> tuple[str, str] | None:
    if kind == b"tEXt":
        if b"\x00" not in data:
            return None
        keyword, text = data.split(b"\x00", 1)
        return keyword.decode("latin-1"), text.decode("latin-1")

    if kind == b"zTXt":
        if b"\x00" not in data:
            return None
        keyword, rest = data.split(b"\x00", 1)
        if not rest or rest[0] != 0:
            return None
        return keyword.decode("latin-1"), zlib.decompress(rest[1:]).decode("utf-8")

    if kind == b"iTXt":
        parts = data.split(b"\x00", 5)
        if len(parts) != 6:
            return None
        keyword, compression_flag, compression_method, _language, _translated, text = parts
        if compression_flag == b"\x00":
            text_bytes = text
        elif compression_flag == b"\x01" and compression_method == b"\x00":
            text_bytes = zlib.decompress(text)
        else:
            return None
        return keyword.decode("latin-1"), text_bytes.decode("utf-8")

    return None


def _card_text_chunks(chunks: list[PngChunk]) -> dict[str, str]:
    found: dict[str, str] = {}
    for chunk in chunks:
        decoded = _decode_possible_text(chunk.kind, chunk.data)
        if decoded is None:
            continue
        keyword, text = decoded
        if keyword in CARD_CHUNK_NAMES:
            found[keyword] = text
    return found


def decode_card_json(encoded_text: str) -> tuple[dict[str, Any], str]:
    stripped = encoded_text.strip()
    try:
        padding = "=" * (-len(stripped) % 4)
        decoded = base64.b64decode(stripped + padding, validate=False).decode("utf-8")
    except Exception:
        decoded = stripped

    try:
        card = json.loads(decoded)
    except json.JSONDecodeError as exc:
        raise CardFormatError(f"Embedded card JSON could not be parsed: {exc}") from exc
    if not isinstance(card, dict):
        raise CardFormatError("Embedded card JSON must be a JSON object.")
    return card, decoded


def encode_card_json(card: dict[str, Any]) -> str:
    json_text = json.dumps(card, ensure_ascii=False, indent=2)
    return base64.b64encode(json_text.encode("utf-8")).decode("ascii")


def load_card(path: os.PathLike[str] | str) -> LoadedCard:
    png_path = Path(path)
    chunks = read_png_chunks(png_path)
    text_chunks = _card_text_chunks(chunks)
    for keyword in CARD_CHUNK_PRIORITY:
        if keyword in text_chunks:
            card, raw_json_text = decode_card_json(text_chunks[keyword])
            return LoadedCard(png_path, keyword, card, raw_json_text)
    raise CardFormatError("No chub/SillyTavern card metadata found. Expected a 'ccv3' or 'chara' PNG text chunk.")


def _chunk_keyword(chunk: PngChunk) -> str | None:
    decoded = _decode_possible_text(chunk.kind, chunk.data)
    return decoded[0] if decoded else None


def _make_text_chunk(keyword: str, text: str) -> PngChunk:
    if not keyword or len(keyword) > 79:
        raise CardFormatError("PNG tEXt keyword length must be between 1 and 79 characters.")
    keyword_bytes = keyword.encode("latin-1")
    text_bytes = text.encode("latin-1")
    return PngChunk(b"tEXt", keyword_bytes + b"\x00" + text_bytes)


def save_card_to_png(
    source_path: os.PathLike[str] | str,
    target_path: os.PathLike[str] | str,
    card: dict[str, Any],
    chunk_keyword: str = "chara",
) -> None:
    if chunk_keyword not in CARD_CHUNK_NAMES:
        raise CardFormatError("Card chunk keyword must be 'chara' or 'ccv3'.")

    chunks = read_png_chunks(source_path)
    encoded = encode_card_json(card)
    new_chunk = _make_text_chunk(chunk_keyword, encoded)
    output_chunks: list[PngChunk] = []
    inserted = False

    for chunk in chunks:
        if _chunk_keyword(chunk) in CARD_CHUNK_NAMES:
            continue
        if chunk.kind == b"IEND" and not inserted:
            output_chunks.append(new_chunk)
            inserted = True
        output_chunks.append(chunk)

    if not inserted:
        raise CardFormatError("Invalid PNG: could not insert metadata before IEND.")

    source = Path(source_path).resolve()
    target = Path(target_path).resolve()
    if source == target:
        fd, tmp_name = tempfile.mkstemp(prefix=target.stem + ".", suffix=".tmp.png", dir=str(target.parent))
        os.close(fd)
        tmp_path = Path(tmp_name)
        try:
            write_png_chunks(tmp_path, output_chunks)
            os.replace(tmp_path, target)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()
    else:
        write_png_chunks(target, output_chunks)


def _empty_v2_card() -> dict[str, Any]:
    return {
        "spec": "chara_card_v2",
        "spec_version": "2.0",
        "data": {
            "name": "",
            "description": "",
            "personality": "",
            "scenario": "",
            "first_mes": "",
            "mes_example": "",
            "creator_notes": "",
            "system_prompt": "",
            "post_history_instructions": "",
            "alternate_greetings": [],
            "tags": [],
            "creator": "",
            "character_version": "",
            "extensions": {},
        },
    }


def _empty_v3_card() -> dict[str, Any]:
    return {
        "spec": "chara_card_v3",
        "spec_version": "3.0",
        "data": {
            "name": "",
            "description": "",
            "personality": "",
            "scenario": "",
            "first_mes": "",
            "mes_example": "",
            "creator_notes": "",
            "system_prompt": "",
            "post_history_instructions": "",
            "alternate_greetings": [],
            "tags": [],
            "creator": "",
            "character_version": "",
            "extensions": {},
            "group_only_greetings": [],
        },
    }


def new_card_from_png(path: os.PathLike[str] | str, card_version: str = "v3") -> LoadedCard:
    png_path = Path(path)
    chunks = read_png_chunks(png_path)
    if _card_text_chunks(chunks):
        raise CardFormatError("This PNG already contains character-card metadata. Use Open to edit the existing card.")

    if card_version == "v3":
        card = _empty_v3_card()
        keyword = "ccv3"
    elif card_version == "v2":
        card = _empty_v2_card()
        keyword = "chara"
    else:
        raise CardFormatError("New cards must use Character Card V2 or V3.")

    return LoadedCard(png_path, keyword, card, json.dumps(card, ensure_ascii=False, indent=2))


def normalize_for_editing(card: dict[str, Any]) -> dict[str, Any]:
    normalized = copy.deepcopy(card)
    if not isinstance(normalized.get("data"), dict):
        data = {key: normalized.get(key, "") for key in TEXT_FIELDS}
        for key in LINE_LIST_FIELDS:
            value = normalized.get(key, [])
            data[key] = value if isinstance(value, list) else []
        for key in METADATA_FIELDS:
            data[key] = normalized.get(key, "")
        data["alternate_greetings"] = normalized.get("alternate_greetings", [])
        data["character_book"] = normalized.get("character_book")
        data["extensions"] = normalized.get("extensions", {})
        normalized = {"spec": "chara_card_v2", "spec_version": "2.0", "data": data}

    data = normalized.setdefault("data", {})
    for key in TEXT_FIELDS + METADATA_FIELDS:
        data.setdefault(key, "")
        if data[key] is None:
            data[key] = ""
    for key in LINE_LIST_FIELDS:
        value = data.get(key, [])
        if isinstance(value, str):
            data[key] = [item.strip() for item in value.split(",") if item.strip()]
        elif not isinstance(value, list):
            data[key] = []
    if not isinstance(data.get("alternate_greetings"), list):
        data["alternate_greetings"] = []
    if data.get("extensions") is None:
        data["extensions"] = {}
    return normalized


def _json_dumps_for_box(value: Any) -> str:
    if value is None:
        return ""
    return json.dumps(value, ensure_ascii=False, indent=2)


def _parse_json_box(label: str, value: str, default: Any) -> Any:
    stripped = value.strip()
    if not stripped:
        return copy.deepcopy(default)
    try:
        return json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise CardFormatError(f"{label} is not valid JSON: {exc}") from exc


class CardEditorApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Chub PNG Character Card Editor")
        self.geometry("1040x760")
        self.minsize(860, 620)

        self.source_path: Path | None = None
        self.current_path: Path | None = None
        self.chunk_keyword = "chara"
        self.card = _empty_v2_card()

        self.text_boxes: dict[str, ScrolledText] = {}
        self.entries: dict[str, ttk.Entry] = {}
        self.json_boxes: dict[str, ScrolledText] = {}
        self.raw_box: ScrolledText | None = None
        self.status_var = tk.StringVar(value="Ready. Open a card or create one from an ordinary PNG.")

        self._build_menu()
        self._build_layout()
        self._load_into_form(self.card)

    def _build_menu(self) -> None:
        menu = tk.Menu(self)
        file_menu = tk.Menu(menu, tearoff=False)
        new_menu = tk.Menu(file_menu, tearoff=False)
        new_menu.add_command(label="Character Card V3 (recommended)", command=self.create_v3_card)
        new_menu.add_command(label="Character Card V2", command=self.create_v2_card)
        file_menu.add_cascade(label="New Card from PNG", menu=new_menu)
        file_menu.add_separator()
        file_menu.add_command(label="Open", command=self.open_file, accelerator="Ctrl+O")
        file_menu.add_command(label="Save", command=self.save_file, accelerator="Ctrl+S")
        file_menu.add_command(label="Save As", command=self.save_file_as, accelerator="Ctrl+Shift+S")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.destroy)
        menu.add_cascade(label="File", menu=file_menu)
        self.config(menu=menu)
        self.bind_all("<Control-o>", lambda _event: self.open_file())
        self.bind_all("<Control-s>", lambda _event: self.save_file())
        self.bind_all("<Control-Shift-S>", lambda _event: self.save_file_as())

    def _build_layout(self) -> None:
        toolbar = ttk.Frame(self, padding=(8, 8, 8, 4))
        toolbar.pack(fill=tk.X)
        ttk.Button(toolbar, text="New Card from PNG", command=self.create_v3_card).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(toolbar, text="Open", command=self.open_file).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(toolbar, text="Save", command=self.save_file).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(toolbar, text="Save As", command=self.save_file_as).pack(side=tk.LEFT)
        ttk.Label(toolbar, textvariable=self.status_var).pack(side=tk.LEFT, padx=(14, 0), fill=tk.X, expand=True)

        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        core = ttk.Frame(notebook, padding=8)
        prompts = ttk.Frame(notebook, padding=8)
        metadata = ttk.Frame(notebook, padding=8)
        advanced = ttk.Frame(notebook, padding=8)
        raw = ttk.Frame(notebook, padding=8)

        notebook.add(core, text="Core Fields")
        notebook.add(prompts, text="Prompt Modules")
        notebook.add(metadata, text="Metadata")
        notebook.add(advanced, text="Advanced JSON")
        notebook.add(raw, text="Full JSON Preview")

        self._add_text_grid(
            core,
            (
                ("name", "Name", 3),
                ("description", "Description", 8),
                ("personality", "Personality", 6),
                ("scenario", "Scenario", 6),
                ("first_mes", "First Message", 7),
                ("mes_example", "Example Dialogues", 8),
            ),
        )
        self._add_text_grid(
            prompts,
            (
                ("creator_notes", "Creator Notes", 7),
                ("system_prompt", "System Prompt", 8),
                ("post_history_instructions", "Post-History Instructions", 8),
            ),
        )
        self._add_metadata_tab(metadata)
        self._add_advanced_tab(advanced)

        ttk.Label(raw, text="This preview is regenerated from the form before saving. Unknown fields are preserved in Other data fields JSON.").pack(
            anchor=tk.W
        )
        self.raw_box = ScrolledText(raw, wrap=tk.WORD, height=30, undo=True)
        self.raw_box.pack(fill=tk.BOTH, expand=True, pady=(6, 0))
        ttk.Button(raw, text="Refresh Preview", command=self.refresh_raw_preview).pack(anchor=tk.E, pady=(6, 0))

    def _add_text_grid(self, parent: ttk.Frame, fields: tuple[tuple[str, str, int], ...]) -> None:
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)
        for index, (key, label, height) in enumerate(fields):
            frame = ttk.LabelFrame(parent, text=label, padding=6)
            frame.grid(row=index // 2, column=index % 2, sticky="nsew", padx=5, pady=5)
            parent.rowconfigure(index // 2, weight=1)
            box = ScrolledText(frame, wrap=tk.WORD, height=height, undo=True)
            box.pack(fill=tk.BOTH, expand=True)
            self.text_boxes[key] = box

    def _add_metadata_tab(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        for row, (key, label) in enumerate(
            (
                ("creator", "Creator"),
                ("character_version", "Character Version"),
            )
        ):
            frame = ttk.LabelFrame(parent, text=label, padding=6)
            frame.grid(row=row, column=0, sticky="ew", padx=5, pady=5)
            entry = ttk.Entry(frame)
            entry.pack(fill=tk.X)
            self.entries[key] = entry

        tags_frame = ttk.LabelFrame(parent, text="Tags (one per line)", padding=6)
        tags_frame.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)
        tags_box = ScrolledText(tags_frame, wrap=tk.WORD, height=10, undo=True)
        tags_box.pack(fill=tk.BOTH, expand=True)
        self.text_boxes["tags"] = tags_box
        parent.rowconfigure(2, weight=1)

        greeting_frame = ttk.LabelFrame(parent, text="Alternate Greetings (separate entries with a line containing ---)", padding=6)
        greeting_frame.grid(row=3, column=0, sticky="nsew", padx=5, pady=5)
        greetings_box = ScrolledText(greeting_frame, wrap=tk.WORD, height=12, undo=True)
        greetings_box.pack(fill=tk.BOTH, expand=True)
        self.text_boxes["alternate_greetings_text"] = greetings_box
        parent.rowconfigure(3, weight=1)

    def _add_advanced_tab(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)
        for index, (key, label) in enumerate(
            (
                ("character_book", "Character Book JSON"),
                ("extensions", "Extensions JSON"),
                ("extra_data", "Other data fields JSON"),
                ("envelope_extra", "Top-level extra fields JSON"),
            )
        ):
            frame = ttk.LabelFrame(parent, text=label, padding=6)
            frame.grid(row=index // 2, column=index % 2, sticky="nsew", padx=5, pady=5)
            parent.rowconfigure(index // 2, weight=1)
            box = ScrolledText(frame, wrap=tk.NONE, height=18, undo=True)
            box.pack(fill=tk.BOTH, expand=True)
            self.json_boxes[key] = box

    def _set_box(self, box: ScrolledText, value: str) -> None:
        box.delete("1.0", tk.END)
        box.insert("1.0", value)

    def _get_box(self, box: ScrolledText) -> str:
        return box.get("1.0", tk.END).rstrip("\n")

    def _load_into_form(self, card: dict[str, Any]) -> None:
        self.card = normalize_for_editing(card)
        data = self.card["data"]
        for key in TEXT_FIELDS:
            self._set_box(self.text_boxes[key], str(data.get(key, "") or ""))
        for key in METADATA_FIELDS:
            self.entries[key].delete(0, tk.END)
            self.entries[key].insert(0, str(data.get(key, "") or ""))
        self._set_box(self.text_boxes["tags"], "\n".join(str(item) for item in data.get("tags", [])))
        self._set_box(self.text_boxes["alternate_greetings_text"], "\n---\n".join(str(item) for item in data.get("alternate_greetings", [])))
        self._set_box(self.json_boxes["character_book"], _json_dumps_for_box(data.get("character_book")))
        self._set_box(self.json_boxes["extensions"], _json_dumps_for_box(data.get("extensions", {})))

        extra_data = {key: value for key, value in data.items() if key not in KNOWN_DATA_FIELDS}
        envelope_extra = {key: value for key, value in self.card.items() if key not in {"spec", "spec_version", "data"}}
        self._set_box(self.json_boxes["extra_data"], _json_dumps_for_box(extra_data))
        self._set_box(self.json_boxes["envelope_extra"], _json_dumps_for_box(envelope_extra))
        self.refresh_raw_preview()

    def _form_to_card(self) -> dict[str, Any]:
        card = copy.deepcopy(self.card)
        data = card.setdefault("data", {})
        for key in TEXT_FIELDS:
            data[key] = self._get_box(self.text_boxes[key])
        for key in METADATA_FIELDS:
            data[key] = self.entries[key].get().strip()

        tags_text = self._get_box(self.text_boxes["tags"])
        data["tags"] = [line.strip() for line in tags_text.splitlines() if line.strip()]

        greetings_text = self._get_box(self.text_boxes["alternate_greetings_text"])
        greetings = [part.strip() for part in greetings_text.split("\n---\n") if part.strip()]
        data["alternate_greetings"] = greetings

        character_book = _parse_json_box("Character Book", self._get_box(self.json_boxes["character_book"]), None)
        if character_book is None:
            data.pop("character_book", None)
        else:
            data["character_book"] = character_book
        data["extensions"] = _parse_json_box("Extensions", self._get_box(self.json_boxes["extensions"]), {})

        extra_data = _parse_json_box("Other data fields", self._get_box(self.json_boxes["extra_data"]), {})
        envelope_extra = _parse_json_box("Top-level extra fields", self._get_box(self.json_boxes["envelope_extra"]), {})
        if not isinstance(extra_data, dict):
            raise CardFormatError("Other data fields JSON must be an object.")
        if not isinstance(envelope_extra, dict):
            raise CardFormatError("Top-level extra fields JSON must be an object.")

        for key in list(data.keys()):
            if key not in KNOWN_DATA_FIELDS:
                data.pop(key)
        data.update(extra_data)

        for key in list(card.keys()):
            if key not in {"spec", "spec_version", "data"}:
                card.pop(key)
        card.update(envelope_extra)
        return card

    def refresh_raw_preview(self) -> None:
        if self.raw_box is None:
            return
        try:
            card = self._form_to_card() if self.text_boxes else self.card
            text = json.dumps(card, ensure_ascii=False, indent=2)
        except Exception as exc:
            text = f"Cannot refresh preview: {exc}"
        self._set_box(self.raw_box, text)

    def open_file(self) -> None:
        filename = filedialog.askopenfilename(
            title="Open Chub/SillyTavern PNG card",
            filetypes=(("PNG files", "*.png"), ("All files", "*.*")),
        )
        if not filename:
            return
        try:
            loaded = load_card(filename)
        except Exception as exc:
            messagebox.showerror("Open failed", str(exc))
            return

        self.source_path = loaded.path
        self.current_path = loaded.path
        self.chunk_keyword = loaded.chunk_keyword
        self._load_into_form(loaded.card)
        self.status_var.set(f"Opened: {loaded.path} [{loaded.chunk_keyword}]")

    def create_v3_card(self) -> None:
        self.create_card_from_png("v3")

    def create_v2_card(self) -> None:
        self.create_card_from_png("v2")

    def create_card_from_png(self, card_version: str) -> None:
        filename = filedialog.askopenfilename(
            title=f"Create a Character Card {card_version.upper()} from PNG",
            filetypes=(("PNG files", "*.png"), ("All files", "*.*")),
        )
        if not filename:
            return
        try:
            loaded = new_card_from_png(filename, card_version)
        except Exception as exc:
            messagebox.showerror("New card failed", str(exc))
            return

        self.source_path = loaded.path
        self.current_path = None
        self.chunk_keyword = loaded.chunk_keyword
        self._load_into_form(loaded.card)
        self.status_var.set(
            f"New Character Card {card_version.upper()} from: {loaded.path.name}. Use Save or Save As to choose a new file."
        )

    def save_file(self) -> None:
        if self.current_path is None or self.source_path is None:
            self.save_file_as()
            return
        self._save_to(self.current_path)

    def save_file_as(self) -> None:
        if self.source_path is None:
            messagebox.showinfo("Open a PNG first", "Open an existing PNG card first; this tool edits card metadata inside that image.")
            return
        filename = filedialog.asksaveasfilename(
            title="Save Chub/SillyTavern PNG card as",
            defaultextension=".png",
            initialdir=str(self.source_path.parent),
            initialfile=self.current_path.name if self.current_path else f"{self.source_path.stem}_card.png",
            filetypes=(("PNG files", "*.png"), ("All files", "*.*")),
        )
        if not filename:
            return
        self._save_to(Path(filename))

    def _save_to(self, target_path: os.PathLike[str] | str) -> None:
        try:
            card = self._form_to_card()
            save_card_to_png(self.source_path, target_path, card, self.chunk_keyword)
        except Exception as exc:
            messagebox.showerror("Save failed", str(exc))
            return

        self.current_path = Path(target_path)
        self.source_path = Path(target_path)
        self.card = card
        self.refresh_raw_preview()
        self.status_var.set(f"Saved: {self.current_path} [{self.chunk_keyword}]")
        messagebox.showinfo("Saved", f"Saved PNG card:\n{self.current_path}")


def main() -> None:
    app = CardEditorApp()
    app.mainloop()


if __name__ == "__main__":
    main()
