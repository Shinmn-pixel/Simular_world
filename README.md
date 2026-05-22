# 🧠 AI 驱动人生模拟器

> AI-driven Life Simulator — 融合状态模拟、AI 叙事、世界规则引擎与记忆系统的可扩展框架

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## 概述

一个类似 **SillyTavern + 人生模拟器 + 规则引擎** 的 AI 叙事框架。玩家创建自定义角色，在 AI 驱动的世界中体验每一天的生活。系统模拟真实的生理需求、社交关系、时间流逝，AI 根据上下文生成沉浸式故事。

### 核心特性

- **双模式交互**：自由文字模式（任意输入，AI 即兴叙事）与选项模式（AI 生成事件 + 选项分支）
- **深度生理模拟**：体力/心情/金钱 + 饱腹度/睡眠欲/性欲/健康/洁净度/容貌度，10 条联动规则
- **女性生理周期**：28 天完整周期（PMS + 经期），联动体力/心情/健康
- **社交系统**：5 种关系类型（伴侣/亲人/亲友/朋友/陌生人），好感度 -100~100，关系越深负面互动影响越小
- **位置系统**：17 个场景（家/大学/商业街 + 子位置），支持移动、场景互动、NPC 在场
- **服装系统**：12 层分件穿搭，AI 在叙事中自然融入穿着描述
- **真实日历**：公历时间（年/月/日/时/分），中国法定节假日自动匹配
- **世界书规则引擎**：15 条预设规则，支持状态触发/关键词触发/时间触发
- **记忆系统**：长期记忆存储与检索，每 7 天自动压缩
- **时间跳过**：可跳过 N 天，AI 自动结算状态变化并生成摘要

## 技术栈

| 层面 | 选择 |
|------|------|
| 语言 | Python 3.11+ |
| AI 接口 | OpenAI 兼容 API（支持 DeepSeek / Ollama / 任意第三方端点） |
| 数据存储 | JSON 文件 |
| 前端 | 命令行 CLI（预留 Web UI 接口） |

## 快速开始

### 环境要求

- Python 3.11+
- 可用的 OpenAI 兼容 API（如 [DeepSeek](https://platform.deepseek.com/)、[Ollama](https://ollama.com/) 本地模型等）

### 安装

```bash
git clone <repo-url>
cd simular-world
pip install -r requirements.txt
```

### 配置

编辑 `.env` 文件，填入你的 API 信息：

```bash
OPENAI_API_KEY=sk-your-key-here
OPENAI_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
GAME_MODE=free_text
TURNS_PER_DAY=5
```

### 运行

```bash
python main.py
```

或双击 `run.bat`（Windows）。

首次运行会进入角色创建向导，之后即可开始游戏。

## 游戏模式

### 自由文字模式（默认）

输入任意文字描述你想做的事情，AI 据此生成叙事并结算状态。

```
> 我想去便利店买点吃的，然后回家洗个澡早点睡觉
```

### 选项模式

AI 生成每日事件和选项，玩家通过数字选择。包含三个子模式：

| 子模式 | 说明 | 触发 |
|--------|------|------|
| 📖 剧情 | AI 生成事件 + 分支选项 | 选项模式默认 |
| 🚶 移动 | 移动到其他位置，触发场景操作 | `/move` |
| 🤝 互动 | 与在场 NPC 或物品互动 | `/interact` |

## 命令列表

| 命令 | 说明 |
|------|------|
| `/mode free` | 切换到自由文字模式 |
| `/mode choice` | 切换到选项模式 |
| `/move` | 移动到其他位置 |
| `/interact` | 与当前位置 NPC/物品互动 |
| `/skip N` | 跳过 N 天（AI 自动结算） |
| `/relationship` | 查看 NPC 好感度 |
| `/outfit` | 查看当前服装 |
| `/next` | 手动推进一天 |
| `/save` | 保存游戏 |
| `/status` | 显示完整状态面板 |
| `/help` | 显示帮助 |
| `/quit` | 退出并保存 |

## 项目结构

```
simular-world/
├── main.py                    # 入口
├── config/
│   ├── settings.py            # 全局配置
│   ├── character_card.json    # 角色卡
│   ├── world_prompt.txt       # 世界设定
│   ├── locations.json         # 位置图谱
│   └── holidays.json          # 节假日数据
├── src/
│   ├── core/                  # 核心循环 + 状态管理
│   ├── ai/                    # AI 管线（Narrator / Planner / Executor）
│   ├── systems/               # 业务系统（8 个模块）
│   │   ├── calendar_utils.py  # 日历时间
│   │   ├── clothing.py        # 服装系统
│   │   ├── social.py          # 社交系统
│   │   ├── position.py        # 位置系统
│   │   ├── appearance.py      # 容貌系统
│   │   ├── cleanliness.py     # 洁净度系统
│   │   └── time_skip.py       # 时间跳过
│   ├── world/                 # 世界书规则引擎
│   ├── memory/                # 记忆系统
│   ├── ui/                    # UI 抽象层
│   └── utils/                 # 工具
└── data/save/                 # 存档
```

## 路线图

- [x] 核心游戏循环（双模式）
- [x] 生理系统 + 联动规则
- [x] AI 双管线（Narrator / Planner + Executor）
- [x] 世界书规则引擎
- [x] 记忆系统
- [x] 日历 + 节假日
- [x] 服装系统
- [x] 社交系统
- [x] 位置系统（17 个场景）
- [x] 时间跳过
- [ ] Web UI
- [ ] 职业系统
- [ ] NPC AI 自治
- [ ] 经济系统
- [ ] 多角色模式

## 使用方法

目前暂无GUI的情况下，直接下载源文件解压后运行run.bat即可
通过记事本打开位于根目录下的.env输入你的baseURL、API key以及模型名称以确保AI大模型能正常运行

## 许可

MIT License
