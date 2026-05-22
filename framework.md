# 🧠 AI驱动人生模拟器 — 开发框架文档（v4）

> **标记说明**：`🆕 [v4新增]` 表示根据 `newneeds.md` 新增/修改的内容。`🆕 [v3新增]` 为上一版本保留标记。

---

## 1. 技术选型（无变化）

| 层面 | 选择 | 理由 |
|------|------|------|
| 语言 | Python 3.11+ | LLM生态最成熟，快速原型开发 |
| AI接口 | OpenAI兼容API + 第三方base_url | 支持任意第三方API |
| 数据存储 | JSON文件 (MVP) → SQLite | 零依赖起步，结构清晰易调试 |
| 前端 | 命令行CLI (MVP)，预留UI接口层 | CLI先跑通逻辑 |
| 包管理 | pip + requirements.txt | 简单直接 |

---

## 2. 交互模式体系（v4 重构）

### 2.1 顶层模式：自由文字 vs 选项模式

两种顶层模式可通过 `/mode` 切换，保持不变。

### 2.2 🆕 [v4新增] 选项模式三大子模式

选项模式不再只有"AI生成事件→选选项"。现在分为三个**并存的子模式**：

| 子模式 | 说明 | 触发方式 |
|--------|------|---------|
| 📖 **剧情模式** | 原有逻辑：AI生成每日事件，玩家选择选项 | 进入选项模式后默认 |
| 🚶 **移动模式** | 移动到其他位置，到达后提供该位置的操作选项 | 输入 `/move` 或在剧情模式中选择移动类选项 |
| 🤝 **互动模式** | 与当前位置的NPC/物品互动 | 输入 `/interact` 或在移动模式到达后自动触发 |

### 2.3 模式切换命令汇总

```
/mode free        → 切换到自由文字模式
/mode choice      → 切换到选项模式（默认剧情子模式）
/move             → 进入移动模式（仅选项模式下可用）
/interact         → 进入互动模式（仅选项模式下可用）
/skip N           → 🆕 跳过N天，AI自动结算状态变化
/relationship     → 🆕 查看所有NPC好感度
/outfit           → 🆕 查看当前服装
/help             → 查看所有命令
```

### 2.4 选项模式内子模式流转图

```
                  ┌──────────────────┐
                  │   剧情模式        │
                  │ (AI生成事件+选项) │
                  └───┬──────┬───────┘
           /move      │      │  /interact
          选择移动选项 │      │  选择互动选项
                      ▼      ▼
          ┌─────────────┐  ┌──────────────┐
          │  移动模式     │  │  互动模式      │
          │ 选择目的地    │  │ 选NPC/物品     │
          │ → 到达后自动  │  │ → 互动选项     │
          │   转互动模式  │  │   影响好感度   │
          └─────────────┘  └──────────────┘
```

---

## 3. 🆕 [v4新增] 项目目录结构

```
simular-world/
├── main.py
├── requirements.txt
├── .env
├── config/
│   ├── settings.py
│   ├── character_card.json    # 🆕 角色卡大幅扩展（见§9）
│   ├── world_prompt.txt
│   ├── locations.json         # 🆕 位置定义（房间/场所+可互动物品+NPC刷出规则）
│   └── holidays.json          # 🆕 各国法定节假日数据
├── src/
│   ├── core/
│   │   ├── game_loop.py       # 🆕 三子模式分支 + 时间跳过逻辑
│   │   ├── state_manager.py   # 🆕 扩展PlayerState（洁净/容貌/位置/日期时间/NPC关系）
│   │   └── event_engine.py
│   ├── ai/
│   │   ├── llm_client.py
│   │   ├── narrator.py        # 🆕 扩展上下文（服装/位置/社交/时间）
│   │   ├── planner.py         # 🆕 扩展上下文（同上）
│   │   └── executor.py
│   ├── systems/               # 🆕 [v4新增] 所有新增子系统
│   │   ├── __init__.py
│   │   ├── clothing.py        # 服装系统（分层穿戴）
│   │   ├── social.py          # 社交系统（NPC管理+好感度）
│   │   ├── position.py        # 位置系统（地点图谱+移动+场景物品）
│   │   ├── calendar_utils.py  # 日历系统（真实时间+节假日+AI时间推断）
│   │   ├── appearance.py      # 容貌/外貌系统
│   │   ├── cleanliness.py     # 洁净度系统
│   │   └── time_skip.py       # 日程跳过逻辑
│   ├── world/
│   │   ├── worldbook.py
│   │   └── rules.json
│   ├── memory/
│   │   ├── memory_store.py
│   │   └── memories.json
│   ├── ui/
│   │   ├── base.py            # 🆕 新增 location/relationship/outfit 显示方法
│   │   ├── cli.py             # 🆕 新增面板（位置栏/时间栏/好感度表/服装表）
│   │   └── web.py
│   └── utils/
│       ├── prompt_builder.py  # 🆕 七套Prompt全部扩展新上下文
│       ├── character_creator.py # 🆕 角色创建全面重做
│       └── logger.py
├── data/
│   └── save/
│       ├── player_state.json
│       ├── npcs.json          # 🆕 NPC持久化数据
│       └── game_log.json
└── tests/
```

