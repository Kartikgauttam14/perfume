"""Knowledge loader and data preparation for Mansam SSOT chunks."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Set, Tuple
from src.config import settings
from src.models import Chunk, GalaxyCategory, ProductCard

logger = logging.getLogger(__name__)


class KnowledgeLoader:
    """Loads, validates, and deduplicates knowledge chunks from JSONL."""

    def __init__(self, file_path: Path = settings.CHUNKS_PATH):
        self.file_path = file_path

    def load_chunks(self) -> List[Chunk]:
        """Reads JSONL file and returns deduplicated Chunk objects."""
        if not self.file_path.exists():
            raise FileNotFoundError(f"Knowledge file not found at: {self.file_path}")

        chunks: List[Chunk] = []
        seen_ids: Set[str] = set()

        with open(self.file_path, "r", encoding="utf-8") as f:
            for line_idx, line in enumerate(f, 1):
                raw = line.strip()
                if not raw:
                    continue
                chunk = self._parse_and_dedup(raw, line_idx, seen_ids)
                if chunk:
                    chunks.append(chunk)

        logger.info("Successfully loaded %d chunks from %s", len(chunks), self.file_path.name)
        return chunks

    def _parse_and_dedup(self, line_text: str, line_idx: int, seen_ids: Set[str]) -> Chunk:
        """Parses a single JSON line and ensures chunk ID uniqueness."""
        data = json.loads(line_text)
        cid = data.get("chunk_id", f"chunk_{line_idx}")

        if cid in seen_ids:
            # Suffix with row/part to prevent vector DB overwrites
            loc = data.get("location", {})
            suffix = loc.get("row") or loc.get("page") or line_idx
            cid = f"{cid}::r{suffix}"

        seen_ids.add(cid)
        return Chunk(
            chunk_id=cid,
            source=data.get("source", "unknown"),
            type=data.get("type", "general"),
            text=data.get("text", ""),
            location=data.get("location", {}),
            metadata=data.get("metadata", {}),
        )

    def load_galaxy_categories(self) -> List[GalaxyCategory]:
        """Returns the official Mansam Galaxy 7-mood emotional classification."""
        return [
            GalaxyCategory(
                id="nobility",
                name_en="Nobility",
                name_ar="النبل",
                description_en="Regal presence and majestic heritage of royal Arabian courts.",
                description_ar="الهيبة والسيادة المستوحاة من القصور الملكية الأصيلة.",
                fragrances=["Safaa Al Nada", "Al Hawa Ghallab", "Mamlakati", "Al Shagaf Al Ahmar"],
                olfactive_profile="Pure Cambodian Oud, Amber, Royal Rose & Rare Spices",
            ),
            GalaxyCategory(
                id="pride",
                name_en="Pride",
                name_ar="الفخر",
                description_en="Bold assertion of identity, cultural elevation, and sovereignty.",
                description_ar="تجسيد للاعتزاز بالهوية العربية والتألق الفريد.",
                fragrances=["Sarhan", "Shatha Biladi"],
                olfactive_profile="Milky Sandalwood, Bergamot, Smoked Amber & White Musk",
            ),
            GalaxyCategory(
                id="pleasure",
                name_en="Pleasure",
                name_ar="البهجة",
                description_en="Luminous moments of pure aesthetic charm and floral rapture.",
                description_ar="لحظات السعادة والبهجة الفاخرة مع باقات الزهور الملكية.",
                fragrances=["Aala Taj Warda", "Hadeeth Al Rooh", "Fakhamat Al Warda", "Aala Sathi Al Qamar"],
                olfactive_profile="Bulgarian Rose, White Rum Accord, Pink Pepper, Vanilla Orchid",
            ),
            GalaxyCategory(
                id="passion",
                name_en="Passion",
                name_ar="الشغف",
                description_en="Intense emotional currents, bold allure, and romantic depth.",
                description_ar="عواطف جياشة وجاذبية تأسر الحواس.",
                fragrances=["Thawrat Al Ahasseess", "Khatiiiiiir", "Qublat Ward"],
                olfactive_profile="Warm Patchouli, Amberwood, Velvety Musk, Dark Rose",
            ),
            GalaxyCategory(
                id="generosity",
                name_en="Generosity",
                name_ar="الكرم",
                description_en="Open-hearted Arabian hospitality and bountiful warmth.",
                description_ar="كرم الضيافة العربية الأصيلة ودفء اللقاء.",
                fragrances=["Amtar", "Horr Fi Al Riyah"],
                olfactive_profile="Benzoin Resin, Soft Almond, White Lily, Golden Vanilla",
            ),
            GalaxyCategory(
                id="happiness",
                name_en="Happiness",
                name_ar="السعادة",
                description_en="Serene optimism, starry desert night dreams, and tranquility.",
                description_ar="تفاؤل وانسجام ساحر تحت نجوم الصحراء.",
                fragrances=["Nasseem Al Ward", "Tahta Al Noujoum"],
                olfactive_profile="Neroli, Orange Blossom, Jasmine, Smoky Patchouli",
            ),
            GalaxyCategory(
                id="desire",
                name_en="Desire",
                name_ar="الرغبة",
                description_en="Seductive, mysterious magnetism woven from white florals and oud.",
                description_ar="سحر خفي وجاذبية لا تُقاوم مع نفحات العود والياسمين.",
                fragrances=["Safaa Al Nada", "Min Ana"],
                olfactive_profile="Narcissus, Night-blooming Jasmine, Hint of Aged Oud",
            ),
        ]
