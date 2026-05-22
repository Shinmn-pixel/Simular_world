import json
import os
from src.systems.clothing import Outfit

_SKIP = object()


def _safe_input(ui, prompt: str, allow_skip: bool = False) -> str:
    """Wrapper around ui.get_input() that handles /skip and /quit commands.
    Returns _SKIP sentinel if /skip is used on an optional step.
    """
    while True:
        val = ui.get_input(prompt).strip()
        cmd = ui.check_command(val)
        if cmd == "/quit":
            if _ask_yn_raw(ui, "\n确定要退出角色创建吗？(y/n): "):
                ui.show_message("已取消角色创建。")
                exit(0)
            continue
        if cmd == "/skip":
            if allow_skip:
                return _SKIP
            ui.show_message("此项为必填，不能跳过。")
            continue
        return val


def _ask_yn_raw(ui, prompt: str) -> bool:
    """Simple yes/no without skip support (used by _safe_input itself)."""
    val = ui.get_input(prompt).strip().lower()
    return val in ("y", "yes", "是", "")


def create_character(ui) -> dict:
    """10-step interactive character creation wizard. Returns character_card dict."""

    ui.show_message("=" * 50)
    ui.show_message("     🧠 AI人生模拟器 — 角色创建")
    ui.show_message("=" * 50)
    ui.show_message("（随时输入 /skip 跳过可选步骤）\n")

    card = {}

    # Step 1: Basic info
    card["name"] = _ask_required(ui, "1/10 请输入角色姓名：")
    card["gender"] = _ask_gender(ui)
    card["age"] = _ask_int(ui, "2/10 请输入年龄：", 1, 120)
    card["birthday"] = _safe_input(ui, "3/10 请输入生日（如 4月28日）：", allow_skip=True)
    if card["birthday"] is _SKIP or not card["birthday"]:
        card["birthday"] = "1月1日"

    # Step 2: Occupation & class
    card["job"] = _safe_input(ui, "4/10 请输入职业：", allow_skip=True)
    if card["job"] is _SKIP or not card["job"]:
        card["job"] = "无业"
    card["social_class"] = _ask_class(ui)

    # Step 3: Personality
    personality = _safe_input(ui, "5/10 请描述角色性格：", allow_skip=True)
    card["personality"] = personality if (personality is not _SKIP and personality) else "普通人的性格"

    # Step 4: Appearance
    card["appearance"] = _ask_int(ui, "6/10 请输入容貌度 (1-100, 越高越好看)：", 1, 100, default=50)

    # Step 5: Body attributes
    ui.show_message("\n7/10 体型外貌设置：")
    body = {}
    body["height"] = _ask_int(ui, "  身高(cm)：", 100, 250,
                              default=175 if card["gender"] == "男" else 162)
    body["weight"] = _ask_int(ui, "  体重(kg)：", 30, 200,
                              default=70 if card["gender"] == "男" else 52)

    if card["gender"] == "女":
        cup = _safe_input(ui, "  罩杯 (A/B/C/D/E，回车跳过)：", allow_skip=True)
        body["cup_size"] = cup.upper() if (cup is not _SKIP and cup) else "B"
        body["genital_length"] = 0
    else:
        body["cup_size"] = ""
        body["genital_length"] = _ask_int(ui, "  生殖器长度(cm)：", 0, 30, default=12)

    body["body_hair"] = _ask_choice(ui, "  体毛程度：", ["少", "中等", "多"], default="中等")
    body["body_type"] = _ask_choice(ui, "  体型：", ["瘦", "标准", "丰满", "健壮"], default="标准")
    skin = _safe_input(ui, "  肤色描述（回车=自然肤色）：", allow_skip=True)
    body["skin_tone"] = skin if (skin is not _SKIP and skin) else "自然肤色"
    card["body_attributes"] = body

    # Step 6: Initial NPC relationships
    ui.show_message("\n8/10 设置初始社交关系（输入 /skip 跳过）：")
    npcs = []

    # Parents
    if _ask_yn(ui, "  是否有父母角色？(y/n)："):
        father_name = _safe_input(ui, "    父亲姓名：", allow_skip=True)
        if father_name is not _SKIP and father_name:
            npcs.append(_make_npc(father_name, "男", "亲人", "父母", age=card["age"] + 28, affection=80))
        mother_name = _safe_input(ui, "    母亲姓名：", allow_skip=True)
        if mother_name is not _SKIP and mother_name:
            npcs.append(_make_npc(mother_name, "女", "亲人", "父母", age=card["age"] + 26, affection=85))

    # Siblings
    if _ask_yn(ui, "  是否有兄弟姐妹？(y/n)："):
        while True:
            sib_name = _safe_input(ui, "    兄弟姐妹姓名（回车结束）：", allow_skip=True)
            if sib_name is _SKIP or not sib_name:
                break
            sib_gender = _ask_gender(ui, "    性别（男/女）：")
            sib_age = _ask_int(ui, "    年龄：", 0, 120, default=card["age"] - 2)
            relation = "兄" if sib_gender == "男" and sib_age > card["age"] else \
                       "弟" if sib_gender == "男" else \
                       "姐" if sib_age > card["age"] else "妹"
            npcs.append(_make_npc(sib_name, sib_gender, "亲人", relation, age=sib_age, affection=70))

    # Best friend
    if _ask_yn(ui, "  是否有闺蜜/哥们？(y/n)："):
        bf_name = _safe_input(ui, "    姓名：", allow_skip=True)
        if bf_name is not _SKIP and bf_name:
            bf_gender = _ask_gender(ui, "    性别（男/女）：")
            subtype = "闺蜜" if bf_gender == "女" else "哥们"
            bf_age = _ask_int(ui, "    年龄：", 0, 120, default=card["age"])
            npcs.append(_make_npc(bf_name, bf_gender, "亲友", subtype, age=bf_age, affection=75))

    # Partner
    if _ask_yn(ui, "  是否有伴侣（男友/女友）？(y/n)："):
        partner_name = _safe_input(ui, "    姓名：", allow_skip=True)
        if partner_name is not _SKIP and partner_name:
            partner_gender = "女" if card["gender"] == "男" else "男"
            if _ask_yn(ui, f"    对方性别是否为{partner_gender}？(y/n，n则手动输入)："):
                pass
            else:
                partner_gender = _ask_gender(ui, "    性别（男/女）：")
            subtype = "男友" if partner_gender == "男" else "女友"
            partner_age = _ask_int(ui, "    年龄：", 0, 120, default=card["age"])
            npcs.append(_make_npc(partner_name, partner_gender, "伴侣", subtype, age=partner_age, affection=85))

    card["_npcs"] = npcs

    # Step 7: Initial location
    loc = _safe_input(ui, "9/10 请输入初始位置（回车=家中卧室）：", allow_skip=True)
    card["initial_location"] = loc if (loc is not _SKIP and loc) else "家中卧室"

    # Step 8: Initial outfit
    ui.show_message("\n10/10 初始服装：")
    if _ask_yn(ui, "  是否自定义初始服装？(y/n，n=自动生成)："):
        outfit = Outfit.default_outfit(card["gender"])
        val = _safe_input(ui, "  发型描述：", allow_skip=True)
        outfit.hairstyle = val if (val is not _SKIP and val) else outfit.hairstyle
        val = _safe_input(ui, "  上装内层：", allow_skip=True)
        outfit.top_inner = val if (val is not _SKIP and val) else outfit.top_inner
        val = _safe_input(ui, "  上装外层（回车跳过）：", allow_skip=True)
        outfit.top_outer = val if val is not _SKIP else ""
        val = _safe_input(ui, "  下装：", allow_skip=True)
        outfit.bottom = val if (val is not _SKIP and val) else outfit.bottom
        val = _safe_input(ui, "  鞋子：", allow_skip=True)
        outfit.shoes = val if (val is not _SKIP and val) else outfit.shoes
        if card["gender"] == "女":
            val = _safe_input(ui, "  内衣/文胸：", allow_skip=True)
            outfit.bra = val if (val is not _SKIP and val) else outfit.bra
        val = _safe_input(ui, "  内裤：", allow_skip=True)
        outfit.underwear = val if (val is not _SKIP and val) else outfit.underwear
        card["_outfit"] = outfit.to_dict()
    else:
        outfit = Outfit.default_outfit(card["gender"])
        card["_outfit"] = outfit.to_dict()

    # Step 9: Background story
    bg = _safe_input(ui, "\n请用一句话描述角色的故事背景（可选）：\n> ", allow_skip=True)
    card["background"] = bg if (bg is not _SKIP and bg) else \
                         f"{card['age']}岁的{card['job']}，生活在现代都市中"

    # Show summary and confirm
    _show_summary(ui, card, npcs)

    if not _ask_yn(ui, "\n确认以上信息？(y/n，n=重新创建)："):
        return create_character(ui)

    return card


