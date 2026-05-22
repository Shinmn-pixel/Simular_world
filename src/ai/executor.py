from src.utils.prompt_builder import build_executor_prompt
from src.utils.logger import get_logger

logger = get_logger(__name__)


class Executor:
    """Executor AI for choice mode."""

    def __init__(self, llm_client):
        self.llm = llm_client

    def render(self, event_json: dict, state, character_card: dict,
               social_manager=None, holidays=None) -> str:
        prompt = build_executor_prompt(
            event_json=event_json, state=state, character_card=character_card,
            social_manager=social_manager, holidays=holidays,
        )

        logger.info(f"Executor: rendering event '{event_json.get('title', '?')}'")
        narrative = self.llm.chat(system_prompt="", user_prompt=prompt)
        logger.info(f"Executor: {len(narrative)} chars rendered")
        return narrative
