import json
import os
from dataclasses import dataclass, field, asdict
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Location:
    name: str
    location_type: str = "room"        # residence/public/utility/private_room/common_room
    parent: str = ""                    # parent location name
    objects: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    description: str = ""
    npc_pool: list[str] = field(default_factory=list)  # types of NPCs that may appear
    sub_locations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Location":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class PositionManager:
    """Manages location graph, movement, and location-specific actions."""

    def __init__(self, config_file: str = None):
        self.locations: dict[str, Location] = {}
        self.current: str = ""
        if config_file and os.path.exists(config_file):
            self._load(config_file)
        else:
            self._load_defaults()

    def _load(self, filepath: str):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            locs = data if isinstance(data, list) else data.get("locations", [])
            for d in locs:
                loc = Location.from_dict(d) if isinstance(d, dict) else Location(name=str(d))
                self.locations[loc.name] = loc
            logger.info(f"Loaded {len(self.locations)} locations")
        except Exception as e:
            logger.warning(f"Failed to load locations: {e}, using defaults")
            self._load_defaults()

    def _load_defaults(self):
        defaults = [
            Location("家中", "residence", sub_locations=["卧室", "客厅", "厨房", "卫生间", "阳台"],
                     npc_pool=["家人"], description="你的住所"),
            Location("卧室", "private_room", parent="家中",
                     objects=["床", "衣柜", "书桌", "镜子"],
                     actions=["睡觉", "换衣服", "看书", "照镜子", "打发时间", "休息"]),
            Location("客厅", "common_room", parent="家中",
                     objects=["沙发", "电视", "茶几"],
                     actions=["看电视", "休息", "会客", "打发时间"]),
            Location("厨房", "utility", parent="家中",
                     objects=["冰箱", "灶台", "餐桌", "水槽"],
                     actions=["做饭", "吃饭", "喝水", "拿零食", "洗碗"]),
            Location("卫生间", "utility", parent="家中",
                     objects=["马桶", "淋浴", "洗手台", "洗衣机"],
                     actions=["上厕所", "洗澡", "刷牙洗脸", "换卫生巾", "洗衣服", "照镜子"]),
            Location("阳台", "utility", parent="家中",
                     objects=["晾衣架", "洗衣机"],
                     actions=["晾衣服", "发呆", "抽烟"]),
            Location("大学校园", "public",
                     sub_locations=["教室", "图书馆", "食堂", "操场", "宿舍"],
                     npc_pool=["同学", "老师"], description="你就读的大学"),
            Location("教室", "room", parent="大学校园",
                     objects=["课桌", "黑板"],
                     actions=["上课", "自习", "和同学聊天"]),
            Location("图书馆", "room", parent="大学校园",
                     objects=["书架", "阅览桌", "电脑"],
                     actions=["看书", "自习", "借书", "查资料"]),
            Location("食堂", "public", parent="大学校园",
                     objects=["打饭窗口", "餐桌"],
                     actions=["吃饭", "和朋友聚餐", "休息"]),
            Location("宿舍", "private_room", parent="大学校园",
                     objects=["床", "书桌", "衣柜"],
                     actions=["睡觉", "休息", "看书", "换衣服"]),
            Location("商业街", "public",
                     sub_locations=["便利店", "服装店", "餐厅", "咖啡厅"],
                     npc_pool=["路人", "店员"], description="繁华的商业街"),
            Location("便利店", "shop", parent="商业街",
                     objects=["货架", "收银台", "冷柜"],
                     actions=["买东西", "买零食", "买日用品"]),
            Location("服装店", "shop", parent="商业街",
                     objects=["衣架", "试衣间", "镜子"],
                     actions=["买衣服", "试衣服", "逛街"]),
            Location("餐厅", "public", parent="商业街",
                     objects=["餐桌", "菜单"],
                     actions=["吃饭", "和朋友聚餐", "约会"]),
        ]
        for loc in defaults:
            self.locations[loc.name] = loc

    def set_current(self, name: str):
        if name in self.locations:
            self.current = name

    def get_current(self) -> Location | None:
        return self.locations.get(self.current)

    def get(self, name: str) -> Location | None:
        return self.locations.get(name)

    def get_reachable(self) -> list[str]:
        """Get locations reachable from current position."""
        current = self.get_current()
        if not current:
            return list(self.locations.keys())

        reachable = []

        # Can go to parent
        if current.parent and current.parent in self.locations:
            reachable.append(current.parent)

        # Can go to sub-locations
        for sub in current.sub_locations:
            if sub in self.locations:
                reachable.append(sub)

        # Can go to sibling locations (same parent)
        if current.parent:
            parent = self.locations.get(current.parent)
            if parent:
                for sub in parent.sub_locations:
                    if sub != self.current and sub in self.locations:
                        reachable.append(sub)

        # Top-level public locations always reachable (but with travel time)
        for name, loc in self.locations.items():
            if loc.location_type == "public" and not loc.parent:
                if name not in reachable and name != self.current:
                    reachable.append(name)

        # Also include all top-level locations without parents
        for name, loc in self.locations.items():
            if not loc.parent and name not in reachable and name != self.current:
                reachable.append(name)

        return reachable

    def movement_time(self, destination: str) -> int:
        """Estimate movement time in minutes."""
        dest = self.locations.get(destination)
        if not dest:
            return 15

        current = self.get_current()
        if not current:
            return 15

        # Same parent → short (within building)
        if current.parent and current.parent == dest.parent:
            return 2
        # Going to parent or sub → short
        if destination == current.parent or current.name == dest.parent:
            return 1
        # Different public locations → longer
        if current.location_type == "public" and dest.location_type == "public":
            return 30
        # Home ↔ public → commute
        if (current.parent == "家中" and dest.location_type == "public") or \
           (dest.parent == "家中" and current.location_type == "public"):
            return 45
        if (current.parent == "大学校园" and dest.parent == "家中") or \
           (dest.parent == "大学校园" and current.parent == "家中"):
            return 40

        return 20
