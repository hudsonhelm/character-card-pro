import base64
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from chub_card_editor import (
    CardFormatError,
    PngChunk,
    _make_text_chunk,
    load_card,
    new_card_from_png,
    normalize_for_editing,
    read_png_chunks,
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


def make_png(path: Path, card: dict | None = None, keyword: str = "chara") -> None:
    chunks = [
        PngChunk(
            b"IHDR",
            b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00",
        ),
    ]
    if card is not None:
        chunks.append(_make_text_chunk(keyword, encode_card(card)))
    chunks.extend(
        [
            PngChunk(b"tEXt", b"Comment\x00preserve me"),
            PngChunk(b"IDAT", b"\x78\x9c\x63\x60\x00\x00\x00\x02\x00\x01"),
            PngChunk(b"IEND", b""),
        ]
    )
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

    def test_create_v3_card_from_ordinary_png_without_changing_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source_path = Path(tmp) / "portrait.png"
            target_path = Path(tmp) / "portrait_card.png"
            make_png(source_path)
            source_bytes = source_path.read_bytes()
            source_chunks = read_png_chunks(source_path)

            loaded = new_card_from_png(source_path)
            self.assertEqual(loaded.chunk_keyword, "ccv3")
            self.assertEqual(loaded.card["spec"], "chara_card_v3")
            self.assertEqual(loaded.card["spec_version"], "3.0")
            self.assertEqual(loaded.card["data"]["group_only_greetings"], [])

            loaded.card["data"]["name"] = "New Character"
            save_card_to_png(source_path, target_path, loaded.card, loaded.chunk_keyword)

            self.assertEqual(source_path.read_bytes(), source_bytes)
            reloaded = load_card(target_path)
            self.assertEqual(reloaded.card["data"]["name"], "New Character")
            target_non_card_chunks = [chunk for chunk in read_png_chunks(target_path) if chunk.kind != b"tEXt" or not chunk.data.startswith(b"ccv3\x00")]
            self.assertEqual(target_non_card_chunks, source_chunks)

    def test_create_v2_card_from_ordinary_png(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source_path = Path(tmp) / "portrait.png"
            make_png(source_path)

            loaded = new_card_from_png(source_path, "v2")

            self.assertEqual(loaded.chunk_keyword, "chara")
            self.assertEqual(loaded.card["spec"], "chara_card_v2")
            self.assertEqual(loaded.card["spec_version"], "2.0")

    def test_new_card_rejects_png_that_already_contains_card_data(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            png_path = Path(tmp) / "card.png"
            make_png(png_path, make_card("Existing", "Keep me"))

            with self.assertRaisesRegex(CardFormatError, "already contains"):
                new_card_from_png(png_path)

    def test_unknown_fields_survive_edit_and_save(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            png_path = Path(tmp) / "card.png"
            card = make_card("Existing", "Unknown fields")
            card["vendor_top_level"] = {"keep": True}
            card["data"]["vendor_data"] = [1, 2, 3]
            card["data"]["extensions"]["vendor/example"] = {"enabled": True}
            make_png(png_path, card)

            loaded = load_card(png_path)
            edited = normalize_for_editing(loaded.card)
            edited["data"]["description"] = "Edited"
            save_card_to_png(png_path, png_path, edited, loaded.chunk_keyword)

            reloaded = load_card(png_path).card
            self.assertEqual(reloaded["vendor_top_level"], {"keep": True})
            self.assertEqual(reloaded["data"]["vendor_data"], [1, 2, 3])
            self.assertEqual(reloaded["data"]["extensions"]["vendor/example"], {"enabled": True})


if __name__ == "__main__":
    unittest.main()