def save_character_card(card: dict, filepath: str):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    # Save NPCs separately
    npcs = card.pop("_npcs", [])
    card["_npcs"] = npcs  # restore
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(card, f, ensure_ascii=False, indent=2)


def save_initial_npcs(npcs: list, filepath: str):
    if not npcs:
        return
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(npcs, f, ensure_ascii=False, indent=2)


def load_character_card(filepath: str) -> dict | None:
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def card_to_prompt(card: dict) -> str:
    lines = [
        f"你叫{card['name']}，{card['age']}岁，{card['gender']}性。",
        f"生日：{card.get('birthday', '未知')}。",
        f"职业：{card.get('job', '无业')}。",
        f"社会阶层：{card.get('social_class', '工薪')}。",
    ]
    if card.get("background"):
        lines.append(f"背景：{card['background']}。")
    if card.get("personality"):
        lines.append(f"性格：{card['personality']}。")
    return "\n".join(lines)


# === Internal helpers ===

def _ask_class(ui) -> str:
    """Ask for social class."""
    ui.show_message("请选择社会阶层：")
    ui.show_message("  [1] 工薪  [2] 中产  [3] 富裕  [4] 精英")
    val = _safe_input(ui, "> ", allow_skip=True)
    if val is _SKIP:
        return "工薪"
    mapping = {"1": "工薪", "2": "中产", "3": "富裕", "4": "精英"}
    return mapping.get(val, "工薪")


