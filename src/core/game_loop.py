import os

from config import settings
from src.core.state_manager import PlayerState
from src.utils.logger import get_logger

logger = get_logger(__name__)


def game_loop(
    state: PlayerState,
    character_card: dict,
    world_setting: str,
    ui,
    narrator,
    planner,
    executor,
    memory_store,
    worldbook,
    social_manager=None,     # v4
    position_manager=None,   # v4
    holidays=None,           # v4
):
    """Main game loop with dual top-level modes and choice sub-modes."""

    mode_label = "自由文字" if settings.GAME_MODE == "free_text" else "剧情选项"
    ui.show_message(f"\n当前模式: {mode_label}")
    ui.show_message("输入 /help 查看可用命令\n")

    while True:
        # Day tick on new day
        if state.turn_in_day == 0:
            state.apply_daily_decay()
            _check_critical_state(state, ui)
            if state.day % 7 == 0 and state.day > 0:
                memory_store.compress(before_day=state.day - 7)

        # Check worldbook rules
        active_rules = worldbook.check(state)

        # Show state
        ui.display_state(state)

        # Update NPC presence based on location
        if social_manager and position_manager:
            _update_npc_presence(state, social_manager, position_manager)

        # Branch by top-level game mode
        if settings.GAME_MODE == "free_text":
            _run_free_text_turn(state, character_card, world_setting, ui,
                                narrator, memory_store, active_rules,
                                social_manager, position_manager, holidays)
        elif settings.GAME_MODE == "choice":
            _run_choice_mode(state, character_card, world_setting, ui,
                             planner, executor, memory_store, active_rules,
                             social_manager, position_manager, holidays)
        else:
            settings.GAME_MODE = "free_text"


# ========== Free-text mode ==========

def _run_free_text_turn(state, character_card, world_setting, ui,
                        narrator, memory_store, active_rules,
                        social_manager, position_manager, holidays):
    user_input = ui.get_free_text("你想做什么？（输入你的行动意图）")
    if not user_input:
        return

    cmd = ui.check_command(user_input)

    # Route /move and /interact to full sub-mode experience (same as choice mode)
    if cmd == "/move":
        if position_manager:
            _run_move_mode(state, character_card, world_setting, ui,
                          None, memory_store, position_manager, social_manager, holidays)
        else:
            ui.show_message("❌ 位置系统未初始化")
        return
    if cmd == "/interact":
        if position_manager and social_manager:
            _run_interact_mode(state, character_card, world_setting, ui,
                              None, memory_store, position_manager, social_manager, holidays)
        else:
            ui.show_message("❌ 位置/社交系统未初始化")
        return

    if cmd:
        _handle_command(cmd, user_input, state, ui, memory_store, social_manager,
                        position_manager, holidays, narrator, character_card, world_setting)
        if cmd == "/quit":
            exit(0)
        return

    try:
        ui.show_message("\n⏳ AI正在构思故事...\n")
        narrative, state_changes = narrator.narrate(
            user_input=user_input, state=state,
            memories=memory_store.context_memories(),
            active_rules=active_rules,
            character_card=character_card,
            world_setting=world_setting,
            social_manager=social_manager,
            holidays=holidays,
        )
        ui.display_narrative(narrative)

        if state_changes:
            state.apply_changes(state_changes)
            ui.show_message(f"\n📊 状态变化: {_format_changes(state_changes)}")

        # Infer time passage from action
        from src.systems.calendar_utils import estimate_action_minutes
        mins = estimate_action_minutes(user_input)
        gdt = state.get_datetime()
        gdt.advance_minutes(mins)
        state.set_datetime(gdt)

        # Cleanliness update based on activity (only if narrator didn't already set it)
        if not state_changes or "cleanliness" not in state_changes:
            from src.systems.cleanliness import activity_from_description
            activity = activity_from_description(user_input)
            if activity in ("active", "heavy"):
                state.cleanliness = max(0, state.cleanliness - 5)
            elif activity == "idle":
                state.cleanliness = min(100, state.cleanliness + 2)

        memory_store.record(
            day=state.day,
            event=f"用户行动: {user_input} | {narrative[:120]}",
            impact=state_changes,
        )

    except Exception as e:
        logger.error(f"Narrator AI error: {e}")
        ui.show_message(f"\n❌ AI调用失败: {e}")
        return

    state.turn_in_day += 1
    if state.turn_in_day >= settings.TURNS_PER_DAY:
        state.day += 1
        state.turn_in_day = 0
        new_gdt = state.get_datetime()
        new_gdt.advance_days(1)
        new_gdt.hour = 8
        new_gdt.minute = 0
        state.set_datetime(new_gdt)
        ui.show_message(f"\n--- 🌅 进入第{state.day}天 ---")


