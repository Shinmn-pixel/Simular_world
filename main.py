import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from config import settings
from src.core.state_manager import PlayerState
from src.core.game_loop import game_loop, load_game, save_game
from src.ui.cli import CLI
from src.utils.character_creator import (
    create_character, save_character_card, load_character_card, save_initial_npcs, card_to_prompt
)
from src.ai.llm_client import get_llm_client
from src.ai.narrator import Narrator
from src.ai.planner import Planner
from src.ai.executor import Executor
from src.memory.memory_store import MemoryStore
from src.world.worldbook import Worldbook
from src.systems.social import SocialManager, NPC
from src.systems.position import PositionManager
from src.systems.calendar_utils import load_holidays, GameDateTime
from src.systems.clothing import Outfit
from src.utils.logger import get_logger

logger = get_logger(__name__)


def main():
    ui = CLI()

    ui.show_message("=" * 50)
    ui.show_message("     🧠 AI驱动人生模拟器 v0.3 (MVP)")
    ui.show_message("=" * 50)

    # --- Character setup ---
    character_card = load_character_card(settings.CHARACTER_CARD_PATH)
    is_new_game = False

    if character_card and character_card.get("name"):
        ui.show_message(f"\n检测到已有角色: {character_card['name']}")
        choice = ui.get_input("是否使用已有角色？(y/n)：").strip().lower()
        if choice not in ("y", "yes", "是", ""):
            character_card = None

    if not character_card or not character_card.get("name"):
        character_card = create_character(ui)
        save_character_card(character_card, settings.CHARACTER_CARD_PATH)
        # Save initial NPCs
        npcs = character_card.get("_npcs", [])
        if npcs:
            save_initial_npcs(npcs, settings.NPCS_PATH)
        is_new_game = True

    # --- Load subsystems ---
    holidays = load_holidays(settings.HOLIDAYS_PATH, settings.HOLIDAY_COUNTRY)
    world_setting = _load_world_setting()

    # --- Social manager ---
    social_manager = SocialManager(settings.NPCS_PATH)
    # If new game and NPCs were saved, reload
    if is_new_game and character_card.get("_npcs"):
        social_manager = SocialManager(settings.NPCS_PATH)

    # --- Position manager ---
    position_manager = PositionManager(settings.LOCATIONS_PATH)

    # --- Memory store ---
    memory_store = MemoryStore(settings.MEMORIES_PATH)

    # --- Worldbook ---
    worldbook = Worldbook(settings.RULES_PATH)

    # --- Load or create state ---
    state = load_game()
    if state is None or is_new_game:
        state = PlayerState(
            name=character_card["name"],
            gender=character_card["gender"],
            age=character_card["age"],
            birthday=character_card.get("birthday", "1月1日"),
            job=character_card.get("job", "无业"),
            social_class=character_card.get("social_class", "工薪"),
            background=character_card.get("background", ""),
            personality=character_card.get("personality", ""),
            appearance=character_card.get("appearance", 50),
            body_attributes=character_card.get("body_attributes", {}),
            current_location=character_card.get("initial_location", "家中卧室"),
        )
        # Set initial outfit
        outfit_dict = character_card.get("_outfit", {})
        if outfit_dict:
            state.set_outfit(outfit_dict)
        else:
            state.set_outfit(Outfit.default_outfit(state.gender))

        # Set initial datetime (Aug 1, 2026 08:00)
        gdt = GameDateTime(year=2026, month=8, day=1, hour=8, minute=0)
        state.set_datetime(gdt)

        ui.show_message("\n开始全新游戏！")

    ui.show_message(f"\n✅ 记忆系统：{len(memory_store.all())}条记忆")
    ui.show_message(f"✅ 社交系统：{len(social_manager.all())}个NPC")
    ui.show_message(f"✅ 世界书：{len(worldbook.list_rules())}条规则")
    ui.show_message(f"✅ 位置系统：{len(position_manager.locations)}个位置")
    ui.show_message(f"✅ 日历系统：{len(holidays)}个节假日")

    # --- Initialize AI ---
    ui.show_message("正在初始化AI连接...")
    try:
        narrator_llm = get_llm_client(model=settings.NARRATOR_MODEL)
        narrator = Narrator(narrator_llm)

        planner_llm = get_llm_client(model=settings.PLANNER_MODEL)
        executor_llm = get_llm_client(model=settings.EXECUTOR_MODEL)
        planner = Planner(planner_llm)
        executor = Executor(executor_llm)

        ui.show_message(f"✅ AI已连接")
        ui.show_message(f"   Narrator: {settings.NARRATOR_MODEL}")
        ui.show_message(f"   Planner:  {settings.PLANNER_MODEL}")
        ui.show_message(f"   Executor: {settings.EXECUTOR_MODEL}")
        ui.show_message(f"   端点: {settings.LLM_CONFIG['base_url']}")
    except Exception as e:
        ui.show_message(f"\n❌ AI初始化失败: {e}")
        ui.show_message("请检查 .env 文件中的配置")
        return

    # --- Start ---
    ui.show_message(f"\n{'=' * 50}")
    ui.show_message(f"  角色: {character_card['name']}")
    ui.show_message(f"  年龄: {character_card['age']}岁 | 性别: {character_card['gender']}")
    ui.show_message(f"  职业: {character_card.get('job', '无业')}")
    ui.show_message(f"  位置: {state.current_location}")
    ui.show_message(f"  模式: {'自由文字' if settings.GAME_MODE == 'free_text' else '剧情选项'}")
    ui.show_message(f"{'=' * 50}")

    try:
        game_loop(
            state=state,
            character_card=character_card,
            world_setting=world_setting,
            ui=ui,
            narrator=narrator,
            planner=planner,
            executor=executor,
            memory_store=memory_store,
            worldbook=worldbook,
            social_manager=social_manager,
            position_manager=position_manager,
            holidays=holidays,
        )
    except KeyboardInterrupt:
        ui.show_message("\n\n正在保存游戏...")
        save_game(state)
        ui.show_message("👋 再见！")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        ui.show_message(f"\n❌ 发生错误: {e}")
        save_game(state)
        ui.show_message("游戏已自动保存。")


def _load_world_setting() -> str:
    if os.path.exists(settings.WORLD_PROMPT_PATH):
        with open(settings.WORLD_PROMPT_PATH, "r", encoding="utf-8") as f:
            return f.read().strip()
    return "一个虚构的现代都市世界，时间背景为2026年。"


if __name__ == "__main__":
    main()