def _ask_required(ui, prompt: str) -> str:
    while True:
        val = _safe_input(ui, prompt, allow_skip=False)
        if val:
            return val
        ui.show_message("此项为必填，请重新输入。")


def _ask_gender(ui, prompt: str = "请选择性别（男/女）：") -> str:
    while True:
        val = _safe_input(ui, prompt, allow_skip=False)
        if val in ("男", "女"):
            return val
        ui.show_message("请输入'男'或'女'。")


def _ask_int(ui, prompt: str, min_val: int, max_val: int, default: int = None) -> int:
    allow_skip = default is not None
    while True:
        raw = _safe_input(ui, prompt, allow_skip=allow_skip)
        if raw is _SKIP:
            return default
        if not raw and default is not None:
            return default
        try:
            val = int(raw)
            if min_val <= val <= max_val:
                return val
            ui.show_message(f"请输入{min_val}-{max_val}之间的数字")
        except ValueError:
            ui.show_message("请输入有效数字")


def _ask_choice(ui, prompt: str, options: list[str], default: str = None) -> str:
    ui.show_message(prompt + " (" + "/".join(options) + ")")
    val = _safe_input(ui, "> ", allow_skip=True)
    if val is _SKIP:
        return default or options[0]
    if val in options:
        return val
    return default or options[0]


def _ask_yn(ui, prompt: str) -> bool:
    val = _safe_input(ui, prompt, allow_skip=True)
    if val is _SKIP:
        return False
    return val.lower() in ("y", "yes", "是", "")


def _make_npc(name: str, gender: str, rel_type: str, subtype: str,
              age: int = 25, affection: int = 50) -> dict:
    return {
        "name": name, "gender": gender, "age": age,
        "relationship_type": rel_type, "subtype": subtype,
        "affection": affection, "is_present": False,
        "current_location": "", "personality": "",
        "appearance": "", "backstory": "",
    }


def _show_summary(ui, card: dict, npcs: list):
    ui.show_message("\n" + "=" * 50)
    ui.show_message("         角色创建完成！")
    ui.show_message("=" * 50)
    ui.show_message(f"  姓名：{card['name']}")
    ui.show_message(f"  性别：{card['gender']} | 年龄：{card['age']}岁")
    ui.show_message(f"  生日：{card['birthday']}")
    ui.show_message(f"  职业：{card['job']} | 阶层：{card['social_class']}")
    ui.show_message(f"  容貌度：{card['appearance']}/100")
    ba = card["body_attributes"]
    ui.show_message(f"  体型：{ba['height']}cm / {ba['weight']}kg / {ba['body_type']}")
    if card["gender"] == "女":
        ui.show_message(f"  罩杯：{ba['cup_size']}")
    else:
        ui.show_message(f"  生殖器：{ba['genital_length']}cm")
    ui.show_message(f"  性格：{card['personality']}")
    if npcs:
        ui.show_message(f"  初始社交关系：{len(npcs)}人")
        for n in npcs:
            ui.show_message(f"    {n['name']}（{n.get('subtype', n['relationship_type'])}）❤️{n['affection']:+d}")
    ui.show_message(f"  初始位置：{card.get('initial_location', '家中卧室')}")
    ui.show_message("=" * 50)