---

## 4. 🆕 [v4新增] 日历与时间系统 (`calendar_utils.py`)

### 需求来源：newneeds.md #8

**核心数据结构**：

```python
@dataclass
class GameDateTime:
    year: int = 2026
    month: int = 8
    day: int = 1
    hour: int = 8       # 24小时制
    minute: int = 0

    def advance_minutes(self, n: int): ...
    def advance_hours(self, n: int): ...
    def advance_days(self, n: int): ...
    def weekday(self) -> str: ...       # 星期一~星期日
    def is_weekend(self) -> bool: ...
    def is_holiday(self, country="CN") -> bool: ...
    def holiday_name(self, country="CN") -> str | None: ...
    def to_display(self) -> str:        # "2026年8月1日 08:30"
    def to_iso(self) -> str: ...
```

**节假日系统**：
- `config/holidays.json` 存储各国法定节假日（中国春节/国庆/中秋，美国 Christmas/Thanksgiving 等）
- 固定日期节日（国庆10/1）：直接匹配
- 浮动日期节日（春节、复活节）：根据算法推算
- 若年份超前未公布，由 **AI 自动推算**（Planner/Narrator注入推算逻辑）
- 节假日自动触发：工作暂停、社交事件增多、特定节日叙事

**AI时间推断**：
- AI内置常见动作耗时参照表（吃饭20-40分钟、洗澡15-30分钟、通勤30-90分钟等）
- Prompt中注入当前时间，AI根据动作内容自行推断时间流逝
- 系统解析AI返回的时间推进量，更新 `game_datetime`

**显示格式**：
```
🕐 2026年8月1日 星期六 15:30  [处暑 · 无节假日]
```

---

## 5. 🆕 [v4新增] 服装系统 (`clothing.py`)

### 需求来源：newneeds.md #1

**分层服装结构**：

```python
@dataclass
class Outfit:
    hairstyle: str = ""              # 发型（AI描述，如"黑色长发披肩"）
    accessories: list[str] = field(default_factory=list)  # ["珍珠项链","银耳环","皮质手链","卡西欧手表"]
    makeup: str = ""                 # 妆容（AI精简描述，如"淡妆：粉底+口红"）
    bra: str = ""                    # 🆕 内衣（仅女性显示，如"白色蕾丝文胸"）
    underwear: str = ""              # 内裤
    top_inner: str = ""              # 上装内层（如"白色T恤"）
    top_outer: str = ""              # 上装外层（如"针织开衫"）
    jacket: str = ""                 # 外套（如"风衣"）
    bottom: str = ""                 # 下装（裤/裙，若连衣裙则填此处，如"碎花连衣裙"）
    skirt_hem: str = ""              # 🆕 裙摆（仅连衣裙/长裙时AI返回，如"及膝裙摆"）
    socks: str = ""                  # 袜子
    shoes: str = ""                  # 鞋子

    def to_prompt(self) -> str:      # 转为AI Prompt片段
    def to_display(self) -> str:     # 转为CLI展示文本
    def is_complete(self) -> bool:   # 是否穿搭完整（基本衣物不缺）
```

**服装系统行为**：
- 角色创建时用户指定初始服装，或AI自动推断默认服装
- 每次换装通过AI交互完成（用户描述想换的衣服，AI生成新的Outfit）
- 服装影响社交（衣着得体加分）、洁净度（穿久了变脏）
- Prompt中注入当前服装描述，让AI叙事中体现穿着状态

**CLI展示示例**：
```
👗 当前穿搭：
  发型：黑色长发披肩
  首饰：珍珠项链、银耳环
  妆容：淡妆（粉底+口红）
  上装：白色T恤 + 针织开衫
  下装：碎花连衣裙（及膝裙摆）
  鞋袜：白色短袜、帆布鞋
```

---

## 6. 🆕 [v4新增] 社交系统 (`social.py`)

### 需求来源：newneeds.md #3

**NPC数据结构**：

