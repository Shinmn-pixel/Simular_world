# Phase Snapshot v1.1 — AI驱动人生模拟器

> 生成日期：2026-05-22 | 版本：v0.3.1 (MVP + Phase 3 扫尾完成) | 总代码量：~3,330 行 Python + ~175 行 JSON 配置

---

## 1. 当前实现了什么

### 1.1 核心游戏循环（双顶层模式 + 选项三子模式）

```
顶层模式
├── 自由文字模式：用户输入任意文字 → Narrator AI 叙事 → 状态结算
└── 选项模式
    ├── 📖 剧情模式：Planner AI 生成事件JSON → Executor AI 渲染 → 玩家选选项
    ├── 🚶 移动模式：选择目的地 → 移动到新位置 → 触发位置专属操作
    └── 🤝 互动模式：选择在场NPC或物品 → 互动 → 好感度/状态变化
```

- 双模式通过 `/mode free` / `/mode choice` 随时切换
- **v0.3.1 新增**: 自由文字模式下 `/move` 和 `/interact` 已路由到完整子模式函数（含 AI 叙事、位置操作、NPC 互动）
- 自由文字模式支持连续对话，N轮后自动推进一天（TURNS_PER_DAY 可配置）
- 所有模式共享：每日生理衰减 → 世界书规则检查 → 记忆写入 → 存档

### 1.2 玩家状态系统（`state_manager.py` — 289行）

| 类别 | 字段 | 说明 |
|------|------|------|
| 基础 | energy / mood / money | 体力 / 心情 / 金钱 |
| 生理 | hunger / sleep_drive / libido / health | 饱腹 / 睡眠欲 / 性欲 / 健康 |
| 周期 | is_menstruating / menstrual_day / cycle_day | 28天女性生理周期（含PMS+经期） |
| 新增 | cleanliness / appearance | 洁净度 / 容貌度 |
| 身份 | name / gender / age / birthday / job / social_class / background / personality | 完整角色信息 |
| 体型 | body_attributes (height/weight/cup_size/genital_length/body_hair/body_type/skin_tone) | NSFW体型数据 |
| 时空 | game_datetime (year/month/day/hour/minute) / current_location / turn_in_day | 日历时间+位置 |
| 服装 | _outfit (12层分件穿搭) | 发型→鞋子的完整穿搭 |

- **10条生理联动规则**：饥饿→掉体力、缺觉→伤健康、经期→降心情等
- **每日自然衰减**：饱腹-15~25、睡眠欲-20~30、性欲+5~15、洁净度-5~12
- **v0.3 修复**: `_last_decay_day` 计数器防止重复衰减（如刷 `/status` 不会推进生理周期）
- **旧存档自动迁移**：缺失字段自动填充默认值

### 1.3 AI系统（双管线）

| 管线 | 使用场景 | AI类 | 输入 | 输出 |
|------|---------|------|------|------|
| Narrator | 自由文字模式 | `narrator.py` | 用户文字+全上下文 | 叙事文本+状态变化JSON |
| Planner+Executor | 选项模式（剧情） | `planner.py` + `executor.py` | 状态+记忆+规则 | 事件JSON → 叙事文本 |

- 基于 OpenAI 兼容 API，支持任意第三方端点（DeepSeek/Ollama/本地）
- Planner/Executor/Narrator 可分别配置不同模型以节省成本
- AI输入上下文统一注入：时间/位置/服装/洁净度/容貌/体型/在场NPC/好感度/生理感受/记忆/世界规则
- **v0.3.1 修复**: cleanliness 重复更新 — narrator 返回 cleanliness 变化时跳过 activity-based 手动更新

### 1.4 系统模块（`src/systems/` — 7个模块）

| 模块 | 行数 | 核心功能 |
|------|------|---------|
| `calendar_utils.py` | 149 | GameDateTime（真实公历+星期+节假日+时间推进+AI耗时推断）；`load_holidays()` 支持按国家过滤 |
| `clothing.py` | 123 | Outfit（12层穿搭：发型/首饰/妆容/内衣/内裤/上装内外/外套/下装/裙摆/袜子/鞋子） |
| `social.py` | 171 | NPC + SocialManager（5种关系类型/好感度-100~100/关系衰减因子/在场管理） |
| `position.py` | 177 | PositionManager（17个位置/父子层级/可到达计算/移动耗时/场景物品与动作） |
| `appearance.py` | 81 | Appearance（容貌度0-100/体型数据/化妆服装临时加成/社交倍率） |
| `cleanliness.py` | 68 | 洁净度衰减/社交削弱倍率(0.3x~1.3x)/NPC初次印象惩罚/活动类型推断 |
| `time_skip.py` | 127 | skip_days(N)（逐日结算生理+金钱+好感度+记忆+世界规则+关键事件摘要） |

