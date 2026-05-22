from dataclasses import dataclass, field, asdict


@dataclass
class Outfit:
    hairstyle: str = ""              # 发型
    accessories: list[str] = field(default_factory=list)  # 首饰列表
    makeup: str = ""                 # 妆容
    bra: str = ""                    # 内衣（仅女性）
    underwear: str = ""              # 内裤
    top_inner: str = ""              # 上装内层
    top_outer: str = ""              # 上装外层
    jacket: str = ""                 # 外套
    bottom: str = ""                 # 下装
    skirt_hem: str = ""              # 裙摆（连衣裙/长裙时使用）
    socks: str = ""                  # 袜子
    shoes: str = ""                  # 鞋子

    def to_prompt(self, gender: str = "男") -> str:
        """Convert outfit to a concise AI prompt snippet."""
        parts = []
        if self.hairstyle:
            parts.append(f"发型：{self.hairstyle}")
        if self.accessories:
            parts.append(f"配饰：{'、'.join(self.accessories)}")
        if self.makeup:
            parts.append(f"妆容：{self.makeup}")

        # Build clothing layers
        clothing = []
        if gender == "女" and self.bra:
            clothing.append(self.bra)
        if self.underwear:
            clothing.append(self.underwear)
        if self.top_inner:
            clothing.append(self.top_inner)
        if self.top_outer:
            clothing.append(self.top_outer)
        if self.jacket:
            clothing.append(self.jacket)
        if self.bottom:
            clothing.append(self.bottom)
            if self.skirt_hem and ("裙" in self.bottom):
                clothing[-1] += f"（{self.skirt_hem}）"
        if self.socks:
            clothing.append(self.socks)
        if self.shoes:
            clothing.append(self.shoes)

        if clothing:
            parts.append(f"穿着：{' + '.join(clothing)}")

        return " | ".join(parts) if parts else "穿着普通日常服装"

    def to_display(self, gender: str = "男") -> str:
        """Format outfit for CLI display."""
        lines = ["👗 当前穿搭："]
        if self.hairstyle:
            lines.append(f"  发型：{self.hairstyle}")
        if self.accessories:
            lines.append(f"  首饰：{'、'.join(self.accessories)}")
        if self.makeup:
            lines.append(f"  妆容：{self.makeup}")
        if gender == "女" and self.bra:
            lines.append(f"  内衣：{self.bra}")
        if self.underwear:
            lines.append(f"  内裤：{self.underwear}")

        top_str = self.top_inner
        if self.top_outer:
            top_str += f" + {self.top_outer}"
        if self.jacket:
            top_str += f" + 外套：{self.jacket}"
        if top_str:
            lines.append(f"  上装：{top_str}")

        if self.bottom:
            bottom_str = self.bottom
            if self.skirt_hem:
                bottom_str += f"（{self.skirt_hem}）"
            lines.append(f"  下装：{bottom_str}")

        foot = []
        if self.socks:
            foot.append(self.socks)
        if self.shoes:
            foot.append(self.shoes)
        if foot:
            lines.append(f"  鞋袜：{'、'.join(foot)}")

        return "\n".join(lines)

    def is_complete(self) -> bool:
        """Check if the outfit has at least basic items."""
        return bool(self.top_inner and self.bottom and self.shoes)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Outfit":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    @classmethod
    def default_outfit(cls, gender: str = "男") -> "Outfit":
        if gender == "女":
            return cls(
                hairstyle="黑色长发",
                top_inner="白色T恤",
                bottom="牛仔裤",
                underwear="棉质内裤",
                bra="白色文胸",
                shoes="帆布鞋",
                socks="短袜",
            )
        return cls(
            hairstyle="短发",
            top_inner="灰色T恤",
            bottom="休闲裤",
            underwear="棉质内裤",
            shoes="运动鞋",
            socks="短袜",
        )
