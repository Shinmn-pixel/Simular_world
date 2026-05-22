from openai import OpenAI
from config.settings import LLM_CONFIG
from src.utils.logger import get_logger

logger = get_logger(__name__)


class LLMClient:
    """OpenAI-compatible LLM client supporting third-party base_url."""

    def __init__(self, model: str = None):
        self.client = OpenAI(
            api_key=LLM_CONFIG["api_key"],
            base_url=LLM_CONFIG["base_url"],
        )
        self.model = model or LLM_CONFIG["model"]
        self.temperature = LLM_CONFIG["temperature"]
        self.max_tokens = LLM_CONFIG["max_tokens"]

    def chat(self, system_prompt: str, user_prompt: str = "") -> str:
        """Send a chat completion request. Returns the response text."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt or system_prompt})

        logger.info(f"Calling LLM [{self.model}]...")

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            content = response.choices[0].message.content
            logger.info(f"LLM response received ({len(content)} chars)")
            return content
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise


def get_llm_client(model: str = None) -> LLMClient:
    return LLMClient(model=model)
