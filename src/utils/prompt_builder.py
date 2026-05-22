from src.core.state_manager import PlayerState


def _build_shared_context(state, character_card, world_setting, memories, active_rules,
                          social_manager=None, holidays=None) -> str:
    """Build the shared context block injected into all AI prompts."""
    parts = []

    # Time
    gdt = state.get_datetime()
    parts.append(f"【时间】{gdt.to_display(holidays)}")

    # Location
    parts.append(f"【位置】你目前在：{state.current_location}")

    # Outfit
    outfit = state.get_outfit()
    outfit_prompt = outfit.to_prompt(state.gender)
    parts.append(f"【服装】{outfit_prompt}")

    # Cleanliness & appearance
    parts.append(f"【洁净度】{state.cleanliness}/100")
    eff_beauty = state.appearance
    parts.append(f"【容貌】{eff_beauty}/100")
    if state.gender == "女":
        ba = state.body_attributes
        parts.append(f"【体型】{ba.get('height', 170)}cm, {ba.get('cup_size', '')}罩杯, {ba.get('body_type', '标准')}身材")
    else:
        ba = state.body_attributes
        parts.append(f"【体型】{ba.get('height', 170)}cm, {ba.get('body_type', '标准')}身材")

    # NPC context
    if social_manager and hasattr(social_manager, 'npc_context_for_prompt'):
        npc_ctx = social_manager.npc_context_for_prompt(state.current_location)
        parts.append(f"【社交】{npc_ctx}")

    return "\n".join(parts)


def build_narrator_prompt(
    state: PlayerState,
    memories: list,
    active_rules: list,
    user_input: str,
    character_card: dict,
    world_setting: str,
    social_manager=None,
    holidays=None,
) -> str:
    phys_desc = state.get_physiological_description()
    memory_text = _format_memories(memories)
    rules_text = _format_rules(active_rules)
    shared_ctx = _build_shared_context(state, character_card, world_setting,
                                       memories, active_rules, social_manager, holidays)

    menstruation_line = ""
    if state.is_menstruating:
        menstruation_line = f"⚠️ 你正处于生理期第{state.menstrual_day}天。"

    prompt = f"""你是一个AI叙事引擎，负责驱动一个人生模拟器的故事。

【角色信息】
你叫{character_card.get('name', state.name)}，{character_card.get('age', state.age)}岁，{character_card.get('gender', state.gender)}性。
生日：{character_card.get('birthday', '未知')}。
职业：{character_card.get('job', state.job)}。社会阶层：{character_card.get('social_class', '工薪')}。
背景：{character_card.get('background', state.background)}。
性格：{character_card.get('personality', state.personality)}。

【世界设定】
{world_setting}

{shared_ctx}

【基础状态】
体力：{state.energy}/100  心情：{state.mood}/100  金钱：{state.money}元
饱腹度：{state.hunger}/100  睡眠欲：{state.sleep_drive}/100
性欲：{state.libido}/100  健康：{state.health}/100
{menstruation_line}

【身体感受】
{phys_desc}

【近期记忆】
{memory_text}

【当前生效的世界规则】
{rules_text}

---
玩家（你）的意图或行动：
"{user_input}"

请你以**第二人称**（"你"）叙述接下来发生的故事。写作要求：
1. 故事必须与玩家的意图一致，但可以适当展开细节和意外发展
2. 自然地融入【身体感受】中的生理状态
3. 自然地融入【服装】和【位置】的当前状态
4. 如果【社交】中有在场人物，应在叙事中适当提及
5. 叙事控制在150-400字
6. 保持沉浸式的文学性叙述

在叙事之后，必须用以下格式标注状态变化（只包含实际发生变化的属性）：
【状态变化】
{{"money": -15, "hunger": +30, "cleanliness": -5}}"""

    return prompt


