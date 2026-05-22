import json
import os
import re
from src.utils.logger import get_logger

logger = get_logger(__name__)


class Worldbook:
    """World rule engine with trigger matching.
    Supports three trigger types:
    - state trigger:  "energy < 30"
    - keyword trigger: "keyword: 医院"
    - time trigger:    "day % 7 == 0"
    """

    def __init__(self, rules_file: str = None):
        self.rules: list[dict] = []
        self.rules_file = rules_file
        if rules_file and os.path.exists(rules_file):
            self._load()

    def _load(self):
        try:
            with open(self.rules_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.rules = data if isinstance(data, list) else data.get("rules", [])
            logger.info(f"Loaded {len(self.rules)} worldbook rules")
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Failed to load rules: {e}")
            self.rules = []

    def _save(self):
        if not self.rules_file:
            return
        os.makedirs(os.path.dirname(self.rules_file), exist_ok=True)
        with open(self.rules_file, "w", encoding="utf-8") as f:
            json.dump(self.rules, f, ensure_ascii=False, indent=2)

    def check(self, state, context_text: str = "") -> list[dict]:
        """Check all rules against current state and context.
        Returns list of matched rules, sorted by priority descending.
        """
        matched = []
        for rule in self.rules:
            trigger = rule.get("trigger", "")
            if self._match_trigger(trigger, state, context_text):
                matched.append(rule)

        matched.sort(key=lambda r: r.get("priority", 0), reverse=True)
        if matched:
            logger.info(f"Matched {len(matched)} rules: {[r.get('trigger', '')[:40] for r in matched]}")
        return matched

    def _match_trigger(self, trigger: str, state, context_text: str) -> bool:
        """Evaluate a single trigger against current state."""
        if not trigger:
            return False

        trigger = trigger.strip()

        # Keyword trigger: "keyword: xxx"
        if trigger.startswith("keyword:"):
            keyword = trigger.split(":", 1)[1].strip()
            return keyword in context_text if context_text else False

        # Time trigger: contains "day" and no state attributes
        if "day" in trigger and not any(attr in trigger for attr in
            ["energy", "mood", "money", "hunger", "sleep_drive", "libido", "health",
             "is_menstruating", "menstrual_day", "cycle_day", "age"]):
            try:
                # Build safe eval environment with only 'day' accessible
                return self._safe_eval(trigger, {"day": state.day})
            except Exception:
                return False

        # State trigger: evaluate against state attributes
        state_dict = {
            "energy": state.energy,
            "mood": state.mood,
            "money": state.money,
            "hunger": state.hunger,
            "sleep_drive": state.sleep_drive,
            "libido": state.libido,
            "health": state.health,
            "is_menstruating": state.is_menstruating,
            "menstrual_day": state.menstrual_day,
            "cycle_day": state.cycle_day,
            "day": state.day,
            "age": state.age,
            "turn_in_day": state.turn_in_day,
        }

        try:
            return self._safe_eval(trigger, state_dict)
        except Exception as e:
            logger.warning(f"Failed to evaluate trigger '{trigger}': {e}")
            return False

    def _safe_eval(self, expr: str, context: dict) -> bool:
        """Safely evaluate a boolean expression with given context variables."""
        # Only allow: variable names, numbers, comparison operators, logical operators, parentheses
        allowed_pattern = r'^[\w\s<>=!&\|\(\)\.\-\+\*/%:,]+$'
        if not re.match(allowed_pattern, expr):
            return False

        # Restrict builtins
        safe_globals = {"__builtins__": {
            "True": True, "False": False, "None": None,
            "abs": abs, "min": min, "max": max, "len": len,
            "int": int, "float": float, "str": str, "bool": bool,
        }}
        try:
            result = eval(expr, safe_globals, context)
            return bool(result)
        except Exception:
            return False

    def add_rule(self, trigger: str, effect: str, priority: int = 5) -> dict:
        """Add a new rule. Returns the added rule."""
        rule = {"trigger": trigger, "effect": effect, "priority": priority}
        self.rules.append(rule)
        self._save()
        return rule

    def remove_rule(self, trigger: str):
        """Remove rules matching the given trigger."""
        self.rules = [r for r in self.rules if r.get("trigger") != trigger]
        self._save()

    def list_rules(self) -> list[dict]:
        return list(self.rules)
