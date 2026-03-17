import React, { useState } from "react";
import axios from "axios";

type SsqRecommendation = {
  reds: number[];
  blue: number;
  score: number;
};

type DltRecommendation = {
  fronts: number[];
  backs: number[];
  score: number;
};

type Tab = "ssq" | "dlt" | "stats" | "history";

type HistoryRecord = {
  id: string;
  lottery_type: string;
  created_at: string;
  target_issue?: string | null;
  target_date?: string | null;
  params: { recommend_count?: number };
  results: Array<{ reds?: number[]; blue?: number; fronts?: number[]; backs?: number[]; score: number }>;
};

type NextInfo = { issue: string; draw_date: string };
type CompareDetail =
  | { record_id: string; target_issue?: string | null; issue: string; draw_date: string; hit_reds: number; hit_blue: number }
  | { record_id: string; target_issue?: string | null; issue: string; draw_date: string; hit_fronts: number; hit_backs: number };

type NumberStat = {
  number: number;
  count: number;
  probability: number;
  omission: number;
};

type SsqStatsSummary = {
  total_draws: number;
  reds: NumberStat[];
  blues: NumberStat[];
};

type DltStatsSummary = {
  total_draws: number;
  fronts: NumberStat[];
  backs: NumberStat[];
};

const pad2 = (n: number) => String(n).padStart(2, "0");

function formatSsqCopy(item: SsqRecommendation): string {
  const redStr = (item.reds as number[]).map(pad2).join(" ");
  return `红球: ${redStr} 蓝球: ${pad2(item.blue)}`;
}

function formatDltCopy(item: DltRecommendation): string {
  const frontStr = (item.fronts as number[]).map(pad2).join(" ");
  const backStr = (item.backs as number[]).map(pad2).join(" ");
  return `前区: ${frontStr} 后区: ${backStr}`;
}

