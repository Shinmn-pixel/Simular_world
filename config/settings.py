import os
from dotenv import load_dotenv

load_dotenv()

LLM_CONFIG = {
    "api_key": os.getenv("OPENAI_API_KEY", "sk-xxxx"),
    "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    "model": os.getenv("LLM_MODEL", "gpt-4o-mini"),
    "temperature": 0.8,
    "max_tokens": 1024,
}

PLANNER_MODEL = os.getenv("PLANNER_MODEL", LLM_CONFIG["model"])
EXECUTOR_MODEL = os.getenv("EXECUTOR_MODEL", LLM_CONFIG["model"])
NARRATOR_MODEL = os.getenv("NARRATOR_MODEL", LLM_CONFIG["model"])

GAME_MODE = os.getenv("GAME_MODE", "free_text")  # "free_text" | "choice"
TURNS_PER_DAY = int(os.getenv("TURNS_PER_DAY", "5"))
HOLIDAY_COUNTRY = os.getenv("HOLIDAY_COUNTRY", "CN")  # CN / US / JP / ALL

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
CONFIG_DIR = os.path.dirname(__file__)
SAVE_DIR = os.path.join(PROJECT_ROOT, "data", "save")
SYSTEMS_DIR = os.path.join(PROJECT_ROOT, "src", "systems")

CHARACTER_CARD_PATH = os.path.join(CONFIG_DIR, "character_card.json")
WORLD_PROMPT_PATH = os.path.join(CONFIG_DIR, "world_prompt.txt")
LOCATIONS_PATH = os.path.join(CONFIG_DIR, "locations.json")
HOLIDAYS_PATH = os.path.join(CONFIG_DIR, "holidays.json")
RULES_PATH = os.path.join(PROJECT_ROOT, "src", "world", "rules.json")
MEMORIES_PATH = os.path.join(SAVE_DIR, "memories.json")
NPCS_PATH = os.path.join(SAVE_DIR, "npcs.json")