### 1.5 基础设施

| 模块 | 行数 | 功能 |
|------|------|------|
| `memory_store.py` | 165 | 记忆的写入/检索（recent+important去重合并）/每7天自动压缩/50条上限 |
| `worldbook.py` + `rules.json` | 132 | 15条预设规则（状态触发/关键词触发/时间触发），支持动态增删 |
| `llm_client.py` | 45 | OpenAI兼容客户端（base_url可配置） |
| `prompt_builder.py` | 252 | 4套Prompt模板（narrator/planner/executor/move），全部注入v4新上下文 |
| `character_creator.py` | 312 | 10步交互式角色创建向导，含 `/skip` `/quit` 命令支持 |
| `ui/base.py` + `cli.py` | 62 + 144 | UI抽象接口（14个方法）+ CLI实现（含状态面板/好感度表/服装展示/时间位置栏） |
| `settings.py` + `.env` | 33 | 集中配置管理（LLM参数/游戏模式/路径/节假日国家） |

### 1.6 玩家可用的命令（12个）

```
/mode free|choice   — 切换游戏模式
/next               — 手动推进一天
/skip N             — 跳过N天（AI自动结算）
/move               — 移动到其他位置（全模式支持完整AI叙事+位置操作）
/interact           — 与NPC或物品互动（全模式支持）
/relationship       — 查看所有NPC好感度
/outfit             — 查看当前服装穿搭
/save               — 保存游戏
/status             — 显示完整状态面板
/quit               — 退出并保存
/help               — 帮助
```

### 1.7 节假日系统（v0.3.1 国际化 - 新增）

- 支持按国家过滤：CN（中国15条）/ US（美国10条）/ JP（日本16条）/ ALL（全部41条）
- 通过 `.env` 中 `HOLIDAY_COUNTRY` 配置（默认 `CN`）
- 固定日期规则 + 春节农历估算

---

## 2. 架构决策

### 2.1 分层架构

```
main.py (入口/初始化)
    ↓
game_loop.py (核心循环/模式分发)
    ├── ai/          AI管线（narrator/planner/executor/llm_client）
    ├── systems/     业务系统（calendar/clothing/social/position/appearance/cleanliness/time_skip）
    ├── core/        核心状态（state_manager）
    ├── world/       世界规则（worldbook）
    ├── memory/      记忆系统（memory_store）
    ├── ui/          UI抽象层（base → cli/web）
    └── utils/       工具（prompt_builder/character_creator/logger）
```

### 2.2 关键架构决策

| 决策 | 理由 |
|------|------|
| **双AI管线（Narrator vs Planner+Executor）** | 自由文字和选项模式对AI的要求不同，分开管线让每边都可以独立调优Prompt和模型 |
| **UI抽象层（UIBase ABC）** | CLI和未来Web UI实现同一接口，game_loop不感知具体UI实现 |
| **嵌套对象用dict而非dataclass存储** | GameDateTime/Outfit在PlayerState中以dict存储，通过getter/setter访问。避免JSON序列化时嵌套dataclass的复杂性，同时保持旧存档兼容 |
| **系统模块独立为 `src/systems/`** | 服装/社交/位置/日历/洁净/容貌/时间跳过 —— 每个系统是高内聚模块，互不依赖，通过game_loop编排 |
| **选项模式三子模式共存而非互斥** | 剧情/移动/互动是三种不同的"行动类型"，用户在每个回合选择一种，而非切换整个模式 |
| **男女双轨生理系统** | 女性有完整的28天生理周期（PMS+经期+联动），男性有独立的性欲和生殖器数据。系统根据gender字段自动分支 |
| **Prompt中注入完整上下文** | 所有AI调用统一注入：时间/位置/服装/洁净度/容貌/体型/社交关系/生理感受。AI叙事能自然融入这些状态 |
| **命令路由在game_loop层级而非_handle_command** ★新 | v0.3.1 将 `/move` `/interact` 路由提升到 `_run_free_text_turn()` 和 `_run_choice_mode()` 层级，直接调用完整子模式函数，避免命令处理器中重复实现 |
| **_safe_input 包装器** ★新 | 角色创建中统一处理 `/skip` `/quit`，必填项拒绝跳过、可选步返回 `_SKIP` 哨兵值、退出需二次确认 |
| **load_holidays 按国家过滤** ★新 | 节假日数据统一存储在 `holidays.json` 中（每条标记 country），加载时根据 `HOLIDAY_COUNTRY` 配置过滤，支持 CN/US/JP/ALL |

