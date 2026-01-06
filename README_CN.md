# LoRA Arena（ComfyUI 自定义节点）

基于 ELO 评分机制的 LoRA Checkpoint 评估系统。通过双图对比投票，快速找出训练效果最好的 LoRA。

## 安装（ComfyUI）

1. 将 `comfyui-lorarena` 目录复制或软链接到 ComfyUI 的 `custom_nodes/`：
   - 示例路径：`F:\AI\ComfyUI\custom_nodes\comfyui-lorarena`
2. 安装依赖：
   ```bash
   pip install -r custom_nodes/comfyui-lorarena/requirements.txt
   ```
3. 重启 ComfyUI。

## 快速开始

1. 在 ComfyUI 中导入示例工作流：
   - `comfyui-lorarena/examples/lorarena_sdxl_basic.json`
2. 运行 `LoRArena Checkpoint Scanner` 扫描导入 LoRA。
3. 运行 `LoRArena Matchmaker` → `LoRArena Battle Generator` → `LoRArena Vote Recorder` 进行对战与投票。

## 节点列表

- **LoRArena Matchmaker**：对战匹配（balanced / random / exploration）
- **LoRArena Battle Generator**：双图生成（相同 prompt/seed，仅 LoRA 不同）
- **LoRArena Vote Recorder**：投票记录 + ELO 更新
- **LoRArena Leaderboard**：排行榜（JSON 输出）
- **LoRArena Checkpoint Scanner**：扫描 LoRA 并导入数据库
- **LoRArena ELO Display**：单个 LoRA 的 ELO 统计

## Web 面板（内嵌前端）

ComfyUI 顶部菜单会出现 “LoRArena 面板” 按钮，点击可打开内嵌前端页面。

> 注意：当前只提供了基础数据接口，前端完整功能（如对战生成等）仍在迁移中。

