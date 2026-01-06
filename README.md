# LoRA Arena

基于 ELO 评分机制的 LoRA Checkpoint 评估系统。通过双图对比投票，快速找出训练效果最好的 checkpoint。

## 功能特点

- **ELO 评分系统**: 经典 ELO 算法，科学评估 checkpoint 质量
- **双图对比**: 相同 seed/prompt，唯一变量是 LoRA，确保公平对比
- **排行榜**: 实时排名，ELO 历史趋势图
- **Checkpoint 管理**: 扫描导入、启用/禁用、元数据编辑
- **灵活配置**: Base Model、生成参数均可自由配置

## 技术栈

- **前端**: React + TypeScript + Vite + Tailwind CSS
- **后端**: FastAPI + SQLAlchemy + SQLite
- **图像生成**: ComfyUI API

## 快速开始

### 1. 安装后端依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 配置环境

复制 `.env.example` 为 `.env` 并根据需要修改：

```bash
cp .env.example .env
```

### 3. 启动后端

```bash
cd backend
uvicorn main:app --reload --port 8000
```

### 4. 安装前端依赖

```bash
cd frontend
npm install
```

### 5. 启动前端

```bash
npm run dev
```

### 6. 访问应用

打开浏览器访问 http://localhost:5173

## 使用流程

1. **配置 ComfyUI**: 在 Settings 页面配置 ComfyUI 服务器地址
2. **配置 LoRA 目录**: 设置你的 LoRA 文件存放路径
3. **导入 Checkpoint**: 在 Checkpoints 页面点击 "Scan Directory"
4. **开始对战**: 在 Arena 页面进行双图对比投票
5. **查看排行**: 在 Leaderboard 页面查看 ELO 排名

## API 端点

### Battles
- `POST /api/battles/new` - 创建新对战
- `POST /api/battles/{id}/vote` - 提交投票
- `GET /api/battles/history/list` - 获取历史对战

### Checkpoints
- `POST /api/checkpoints/scan` - 扫描导入 LoRA
- `GET /api/checkpoints` - 获取列表
- `PUT /api/checkpoints/{id}` - 更新元数据
- `PATCH /api/checkpoints/{id}/toggle` - 切换激活状态

### Leaderboard
- `GET /api/leaderboard` - 获取排行榜
- `GET /api/leaderboard/{id}/history` - 获取 ELO 历史

### Config
- `GET /api/config` - 获取配置
- `PUT /api/config` - 更新配置
- `GET /api/config/comfyui/status` - 检查 ComfyUI 连接状态
- `GET /api/config/comfyui/models` - 获取可用模型列表

## 项目结构

```
lorarena/
├── backend/
│   ├── main.py                 # FastAPI 入口
│   ├── config.py               # 配置管理
│   ├── requirements.txt
│   ├── routers/                # API 路由
│   │   ├── battles.py
│   │   ├── checkpoints.py
│   │   ├── leaderboard.py
│   │   └── config.py
│   ├── services/               # 业务逻辑
│   │   ├── elo_service.py
│   │   ├── battle_service.py
│   │   ├── checkpoint_service.py
│   │   ├── matchmaking_service.py
│   │   └── comfyui/
│   │       ├── client.py
│   │       └── workflow_builder.py
│   ├── models/                 # 数据模型
│   │   ├── database.py
│   │   └── schemas.py
│   └── db/
│       └── session.py
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── ArenaPage.tsx
│   │   │   ├── LeaderboardPage.tsx
│   │   │   ├── CheckpointsPage.tsx
│   │   │   └── SettingsPage.tsx
│   │   ├── components/
│   │   ├── services/
│   │   ├── hooks/
│   │   └── types/
│   └── ...
│
└── README.md
```

## License

MIT