# ========== Choice mode (with sub-modes) ==========

def _run_choice_mode(state, character_card, world_setting, ui,
                     planner, executor, memory_store, active_rules,
                     social_manager, position_manager, holidays):
    """Choice mode entry - lets player pick sub-mode."""

    # Show context-aware options
    ui.show_message("")
    ui.show_message("请选择行动模式：")
    ui.show_message("  📖 [1] 剧情模式 — 让AI生成今天的事件")
    ui.show_message("  🚶 [2] 移动模式 — 移动到其他位置")
    ui.show_message("  🤝 [3] 互动模式 — 与当前位置的NPC或物品互动")
    ui.show_message("  或者输入 /help 查看其他命令")

    raw = ui.get_input("\n请选择 (1/2/3 或命令)：").strip()

    # Check commands
    cmd = ui.check_command(raw)
    if cmd == "/move":
        _run_move_mode(state, character_card, world_setting, ui,
                      None, memory_store, position_manager, social_manager, holidays)
        return
    if cmd == "/interact":
        _run_interact_mode(state, character_card, world_setting, ui,
                          None, memory_store, position_manager, social_manager, holidays)
        return
    if cmd:
        _handle_command(cmd, raw, state, ui, memory_store, social_manager,
                        position_manager, holidays, None, character_card, world_setting)
        if cmd == "/quit":
            exit(0)
        return

    # Parse sub-mode choice
    if raw == "1":
        _run_story_mode(state, character_card, world_setting, ui,
                        planner, executor, memory_store, active_rules,
                        social_manager, holidays)
    elif raw == "2":
        _run_move_mode(state, character_card, world_setting, ui,
                       planner, memory_store, position_manager, social_manager, holidays)
    elif raw == "3":
        _run_interact_mode(state, character_card, world_setting, ui,
                           executor, memory_store, position_manager, social_manager, holidays)
    else:
        ui.show_message("请输入 1、2 或 3")


def _run_story_mode(state, character_card, world_setting, ui,
                    planner, executor, memory_store, active_rules,
                    social_manager, holidays):
    """Original choice mode: AI generates event, player chooses."""
    if not planner or not executor:
        ui.show_message("❌ 剧情模式需要Planner和Executor AI")
        return

    from src.utils.prompt_builder import build_planner_prompt, build_executor_prompt

    try:
        ui.show_message("\n⏳ AI正在生成今日事件...\n")
        event_json = planner.generate_event(
            state=state, memories=memory_store.context_memories(),
            active_rules=active_rules,
            character_card=character_card, world_setting=world_setting,
            social_manager=social_manager, holidays=holidays,
        )

        narrative = executor.render(
            event_json=event_json, state=state, character_card=character_card,
            social_manager=social_manager, holidays=holidays,
        )
        ui.display_narrative(narrative)

        choices = event_json.get("choices", [])
        if not choices:
            ui.show_message("（AI未生成有效选项，跳过今日）")
        else:
            choice_idx = ui.get_choice(choices)
            state.apply_event(event_json, choice_idx)
            chosen = choices[choice_idx]
            impact = chosen.get("impact", {})
            if impact:
                ui.show_message(f"\n📊 状态变化: {_format_changes(impact)}")
            memory_store.record(
                day=state.day,
                event=f"{event_json.get('title', '事件')} → {chosen.get('text', '')}",
                impact=impact,
            )

        # Advance time
        state.day += 1
        state.turn_in_day = 0
        gdt = state.get_datetime()
        gdt.advance_days(1)
        state.set_datetime(gdt)

    except Exception as e:
        logger.error(f"Story mode error: {e}")
        ui.show_message(f"\n❌ AI调用失败: {e}")