### 2.3 数据流

```
用户输入 → game_loop → 模式分支
                          ├── free_text: user_input → 命令路由(/move /interact 走子模式) → Prompt(+全上下文) → Narrator AI → 解析叙事+状态变化 → 结算
                          └── choice:
                               ├── story: → Prompt → Planner AI → 事件JSON → Executor AI → 叙事 → 选择 → 结算
                               ├── move: → 选目的地 → AI移动叙述 → 位置操作 → 结算
                               └── interact: → 选NPC/物品 → AI互动叙述 → 好感度结算 → 状态结算
                          
                          结算后: state.apply() → memory_store.record() → state.save()
```

---

## 3. 数据结构

### 3.1 PlayerState（核心状态）

```python
@dataclass
class PlayerState:
    # 基础
    energy: int = 100;     mood: int = 70;      money: int = 500
    # 生理
    hunger: int = 80;      sleep_drive: int = 90;  libido: int = 50
    health: int = 100;     cleanliness: int = 80;   appearance: int = 50
    # 身份
    name: str;             gender: str;         age: int
    birthday: str;         job: str;            social_class: str
    background: str;       personality: str
    # 生理周期
    is_menstruating: bool; menstrual_day: int;  cycle_day: int
    # 体型
    body_attributes: dict  # {height, weight, cup_size, genital_length, body_hair, body_type, skin_tone}
    # 时空
    day: int;              turn_in_day: int
    _last_decay_day: int   # ★ v0.3 新增: 防止重复衰减计数器
    current_location: str  # "家中卧室"
    _game_datetime: dict   # {year, month, day, hour, minute}
    _outfit: dict          # Outfit.to_dict()
```

### 3.2 NPC & 社交

```python
@dataclass
class NPC:
    name: str;              gender: str;         age: int
    relationship_type: str  # "伴侣"|"亲人"|"亲友"|"朋友"|"陌生人"
    subtype: str            # "男友"|"闺蜜"|"父母"|"哥们"...
    affection: int          # -100 ~ 100
    is_present: bool;       current_location: str
    personality: str;       appearance: str;     backstory: str
```

好感度衰减因子：伴侣/亲人 0.2x → 亲友 0.3x → 朋友 0.5x → 陌生人 1.0x

### 3.3 GameDateTime

```python
@dataclass
class GameDateTime:
    year: int;   month: int;   day: int
    hour: int;   minute: int
    # 方法: advance_minutes/hours/days, weekday, is_weekend, is_holiday, to_display
```

显示格式：`2026年8月1日 星期六 15:30 [国庆节]`

### 3.4 Outfit（12层服装）

```python
@dataclass
class Outfit:
    hairstyle: str        # "黑色长发披肩"
    accessories: list      # ["珍珠项链","银耳环"]
    makeup: str           # "淡妆：粉底+口红"
    bra: str              # 仅女性
    underwear: str        # 内裤
    top_inner: str        # 上装内层
    top_outer: str        # 上装外层
    jacket: str           # 外套
    bottom: str           # 下装（裤/裙/连衣裙）
    skirt_hem: str        # 裙摆（连衣裙时使用）
    socks: str;  shoes: str
```

### 3.5 Memory

```python
@dataclass
class Memory:
    day: int;             event: str
    impact: dict          # {"money": -15, "hunger": +30}
    emotional_tag: str    # "positive"|"negative"|"neutral"
    importance: int       # 1-10
```

### 3.6 世界书规则

```json
{
  "trigger": "is_menstruating == True and energy < 50",
  "effect": "触发痛经加重环境——体力下降，行动受阻",
  "priority": 15
}
```

三种触发：状态触发（`energy < 30`）/ 关键词触发（`keyword: 医院`）/ 时间触发（`day % 7 == 0`）

### 3.7 位置图谱

```
家中 → 卧室/客厅/厨房/卫生间/阳台
大学校园 → 教室/图书馆/食堂/操场/宿舍
商业街 → 便利店/服装店/餐厅/咖啡厅
```

每个位置定义：parent / type / objects[] / actions[] / npc_pool[] / description

### 3.8 存档文件

```
data/save/
├── player_state.json   # PlayerState完整序列化
├── memories.json       # Memory[] （最多50条）
└── npcs.json           # NPC[] （社交关系持久化）
```

---

## 4. 模块清单

