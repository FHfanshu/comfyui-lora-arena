# LoRArena 示例工作流

## 节点说明

### Random LoRA Pair (随机LoRA对)

从指定子目录随机选择两个 LoRA 文件。

**输入:**
- `lora_directory`: 相对路径，如 `748` 或 `styles/748cm`

**输出:**
- `lora_a`: LoRA A 路径 (如 `748\xxx.safetensors`)
- `lora_b`: LoRA B 路径
- `seed`: 随机种子

### Random Prompt (随机提示词)

随机选择提示词。

**输入:**
- `mode`: `preset` / `directory` / `custom`
- `prompt_directory`: txt 文件目录路径

**输出:**
- `prompt`: 提示词
- `negative`: 负向提示词
- `seed`: 种子

## 使用方法

1. 添加 `Random LoRA Pair` 节点
2. 设置 `lora_directory` 为你的 LoRA 子目录名
3. 连接 `lora_a` 和 `lora_b` 到两个 LoRA Loader
4. 连接 `seed` 到 KSampler 确保一致性