def _run_move_mode(state, character_card, world_setting, ui,
                   planner, memory_store, position_manager, social_manager, holidays):
    """Move to a different location."""
    if not position_manager:
        ui.show_message("❌ 位置系统未初始化")
        return

    reachable = position_manager.get_reachable()
    if not reachable:
        ui.show_message("没有可到达的位置")
        return

    ui.show_message(f"\n📍 当前位置：{state.current_location}")
    ui.show_message("可到达的位置：")
    for i, loc_name in enumerate(reachable):
        loc = position_manager.get(loc_name)
        desc = f" — {loc.description}" if loc and loc.description else ""
        ui.show_message(f"  [{i + 1}] {loc_name}{desc}")

    raw = ui.get_input("\n选择目的地（编号）：").strip()
    try:
        idx = int(raw) - 1
        if not (0 <= idx < len(reachable)):
            ui.show_message("无效选择")
            return
    except ValueError:
        ui.show_message("请输入有效数字")
        return

    destination = reachable[idx]
    travel_mins = position_manager.movement_time(destination)

    # AI narrates movement
    if planner:
        from src.utils.prompt_builder import build_move_prompt
        try:
            move_prompt = build_move_prompt(state, destination, character_card, world_setting, holidays)
            move_narrative = planner.llm.chat(system_prompt="", user_prompt=move_prompt)
            ui.display_narrative(move_narrative)
        except Exception:
            ui.show_message(f"你来到了{destination}。")

    # Update position and time
    state.current_location = destination
    gdt = state.get_datetime()
    gdt.advance_minutes(travel_mins)
    state.set_datetime(gdt)
    state.cleanliness = max(0, state.cleanliness - 2)  # minor travel dirt

    ui.show_message(f"✅ 已到达 {destination}（耗时约{travel_mins}分钟）")

    # Show location info and available actions
    loc = position_manager.get(destination)
    if loc:
        ui.display_location(destination, social_manager.present_npcs(destination) if social_manager else [],
                          {"description": loc.description, "objects": loc.objects, "actions": loc.actions})

        # Show location-specific actions
        if loc.actions:
            ui.show_message("\n在此可以：")
            action_choices = [{"text": a, "risk": "", "hint": ""} for a in loc.actions]
            action_choices.append({"text": "返回（不做任何事）", "risk": "", "hint": ""})
            choice_idx = ui.get_choice(action_choices)

            if choice_idx < len(loc.actions):
                action = loc.actions[choice_idx]
                _execute_location_action(state, action, ui, memory_store, social_manager, planner,
                                        character_card, world_setting, holidays)

        memory_store.record(day=state.day, event=f"移动到{destination}", impact={}, importance=1)

    state.turn_in_day += 1