def build_planner_prompt(
    state: PlayerState,
    memories: list,
    active_rules: list,
    character_card: dict,
    world_setting: str,
    social_manager=None,
    holidays=None,
) -> str:
    phys_desc = state.get_physiological_description()
    memory_text = _format_memories(memories)
    rules_text = _format_rules(active_rules)
    shared_ctx = _build_shared_context(state, character_card, world_setting,
                                       memories, active_rules, social_manager, holidays)

    menstruation_line = ""
    if state.is_menstruating:
        menstruation_line = f"⚠️ 生理期第{state.menstrual_day}天。"

    prompt = f"""你是一个AI事件生成器（Planner），负责为人生模拟器生成每日事件。

【角色】{character_card.get('name', state.name)}，{character_card.get('age', state.age)}岁，{character_card.get('gender', state.gender)}性。
职业：{character_card.get('job', state.job)}。性格：{character_card.get('personality', state.personality)}。

【世界设定】{world_setting}

{shared_ctx}

【基础状态】
体力：{state.energy}/100  心情：{state.mood}/100  金钱：{state.money}元
饱腹度：{state.hunger}/100  睡眠欲：{state.sleep_drive}/100
性欲：{state.libido}/100  健康：{state.health}/100
{menstruation_line}

【身体感受】{phys_desc}
【记忆】{memory_text}
【规则】{rules_text}

请生成今天发生的事件。返回严格JSON格式：
```json
{{
  "event_type": "work|random|health|social|money|food|rest|physiological|medical",
  "title": "事件标题",
  "description_seed": "事件简述",
  "mood": "neutral|positive|negative|tense",
  "choices": [
    {{
      "text": "选项描述",
      "risk": "low|medium|high",
      "hint": "可能的结果提示",
      "impact": {{"energy": 0, "mood": 0, "money": 0, "hunger": 0, "sleep_drive": 0, "libido": 0, "health": 0, "cleanliness": 0}}
    }}
  ]
}}
```

要求：
1. 事件类型应匹配当前状态
2. 根据【位置】生成符合该场景的事件
3. 如果【社交】中有在场人物，优先涉及社交互动
4. 提供2-4个选项
5. impact中加入cleanliness变化（如运动/外出降洁净度，洗澡升洁净度）
6. 只返回JSON，不要额外文字"""

    return prompt


def build_executor_prompt(
    event_json: dict,
    state: PlayerState,
    character_card: dict,
    social_manager=None,
    holidays=None,
) -> str:
    gdt = state.get_datetime()
    outfit = state.get_outfit()

    prompt = f"""你是一个AI叙事引擎，请将以下事件渲染成沉浸式的故事文本。

【角色】{character_card.get('name', state.name)}，{character_card.get('age', state.age)}岁，{character_card.get('gender', state.gender)}性。
【时间】{gdt.to_display(holidays)}
【位置】{state.current_location}
【服装】{outfit.to_prompt(state.gender)}

【事件数据】
{event_json}

【当前状态】
体力：{state.energy}/100  心情：{state.mood}/100  金钱：{state.money}元

请以第二人称叙事（"你"），将此事件渲染成150-300字的生动故事。
自然地融入服装、位置和时间的描述。
同时格式化选项列表，按原顺序输出。
直接输出故事文本和选项，不要输出JSON。"""

    return prompt


def build_move_prompt(
    state: PlayerState,
    destination: str,
    character_card: dict,
    world_setting: str,
    holidays=None,
) -> str:
    """Prompt for move mode narration."""
    gdt = state.get_datetime()
    outfit = state.get_outfit()

    prompt = f"""你是一个AI叙事引擎。请叙述角色移动的过程。

【角色】{character_card.get('name', state.name)}
【当前时间】{gdt.to_display(holidays)}
【服装】{outfit.to_prompt(state.gender)}
【出发地】{state.current_location}
【目的地】{destination}

请用1-2句话叙述这次移动过程（第二人称"你"）。
简单直接即可，不需要过多文学修饰。"""

    return prompt


def _format_memories(memories: list) -> str:
    if not memories:
        return "（暂无重要记忆）"
    lines = []
    for m in memories[-5:]:
        if isinstance(m, dict):
            lines.append(f"- 第{m.get('day', '?')}天: {m.get('event', m.get('content', ''))}")
        else:
            lines.append(f"- {str(m)}")
    return "\n".join(lines) if lines else "（暂无重要记忆）"


def _format_rules(rules: list) -> str:
    if not rules:
        return "（当前无特殊规则生效）"
    lines = []
    for r in rules:
        if isinstance(r, dict):
            lines.append(f"- [{r.get('priority', '?')}] {r.get('effect', str(r))}")
        else:
            lines.append(f"- {str(r)}")
    return "\n".join(lines)