| 文件 | 行数 | 职责 |
|------|------|------|
| `main.py` | 172 | 入口：初始化所有子系统 → 启动 game_loop |
| `config/settings.py` | 33 | 集中配置（LLM/路径/模式/节假日国家） |
| `src/core/state_manager.py` | 289 | PlayerState dataclass + 生理联动 + 序列化 |
| `src/core/game_loop.py` | 664 | 核心游戏循环 + 双模式分发 + 命令处理 |
| `src/ai/narrator.py` | 75 | 自由文字 AI 叙事 |
| `src/ai/planner.py` | 54 | 选项模式事件生成 |
| `src/ai/executor.py` | 23 | 选项模式事件渲染 |
| `src/ai/llm_client.py` | 45 | OpenAI 兼容 LLM 客户端 |
| `src/systems/calendar_utils.py` | 149 | 游戏日历 + 节假日加载与过滤 |
| `src/systems/clothing.py` | 123 | 12层服装系统 |
| `src/systems/social.py` | 171 | NPC + 社交关系管理 |
| `src/systems/position.py` | 177 | 位置图谱 + 移动系统 |
| `src/systems/appearance.py` | 81 | 容貌系统 + 社交加成 |
| `src/systems/cleanliness.py` | 68 | 洁净度 + 社交修饰 |
| `src/systems/time_skip.py` | 127 | 多日跳过 + 自动结算 |
| `src/memory/memory_store.py` | 165 | 长期记忆存储与压缩 |
| `src/world/worldbook.py` | 132 | 世界书规则引擎 |
| `src/utils/prompt_builder.py` | 252 | 4套 Prompt 模板 |
| `src/utils/character_creator.py` | 312 | 10步角色创建向导（含 /skip /quit） |
| `src/utils/logger.py` | 13 | 日志工具 |
| `src/ui/base.py` | 62 | UI 抽象接口（14个方法） |
| `src/ui/cli.py` | 144 | CLI 实现 |
| `config/locations.json` | 123 | 17个位置定义 |
| `config/holidays.json` | 45 | 节假日数据（CN/US/JP 共41条） |
| `config/rules.json` | — | 15条世界规则 |
| `config/world_prompt.txt` | — | 世界设定 Prompt |

---

## 5. TODO

### 5.1 短期（Phase 4 预备）

- [ ] **Web UI**（`ui/web.py`）：Flask/FastAPI 实现 UIBase 接口
- [ ] **事件池扩充**：工作/社交/健康/随机/饮食/休息/生理/医疗 — 当前主要是AI自由生成，缺少预设事件模板库
- [ ] **服装更换命令**：直接换装命令（如 `/change top_inner "黑色T恤"`）
- [ ] **NPC AI自治**：NPC目前是静态数据，不会自主移动/做决策/发展关系
- [ ] **存档槽**：支持多个存档位（当前只有一个自动档）
- [ ] **时间跳过AI摘要**：narrator 参数在 skip_days 中未使用

### 5.2 中期

- [ ] **职业系统**：职业等级/薪资/晋升/失业事件
- [ ] **经济系统**：房租/账单/投资/资产管理
- [ ] **多角色模式**：控制多个角色，切换视角
- [ ] **Graph事件系统**：非线性剧情分支，事件前后置条件
- [ ] **关系网络可视化**：NPC之间的关系（不只是与玩家的关系）
- [ ] **AI记忆压缩增强**：真正的语义摘要压缩

### 5.3 长期

- [ ] **城市/世界模拟**：多个城市/区域/动态经济
- [ ] **自动世界生成**：AI根据初始Prompt生成整个世界的设定
- [ ] **Tauri桌面应用**：替代CLI
- [ ] **图像生成集成**：AI生成角色立绘/场景图
- [ ] **多人在线**：多个玩家的模拟器世界互通

---

## 附录: v0.3 → v0.3.1 变更记录

| # | 问题 | 解决 |
|---|------|------|
| 1 | `event_engine.py` 空壳 | 确认文件不存在且无引用，无需处理 |
| 2 | cleanliness 重复更新 | `game_loop.py:106` 加守卫：narrator 已返回 cleanliness 时跳过 activity-based 更新 |
| 3 | 自由文字模式 /move /interact 不可用 | 路由到完整子模式函数 `_run_move_mode()` / `_run_interact_mode()`，含 AI 叙事；`_handle_command()` 中移除裸壳处理器 |
| 4 | 节假日仅中国 | `settings.py` 新增 `HOLIDAY_COUNTRY`；`holidays.json` 增加 US(10) + JP(16)；`load_holidays()` 支持按国家过滤 |
| 5 | 角色创建 /skip /quit 混淆 | 新增 `_safe_input()` 包装器：`/skip` 跳过可选步/必填项拒绝，`/quit` 二次确认退出；补充缺失的 `_ask_class()` |

---

> 文档版本：v1.1 | Phase 1-3 完成（含扫尾） | 代码量：~3,330 行 Python | 下次更新：Phase 4 启动时
