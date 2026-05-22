import json
import os
from dataclasses import dataclass, field, asdict
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Memory:
    day: int
    event: str
    impact: dict = field(default_factory=dict)
    emotional_tag: str = "neutral"  # "positive" / "negative" / "neutral"
    importance: int = 1             # 1-10

    @classmethod
    def from_dict(cls, d: dict) -> "Memory":
        return cls(
            day=d.get("day", 1),
            event=d.get("event", ""),
            impact=d.get("impact", {}),
            emotional_tag=d.get("emotional_tag", "neutral"),
            importance=d.get("importance", 1),
        )

    def to_dict(self) -> dict:
        return asdict(self)


class MemoryStore:
    """Persistent memory storage with retrieval and compression."""

    MAX_MEMORIES = 50
    RECENT_COUNT = 5
    IMPORTANT_COUNT = 3

    def __init__(self, filepath: str):
        self.filepath = filepath
        self._memories: list[Memory] = []
        self._load()

    def _load(self):
        if not os.path.exists(self.filepath):
            return
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._memories = [Memory.from_dict(d) for d in data]
            logger.info(f"Loaded {len(self._memories)} memories")
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Failed to load memories: {e}")
            self._memories = []

    def _save(self):
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump([m.to_dict() for m in self._memories], f, ensure_ascii=False, indent=2)

    def record(self, day: int, event: str, impact: dict = None,
               emotional_tag: str = None, importance: int = None):
        """Add a new memory entry."""
        if impact is None:
            impact = {}

        if emotional_tag is None:
            total = sum(impact.values())
            if total > 0:
                emotional_tag = "positive"
            elif total < 0:
                emotional_tag = "negative"
            else:
                emotional_tag = "neutral"

        if importance is None:
            importance = min(max(abs(v) for v in impact.values()) if impact else 1, 1)
            importance = min(max(importance, 1), 10)

        memory = Memory(
            day=day,
            event=event[:500],  # Truncate long events
            impact=impact,
            emotional_tag=emotional_tag,
            importance=importance,
        )
        self._memories.append(memory)

        # Prune old memories
        if len(self._memories) > self.MAX_MEMORIES:
            self._memories = self._memories[-self.MAX_MEMORIES:]

        self._save()

    def recent(self, n: int = None) -> list[dict]:
        """Get the N most recent memories."""
        if n is None:
            n = self.RECENT_COUNT
        return [m.to_dict() for m in self._memories[-n:]]

    def important(self, n: int = None) -> list[dict]:
        """Get the N most important memories."""
        if n is None:
            n = self.IMPORTANT_COUNT
        sorted_memories = sorted(self._memories, key=lambda m: m.importance, reverse=True)
        return [m.to_dict() for m in sorted_memories[:n]]

    def context_memories(self, recent_n: int = None, important_n: int = None) -> list[dict]:
        """Get memories for AI context: recent + important, deduplicated."""
        if recent_n is None:
            recent_n = self.RECENT_COUNT
        if important_n is None:
            important_n = self.IMPORTANT_COUNT

        recent_list = self._memories[-recent_n:] if self._memories else []
        important_list = sorted(self._memories, key=lambda m: m.importance, reverse=True)[:important_n]

        # Merge, deduplicate by reference, sort by day
        seen_ids = set()
        merged = []
        for m in recent_list + important_list:
            mid = (m.day, m.event[:50])
            if mid not in seen_ids:
                seen_ids.add(mid)
                merged.append(m)
        merged.sort(key=lambda m: m.day)

        return [m.to_dict() for m in merged]

    def compress(self, before_day: int) -> str:
        """Compress memories older than the given day into a summary string."""
        old = [m for m in self._memories if m.day < before_day]
        if not old:
            return ""

        positives = [m for m in old if m.emotional_tag == "positive"]
        negatives = [m for m in old if m.emotional_tag == "negative"]
        neutrals = [m for m in old if m.emotional_tag == "neutral"]

        summary_parts = []
        if positives:
            summary_parts.append(f"发生了{len(positives)}件好事，包括：{positives[-1].event[:80]}")
        if negatives:
            summary_parts.append(f"遭遇了{len(negatives)}件坏事，包括：{negatives[-1].event[:80]}")
        if neutrals:
            summary_parts.append(f"还有{len(neutrals)}件日常琐事")

        # Remove old memories and replace with a summary entry
        self._memories = [m for m in self._memories if m.day >= before_day]
        summary = "过去发生了：" + "；".join(summary_parts) if summary_parts else "过去的日子平淡无奇。"
        self._memories.insert(0, Memory(
            day=before_day - 1,
            event=summary[:500],
            emotional_tag="neutral",
            importance=3,
        ))
        self._save()
        logger.info(f"Compressed {len(old)} memories before day {before_day}")
        return summary

    def all(self) -> list[dict]:
        return [m.to_dict() for m in self._memories]

    def clear(self):
        self._memories = []
        self._save()
