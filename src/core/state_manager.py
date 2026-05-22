from dataclasses import dataclass, field, asdict
import random
import json
import os


# Forward reference helper
def _default_game_datetime():
    from src.systems.calendar_utils import GameDateTime
    return GameDateTime()


@dataclass
class PlayerState:
    # === 基础三维 ===
    energy: int = 100
    mood: int = 70
    money: int = 500

    # === 生理需求 ===
    hunger: int = 80
    sleep_drive: int = 90
    libido: int = 50
    health: int = 100

    # === v4 新增系统 ===
    cleanliness: int = 80
    appearance: int = 50             # 容貌度 0-100

    # === 角色身份 ===
    name: str = ""
    gender: str = "男"
    age: int = 25
    birthday: str = ""               # "4月28日"
    job: str = "无业"
    social_class: str = "工薪"       # 工薪/中产/富裕/精英
    background: str = ""
    personality: str = ""

    # === 体型外貌（NSFW数值） ===
    body_attributes: dict = field(default_factory=lambda: {
        "height": 170,
        "weight": 60,
        "cup_size": "",
        "genital_length": 0,
        "body_hair": "中等",
        "body_type": "标准",
        "skin_tone": "自然肤色",
    })

    # === 生理周期（女性） ===
    is_menstruating: bool = False
    menstrual_day: int = 0
    cycle_day: int = 0

    # === 时间系统 ===
    day: int = 1
    turn_in_day: int = 0

    # === 位置系统 ===
    current_location: str = "家中卧室"

    # === 服装系统（存储为dict，通过outfit属性存取） ===
    _outfit: dict = field(default_factory=lambda: {
        "hairstyle": "", "accessories": [], "makeup": "",
        "bra": "", "underwear": "", "top_inner": "", "top_outer": "",
        "jacket": "", "bottom": "", "skirt_hem": "",
        "socks": "", "shoes": "",
    })

    def get_outfit(self):
        from src.systems.clothing import Outfit
        return Outfit.from_dict(self._outfit)

    def set_outfit(self, outfit):
        from src.systems.clothing import Outfit
        if isinstance(outfit, Outfit):
            self._outfit = outfit.to_dict()
        elif isinstance(outfit, dict):
            self._outfit = outfit

    def get_datetime(self):
        from src.systems.calendar_utils import GameDateTime
        return GameDateTime.from_dict(self._game_datetime)

    def set_datetime(self, gdt):
        from src.systems.calendar_utils import GameDateTime
        if isinstance(gdt, GameDateTime):
            self._game_datetime = gdt.to_dict()
        elif isinstance(gdt, dict):
            self._game_datetime = gdt

    @property
    def game_datetime(self):
        return self.get_datetime()

    # Store datetime as dict for JSON compatibility
    _game_datetime: dict = field(default_factory=lambda: {
        "year": 2026, "month": 8, "day": 1, "hour": 8, "minute": 0,
    })

    # ===== Methods =====

    def clamp(self):
        for attr in ["energy", "mood", "hunger", "sleep_drive", "libido", "health", "cleanliness", "appearance"]:
            val = getattr(self, attr)
            if isinstance(val, (int, float)):
                setattr(self, attr, max(0, min(100, int(val))))

    _last_decay_day: int = 0

    def apply_daily_decay(self):
        if self.day <= self._last_decay_day:
            return
        self._last_decay_day = self.day

        self.hunger -= random.randint(15, 25)
        self.sleep_drive -= random.randint(20, 30)
        self.libido += random.randint(5, 15)
        self.energy += 5
        if self.sleep_drive > 70:
            self.energy += 10

        # Cleanliness decay
        self.cleanliness -= random.randint(5, 12)

        # Menstrual cycle (female only)
        if self.gender == "女":
            self.cycle_day += 1
            if self.cycle_day > 28:
                self.cycle_day = 1
            if 1 <= self.cycle_day <= 7:
                self.is_menstruating = True
                self.menstrual_day = self.cycle_day
            else:
                self.is_menstruating = False
                self.menstrual_day = 0

        self._apply_physiological_linkage()
        self.clamp()

    def _apply_physiological_linkage(self):
        """Cross-effect rules between physiological systems."""
        if self.hunger < 30:
            self.energy -= 10
            self.mood -= 5
        if self.hunger < 10:
            self.health -= 5
        if self.sleep_drive < 30:
            self.energy -= 15
            self.mood -= 8
        if self.sleep_drive < 10:
            self.health -= 3
        if self.libido > 80:
            self.mood -= 5
        if self.libido > 95:
            self.energy -= 3
        if self.is_menstruating:
            self.energy -= 15
            self.mood -= 10
            if self.menstrual_day <= 3:
                self.health -= 2
        if self.health < 40:
            self.energy -= 3
            self.mood -= 3
            self.hunger -= 3
            self.sleep_drive -= 3
            self.libido -= 3
        if self.mood < 20:
            self.energy -= 5
        if self.cleanliness < 20:
            self.mood -= 3

    def apply_changes(self, changes: dict):
        valid_keys = {
            "energy", "mood", "money", "hunger", "sleep_drive",
            "libido", "health", "cleanliness", "appearance",
        }
        for attr, delta in changes.items():
            if attr in valid_keys and isinstance(delta, (int, float)):
                setattr(self, attr, getattr(self, attr, 0) + int(delta))
        self.clamp()

    def apply_event(self, event_json: dict, choice_idx: int):
        choices = event_json.get("choices", [])
        if 0 <= choice_idx < len(choices):
            impact = choices[choice_idx].get("impact", {})
            self.apply_changes(impact)

    def get_physiological_description(self) -> str:
        parts = []

        if self.hunger < 10:
            parts.append("你饿得头晕眼花，再不吃饭可能就要晕倒了")
        elif self.hunger < 30:
            parts.append("你的胃在咕咕叫，饥饿感挥之不去")
        elif self.hunger < 50:
            parts.append("你开始感到有些饿了")

        if self.sleep_drive < 10:
            parts.append("你眼皮沉重得几乎睁不开，随时可能昏睡过去")
        elif self.sleep_drive < 30:
            parts.append("你感到极度疲惫，哈欠连天")
        elif self.sleep_drive < 50:
            parts.append("你有点困了，想打个盹")

        if self.libido > 95:
            parts.append("一股难以抑制的焦躁在你体内涌动，让你难以专注")
        elif self.libido > 80:
            parts.append("你感到一阵莫名的躁动，身体渴望释放")

        if self.is_menstruating:
            if self.menstrual_day <= 3:
                parts.append(f"生理期第{self.menstrual_day}天，小腹坠痛感最为强烈，浑身乏力")
            else:
                parts.append(f"生理期第{self.menstrual_day}天，腹痛有所缓解，但仍感疲惫")

        if self.health < 30:
            parts.append("你身体虚弱，可能需要去看医生")
        elif self.health < 50:
            parts.append("你感觉身体不太舒服")

        if self.cleanliness < 20:
            parts.append("你身上有明显的汗臭味，急需洗个澡")
        elif self.cleanliness < 40:
            parts.append("你感觉自己有些邋遢，该洗漱了")

        if self.gender == "女" and not self.is_menstruating and 22 <= self.cycle_day <= 28:
            days_left = 28 - self.cycle_day + 1
            parts.append(f"你感到胸部胀痛，情绪波动——生理期快到了（约{days_left}天后）")

        if not parts:
            return "你感觉身体状态不错。"
        return "。".join(parts) + "。"

    # ===== Serialization =====

    def to_dict(self) -> dict:
        d = {}
        for fld in self.__dataclass_fields__:
            val = getattr(self, fld)
            d[fld] = val
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "PlayerState":
        field_names = set(cls.__dataclass_fields__.keys())
        clean = {}
        for k, v in d.items():
            if k in field_names:
                # Handle default_factory fields
                if k == "body_attributes" and not isinstance(v, dict):
                    v = {
                        "height": 170, "weight": 60, "cup_size": "",
                        "genital_length": 0, "body_hair": "中等",
                        "body_type": "标准", "skin_tone": "自然肤色",
                    }
                if k == "_outfit" and not isinstance(v, dict):
                    v = {}
                if k == "_game_datetime" and not isinstance(v, dict):
                    v = {"year": 2026, "month": 8, "day": 1, "hour": 8, "minute": 0}
                clean[k] = v
        return cls(**clean)

    def save(self, filepath: str):
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, filepath: str) -> "PlayerState":
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Migrate old saves: add missing fields
        data.setdefault("cleanliness", 80)
        data.setdefault("appearance", 50)
        data.setdefault("birthday", "")
        data.setdefault("social_class", "工薪")
        data.setdefault("body_attributes", {
            "height": 170, "weight": 60, "cup_size": "",
            "genital_length": 0, "body_hair": "中等",
            "body_type": "标准", "skin_tone": "自然肤色",
        })
        data.setdefault("current_location", "家中卧室")
        data.setdefault("_outfit", {})
        data.setdefault("_game_datetime", {
            "year": 2026, "month": 8, "day": 1, "hour": 8, "minute": 0,
        })
        return cls.from_dict(data)