```python
@dataclass
class NPC:
    name: str
    gender: str                     # "男" / "女"
    age: int
    relationship_type: str          # "伴侣"/"亲人"/"亲友"/"朋友"/"陌生人"
    subtype: str = ""               # 🆕 "哥们"/"闺蜜"/"子女"/"父母"/"男友"/"女友"
    affection: int = 0              # 好感度 (-100 ~ 100)
    is_present: bool = False        # 是否在当前场景
    current_location: str = ""      # NPC当前位置
    personality: str = ""           # NPC性格简述
    appearance: str = ""            # NPC外貌简述
    backstory: str = ""             # 与玩家的关系背景

    def relationship_decay_factor(self) -> float:
        """关系越深，负面互动影响越小"""
        # 伴侣/亲人: 0.2, 亲友: 0.3, 朋友: 0.5, 陌生人: 1.0
```

**好感度规则**：

| 互动类型 | 正面效果 | 负面效果 | 受洁净度/容貌度影响 |
|---------|---------|---------|-----------------|
| 伴侣/亲人 | `+3~8` | `-1~3`（衰减因子0.2） | 容貌度加成 |
| 亲友 | `+2~6` | `-2~5`（衰减因子0.3） | 容貌度+洁净度加成 |
| 朋友 | `+1~5` | `-3~8`（衰减因子0.5） | 容貌度+洁净度加成 |
| 陌生人 | `+1~4` | `-5~10`（衰减因子1.0） | 容貌度+洁净度大幅加成 |

🆕 **洁净度对社交的削弱**（见§7）：
- `cleanliness > 80`：社交加成 ×1.2
- `cleanliness < 30`：社交效果 ×0.5，陌生人初次印象 -10
- `cleanliness < 10`：NPC自动疏远

**查询命令**：
```
>> /relationship
  NPC好感度一览：
  👨 王大明（父亲）    ❤️ +85  亲人
  👩 李美玲（母亲）    ❤️ +92  亲人
  👧 张小雨（闺蜜）    ❤️ +72  亲友·闺蜜
  👦 陈浩然（男友）    ❤️ +88  伴侣·男友
  👤 刘老师            ❤️ +15  陌生人
```

---

## 7. 🆕 [v4新增] 洁净度系统 (`cleanliness.py`)

### 需求来源：newneeds.md #4

```python
# 集成在 PlayerState 中
cleanliness: int = 80           # 洁净度 (0-100)

# 每日衰减
# cleanliness 每日 -5~15（取决于活动类型）
# 洗澡 +40~60, 洗脸/洗手 +5~10, 换衣服 +15~25
```

**洁净度 → 社交削弱表**：

| 洁净度 | 社交效果倍率 | NPC反应 |
|--------|-----------|--------|
| 90-100 | ×1.3 | "你看起来容光焕发" |
| 60-89 | ×1.0 | 正常 |
| 30-59 | ×0.7 | NPC微皱眉 |
| 10-29 | ×0.5 | "你是不是该洗个澡了" |
| 0-9 | ×0.3 | NPC避而远之，主动对话可能被拒绝 |

---

## 8. 🆕 [v4新增] 位置系统 (`position.py`)

### 需求来源：newneeds.md #5

**位置图谱**（`config/locations.json`）：

```json
{
  "locations": {
    "家中": {
      "type": "residence",
      "sub_locations": ["卧室", "客厅", "厨房", "卫生间", "阳台"],
      "npc_pool": ["家人NPC"],
      "description": "你温馨的小窝"
    },
    "卧室": {
      "parent": "家中",
      "type": "private_room",
      "objects": ["床", "衣柜", "书桌", "镜子"],
      "actions": ["睡觉", "换衣服", "看书", "照镜子", "打发时间"]
    },
    "卫生间": {
      "parent": "家中",
      "type": "utility",
      "objects": ["马桶", "淋浴", "洗手台", "洗衣机"],
      "actions": ["上厕所", "洗澡", "刷牙洗脸", "更换生理用品", "洗衣服"]
    },
    "客厅": {
      "parent": "家中",
      "type": "common_room",
      "objects": ["沙发", "电视", "茶几"],
      "actions": ["看电视", "休息", "会客", "打发时间"]
    },
    "厨房": {
      "parent": "家中",
      "type": "utility",
      "objects": ["冰箱", "灶台", "餐桌"],
      "actions": ["做饭", "吃饭", "喝水", "拿零食"]
    },
    "大学校园": {
      "type": "public",
      "sub_locations": ["教室", "图书馆", "食堂", "操场", "宿舍"],
      "npc_pool": ["同学", "老师"],
      "description": "你就读的大学"
    },
    "商业街": {
      "type": "public",
      "sub_locations": ["便利店", "服装店", "餐厅", "咖啡厅"],
      "npc_pool": ["路人", "店员"],
      "description": "繁华的商业街"
    }
  }
}
```

