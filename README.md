# Lottery Foresee 项目说明

## 项目简介

`Lottery Foresee` 是一个针对 **双色球** 和 **大乐透** 的预测软件，基于历史开奖数据进行大数统计和概率建模，通过加权模拟与筛选给出每期 5 组推荐号码。

> 声明：本项目仅用于数学建模与编程学习研究，不构成任何形式的购彩建议或收益保证。

## 目录结构

- `backend/`：FastAPI 后端服务
  - `app/domain/`：核心领域模型、统计、模拟与打分逻辑
  - `app/services/`：数据加载、预测服务、回测与统计聚合
  - `app/routers/`：HTTP API 路由
  - `app/scripts/`：爬虫与回测脚本
  - `requirements.txt`：后端依赖
- `frontend/`：Vite + React 前端
- `docs/`：架构设计、任务跟踪、测试计划与收敛分析文档

## 后端使用说明

### 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 抓取历史数据

```bash
cd backend
python -m app.scripts.fetch_ssq
python -m app.scripts.fetch_dlt
```

执行成功后会在 `backend/data/` 下生成：

- `ssq_history.csv`
- `dlt_history.csv`

### 启动后端服务

```bash
cd backend
uvicorn app.main:app --reload
```

默认监听 `http://127.0.0.1:8000`。

### 主要接口

- `GET /health`：健康检查
- `POST /ssq/predict`：获取 5 组双色球推荐号码
- `POST /dlt/predict`：获取 5 组大乐透推荐号码
- `GET /ssq/stats/summary`：双色球历史统计汇总（频率、遗漏等）
- `GET /dlt/stats/summary`：大乐透历史统计汇总

回测脚本示例：

```bash
cd backend
python -m app.scripts.backtest_demo
```

## 前端使用说明

### 安装依赖并启动

```bash
cd frontend
npm install
npm run dev
```

默认访问 `http://127.0.0.1:5173`，通过 Vite 代理访问后端接口。

前端主要能力：

- 切换双色球 / 大乐透，一键生成 5 组推荐号码并展示打分
- 查看历史号码热度与遗漏情况（双色球红/蓝球、大乐透前区/后区）

## 测试与回测

在 `backend` 中运行单元测试：

```bash
cd backend
pytest
```

测试覆盖：

- 频率、遗漏等基础统计
- 组合生成与打分逻辑的基本正确性

回测与收敛分析设计请参考 `docs/convergence_analysis.md` 与 `backend/app/scripts/backtest_demo.py`。+
