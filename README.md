# Lottery Foresee（双色球 / 大乐透概率建模预测）

`Lottery Foresee` 是一个用于学习与研究的彩票网号码预测/统计项目，主要包含：

- 基于历史开奖数据进行“大数统计”和概率建模
- 使用加权模拟生成候选组合并打分排序
- 给出双色球/大乐透每次推荐（可配置推荐组数，默认 5 组）
- 在主推荐之后追加 1 注「💥 震荡推荐」（基于主推荐做扰动重组，引入冷门号）
- 记录每次生成结果（历史生成记录）
- 支持“预测与真实开奖比对”（用于差异分析与后续修正）
- 前端提供页面：推荐、历史统计、历史记录、比对结果展示

> 声明：本项目仅用于数学建模与编程学习研究，不构成任何购彩建议或收益保证。

## 仓库结构

- `backend/`：FastAPI 后端（预测、统计、历史记录、比对、数据拉取接口）
  - `backend/app/domain/`：统计、模拟、打分等核心逻辑
  - `backend/app/services/`：服务层（预测服务、历史记录服务、比对服务、调度服务等）
  - `backend/app/routers/`：HTTP API 路由
  - `backend/app/scripts/`：数据抓取脚本（可选）
  - `backend/tests/`：后端单元测试
- `frontend/`：Vite + React 前端（UI 与调用后端接口）
- `docs/`：项目文档（架构、任务计划、测试计划、收敛分析设计、使用指南）
- `dev.sh`：一键启动/停止/拉取数据/运行测试

## 环境要求（建议）

后端：

- Python：3.9+（本项目开发环境使用 3.9）
- 需要网络（仅在执行数据抓取脚本时使用；否则可使用本地示例数据）

前端：

- Node.js：18+（建议与项目兼容版本一致）
- npm：用于安装依赖与启动 Vite

工具：

- 推荐使用 `git` 管理代码与提交

## 关键数据文件说明

后端读取历史开奖数据的默认路径：

- `backend/data/ssq_history.csv`
- `backend/data/dlt_history.csv`

在你首次启动时（如果这些文件不存在），后端会自动生成一份示例数据以保证“开箱可用”。

> 若你希望使用真实历史数据：需要执行 `./dev.sh fetch-data` 或调用后端抓取接口（见下文）。

## 快速开始（推荐）

### 1）启动前：安装依赖

#### 后端（推荐使用虚拟环境）

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

#### 前端

```bash
cd frontend
npm install
```

### 2）一键启动

在仓库根目录执行：

```bash
cd /path/to/lottery_foresee
./dev.sh start
```

- 前端：`http://127.0.0.1:5173/`
- 后端：`http://127.0.0.1:8000/health`

### 3）一键抓取真实历史数据（可选）

如果你希望用真实开奖数据而不是示例数据：

```bash
./dev.sh fetch-data
```

抓取结果将写入：

- `backend/data/ssq_history.csv`
- `backend/data/dlt_history.csv`

> 数据抓取依赖第三方页面结构，若页面结构变更可能导致解析失败；失败时请查看后端日志并可回退到示例数据。

## 前端如何使用

打开 `http://127.0.0.1:5173/`：

1. 选择 Tab：
   - `双色球`
   - `大乐透`
   - `历史统计`
   - `历史记录`
2. 生成推荐：
   - 可在“推荐组数”处设置一次生成返回的组数（1–20）
   - 默认提供“自动拉取（基于上次拉取时间判定）”开关
   - 点击“生成推荐”后，页面会展示推荐号码与每组分数
3. 历史记录与比对：
   - 每次生成会写入历史记录文件（后端自动保存）
   - 在 `历史记录` 页点击“执行比对”，即可展示每条记录对应的实际期号/开奖日与命中差异

## 后端 API（用于开发/调试）

健康检查：

- `GET /health`

下一期信息（按开奖日期规律推算）：

- `GET /ssq/next` → `{"issue":"xxxx","draw_date":"YYYY-MM-DD"}`
- `GET /dlt/next` → `{"issue":"xxxx","draw_date":"YYYY-MM-DD"}`

预测接口（返回推荐 1–20 组，默认取配置/参数）：

- `POST /ssq/predict`
  - Query 参数：
    - `recommend_count`（1–20，可选）
    - `window_size`（可选）
    - `sample_size`（可选）
    - `seed`（可选）
    - `use_correction`（可选，是否启用历史比对修正；当前在比对样本不足时退化为不修正）
  - 返回：`[{reds:[...6], blue:int, score:float, kind:"main"|"shock"}, ...]`
  - 默认在 `recommend_count` 组主推荐之后追加 1 注 `kind="shock"` 的震荡推荐（共 `N+1` 项）
- `POST /dlt/predict` 同理，返回前区/后区组合 + score + kind

历史统计汇总：