**移动模式流程**：
1. 玩家 `/move` → 显示可到达位置列表
2. 玩家选择目的地 → 系统计算移动耗时
3. AI生成移动叙事（"你走出家门，步行10分钟来到商业街..."）
4. 到达后自动展示该位置的操作选项：
   - 🧹 场景互动（上厕所/洗澡/做饭/照镜子/换衣服...）
   - 👥 在场NPC互动
   - ⌛ 打发时间（时间快进，AI自动叙事）
5. 执行操作 → 更新状态 → 回到选项模式

**互动模式流程**：
1. 玩家 `/interact` → 显示当前位置的NPC列表+可互动物品
2. 选择目标 → 显示可用互动选项
3. 执行互动 → AI叙事 → 好感度变化 → 状态更新

---

## 9. 🆕 [v4新增] 容貌/外貌系统 (`appearance.py`)

### 需求来源：newneeds.md #6 + #7

**PlayerState 新增字段**：

```python
appearance: int = 50            # 容貌度 (0-100)，影响社交加成

# 🆕 NSFW体型数值
body_attributes: dict = field(default_factory=lambda: {
    "height": 170,              # 身高cm
    "weight": 60,               # 体重kg
    "cup_size": "",             # 罩杯（仅女性，如"C"）
    "genital_length": 0,        # 🆕 男性生殖器长度cm（仅男性）
    "body_hair": "中等",        # 体毛程度："少"/"中等"/"多"
    "body_type": "标准",        # 体型："瘦"/"标准"/"丰满"/"健壮"
    "skin_tone": "自然肤色",    # 肤色描述
})
```

**容貌度社交加成**：
- `appearance > 80`：陌生人初次印象 +20，异性互动好感获取 ×1.5
- `appearance < 30`：社交影响微减（0.9倍），可通过化妆/打扮提升
- `appearance` 部分值由 `body_attributes` 推导（如身高体重比例）
- 妆容/服装搭配可临时提升表象容貌（`effective_appearance`）

---

## 10. 🆕 [v4新增] 角色创建全面重做 (`character_creator.py`)

### 需求来源：newneeds.md #7

**完整创建流程**：

```
1. 基本信息：姓名、性别、年龄、生日（如2008年4月28日）
2. 职业与阶级：职业、社会阶级（工薪/中产/富裕/精英）
3. 性格：自由描述
4. 容貌度：1-100数字或文字描述（如"漂亮"/"普通"/"丑"）系统自动转数值
5. 🆕 体型外貌：
   - 身高(cm)、体重(kg)
   - 罩杯（仅女性）、生殖器长度（仅男性）
   - 体毛程度（少/中等/多）
   - 体型（瘦/标准/丰满/健壮）
   - 肤色
6. 🆕 初始社交关系：
   - 系统询问：是否有父母？→ 创建父母NPC
   - 是否有闺蜜/哥们？→ 创建亲友NPC
   - 是否有伴侣（男友/女友）？→ 创建伴侣NPC
   - 每个NPC：姓名、年龄、性格简述、初始好感度
   - 用户可随时说"跳过"或"不加了"
7. 🆕 初始位置：用户自定义（如"大学城附近的学生公寓"）
8. 🆕 初始服装：AI根据角色设定自动生成完整Outfit
9. 故事背景：自由描述
10. 确认生成提示词 → 写入 character_card.json + npcs.json
```

---

## 11. 🆕 [v4新增] 日程跳过系统 (`time_skip.py`)

### 需求来源：newneeds.md #2

```
>> /skip 7
准备跳过7天（第10天 → 第17天）...
AI正在根据世界规则和常识自动结算...
─────────────────────────────
跳过期间摘要：
· 金钱：-350元（日常开销）
· 生理期：第1天→第8天（经期已结束）
· 健康：-5（轻微疲劳累积）
· 社交：与陈浩然好感度-3（几天没联系）
· 事件：周末参加了一次同学聚会
─────────────────────────────
当前：第17天 | 2026年8月18日 星期一
```

**跳过逻辑**：
1. 循环执行N天的每日衰减 + 世界书规则检查
2. 调用 Planner AI（摘要模式）生成每天的关键变化摘要
3. 重要事件（如经期开始/结束、生病、大额消费）单独列出
4. 普通事件合并为一行统计
5. 最终输出跳过摘要，不打断叙事流

---

## 12. 🆕 [v4新增] 重构后的 PlayerState

