import random


def daily_cleanliness_decay(current: int, activity_level: str = "normal") -> int:
    """Calculate daily cleanliness decay based on activity."""
    decay_ranges = {
        "idle": (2, 5),       # 宅家不动
        "normal": (5, 12),    # 正常活动
        "active": (10, 18),   # 运动/外出
        "heavy": (15, 25),    # 剧烈运动/体力劳动
    }
    low, high = decay_ranges.get(activity_level, (5, 12))
    return current - random.randint(low, high)


def cleanliness_social_modifier(cleanliness: int) -> float:
    """Social interaction multiplier based on cleanliness."""
    if cleanliness >= 90:
        return 1.3
    if cleanliness >= 60:
        return 1.0
    if cleanliness >= 30:
        return 0.7
    if cleanliness >= 10:
        return 0.5
    return 0.3


def cleanliness_first_impression_penalty(cleanliness: int) -> int:
    """First impression penalty for strangers based on cleanliness."""
    if cleanliness >= 60:
        return 0
    if cleanliness >= 30:
        return -5
    if cleanliness >= 10:
        return -10
    return -20


def cleanliness_npc_reaction(cleanliness: int) -> str:
    """NPC reaction description based on player cleanliness."""
    if cleanliness >= 90:
        return "你看上去容光焕发，令人心生好感"
    if cleanliness >= 60:
        return ""
    if cleanliness >= 30:
        return "你身上有些许汗味，NPC微微皱了皱眉"
    if cleanliness >= 10:
        return "你的体味较重，NPC不自觉地后退了半步"
    return "你浑身脏污不堪，NPC避之不及"


def activity_from_description(desc: str) -> str:
    """Infer activity level from action description."""
    heavy_keywords = ["运动", "跑步", "健身", "搬", "劳动", "打球"]
    active_keywords = ["出门", "逛街", "散步", "走", "购物"]
    idle_keywords = ["躺", "睡觉", "宅", "发呆", "看手机"]

    for kw in heavy_keywords:
        if kw in desc:
            return "heavy"
    for kw in active_keywords:
        if kw in desc:
            return "active"
    for kw in idle_keywords:
        if kw in desc:
            return "idle"
    return "normal"
