import random
from src.utils.logger import get_logger

logger = get_logger(__name__)


def skip_days(
    n: int,
    state,
    memory_store,
    worldbook,
    social_manager,
    narrator=None,
) -> str:
    """Skip N days. Auto-calculate state changes and return a summary string.

    If narrator is provided, also generates an AI summary. Otherwise uses
    deterministic rule-based calculation.
    """

    if n <= 0:
        return "跳过的天数必须大于0"

    summary_lines = []
    summary_lines.append(f"\n⏩ 跳过 {n} 天（第{state.day}天 → 第{state.day + n}天）")
    summary_lines.append("─" * 40)

    total_money_spent = 0
    total_health_change = 0
    key_events = []
    days_menstruated = 0
    affection_changes = {}

    for i in range(n):
        # Daily decay
        state.apply_daily_decay()

        # Money: daily living expenses
        daily_cost = random.randint(50, 150)
        state.money -= daily_cost
        total_money_spent += daily_cost

        # Health tracking
        total_health_change += 0  # tracked via state changes

        # Cleanliness decay
        from src.systems.cleanliness import daily_cleanliness_decay
        state.cleanliness = daily_cleanliness_decay(state.cleanliness, "normal")

        # Time advance
        state.game_datetime.advance_days(1)
        state.day += 1

        # Menstruation tracking
        if state.is_menstruating:
            days_menstruated += 1

        # Check worldbook rules for important triggers
        active_rules = worldbook.check(state) if worldbook else []
        for rule in active_rules:
            if rule.get("priority", 0) >= 15:
                key_events.append(f"第{state.day}天：{rule['effect'][:60]}")

        # Auto-handle basic needs
        if state.hunger < 10:
            state.hunger += random.randint(30, 60)
            state.money -= random.randint(20, 40)
            key_events.append(f"第{state.day}天：极度饥饿，外出就餐")

        if state.sleep_drive < 10:
            state.sleep_drive += random.randint(40, 70)
            key_events.append(f"第{state.day}天：筋疲力尽，睡了很长时间")

        # Social decay: slight affection drop for not contacting
        if social_manager:
            for npc in social_manager.all():
                if npc.relationship_type in ("伴侣", "亲友"):
                    decay = -random.randint(0, 1)
                    if decay != 0:
                        social_manager.modify_affection(npc.name, decay,
                                                        state.appearance,
                                                        state.cleanliness)
                        if npc.name not in affection_changes:
                            affection_changes[npc.name] = 0
                        affection_changes[npc.name] += decay

        # Memory recording (compressed)
        memory_store.record(
            day=state.day,
            event=f"[跳过] 第{state.day}天日常",
            impact={},
            importance=1,
        )

    # Build summary
    summary_lines.append(f"💰 日常开销：-{total_money_spent}元")
    summary_lines.append(f"🕐 当前时间：{state.game_datetime.to_display()}")

    if days_menstruated > 0:
        summary_lines.append(f"🩸 其中经期占{days_menstruated}天")

    if affection_changes:
        lines = []
        for name, delta in affection_changes.items():
            lines.append(f"{name}好感度{delta:+d}")
        summary_lines.append(f"👥 社交变化：{'、'.join(lines)}")

    if key_events:
        summary_lines.append("📌 重要节点：")
        for ev in key_events[-5:]:  # Show at most 5
            summary_lines.append(f"  · {ev}")

    summary_lines.append("─" * 40)

    # Optional AI summary via narrator
    if narrator and key_events:
        try:
            ai_summary = narrator.llm.chat(
                system_prompt="你是一个游戏摘要生成器。请用2-3句话简洁总结以下时间跨越期间发生的事。",
                user_prompt=f"角色在{n}天内经历了以下事件：\n" + "\n".join(key_events) +
                           f"\n当前状态：金钱{state.money}元 体力{state.energy} 心情{state.mood}\n请生成一个简洁的跳过摘要。",
            )
            summary_lines.append(f"📝 AI摘要：{ai_summary}")
        except Exception:
            pass

    return "\n".join(summary_lines)