def _run_interact_mode(state, character_card, world_setting, ui,
                       executor, memory_store, position_manager, social_manager, holidays):
    """Interact with NPCs or objects at current location."""
    loc = position_manager.get_current() if position_manager else None

    ui.show_message(f"\n📍 当前位置：{state.current_location}")

    # List NPCs present
    choices = []
    if social_manager:
        present = social_manager.present_npcs(state.current_location)
        for n in present:
            choices.append({
                "text": f"👤 {n.name}（{n.relationship_label()} ❤️{n.affection:+d}）",
                "type": "npc", "npc_name": n.name, "risk": "", "hint": f"{n.personality}" if n.personality else "",
            })

    # List interactive objects
    if loc and loc.objects:
        for obj in loc.objects:
            choices.append({
                "text": f"🧹 {obj}", "type": "object", "object_name": obj, "risk": "", "hint": "",
            })

    choices.append({"text": "返回", "type": "back", "risk": "", "hint": ""})

    if len(choices) == 1:
        ui.show_message("这里没有可互动的人或物")
        return

    ui.show_message("\n选择互动目标：")
    choice_idx = ui.get_choice(choices)
    chosen = choices[choice_idx]

    if chosen.get("type") == "back":
        return
    elif chosen.get("type") == "npc":
        npc_name = chosen["npc_name"]
        _interact_with_npc(state, npc_name, ui, executor, memory_store,
                          social_manager, character_card, holidays)
    elif chosen.get("type") == "object":
        obj_name = chosen["object_name"]
        _interact_with_object(state, obj_name, ui, executor, memory_store,
                             character_card, holidays)

    state.turn_in_day += 1


# ========== Action helpers ==========

def _execute_location_action(state, action, ui, memory_store, social_manager, planner,
                             character_card, world_setting, holidays):
    """Execute a location-specific action."""
    from src.systems.cleanliness import activity_from_description

    changes = {}

    if "洗澡" in action:
        state.cleanliness = min(100, state.cleanliness + 50)
        changes["cleanliness"] = 50
    elif "上厕所" in action:
        changes["mood"] = 5
        state.cleanliness = max(0, state.cleanliness - 3)
    elif "换衣服" in action:
        state.cleanliness = min(100, state.cleanliness + 15)
        changes["cleanliness"] = 15
    elif "换卫生巾" in action:
        changes["mood"] = 5
    elif "睡觉" in action:
        state.sleep_drive = min(100, state.sleep_drive + 60)
        state.energy = min(100, state.energy + 30)
        changes["sleep_drive"] = 60
        changes["energy"] = 30
        state.cleanliness = max(0, state.cleanliness - 8)
        gdt = state.get_datetime()
        gdt.advance_hours(8)
        state.set_datetime(gdt)
    elif "吃饭" in action:
        state.hunger = min(100, state.hunger + 40)
        state.money -= 20
        changes["hunger"] = 40
        changes["money"] = -20
        gdt = state.get_datetime()
        gdt.advance_minutes(30)
        state.set_datetime(gdt)
    elif "做饭" in action:
        state.hunger = min(100, state.hunger + 35)
        changes["hunger"] = 35
        gdt = state.get_datetime()
        gdt.advance_minutes(45)
        state.set_datetime(gdt)
    elif "买东西" in action or "买零食" in action or "买便当" in action:
        state.money -= random_coin(15, 40)
        state.hunger = min(100, state.hunger + 25)
        changes["money"] = -20
        changes["hunger"] = 25
    elif "洗衣服" in action:
        state.cleanliness = min(100, state.cleanliness + 10)
        changes["cleanliness"] = 10

    # Activity-based cleanliness decay
    activity = activity_from_description(action)
    if activity in ("active", "heavy") and "洗澡" not in action:
        state.cleanliness = max(0, state.cleanliness - 3)

    state.clamp()

    # AI narrate the action
    if planner:
        try:
            prompt = f"角色{character_card.get('name', '')}在{state.current_location}{action}。请用1-2句话叙述（第二人称）。"
            narration = planner.llm.chat(system_prompt="", user_prompt=prompt)
            ui.display_narrative(narration)
        except Exception:
            ui.show_message(f"你在{state.current_location}{action}。")

    if changes:
        state.apply_changes(changes)
        ui.show_message(f"📊 状态变化: {_format_changes(changes)}")

    memory_store.record(day=state.day, event=f"在{state.current_location}{action}", impact=changes)