- `GET /ssq/stats/summary`
- `GET /dlt/stats/summary`

历史生成记录（最近记录）：

- `GET /ssq/history?limit=50`
- `GET /dlt/history?limit=50`

比对接口：

- `POST /data/compare`
  - 返回汇总 + 明细（明细用于前端逐条展示命中差异）
- `GET /ssq/hit-stats`
- `GET /dlt/hit-stats`

数据拉取接口：

- `POST /data/fetch-ssq` / `POST /data/fetch-dlt`（直接拉取，可能需要网络）
- `POST /data/ensure-fresh/{lottery}`
  - 根据后端保存的“上次拉取时间”判断是否需要拉取（用于前端自动拉取逻辑）

算法说明：

- `GET /algorithm`

## 震荡推荐（Shock Recommendation）

主推荐基于概率收敛，会反复命中"热门号码"。为了在不放弃概率信号的前提下留一份"反向探索"的可能性，每次预测会**额外生成 1 注震荡推荐**，附加在主推荐列表末尾（`kind="shock"`）。

生成方式：

1. **保留基底**：从主推荐 N 组里收集所有出现过的号码，按出现次数加权抽取若干个作为"继承号码"
   - 双色球红球继承 3 个，蓝球以 50% 概率从主推荐继承；
   - 大乐透前区继承 2 个，后区继承 1 个；
2. **冷门补全**：剩余位置只从"主推荐里**未出现**的号码"中抽取，权重为 `α · 反向概率 + (1-α) · 均匀`（默认 α=0.6），让低频/冷门号也有合理机会；
3. 同样会被打分并写入历史记录，参与后续比对统计。

行为约束：

- 主推荐的随机种子 (`seed`) 不影响震荡注的生成 RNG，两者互不污染；
- 服务层可通过 `include_shock=False` 关闭（默认开启）；
- 飞书卡片与前端 UI 都会用紫色徽章 "💥 震荡推荐" 单独标识。

## 自动拉取与比对对齐逻辑（简述）

- 预测写入历史记录时，会同时保存“目标期号/目标开奖日”（由 `GET /ssq/next`、`GET /dlt/next` 的推算逻辑产生）
- 比对时优先使用：
  - `history_record.target_issue` 去匹配真实开奖数据的 `issue`
  - 匹配不到时才回退到“按生成时间最近一期”的策略（用于兼容旧记录）

## 测试

在 `backend/` 目录运行：

```bash
cd backend
source .venv/bin/activate
pytest
```

## 开发脚本（dev.sh）

在仓库根目录：

- `./dev.sh start`：启动后端 + 前端
- `./dev.sh stop`：停止后端 + 前端
- `./dev.sh restart`：重启
- `./dev.sh fetch-data`：抓取真实历史数据
- `./dev.sh test`：运行后端 pytest

## 飞书自动通知（GitHub Actions）

项目内置 GitHub Actions 工作流（`.github/workflows/lottery-notify.yml`），可在每个开奖日自动生成推荐并推送到飞书机器人。

### 推送频率

工作流在北京时间 **每天 10:00**（UTC 02:00）触发，默认 `auto` 模式 **每天都会推送双色球 + 大乐透两组预测**，确保提前覆盖最近一期开奖。

支持的彩种模式：

| 模式 | 行为 |
|---|---|
| `auto`（默认） | 每天推 SSQ + DLT |
| `both` | 等同 auto |
| `ssq` / `dlt` | 仅推该单一彩种 |
| `draw_day` | 仅推当天开奖的彩种（SSQ：二/四/日；DLT：一/三/六；周五跳过） |

### 配置 GitHub Secrets

在仓库 `Settings → Secrets and variables → Actions` 中添加：

| Secret 名称 | 必填 | 说明 |
|---|---|---|
| `FEISHU_WEBHOOK_URL` | 是 | 形如 `https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxx` |
| `FEISHU_WEBHOOK_SECRET` | 启用「签名校验」时必填 | 飞书机器人创建时分配的 token |

### 手动触发 / 调试

在 `Actions → Lottery Notify` 中选择 `Run workflow`，可指定：

- `lottery`：`auto`（默认按周几）/ `ssq` / `dlt` / `both`
- `recommend_count`：推荐组数
- `dry_run`：`true` 仅生成不发送

### 本地手动推送

```bash
cd backend
source .venv/bin/activate
export FEISHU_WEBHOOK_URL='https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxx'
export FEISHU_WEBHOOK_SECRET='your-token'
python -m app.scripts.notify_predictions             # 按当天周几自动判断
python -m app.scripts.notify_predictions --lottery ssq
python -m app.scripts.notify_predictions --dry-run --lottery both
```

## 免责声明

彩票属于随机事件，本项目提供的是编程与统计建模学习用途，任何预测结果不代表未来真实结果，也不构成任何投资/购彩建议。

