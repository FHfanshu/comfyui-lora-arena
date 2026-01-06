# LoRA Arena (ComfyUI 自定义节点)

基于 ELO 评分机制的 Stable Diffusion LoRA 评估系统。通过在相同的提示词和种子下同时生成两张图片，科学评估不同 LoRA 权重的表现。

## 主要特点

- **ELO 评分系统**: 使用经典的 ELO 算法科学评估 LoRA 质量。
- **公平对比**: 相同的提示词和种子，LoRA 是唯一的变量，确保对比的公平性。
- **随机匹配**: 自动选择 LoRA 对，并具有稳定的随机分布算法。
- **动态提示词**: 从本地目录、预设或自定义列表中随机抽取提示词。
- **预生成 (Auto-Queue)**: 异步生成流程，投票后自动填充队列，大幅提升评测效率。
- **画布插件**: 直接在 ComfyUI 内使用的交互式投票和排行榜插件。
- **多语言支持**: 完整支持中英文界面。

## 安装方法

1. 将本仓库克隆或下载到 ComfyUI 的 `custom_nodes` 文件夹中：
   ```bash
   cd ComfyUI/custom_nodes
   git clone https://github.com/FHfanshu/comfyui-lora-arena
   ```
2. 安装依赖：
   ```bash
   pip install -r comfyui-lora-arena/comfyui-lorarena/requirements.txt
   ```
3. 重启 ComfyUI。

## 快速上手

1. **加载工作流**: 将 `comfyui-lorarena/examples/lorarena_battle_workflow.json` 导入 ComfyUI。
2. **扫描 LoRA**: 使用 `LoRArena Checkpoint Scanner` 节点索引你的 LoRA 文件。
3. **配置**: 点击右下角的 🏆 按钮，设置你的 LoRA 目录和提示词目录。
4. **开始对战**: 点击 "Queue Prompt" 开始对战。使用 `Battle Display` 部件进行投票。
5. **开启预生成**: 在设置中开启“预生成”，投票后会自动提交后续对战队列。

## 核心节点

- **LoRArena Random LoRA Pair**: 随机选取两个 LoRA 进行对比。
- **LoRArena Random Prompt**: 从不同来源选取随机提示词。
- **LoRArena Battle Display**: 交互式部件，用于查看图片并进行投票。
- **LoRArena Leaderboard Display**: 画布内挂件，显示实时 ELO 排名。
- **LoRArena Checkpoint Scanner**: 扫描目录将 LoRA 添加到评估数据库。

## 开源协议

MIT
