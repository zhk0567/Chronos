# Chronos

个人心理健康洞察系统。从纵向日记文本出发，自动识别情绪锚点、促进与损害因素，生成有证据支持的结构化洞察报告。

## 功能（一期）

- 日记导入（Echo entries、JSON、txt）
- 形态分类与信息单元抽取（Ollama LLM + 启发式兜底）
- 六类锚点涌现检测
- 情绪时间序列与稳定性分析
- 促进/损害/伪促进因素识别
- 关系网络、语言模式、主题生命周期分析
- 六板块结构化报告 + HTML/JSON 导出

## 技术栈

- **桌面端**：Electron 33 + React 18 + TypeScript + Vite
- **分析引擎**：Python 3.11+（FastAPI、pandas、scipy、networkx、jieba）
- **语义抽取**：本地 Ollama（默认 `minimax-m3:cloud`）
- **数据**：本地 `data/` 目录（JSON 文件）

## 环境要求

- Node.js 18+
- Python 3.11+
- （推荐）Ollama 本地运行

## 快速开始

```powershell
cd F:\commercial\Chronos

# 推荐：使用 start.ps1（已配置 UTF-8，避免终端中文乱码）
.\start.ps1

# 或手动启动
npm install
pip install -e ./engine
npm run dev
```

> **终端中文乱码**：请通过 `.\start.ps1` 或 `npm run dev` 启动（内部会设置 UTF-8 代码页）。不要直接在未配置编码的终端里运行 `vite`。

## 从 Echo 导入

1. 启动 Chronos 时会自动从同级 `Echo/entries/` 同步**今年**日记到 `data/entries/`
2. 也可在「导入」页点击「同步 Echo 今年日记」
3. 或运行 `.\scripts\sync-data.ps1`

仅 **当年**日记参与分析与展示，往年数据不会导入本地。

## 数据目录

```
data/
├── entries/     # 当年日记 JSON（仅 YYYY-MM-DD.json）
├── meta/        # Echo 辅助数据（如 name-watchlist.json）
├── analysis/    # 分析中间结果
└── reports/     # 导出报告
```

手动同步：

```powershell
.\scripts\sync-data.ps1
```

## 隐私原则

- 日记原文在本地处理，不上传云端
- 分析结论区分「原文明说」与「系统推断」
- 缺失数据不插补、不猜测
