import json
import re
from src.utils.prompt_builder import build_narrator_prompt
from src.utils.logger import get_logger

logger = get_logger(__name__)


class Narrator:
    """Narrator AI for free-text mode."""

    def __init__(self, llm_client):
        self.llm = llm_client

    def narrate(
        self,
        user_input: str,
        state,
        memories: list,
        active_rules: list,
        character_card: dict,
        world_setting: str,
        social_manager=None,
        holidays=None,
    ) -> tuple[str, dict]:
        prompt = build_narrator_prompt(
            state=state,
            memories=memories,
            active_rules=active_rules,
            user_input=user_input,
            character_card=character_card,
            world_setting=world_setting,
            social_manager=social_manager,
            holidays=holidays,
        )

        logger.info(f"Narrator: processing '{user_input[:50]}...'")
        response = self.llm.chat(system_prompt="", user_prompt=prompt)

        narrative, changes = self._parse_response(response)
        logger.info(f"Narrator: {len(narrative)} chars narrative, changes={changes}")
        return narrative, changes

    def _parse_response(self, response: str) -> tuple[str, dict]:
        narrative = response
        changes = {}

        change_patterns = [
            r'【状态变化】\s*\n?\s*(\{[^}]+\})',
            r'\[状态变化\]\s*\n?\s*(\{[^}]+\})',
            r'状态变化[：:]\s*\n?\s*(\{[^}]+\})',
        ]

        for pattern in change_patterns:
            match = re.search(pattern, narrative, re.DOTALL)
            if match:
                json_str = match.group(1)
                try:
                    changes = json.loads(json_str)
                    narrative = narrative[:match.start()].strip()
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse state changes JSON: {json_str[:100]}")
                break

        narrative = re.sub(r'\n*【状态变化】.*$', '', narrative, flags=re.DOTALL).strip()
        narrative = re.sub(r'\n*\[状态变化\].*$', '', narrative, flags=re.DOTALL).strip()

        valid_keys = {"energy", "mood", "money", "hunger", "sleep_drive",
                      "libido", "health", "cleanliness", "appearance"}
        filtered = {}
        for k, v in changes.items():
            if k in valid_keys and isinstance(v, (int, float)):
                filtered[k] = int(v)

        return narrative, filtered