def _interact_with_npc(state, npc_name, ui, executor, memory_store, social_manager, character_card, holidays):
    """Handle NPC interaction."""
    npc = social_manager.get_npc(npc_name)
    if not npc:
        ui.show_message(f"找不到NPC: {npc_name}")
        return

    ui.show_message(f"\n与 {npc_name}（{npc.relationship_label()} ❤️{npc.affection:+d}）互动")
    choices = [
        {"text": "友好聊天", "hint": "好感度小幅提升"},
        {"text": "表达关心", "hint": "好感度提升，关系越亲密效果越好"},
        {"text": "开玩笑/调侃", "hint": "亲友间效果更好，陌生人可能反感"},
        {"text": "冷淡对待", "hint": "好感度下降（关系越深下降越少）"},
        {"text": "返回", "hint": ""},
    ]

    idx = ui.get_choice(choices)
    if idx == 4:
        return

    action_label = choices[idx]["text"]
    affinity_effects = {
        0: (5, 12),   # 友好聊天
        1: (8, 18),   # 表达关心
        2: (-3, 8),   # 开玩笑
        3: (-15, -5), # 冷淡对待
    }

    low, high = affinity_effects.get(idx, (0, 0))
    delta = random_coin(low, high)
    actual_delta = social_manager.modify_affection(npc_name, delta,
                                                   state.appearance, state.cleanliness)

    # AI narrate
    if executor:
        try:
            gdt = state.get_datetime()
            prompt = f"""角色{character_card.get('name', '')}在{state.current_location}与{npc_name}（{npc.relationship_label()}）进行了互动：{action_label}。当前好感度{npc.affection:+d}（变化{actual_delta:+d}）。
请用1-2句话叙述这次互动（第二人称"你"）。"""
            narration = executor.llm.chat(system_prompt="", user_prompt=prompt)
            ui.display_narrative(narration)
        except Exception:
            ui.show_message(f"你与{npc_name}进行了互动：{action_label}。好感度{actual_delta:+d}")

    ui.show_message(f"👥 {npc_name}好感度：{actual_delta:+d}（当前{npc.affection:+d}）")
    memory_store.record(day=state.day, event=f"与{npc_name}互动：{action_label}",
                       impact={}, importance=5)


def _interact_with_object(state, obj_name, ui, executor, memory_store, character_card, holidays):
    """Handle object interaction."""
    if executor:
        try:
            prompt = f"角色在{state.current_location}使用了{obj_name}。请用1句话叙述（第二人称）。"
            narration = executor.llm.chat(system_prompt="", user_prompt=prompt)
            ui.display_narrative(narration)
        except Exception:
            ui.show_message(f"你使用了{obj_name}。")

    gdt = state.get_datetime()
    gdt.advance_minutes(10)
    state.set_datetime(gdt)
    memory_store.record(day=state.day, event=f"使用了{obj_name}", impact={}, importance=1)


# ========== NPC presence ==========

def _update_npc_presence(state, social_manager, position_manager):
    """Update which NPCs are present based on current location and time."""
    gdt = state.get_datetime()
    current_loc = position_manager.get_current()
    if not current_loc:
        return

    for npc in social_manager.all():
        # Simple rule: NPCs appear at locations matching their context
        if current_loc.location_type in ("private_room", "common_room", "utility") and \
           current_loc.parent == "家中":
            if npc.relationship_type in ("亲人", "伴侣"):
                if random_coin(1, 10) > 3:  # 70% chance at home
                    npc.is_present = True
                    npc.current_location = state.current_location
                    continue

        # Public places: small random chance
        if current_loc.location_type == "public" and \
           random_coin(1, 100) <= 10:  # 10% chance
            npc.is_present = True
            npc.current_location = state.current_location
            continue

        npc.is_present = False
        npc.current_location = ""


# ========== Command handler ==========

