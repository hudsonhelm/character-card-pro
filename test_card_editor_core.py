import base64
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from chub_card_editor import (
    PngChunk,
    _make_text_chunk,
    load_card,
    normalize_for_editing,
    save_card_to_png,
    write_png_chunks,
)


def make_card(name: str, description: str) -> dict:
    return {
        "spec": "chara_card_v2",
        "spec_version": "2.0",
        "data": {
            "name": name,
            "description": description,
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


def encode_card(card: dict) -> str:
    return base64.b64encode(json.dumps(card, ensure_ascii=False).encode("utf-8")).decode("ascii")


def make_png(path: Path, card: dict, keyword: str = "chara") -> None:
    chunks = [
        PngChunk(
            b"IHDR",
            b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00",
        ),
        _make_text_chunk(keyword, encode_card(card)),
        PngChunk(b"IDAT", b"\x78\x9c\x63\x60\x00\x00\x00\x02\x00\x01"),
        PngChunk(b"IEND", b""),
    ]
    write_png_chunks(path, chunks)


class CardEditorCoreTests(unittest.TestCase):
    def test_load_and_save_chinese_card(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            png_path = Path(tmp) / "card.png"
            card = make_card("测试角色", "中文描述 and English text")
            make_png(png_path, card)

            loaded = load_card(png_path)
            self.assertEqual(loaded.chunk_keyword, "chara")
            self.assertEqual(loaded.card["data"]["name"], "测试角色")

            edited = normalize_for_editing(loaded.card)
            edited["data"]["scenario"] = "补充场景"
            save_card_to_png(png_path, png_path, edited, loaded.chunk_keyword)

            reloaded = load_card(png_path)
            self.assertEqual(reloaded.card["data"]["scenario"], "补充场景")

    def test_ccv3_takes_priority_over_chara(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            png_path = Path(tmp) / "card.png"
            v2 = make_card("old", "old")
            v3 = {"spec": "chara_card_v3", "spec_version": "3.0", "data": {"name": "new", "description": "v3"}}
            chunks = [
                PngChunk(b"IHDR", b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"),
                _make_text_chunk("chara", encode_card(v2)),
                _make_text_chunk("ccv3", encode_card(v3)),
                PngChunk(b"IDAT", b"\x78\x9c\x63\x60\x00\x00\x00\x02\x00\x01"),
                PngChunk(b"IEND", b""),
            ]
            write_png_chunks(png_path, chunks)

            loaded = load_card(png_path)
            self.assertEqual(loaded.chunk_keyword, "ccv3")
            self.assertEqual(loaded.card["data"]["name"], "new")


if __name__ == "__main__":
    unittest.main()
