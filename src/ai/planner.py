import json
import re
from src.utils.prompt_builder import build_planner_prompt
from src.utils.logger import get_logger

logger = get_logger(__name__)


class Planner:
    """Planner AI for choice mode."""

    FALLBACK_EVENT = {
        "event_type": "random", "title": "平凡的一天",
        "description_seed": "今天似乎没什么特别的事发生",
        "mood": "neutral",
        "choices": [{"text": "按部就班地度过这一天", "risk": "low", "hint": "顺其自然", "impact": {}}],
    }

    def __init__(self, llm_client):
        self.llm = llm_client

    def generate_event(
        self, state, memories: list, active_rules: list,
        character_card: dict, world_setting: str,
        social_manager=None, holidays=None,
    ) -> dict:
        prompt = build_planner_prompt(
            state=state, memories=memories, active_rules=active_rules,
            character_card=character_card, world_setting=world_setting,
            social_manager=social_manager, holidays=holidays,
        )

        logger.info("Planner: generating event...")
        response = self.llm.chat(system_prompt="", user_prompt=prompt)
        event = self._parse_response(response)
        logger.info(f"Planner: event '{event.get('title', '?')}' with {len(event.get('choices', []))} choices")
        return event

    def _parse_response(self, response: str) -> dict:
        match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', response, re.DOTALL)
        if match:
            json_str = match.group(1)
        else:
            match = re.search(r'\{[\s\S]*\}', response)
            json_str = match.group(0) if match else response

        try:
            event = json.loads(json_str)
            if "choices" not in event or not isinstance(event["choices"], list) or len(event["choices"]) == 0:
                raise ValueError("Invalid choices")
            return event
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse planner response: {e}")
            return dict(self.FALLBACK_EVENT)
