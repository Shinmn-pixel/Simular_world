from dataclasses import dataclass, field, asdict

# Default body attributes by gender
DEFAULT_BODY = {
    "男": {
        "height": 175, "weight": 70, "cup_size": "",
        "genital_length": 12, "body_hair": "中等",
        "body_type": "标准", "skin_tone": "自然肤色",
    },
    "女": {
        "height": 162, "weight": 52, "cup_size": "B",
        "genital_length": 0, "body_hair": "少",
        "body_type": "标准", "skin_tone": "自然肤色",
    },
}


@dataclass
class Appearance:
    beauty: int = 50                    # 容貌度 0-100

    # Body attributes
    height: int = 170                   # 身高cm
    weight: int = 60                    # 体重kg
    cup_size: str = ""                  # 罩杯（仅女性有意义）
    genital_length: int = 0             # 男性生殖器长度cm
    body_hair: str = "中等"             # "少" / "中等" / "多"
    body_type: str = "标准"             # "瘦" / "标准" / "丰满" / "健壮"
    skin_tone: str = "自然肤色"

    # Temporary modifiers
    makeup_bonus: int = 0               # 妆容加成
    outfit_bonus: int = 0               # 服装搭配加成

    def effective_beauty(self) -> int:
        """Get effective appearance including temporary bonuses."""
        return min(100, self.beauty + self.makeup_bonus + self.outfit_bonus)

    def social_bonus(self) -> float:
        """Multiplier for social interactions based on appearance."""
        eff = self.effective_beauty()
        if eff >= 85:
            return 1.5
        if eff >= 70:
            return 1.2
        if eff >= 50:
            return 1.0
        if eff >= 30:
            return 0.9
        return 0.8

    def to_prompt(self, gender: str = "男") -> str:
        """Generate appearance description for AI prompts."""
        parts = []
        if gender == "女" and self.cup_size:
            parts.append(f"身高{self.height}cm，{self.cup_size}罩杯，{self.body_type}身材，{self.skin_tone}")
        elif gender == "男":
            parts.append(f"身高{self.height}cm，{self.body_type}身材，{self.skin_tone}")
        else:
            parts.append(f"身高{self.height}cm，{self.body_type}身材")

        if self.beauty >= 80:
            parts.append("外貌非常出众")
        elif self.beauty >= 60:
            parts.append("外貌端正")
        elif self.beauty < 30:
            parts.append("外貌平平")

        return "；".join(parts)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Appearance":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    @classmethod
    def default_for(cls, gender: str = "男", beauty: int = 50) -> "Appearance":
        body = dict(DEFAULT_BODY.get(gender, DEFAULT_BODY["男"]))
        return cls(beauty=beauty, **body)
