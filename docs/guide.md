# Lottery Foresee 使用指南（guide.md）

## 一、项目功能概览

本项目针对 **双色球** 和 **大乐透**：

- 基于历史开奖数据做 **大数统计 + 概率建模**；
- 通过加权模拟生成大量候选组合并打分；
- 为每种彩票给出 **5 组推荐号码**；
- 支持查看历史号码热度 / 遗漏情况；
- 提供回测脚本，用于“预测 vs 实际”的差异与收敛分析。

> 说明：所有功能仅用于 **数学和编程学习研究**，不构成任何投资或购彩建议。

---

## 二、运行环境准备

### 1. 基本依赖

- 操作系统：macOS / Linux（推荐）
- 已安装：
  - Python 3.10+
  - Node.js 18+ / 20+（推荐）
  - npm / pnpm / yarn（三选一，本指南以 `npm` 为例）

### 2. 目录结构快速浏览

- `backend/`：FastAPI 后端
  - `app/domain/`：模型、统计、模拟与打分
  - `app/services/`：数据加载、预测、回测、统计汇总
  - `app/routers/`：API 路由
  - `app/scripts/`：爬虫和回测脚本
  - `tests/`：后端单元测试
- `frontend/`：Vite + React 前端
- `docs/`：文档（架构、任务、测试、收敛分析、本指南等）
- `dev.sh`：一键开发脚本（启动 / 停止 / 重启 / 抓数 / 测试）

---

## 三、后端（backend）详细说明

### 1. 安装 Python 依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 历史数据（可选）

- **首次直接启动**：若 `backend/data/` 下没有 `ssq_history.csv` 或 `dlt_history.csv`，执行 `./dev.sh start` 时会自动生成示例数据，保证打开即可用。
- **使用真实历史数据**：在项目根目录执行 `./dev.sh fetch-data`（需网络），会从数据源抓取并写入 `backend/data/`。也可在 backend 目录下手动执行 `python -m app.scripts.fetch_ssq` 与 `python -m app.scripts.fetch_dlt`。

抓取或生成后，在 `backend/data/` 下会看到：

- `ssq_history.csv`
- `dlt_history.csv`

### 3. 启动后端服务

```bash
cd backend
uvicorn app.main:app --reload
```

默认监听：`http://127.0.0.1:8000`

### 4. 关键 API 一览

- **健康检查**
  - `GET /health`

- **预测接口**
  - `POST /ssq/predict`
    - 查询参数（可选）：
      - `window_size`：统计窗口期数（默认 config 中设置）
      - `sample_size`：模拟候选组合数量
      - `recommend_count`：返回推荐组数（默认 5）
      - `seed`：随机种子（便于复现）
  - `POST /dlt/predict`
    - 参数含义与双色球类似

- **历史统计接口**
  - `GET /ssq/stats/summary`
    - 返回红/蓝球的出现次数、概率、当前遗漏值等
  - `GET /dlt/stats/summary`
    - 返回前区 / 后区号码的统计信息

- **回测脚本（命令行）**
  - `python -m app.scripts.backtest_demo`
    - 使用固定参数对近期若干期做简单回测，输出平均命中情况。

---

## 四、前端（frontend）详细说明

### 1. 安装前端依赖

```bash
cd frontend
npm install
```

### 2. 启动前端开发服务器

```bash
cd frontend
npm run dev
```

默认地址：`http://127.0.0.1:5173`

Vite 已在 `vite.config.ts` 中配置了代理，将 `/ssq` / `/dlt` / `/health` 等请求转发到 `http://127.0.0.1:8000`。

### 3. 前端页面功能

- 顶部 Tab：
  - **双色球**：调用 `/ssq/predict`，展示 5 组红 + 蓝推荐号码及打分；
  - **大乐透**：调用 `/dlt/predict`，展示 5 组前区 + 后区推荐号码及打分；
  - **历史统计**：调用 `/ssq/stats/summary` 与 `/dlt/stats/summary`，以进度条形式展示各号码的概率与遗漏值。

---

## 五、dev.sh 一键脚本使用说明

项目根目录提供了 `dev.sh` 脚本，用于统一管理：

- 启动 / 停止 / 重启 **后端 + 前端**
- 一键抓取数据
- 一键运行后端测试

> 所有命令请在项目根目录执行：`/Users/macos/dev/lottery_foresee`

### 1. 基础用法

```bash
# 赋予执行权限（首次）
chmod +x dev.sh

# 启动后端 + 前端
./dev.sh start

# 停止后端 + 前端
./dev.sh stop

# 重启（相当于 stop + start）
./dev.sh restart

# 仅抓取最新历史数据（不会启动服务）
./dev.sh fetch-data

# 运行后端 pytest 单元测试
./dev.sh test
```

### 2. 脚本内部约定（简要说明）

- 后端：
  - 使用 `uvicorn app.main:app --reload --port 8000` 启动；
  - 进程 ID 写入 `backend/.dev_backend.pid`。
- 前端：
  - 在 `frontend/` 内执行 `npm run dev`；
  - 进程 ID 写入 `frontend/.dev_frontend.pid`。
- `stop` / `restart` 命令会读取对应 PID 文件并尝试 `kill` 该进程，避免产生僵尸进程。

---

## 六、推荐的开发流程

1. 克隆 / 解压项目后，先阅读：
   - `README.md`（总览）
   - `docs/guide.md`（本文件）
2. 后端：
   - `cd backend && pip install -r requirements.txt`
   - `python -m app.scripts.fetch_ssq` + `python -m app.scripts.fetch_dlt`
   - （可选）`pytest` 验证基础逻辑
3. 前端：
   - `cd frontend && npm install`
4. 一键启动：
   - 回到根目录 `./dev.sh start`
   - 浏览器访问 `http://127.0.0.1:5173` 使用界面

---

## 七、后续扩展建议

- 在 `docs/convergence_analysis.md` 的基础上：
  - 增强回测逻辑（多组预测、不同策略对比）；
  - 将回测数据以 API 方式暴露，并在前端增加折线 / 柱状图。
- 引入更多数学模型（如简单马尔可夫链、模式聚类等），对预测逻辑做 A/B 测试。
- 接入 CI（例如 GitHub Actions），自动跑 `pytest` 和前端构建检查。

如果你希望在某一块（数学模型、爬虫、前端图表等）继续深入，我可以在此基础上再帮你细化设计或实现方案。

