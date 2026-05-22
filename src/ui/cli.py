from src.ui.base import UIBase


class CLI(UIBase):
    """Command-line UI implementation."""

    def display_narrative(self, text: str):
        print(f"\n{text}\n")

    def display_state(self, state):
        gdt = state.get_datetime()
        holidays = []  # Will be injected when available
        self.display_datetime(gdt, holidays)
        self.display_location(state.current_location, [], {})

        print("┌" + "─" * 56 + "┐")
        self._stat_row("⚡ 体力", state.energy)
        self._stat_row("😊 心情", state.mood)
        self._stat_row("💰 金钱", 0, f"{state.money}元")
        self._stat_row("🍖 饱腹", state.hunger)
        self._stat_row("😴 睡眠", state.sleep_drive)
        self._stat_row("🔥 性欲", state.libido)
        self._stat_row("❤️ 健康", state.health)
        self._stat_row("🧼 洁净", state.cleanliness)
        self._stat_row("💄 容貌", state.appearance)
        if state.is_menstruating:
            print(f"│  🩸 生理期第{state.menstrual_day}天".ljust(51) + "│")
        print("└" + "─" * 56 + "┘")
        print()

    def _stat_row(self, label: str, value: int, extra: str = None):
        bar = self._bar(value, 16)
        if extra:
            display = f"{label}: {bar} {extra}"
        else:
            display = f"{label}: {bar} {value:>3}/100"
        # Pad to account for CJK characters (each takes ~2 monospace widths)
        print(f"│  {display}".ljust(55) + "│")

    def _bar(self, value: int, width: int = 14) -> str:
        value = max(0, min(100, value))
        filled = int(value / 100 * width)
        if value > 60:
            char = "█"
        elif value > 30:
            char = "▓"
        else:
            char = "░"
        return char * filled + " " * (width - filled)

    def get_choice(self, choices: list) -> int:
        print()
        for i, choice in enumerate(choices):
            text = choice.get("text", choice) if isinstance(choice, dict) else str(choice)
            hint = ""
            if isinstance(choice, dict):
                risk = choice.get("risk", "")
                hint = choice.get("hint", "")
                risk_tag = f"[{risk}]" if risk else ""
                print(f"  [{i + 1}] {risk_tag} {text}")
            else:
                print(f"  [{i + 1}] {text}")
            if hint:
                print(f"      💡 {hint}")

        while True:
            try:
                raw = input("\n请输入选项编号：").strip()
                idx = int(raw) - 1
                if 0 <= idx < len(choices):
                    return idx
                print(f"请输入 1 到 {len(choices)} 之间的数字")
            except ValueError:
                print("请输入有效数字")

    def get_free_text(self, prompt: str = "") -> str:
        if prompt:
            print(f"\n{prompt}")
        print("(输入 /help 查看可用命令)")
        return input("> ").strip()

    def show_message(self, text: str):
        print(text)

    def get_input(self, prompt: str) -> str:
        return input(prompt)

    def check_command(self, text: str) -> str | None:
        text = text.strip().lower()
        if text.startswith("/"):
            cmd = text.split()[0]
            valid = ["/mode", "/next", "/save", "/help", "/quit", "/status",
                     "/move", "/interact", "/skip", "/relationship", "/outfit"]
            if cmd in valid:
                return cmd
        return None

    # === v4 new display methods ===

    def display_location(self, location_name: str, npcs_present: list, loc_info: dict = None):
        if loc_info is None:
            loc_info = {}
        desc = loc_info.get("description", "")
        objects = loc_info.get("objects", [])
        actions = loc_info.get("actions", [])

        line = f"📍 {location_name}"
        if desc:
            line += f" — {desc}"
        print(line)

        if npcs_present:
            npc_str = "、".join(f"{n.name if hasattr(n, 'name') else n} (❤️{n.affection:+d})"
                               if hasattr(n, 'affection') else str(n) for n in npcs_present)
            print(f"   👥 在场：{npc_str}")

    def display_relationship_table(self, npcs: list):
        print("\n┌" + "─" * 46 + "┐")
        print("│  👥 NPC好感度一览".ljust(41) + "│")
        print("├" + "─" * 46 + "┤")
        if not npcs:
            print("│  （暂无社交关系）".ljust(41) + "│")
        else:
            sorted_npcs = sorted(npcs, key=lambda n: abs(n.affection) if hasattr(n, 'affection') else 0, reverse=True)
            for n in sorted_npcs:
                if hasattr(n, 'affection'):
                    emoji = "❤️" if n.affection >= 50 else "💛" if n.affection >= 0 else "💔"
                    line = f"{emoji} {n.name}（{n.relationship_label()}） {n.affection:+d}"
                    print(f"│  {line}".ljust(41) + "│")
        print("└" + "─" * 46 + "┘")

    def display_outfit(self, outfit, gender: str = "男"):
        if hasattr(outfit, 'to_display'):
            print(outfit.to_display(gender))
        elif isinstance(outfit, dict):
            from src.systems.clothing import Outfit
            print(Outfit.from_dict(outfit).to_display(gender))
        print()

    def display_datetime(self, gdt, holidays: list = None):
        if hasattr(gdt, 'to_display'):
            print(f"🕐 {gdt.to_display(holidays)}")
        else:
            print(f"🕐 {gdt}")