def _handle_command(cmd: str, raw_input: str, state, ui, memory_store,
                    social_manager, position_manager, holidays,
                    narrator, character_card, world_setting):
    parts = raw_input.strip().split(maxsplit=1)
    arg = parts[1] if len(parts) > 1 else ""

    if cmd == "/mode":
        new_mode = arg.strip().lower()
        if new_mode in ("free", "free_text", "自由", "自由文字"):
            settings.GAME_MODE = "free_text"
            ui.show_message("✅ 已切换到【自由文字模式】")
        elif new_mode in ("choice", "选项", "剧情选项"):
            settings.GAME_MODE = "choice"
            ui.show_message("✅ 已切换到【剧情选项模式】")
        else:
            ui.show_message("用法: /mode free 或 /mode choice")

    elif cmd == "/skip":
        try:
            n = int(arg) if arg else 1
            from src.systems.time_skip import skip_days
            summary = skip_days(n, state, memory_store, worldbook, social_manager)
            ui.show_message(summary)
        except ValueError:
            ui.show_message("用法: /skip <天数>  例如 /skip 7")

    elif cmd == "/relationship":
        if social_manager:
            ui.display_relationship_table(social_manager.all())
        else:
            ui.show_message("❌ 社交系统未初始化")

    elif cmd == "/outfit":
        outfit = state.get_outfit()
        ui.display_outfit(outfit, state.gender)

    elif cmd == "/next":
        state.day += 1
        state.turn_in_day = 0
        gdt = state.get_datetime()
        gdt.advance_days(1)
        state.set_datetime(gdt)
        ui.show_message(f"⏩ 已跳到第{state.day}天")

    elif cmd == "/save":
        save_game(state)
        ui.show_message("💾 游戏已存档")

    elif cmd == "/status":
        ui.display_state(state)

    elif cmd == "/help":
        ui.show_message("""
可用命令：
  /mode free       - 切换到自由文字模式
  /mode choice     - 切换到剧情选项模式
  /move            - 移动到其他位置
  /interact        - 与当前位置NPC/物品互动
  /skip <天数>     - 跳过N天（AI自动结算）
  /relationship    - 查看所有NPC好感度
  /outfit          - 查看当前服装
  /next            - 手动推进到下一天
  /save            - 保存游戏进度
  /status          - 显示完整状态面板
  /quit            - 退出游戏
  /help            - 显示此帮助
        """)


def _format_changes(changes: dict) -> str:
    labels = {
        "energy": "体力", "mood": "心情", "money": "金钱",
        "hunger": "饱腹度", "sleep_drive": "睡眠欲",
        "libido": "性欲", "health": "健康", "cleanliness": "洁净度",
        "appearance": "容貌",
    }
    parts = []
    for attr, delta in changes.items():
        if delta == 0:
            continue
        label = labels.get(attr, attr)
        sign = "+" if delta > 0 else ""
        parts.append(f"{label}{sign}{delta}")
    return "  ".join(parts) if parts else "无变化"


def _check_critical_state(state: PlayerState, ui):
    warnings = []
    if state.hunger <= 0:
        warnings.append("⚠️ 你极度饥饿，再不吃东西可能会饿死！")
    if state.sleep_drive <= 0:
        warnings.append("⚠️ 你已严重缺觉，随时可能昏倒！")
    if state.health <= 0:
        warnings.append("💀 你的健康值降为0，请尽快就医！")
    if state.energy <= 0:
        warnings.append("⚠️ 你筋疲力尽，无法继续行动")
    if state.cleanliness <= 5:
        warnings.append("🦠 你浑身脏污，NPC纷纷避而远之")
    for w in warnings:
        ui.show_message(w)


def random_coin(low: int, high: int) -> int:
    import random
    return random.randint(low, high)


def save_game(state: PlayerState):
    filepath = os.path.join(settings.SAVE_DIR, "player_state.json")
    state.save(filepath)
    logger.info(f"Game saved to {filepath}")


def load_game() -> PlayerState | None:
    filepath = os.path.join(settings.SAVE_DIR, "player_state.json")
    if os.path.exists(filepath):
        return PlayerState.load(filepath)
    return None