export const App: React.FC = () => {
  const [tab, setTab] = useState<Tab>("ssq");
  const [ssq, setSsq] = useState<SsqRecommendation[]>([]);
  const [dlt, setDlt] = useState<DltRecommendation[]>([]);
  const [ssqStats, setSsqStats] = useState<SsqStatsSummary | null>(null);
  const [dltStats, setDltStats] = useState<DltStatsSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recommendCount, setRecommendCount] = useState(5);
  const [copyTip, setCopyTip] = useState<string | null>(null);
  const [ssqHistory, setSsqHistory] = useState<HistoryRecord[]>([]);
  const [dltHistory, setDltHistory] = useState<HistoryRecord[]>([]);
  const [expandedHistoryId, setExpandedHistoryId] = useState<string | null>(null);
  const [compareResult, setCompareResult] = useState<{ ssq?: { total_compared: number; avg_red_hits: number; avg_blue_hits: number }; dlt?: { total_compared: number; avg_front_hits: number; avg_back_hits: number } } | null>(null);
  const [compareDetailsByRecord, setCompareDetailsByRecord] = useState<Record<string, CompareDetail[]>>({});
  const [ssqNext, setSsqNext] = useState<NextInfo | null>(null);
  const [dltNext, setDltNext] = useState<NextInfo | null>(null);

  const copyToClipboard = async (text: string, tip: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopyTip(tip);
      setTimeout(() => setCopyTip(null), 1500);
    } catch {
      setCopyTip("复制失败");
      setTimeout(() => setCopyTip(null), 1500);
    }
  };

  const fetchSsq = async (opts?: { fetchDataFirst?: boolean }) => {
    setLoading(true);
    setError(null);
    try {
      if (opts?.fetchDataFirst) {
        try {
          await axios.post("/data/ensure-fresh/ssq");
        } catch (e) {
          setError("拉取双色球数据失败，请检查网络或稍后重试");
          setLoading(false);
          return;
        }
      }
      const res = await axios.post<SsqRecommendation[]>("/ssq/predict", null, {
        params: { recommend_count: recommendCount, use_correction: useCorrection }
      });
      setSsq(res.data);
    } catch (e) {
      setError("获取双色球推荐失败");
    } finally {
      setLoading(false);
    }
  };

  const fetchDlt = async (opts?: { fetchDataFirst?: boolean }) => {
    setLoading(true);
    setError(null);
    try {
      if (opts?.fetchDataFirst) {
        try {
          await axios.post("/data/ensure-fresh/dlt");
        } catch (e) {
          setError("拉取大乐透数据失败，请检查网络或稍后重试");
          setLoading(false);
          return;
        }
      }
      const res = await axios.post<DltRecommendation[]>("/dlt/predict", null, {
        params: { recommend_count: recommendCount, use_correction: useCorrection }
      });
      setDlt(res.data);
    } catch (e) {
      setError("获取大乐透推荐失败");
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    setLoading(true);
    setError(null);
    try {
      const [ssqRes, dltRes] = await Promise.all([
        axios.get<SsqStatsSummary>("/ssq/stats/summary"),
        axios.get<DltStatsSummary>("/dlt/stats/summary")
      ]);
      setSsqStats(ssqRes.data);
      setDltStats(dltRes.data);
    } catch (e) {
      setError("获取统计数据失败");
    } finally {
      setLoading(false);
    }
  };

  const fetchHistory = async () => {
    setLoading(true);
    setError(null);
    try {
      const [ssqRes, dltRes] = await Promise.all([
        axios.get<HistoryRecord[]>("/ssq/history"),
        axios.get<HistoryRecord[]>("/dlt/history")
      ]);
      setSsqHistory(ssqRes.data);
      setDltHistory(dltRes.data);
    } catch (e) {
      setError("获取历史记录失败");
    } finally {
      setLoading(false);
    }
  };

  const fetchNextInfo = async () => {
    try {
      const [ssqRes, dltRes] = await Promise.all([
        axios.get<NextInfo>("/ssq/next"),
        axios.get<NextInfo>("/dlt/next")
      ]);
      setSsqNext(ssqRes.data);
      setDltNext(dltRes.data);
    } catch {
      // ignore
    }
  };

  const runCompare = async () => {
    setError(null);
    try {
      const res = await axios.post<{
        ok: boolean;
        ssq: { total_compared: number; avg_red_hits: number; avg_blue_hits: number };
        dlt: { total_compared: number; avg_front_hits: number; avg_back_hits: number };
        details: { ssq: CompareDetail[]; dlt: CompareDetail[] };
      }>("/data/compare");
      setCompareResult({ ssq: res.data.ssq, dlt: res.data.dlt });
      const map: Record<string, CompareDetail[]> = {};
      for (const d of [...(res.data.details?.ssq || []), ...(res.data.details?.dlt || [])]) {
        const key = (d as { record_id: string }).record_id;
        if (!map[key]) map[key] = [];
        map[key].push(d);
      }
      setCompareDetailsByRecord(map);
    } catch (e) {
      setError("比对失败");
    }
  };

  const [autoFetchEnabled, setAutoFetchEnabled] = useState(true);
  const [useCorrection, setUseCorrection] = useState(false);
  const currentList = tab === "ssq" ? ssq : dlt;

  // 首次渲染后拉取下一期信息（无需每次都请求）
  React.useEffect(() => {
    fetchNextInfo();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleGenerate = () => {
    const opts = { fetchDataFirst: autoFetchEnabled };
    if (tab === "ssq") fetchSsq(opts);
    else fetchDlt(opts);
  };

  const copyOne = (item: SsqRecommendation | DltRecommendation) => {
    const text = tab === "ssq" ? formatSsqCopy(item as SsqRecommendation) : formatDltCopy(item as DltRecommendation);
    copyToClipboard(text, "已复制");
  };

  const copyAll = () => {
    const lines = currentList.map((item) =>
      tab === "ssq" ? formatSsqCopy(item as SsqRecommendation) : formatDltCopy(item as DltRecommendation)
    );
    copyToClipboard(lines.join("\n"), "已复制全部");
  };

  return (
    <div style={{ maxWidth: 960, margin: "0 auto", padding: 24, fontFamily: "system-ui" }}>
      <h1>Lottery Foresee</h1>
      <p style={{ color: "#666", fontSize: 14 }}>
        基于历史数据与概率统计的双色球 / 大乐透推荐，仅供学习与研究使用。
      </p>

      <div style={{ marginTop: 16, marginBottom: 16, display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
        <button
          onClick={() => setTab("ssq")}
          style={{
            padding: "8px 16px",
            borderRadius: 999,
            border: "1px solid #ddd",
            background: tab === "ssq" ? "#e53935" : "#fff",
            color: tab === "ssq" ? "#fff" : "#333",
            cursor: "pointer"
          }}
        >
          双色球
        </button>
        <button
          onClick={() => setTab("dlt")}
          style={{
            padding: "8px 16px",
            borderRadius: 999,
            border: "1px solid #ddd",
            background: tab === "dlt" ? "#1976d2" : "#fff",
            color: tab === "dlt" ? "#fff" : "#333",
            cursor: "pointer"
          }}
        >
          大乐透
        </button>

        <button
          onClick={() => {
            setTab("stats");
            if (!ssqStats || !dltStats) {
              fetchStats();
            }
          }}
          style={{
            padding: "8px 16px",
            borderRadius: 999,
            border: "1px solid #ddd",
            background: tab === "stats" ? "#424242" : "#fff",
            color: tab === "stats" ? "#fff" : "#333",
            cursor: "pointer"
          }}
        >
          历史统计
        </button>
        <button
          onClick={() => {
            setTab("history");
            fetchHistory();
          }}
          style={{
            padding: "8px 16px",
            borderRadius: 999,
            border: "1px solid #ddd",
            background: tab === "history" ? "#6a1b9a" : "#fff",
            color: tab === "history" ? "#fff" : "#333",
            cursor: "pointer"
          }}
        >
          历史记录
        </button>

        <div style={{ flex: 1 }} />

        {tab !== "stats" && tab !== "history" && (
          <>
            <div style={{ fontSize: 13, color: "#555" }}>
              {tab === "ssq" && ssqNext && (
                <span>本次预测期数：{ssqNext.issue}（开奖日 {ssqNext.draw_date}）</span>
              )}
              {tab === "dlt" && dltNext && (
                <span>本次预测期数：{dltNext.issue}（开奖日 {dltNext.draw_date}）</span>
              )}
            </div>
            <label style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span style={{ fontSize: 14 }}>推荐组数</span>
              <select
                value={recommendCount}
                onChange={(e) => setRecommendCount(Number(e.target.value))}
                style={{ padding: "4px 8px", borderRadius: 6 }}
              >
                {Array.from({ length: 20 }, (_, i) => i + 1).map((n) => (
                  <option key={n} value={n}>{n}</option>
                ))}
              </select>
            </label>
            <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 14 }}>
              <input
                type="checkbox"
                checked={autoFetchEnabled}
                onChange={(e) => setAutoFetchEnabled(e.target.checked)}
              />
              自动拉取（基于上次拉取时间判定）
            </label>
            <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 14 }}>
              <input
                type="checkbox"
                checked={useCorrection}
                onChange={(e) => setUseCorrection(e.target.checked)}
              />
              使用历史比对修正
            </label>
            <button
              onClick={handleGenerate}
              style={{
                padding: "8px 16px",
                borderRadius: 8,
                border: "none",
                background: "#4caf50",
                color: "#fff",
                cursor: "pointer"
              }}
            >
              生成推荐
            </button>
            {currentList.length > 0 && (
              <button
                onClick={copyAll}
                style={{ padding: "8px 16px", borderRadius: 8, border: "1px solid #4caf50", background: "#fff", color: "#4caf50", cursor: "pointer" }}
              >
                复制全部
              </button>
            )}
          </>
        )}
      </div>

      {copyTip && <div style={{ color: "#2e7d32", fontSize: 14, marginBottom: 8 }}>{copyTip}</div>}
      {loading && <div>加载中...</div>}
      {error && <div style={{ color: "red" }}>{error}</div>}

      {tab !== "stats" && tab !== "history" && (
        <>
          <details style={{ marginBottom: 16, padding: 12, background: "#f9f9f9", borderRadius: 8 }}>
            <summary style={{ cursor: "pointer", fontWeight: 600 }}>推荐依据（算法说明）</summary>
            <div style={{ marginTop: 8, fontSize: 14, color: "#555", lineHeight: 1.6 }}>
              <p>基于最近 N 期历史开奖，统计各号码出现频率并归一化为概率；按该概率对号码加权，随机生成大量候选组合（蒙特卡洛）；对每个组合按「组合内号码概率之和」打分并排序，取前 K 组作为推荐。</p>
              <p>参数含义：统计窗口期数（默认 100）、候选组合数量（默认 50000）、推荐组数（可设 1–20）。</p>
            </div>
          </details>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 16 }}>
          {currentList.map((item, idx) => (
          <div
            key={idx}
            style={{
              borderRadius: 16,
              border: "1px solid #eee",
              padding: 16,
              boxShadow: "0 4px 12px rgba(0,0,0,0.04)"
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
              <span style={{ fontWeight: 600 }}>推荐 #{idx + 1}</span>
              <button
                type="button"
                onClick={() => copyOne(item)}
                style={{ fontSize: 12, padding: "2px 8px", borderRadius: 6, border: "1px solid #ccc", background: "#fff", cursor: "pointer" }}
              >
                复制
              </button>
            </div>
            <div style={{ marginBottom: 8 }}>
              {tab === "ssq" ? (
                <>
                  <span>红球：</span>
                  {(item as SsqRecommendation).reds.map((n) => (
                    <span
                      key={n}
                      style={{
                        display: "inline-block",
                        minWidth: 28,
                        textAlign: "center",
                        padding: "4px 0",
                        borderRadius: 999,
                        background: "#ffcdd2",
                        marginRight: 4
                      }}
                    >
                      {n}
                    </span>
                  ))}
                  <div style={{ marginTop: 4 }}>
                    <span>蓝球：</span>
                    <span
                      style={{
                        display: "inline-block",
                        minWidth: 28,
                        textAlign: "center",
                        padding: "4px 0",
                        borderRadius: 999,
                        background: "#bbdefb",
                        marginRight: 4
                      }}
                    >
                      {(item as SsqRecommendation).blue}
                    </span>
                  </div>
                </>
              ) : (
                <>
                  <span>前区：</span>
                  {(item as DltRecommendation).fronts.map((n) => (
                    <span
                      key={n}
                      style={{
                        display: "inline-block",
                        minWidth: 28,
                        textAlign: "center",
                        padding: "4px 0",
                        borderRadius: 999,
                        background: "#e3f2fd",
                        marginRight: 4
                      }}
                    >
                      {n}
                    </span>
                  ))}
                  <div style={{ marginTop: 4 }}>
                    <span>后区：</span>
                    {(item as DltRecommendation).backs.map((n) => (
                      <span
                        key={n}
                        style={{
                          display: "inline-block",
                          minWidth: 28,
                          textAlign: "center",
                          padding: "4px 0",
                          borderRadius: 999,
                          background: "#ffecb3",
                          marginRight: 4
                        }}
                      >
                        {n}
                      </span>
                    ))}
                  </div>
                </>
              )}
            </div>
            <div style={{ fontSize: 12, color: "#777" }}>打分：{item.score.toFixed(4)}</div>
          </div>
          ))}
          </div>
        </>
      )}

      {tab === "stats" && (
        <div style={{ marginTop: 16 }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
          <div>
            <h2 style={{ fontSize: 18, marginBottom: 8 }}>双色球号码热度</h2>
            {ssqStats && (
              <>
                <div style={{ fontSize: 12, color: "#777", marginBottom: 8 }}>
                  统计期数：{ssqStats.total_draws}
                </div>
                <div>
                  {ssqStats.reds.map((s) => (
                    <div key={s.number} style={{ display: "flex", alignItems: "center", marginBottom: 2 }}>
                      <span style={{ width: 32 }}>红{s.number}</span>
                      <div style={{ flex: 1, background: "#f5f5f5", borderRadius: 999, overflow: "hidden" }}>
                        <div
                          style={{
                            width: `${Math.min(100, s.probability * 500)}%`,
                            background: "#e53935",
                            height: 6
                          }}
                        />
                      </div>
                      <span style={{ width: 60, fontSize: 12, textAlign: "right" }}>
                        {(s.probability * 100).toFixed(2)}%
                      </span>
                      <span style={{ width: 60, fontSize: 12, textAlign: "right", color: "#777" }}>
                        遗漏 {s.omission}
                      </span>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>

          <div>
            <h2 style={{ fontSize: 18, marginBottom: 8 }}>大乐透号码热度</h2>
            {dltStats && (
              <>
                <div style={{ fontSize: 12, color: "#777", marginBottom: 8 }}>
                  统计期数：{dltStats.total_draws}
                </div>
                <div>
                  {dltStats.fronts.map((s) => (
                    <div key={s.number} style={{ display: "flex", alignItems: "center", marginBottom: 2 }}>
                      <span style={{ width: 32 }}>前{s.number}</span>
                      <div style={{ flex: 1, background: "#f5f5f5", borderRadius: 999, overflow: "hidden" }}>
                        <div
                          style={{
                            width: `${Math.min(100, s.probability * 500)}%`,
                            background: "#1976d2",
                            height: 6
                          }}
                        />
                      </div>
                      <span style={{ width: 60, fontSize: 12, textAlign: "right" }}>
                        {(s.probability * 100).toFixed(2)}%
                      </span>
                      <span style={{ width: 60, fontSize: 12, textAlign: "right", color: "#777" }}>
                        遗漏 {s.omission}
                      </span>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
          </div>
        </div>
      )}

      {tab === "history" && (
        <div style={{ marginTop: 16 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12, flexWrap: "wrap", gap: 8 }}>
            <h2 style={{ fontSize: 18, margin: 0 }}>生成记录</h2>
            <button type="button" onClick={runCompare} style={{ padding: "6px 12px", borderRadius: 8, border: "1px solid #6a1b9a", background: "#fff", cursor: "pointer" }}>执行比对</button>
          </div>
          {compareResult && (
            <div style={{ marginBottom: 12, padding: 12, background: "#f5f5f5", borderRadius: 8, fontSize: 14 }}>
              <div>双色球：已比对 {compareResult.ssq?.total_compared ?? 0} 条，平均红球命中 {compareResult.ssq?.avg_red_hits ?? 0}，蓝球命中 {compareResult.ssq?.avg_blue_hits ?? 0}</div>
              <div>大乐透：已比对 {compareResult.dlt?.total_compared ?? 0} 条，平均前区命中 {compareResult.dlt?.avg_front_hits ?? 0}，后区命中 {compareResult.dlt?.avg_back_hits ?? 0}</div>
            </div>
          )}
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {(() => {
              const combined = [...(ssqHistory || []).map((r) => ({ ...r, _type: "ssq" as const })), ...(dltHistory || []).map((r) => ({ ...r, _type: "dlt" as const }))]
                .sort((a, b) => new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime())
                .slice(0, 50);
              if (combined.length === 0) return <div style={{ color: "#666", padding: 24, textAlign: "center" }}>暂无记录，请先生成推荐</div>;
              return combined.map((rec, index) => (
                <div key={rec.id || `hist-${index}`} style={{ border: "1px solid #eee", borderRadius: 8, overflow: "hidden" }}>
                  <button
                    type="button"
                    onClick={() => setExpandedHistoryId(expandedHistoryId === rec.id ? null : rec.id)}
                    style={{ width: "100%", padding: "10px 12px", display: "flex", justifyContent: "space-between", alignItems: "center", background: "#fafafa", border: "none", cursor: "pointer", textAlign: "left", flexWrap: "wrap", gap: 4 }}
                  >
                    <span>{rec._type === "ssq" ? "双色球" : "大乐透"}</span>
                    <span style={{ fontSize: 12, color: "#666" }}>{rec.created_at ? new Date(rec.created_at).toLocaleString() : "-"}</span>
                    <span style={{ fontSize: 12 }}>推荐 {(rec.results && rec.results.length) || 0} 组</span>
                    {rec.results?.[0] && (
                      <span style={{ fontSize: 12, color: "#888" }}>
                        {rec._type === "ssq"
                          ? `红 ${((rec.results[0] as { reds?: number[] }).reds || []).join(",")} 蓝 ${(rec.results[0] as { blue?: number }).blue ?? "-"}`
                          : `前区 ${((rec.results[0] as { fronts?: number[] }).fronts || []).join(",")} 后区 ${((rec.results[0] as { backs?: number[] }).backs || []).join(",")}`}
                      </span>
                    )}
                    {(rec.target_issue || rec.target_date) && (
                      <span style={{ fontSize: 12, color: "#555" }}>
                        期：{rec.target_issue ?? "-"} 日：{rec.target_date ?? "-"}
                      </span>
                    )}
                  </button>
                  {expandedHistoryId === rec.id && Array.isArray(rec.results) && rec.results.length > 0 && (
                    <div style={{ padding: 12, background: "#fff", borderTop: "1px solid #eee" }}>
                      <div style={{ marginBottom: 10, fontSize: 13, color: "#555" }}>
                        目标期号：{rec.target_issue ?? "-"}（开奖日 {rec.target_date ?? "-"}）
                      </div>
                      <div style={{ marginBottom: 10, fontSize: 13, color: "#555" }}>
                        比对结果：
                        {compareDetailsByRecord[rec.id]?.length ? (
                          <span>
                            {" "}
                            {compareDetailsByRecord[rec.id].map((d, i) => (
                              <span key={i} style={{ marginLeft: 8 }}>
                                实际期号 {(d as any).issue}（{(d as any).draw_date}） 命中{" "}
                                {"hit_reds" in (d as any)
                                  ? `红 ${(d as any).hit_reds} + 蓝 ${(d as any).hit_blue}`
                                  : `前 ${(d as any).hit_fronts} + 后 ${(d as any).hit_backs}`}
                              </span>
                            ))}
                          </span>
                        ) : (
                          <span> 未匹配（可能尚未开奖或未拉取到该期真实数据）</span>
                        )}
                      </div>
                      {rec.results.map((item, idx) => (
                        <div key={idx} style={{ marginBottom: 8, fontSize: 14 }}>
                          #{idx + 1}{" "}
                          {rec._type === "ssq"
                            ? `红球 ${((item as { reds?: number[] }).reds || []).join(" ")} 蓝球 ${(item as { blue?: number }).blue ?? "-"}`
                            : `前区 ${((item as { fronts?: number[] }).fronts || []).join(" ")} 后区 ${((item as { backs?: number[] }).backs || []).join(" ")}`}
                          {" "}(分 {typeof (item as { score?: number }).score === "number" ? (item as { score: number }).score.toFixed(4) : "-"})
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ));
            })()}
          </div>
        </div>
      )}
    </div>
  );
};

