# CLAUDE.md

为 Claude Code 提供本仓库代码指导。

## 项目概述

LoRA Arena 是 ComfyUI 的 ELO 评分 LoRA 对比系统。使用相同提示词和种子生成对比图像，LoRA 是唯一变量。用户投票后系统更新 ELO 评分。

## 安装

```bash
pip install -r requirements.txt
# 将此文件夹链接或复制到 ComfyUI/custom_nodes/
# 重启 ComfyUI
```

## 架构

### 入口 (`__init__.py`)
- 通过 `NODE_CLASS_MAPPINGS` 注册所有节点
- 自动检测语言（中/英）
- 在 `PromptServer.instance.routes` 注册 REST API（前缀 `/lorarena/api/`）
- `WEB_DIRECTORY = "web/js"` 用于前端组件

### 节点 (`nodes/`)
| 节点 | 功能 |
|------|------|
| `matchmaker.py` | 选择两个 LoRA 对战（source: database 数据库匹配 / directory 目录扫描） |
| `battle_generator.py` | 创建对战记录并生成双 LoRA 图像 |
| `battle_display.py` | 画布内显示两张图像及投票按钮 |
| `leaderboard_display.py` | 画布内显示 ELO 排行榜（支持 min_battles 过滤） |
| `elo_display.py` | 显示单个 checkpoint 的 ELO 统计 |
| `random_prompt.py` | 从预设/training_data目录/自定义列表选择提示词 |
| `checkpoint_scanner.py` | 扫描目录并注册 LoRA 到数据库（空值使用 config 默认） |
| `lora_loader.py` | 通过字符串加载 LoRA（非下拉菜单） |
| `panel_node.py` | 接收 CheckpointLoader 的 model/clip/vae |
| `vote_recorder.py` | 记录投票并更新对战状态 |
| `battle_types.py` | 对战数据类型定义 |

### 服务 (`services/`)
| 服务 | 职责 |
|------|------|
| `database.py` | SQLAlchemy 会话管理；SQLite 位于 `data/lorarena.db` |
| `models.py` | ORM 模型：`Checkpoint`, `Battle`, `ELOHistory` |
| `elo_service.py` | 动态 K 因子 ELO 计算 |
| `matchmaking_service.py` | 对手选择，支持淘汰模式过滤 |
| `battle_service.py` | 对战生命周期管理 |
| `checkpoint_service.py` | LoRA checkpoint CRUD 和扫描 |
| `battle_state.py` | 当前对战全局状态 |
| `model_state.py` | Panel Node 加载的 model/clip/vae 状态 |
| `comfyui_generator.py` | 使用 ComfyUI API 内部生成图像 |
| `training_data_service.py` | 训练数据目录扫描 |

### 前端 (`web/js/`)
- `lorarena_extension.js`：注册扩展，添加启动按钮，管理配置面板
- `battle_display_widget.js`：画布内投票 UI
- `leaderboard_display_widget.js`：ELO 排行榜显示
- `panel_widget.js`：面板节点组件
- `voting_widget.js`：共享投票按钮组件

### 数据流
1. **初始化**：`CheckpointScanner` 将 LoRA 文件索引到 SQLite
2. **匹配**：`Matchmaker` 根据策略选择两个 LoRA
3. **生成**：`BattleGenerator` 创建对战，使用相同 seed/prompt 生成图像
4. **投票**：`BattleDisplay` 显示图像，用户通过 API 投票
5. **更新**：处理投票，重新计算 ELO，记录历史

### REST API（在 `__init__.py` 注册）
- `GET /lorarena/api/leaderboard` - 排行榜
- `GET /lorarena/api/leaderboard/{id}/history` - ELO 历史
- `POST /lorarena/api/battles/new` - 创建对战
- `GET /lorarena/api/battles/{id}` - 获取对战状态
- `POST /lorarena/api/battles/{id}/vote` - 提交投票
- `GET /lorarena/api/battles/history/list` - 对战历史分页
- `GET /lorarena/api/checkpoints` - 列出所有 checkpoint
- `POST /lorarena/api/checkpoints/scan` - 触发扫描
- `GET/PUT /lorarena/api/checkpoints/{id}` - 获取/更新 checkpoint
- `PATCH /lorarena/api/checkpoints/{id}/toggle` - 切换激活状态
- `POST /lorarena/api/checkpoints/batch-delete` - 批量删除
- `POST /lorarena/api/checkpoints/batch-status` - 批量启用/禁用
- `GET/PUT /lorarena/api/config` - 配置管理
- `GET /lorarena/api/config/comfyui/models` - 可用模型/采样器
- `GET /lorarena/api/node/battle/current` - 当前对战
- `POST /lorarena/api/node/battle/vote` - 组件投票
- `GET /lorarena/api/node/models-ready` - Panel Node 状态
- `GET /lorarena/images/{filename}` - 提供对战图像

## 配置

`data/config.json`（首次运行创建）：
- `lora_directory`：LoRA 路径（相对于 ComfyUI 的 lora 目录）
- `base_model`：SD checkpoint 文件名
- `steps`, `cfg_scale`, `sampler`, `scheduler`：生成参数
- `lora_strength`：LoRA 强度（默认 0.8）
- `width`, `height`：图像尺寸
- `mode`：`"host"`（完全控制）或 `"guest"`（仅投票）
- `prompt_prefix`：提示词前缀
- `battle_royale_enabled`, `battle_royale_threshold`, `battle_royale_win_rate`：淘汰模式
- `auto_queue_enabled`, `auto_queue_count`, `auto_queue_target`, `auto_queue_max`：自动队列
- `parallel_generation`：同时生成两张图像（默认 true）
- `training_data_directory`：训练数据目录
- `worker_enabled`, `worker_interval`, `worker_target_cache`, `worker_use_training_tags`：后台工作器
- `remote_comfyui`：远程 ComfyUI 模式
- `tipo_tag_length`：TIPO 标签长度

## 代码规范

- **Python**：PEP 8，4 空格缩进
- **JavaScript**：ComfyUI 组件模式；通过 `/lorarena/api/` 通信
- **数据库**：同步 SQLAlchemy，使用 `session_scope()` 上下文管理器

## 测试

无自动化测试。验证更改：
1. 安装扩展到 ComfyUI 的 `custom_nodes/`
2. 加载 `examples/` 中的示例工作流
3. 测试节点连接和投票流程
4. 做完改动后commit and push到main分支
