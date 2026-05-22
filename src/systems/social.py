from dataclasses import dataclass, field, asdict
import json
import os
import random
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class NPC:
    name: str
    gender: str = "男"
    age: int = 25
    relationship_type: str = "陌生人"  # "伴侣"/"亲人"/"亲友"/"朋友"/"陌生人"
    subtype: str = ""                   # "哥们"/"闺蜜"/"子女"/"父母"/"男友"/"女友"
    affection: int = 0                  # -100 ~ 100
    is_present: bool = False
    current_location: str = ""
    personality: str = ""
    appearance: str = ""
    backstory: str = ""

    def relationship_decay_factor(self) -> float:
        """Closer relationship → less impact from negative interactions."""
        if self.relationship_type in ("伴侣", "亲人"):
            return 0.2
        if self.relationship_type == "亲友":
            return 0.3
        if self.relationship_type == "朋友":
            return 0.5
        return 1.0

    def relationship_label(self) -> str:
        if self.subtype:
            return f"{self.relationship_type}·{self.subtype}"
        return self.relationship_type

    def affection_emoji(self) -> str:
        if self.affection >= 80:
            return "❤️❤️"
        if self.affection >= 50:
            return "❤️"
        if self.affection >= 20:
            return "💛"
        if self.affection >= 0:
            return "🤝"
        if self.affection >= -20:
            return "😐"
        return "💔"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "NPC":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class SocialManager:
    """Manages all NPC relationships."""

    def __init__(self, filepath: str = None):
        self.npcs: list[NPC] = []
        self.filepath = filepath
        if filepath and os.path.exists(filepath):
            self._load()

    def _load(self):
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.npcs = [NPC.from_dict(d) for d in data]
            logger.info(f"Loaded {len(self.npcs)} NPCs")
        except Exception as e:
            logger.warning(f"Failed to load NPCs: {e}")
            self.npcs = []

    def _save(self):
        if not self.filepath:
            return
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump([n.to_dict() for n in self.npcs], f, ensure_ascii=False, indent=2)

    def add_npc(self, npc: NPC):
        self.npcs.append(npc)
        self._save()

    def remove_npc(self, name: str):
        self.npcs = [n for n in self.npcs if n.name != name]
        self._save()

    def get_npc(self, name: str) -> NPC | None:
        for n in self.npcs:
            if n.name == name:
                return n
        return None

    def present_npcs(self, location: str = None) -> list[NPC]:
        """Get NPCs present at the given location (or any if None)."""
        result = []
        for n in self.npcs:
            if location is None:
                if n.is_present:
                    result.append(n)
            elif n.is_present and n.current_location == location:
                result.append(n)
        return result

    def modify_affection(self, name: str, delta: int,
                         player_appearance: int = 50,
                         player_cleanliness: int = 80) -> int:
        """Modify affection for an NPC. Returns actual delta applied."""
        npc = self.get_npc(name)
        if not npc:
            return 0

        actual = delta
        if delta < 0:
            actual = int(delta * npc.relationship_decay_factor())

        # Appearance bonus for positive interactions
        if delta > 0 and player_appearance > 70:
            actual += random.randint(1, 3)

        # Cleanliness modifier
        if player_cleanliness < 30:
            if delta > 0:
                actual = int(actual * 0.5)
            else:
                actual = int(actual * 1.3)
        elif player_cleanliness > 80 and delta > 0:
            actual = int(actual * 1.2)

        npc.affection = max(-100, min(100, npc.affection + actual))
        self._save()
        return actual

    def relationship_summary(self) -> str:
        """Generate a concise relationship summary for AI prompts."""
        lines = []
        by_type = {}
        for n in self.npcs:
            t = n.relationship_type
            if t not in by_type:
                by_type[t] = []
            by_type[t].append(f"{n.name}({n.relationship_label()} ❤️{n.affection:+d})")
        for t in ["伴侣", "亲人", "亲友", "朋友", "陌生人"]:
            if t in by_type:
                lines.append(f"{t}：{'、'.join(by_type[t])}")
        return "\n".join(lines) if lines else "暂无社交关系"

    def npc_context_for_prompt(self, location: str = None) -> str:
        """Generate NPC context for AI prompt injection."""
        present = self.present_npcs(location)
        parts = []
        if present:
            parts.append("在场人物：" + "、".join(
                f"{n.name}({n.relationship_label()} ❤️{n.affection:+d})" for n in present
            ))
        # Also list important relationships even if not present
        important = [n for n in self.npcs if n.relationship_type in ("伴侣", "亲人") and n not in present]
        if important:
            parts.append("重要关系（不在场）：" + "、".join(
                f"{n.name}({n.relationship_label()} ❤️{n.affection:+d})" for n in important
            ))
        return "\n".join(parts) if parts else "（独自一人）"

    def all(self) -> list[NPC]:
        return list(self.npcs)