```python
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

    # === 🆕 新增系统 ===
    cleanliness: int = 80       # 洁净度
    appearance: int = 50        # 容貌度

    # === 角色身份 ===
    name: str = ""
    gender: str = "男"
    age: int = 25
    birthday: str = ""          # 🆕 "4月28日"
    job: str = "无业"
    social_class: str = "工薪"  # 🆕 工薪/中产/富裕/精英
    background: str = ""
    personality: str = ""

    # === 🆕 体型外貌 ===
    body_attributes: dict = field(default_factory=dict)

    # === 生理周期（女性） ===
    is_menstruating: bool = False
    menstrual_day: int = 0
    cycle_day: int = 0

    # === 🆕 时间系统 ===
    game_datetime: GameDateTime = field(default_factory=GameDateTime)
    turn_in_day: int = 0

    # === 🆕 位置系统 ===
    current_location: str = "家中卧室"

    # === 🆕 服装系统 ===
    outfit: Outfit = field(default_factory=Outfit)
```

---

## 13. AI Prompt 上下文扩展

所有AI Prompt（Narrator/Planner/Executor）统一注入新增上下文：

```
【时间】2026年8月1日 星期六 15:30（无节假日）

【位置】你目前在：家中卧室

【服装】黑色长发披肩 | 淡妆 | 白色T恤+针织开衫+牛仔裤 | 帆布鞋

【洁净度】85/100（清爽干净）

【容貌】78/100（外貌出众）

【在场NPC】母亲李美玲（客厅）、（无其他人在卧室）

【社交关系概览】
  父亲王大明 ❤️+85 | 母亲李美玲 ❤️+92 | 闺蜜张小雨 ❤️+72 | 男友陈浩然 ❤️+88

【生理感受】...（原有）
【最近记忆】...（原有）
【生效规则】...（原有）
```

---

## 14. UI抽象层扩展 (`ui/base.py`)

```python
class UIBase(ABC):
    # 原有方法...

    @abstractmethod
    def display_location(self, location_name: str, npcs_present: list) -> None:
        """🆕 显示当前位置和在场NPC"""
        ...

    @abstractmethod
    def display_relationship_table(self, npcs: list) -> None:
        """🆕 显示好感度表格"""
        ...

    @abstractmethod
    def display_outfit(self, outfit) -> None:
        """🆕 显示当前服装"""
        ...

    @abstractmethod
    def get_sub_mode(self) -> str:
        """🆕 选项模式内获取子模式选择（剧情/移动/互动）"""
        ...
```

---

## 15. 开发阶段（更新）

### Phase 3：新系统开发（当前阶段）🆕
- [ ] 3.1 日历时间系统 `calendar_utils.py` + `holidays.json`
- [ ] 3.2 服装系统 `clothing.py`
- [ ] 3.3 社交系统 `social.py` + `npcs.json`
- [ ] 3.4 位置系统 `position.py` + `locations.json`
- [ ] 3.5 洁净度系统 `cleanliness.py`
- [ ] 3.6 容貌度系统 `appearance.py`
- [ ] 3.7 日程跳过 `time_skip.py` + `/skip` 命令
- [ ] 3.8 角色创建重做 `character_creator.py`
- [ ] 3.9 选项模式子模式（移动/互动）重构 `game_loop.py`
- [ ] 3.10 UI扩展（位置栏/好感度表/服装表/时间栏）
- [ ] 3.11 Prompt模板全部扩展新上下文
- [ ] 3.12 PlayerState 扩展（洁净/容貌/日期时间/位置/服装/NPC关系/体型）

### Phase 4：UI与交互
- [ ] `ui/web.py` — Web前端实现

---

## 16. 🆕 需求追溯表

| # | newneeds.md | 需求 | 对应模块 | 文档位置 |
|---|-----------|------|---------|---------|
| 1 | #一·1 | 服装系统 | `clothing.py` | §5 |
| 2 | #一·2 | 日程跳过 | `time_skip.py` | §11 |
| 3 | #一·3 | 社交系统 | `social.py` | §6 |
| 4 | #一·4 | 洁净度 | `cleanliness.py` + 社交联动 | §7 |
| 5 | #一·5 | 选项模式+位置系统 | `position.py` + game_loop子模式 | §8 + §2.2 |
| 6 | #一·6 | 容貌度 | `appearance.py` | §9 |
| 7 | #一·7 | 角色创建重做 | `character_creator.py` | §10 |
| 8 | #一·8 | 日历时间系统 | `calendar_utils.py` + `holidays.json` | §4 |

---

> **v4 框架已完成，新增8大系统。请审核后下令开始 Phase 3 编码。**
