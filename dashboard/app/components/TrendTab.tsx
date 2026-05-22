// 트렌드 분석 탭 — 날짜 선택, 종목/섹터 분리, 시장 현황 표시
"use client";

import { useState, useEffect } from "react";
import type { AnalysisData, EconNewsData, NaverData, MarketData, MarketStock, MarketSection } from "../page";

const RAW = "https://raw.githubusercontent.com/makitjung/stock-platform/main";

type DayFilter = "total" | "1d" | "3d" | "7d";
type KwTab = "stock" | "sector";

const DAY_FILTERS: { key: DayFilter; label: string }[] = [
  { key: "total", label: "전체" },
  { key: "1d",    label: "1일" },
  { key: "3d",    label: "3일" },
  { key: "7d",    label: "7일" },
];

function getScore(row: AnalysisData["top50"][0], filter: DayFilter): number {
  switch (filter) {
    case "1d": return row.day1_score ?? 0;
    case "3d": return row.day3_score ?? 0;
    case "7d": return row.day7_score ?? 0;
    default:   return row.total_score ?? 0;
  }
}

function ScoreBadge({ score }: { score: number }) {
  const cls =
    score >= 60 ? "bg-red-100 text-red-700 ring-1 ring-red-200" :
    score >= 30 ? "bg-amber-100 text-amber-700 ring-1 ring-amber-200" :
    score >  0  ? "bg-slate-100 text-slate-600" :
                  "bg-slate-50  text-slate-300";
  return (
    <span className={`inline-block text-xs font-bold px-2.5 py-0.5 rounded-full ${cls}`}>
      {score.toFixed(0)}
    </span>
  );
}

function formatPub(pub: string): string {
  if (!pub) return "";
  const d = new Date(pub);
  if (isNaN(d.getTime())) return "";
  const now = new Date();
  const sameDay =
    d.getDate() === now.getDate() &&
    d.getMonth() === now.getMonth() &&
    d.getFullYear() === now.getFullYear();
  const timeStr = d.toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" });
  if (sameDay) return timeStr;
  const dateStr = `${String(d.getMonth() + 1).padStart(2, "0")}/${String(d.getDate()).padStart(2, "0")}`;
  return `${dateStr} ${timeStr}`;
}

function NaverChangeRate({ rate }: { rate: number }) {
  if (rate > 0)
    return <span className="text-xs font-semibold text-red-500">▲{Math.abs(rate).toFixed(1)}%</span>;
  if (rate < 0)
    return <span className="text-xs font-semibold text-blue-600">▼{Math.abs(rate).toFixed(1)}%</span>;
  return <span className="text-xs text-slate-400">-</span>;
}

function isMarketAllEmpty(m: MarketData | null): boolean {
  if (!m) return true;
  const empty = (s: MarketSection) =>
    s.상한가.length === 0 && s.급등.length === 0 &&
    s.급락.length === 0 && s.하한가.length === 0;
  return empty(m.kospi) && empty(m.kosdaq);
}

interface MarketCardProps {
  title: string;
  emoji: string;
  items: MarketStock[];
  bgClass: string;
  headerBg: string;
  headerText: string;
  rateColor: (r: number) => string;
}

function MarketCard({ title, emoji, items, bgClass, headerBg, headerText, rateColor }: MarketCardProps) {
  return (
    <div className={`rounded-xl border overflow-hidden ${bgClass}`}>
      <div className={`px-4 py-2.5 flex items-center justify-between ${headerBg}`}>
        <h3 className={`font-bold text-sm ${headerText}`}>{emoji} {title}</h3>
        <span className={`text-xs font-medium ${headerText} opacity-70`}>{items.length}종목</span>
      </div>
      {items.length === 0 ? (
        <p className="px-4 py-6 text-xs text-center text-slate-400">해당 없음</p>
      ) : (
        <div className="divide-y divide-white/60 max-h-60 overflow-auto">
          {items.map((s) => (
            <a
              key={s.ticker}
              href={`https://finance.naver.com/item/main.naver?code=${s.ticker}`}
              target="_blank"
              rel="noopener noreferrer"
              className="px-4 py-2 flex items-center justify-between gap-2 hover:bg-white/40 transition-colors block"
            >
              <div className="min-w-0">
                <span className="text-sm font-medium text-slate-800 truncate block">{s.name}</span>
                <span className="text-xs text-slate-400">{s.ticker}</span>
              </div>
              <span className={`text-sm font-bold shrink-0 ${rateColor(s.change_rate)}`}>
                {s.change_rate > 0 ? "▲" : "▼"}{Math.abs(s.change_rate).toFixed(2)}%
              </span>
            </a>
          ))}
        </div>
      )}
    </div>
  );
}

function KeywordTable({
  rows,
  dayFilter,
  mode,
}: {
  rows: AnalysisData["top50"];
  dayFilter: DayFilter;
  mode: string;
}) {
  const isDayOnly = mode === "당일";
  if (rows.length === 0) {
    return <p className="p-5 text-slate-400 text-sm text-center">신호 없음</p>;
  }
  return (
    <div className="overflow-auto max-h-[620px]">
      <table className="w-full text-sm">
        <thead className="sticky top-0 bg-white border-b border-slate-100 text-xs text-slate-400 uppercase tracking-wide">
          <tr>
            <th className="px-4 py-2.5 text-left w-8">#</th>
            <th className="px-4 py-2.5 text-left">키워드</th>
            <th className="px-4 py-2.5 text-right">점수</th>
            <th className="px-4 py-2.5 text-right hidden md:table-cell">1일</th>
            <th className="px-4 py-2.5 text-right hidden md:table-cell">
              3일{isDayOnly && <span className="ml-1 text-slate-300 normal-case">(누적중)</span>}
            </th>
            <th className="px-4 py-2.5 text-right hidden md:table-cell">
              7일{isDayOnly && <span className="ml-1 text-slate-300 normal-case">(누적중)</span>}
            </th>
            <th className="px-4 py-2.5 text-left">시그널</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr
              key={row.keyword}
              className="border-t border-slate-50 hover:bg-slate-50 transition-colors"
            >
              <td className="px-4 py-2.5 text-slate-300 text-xs">{i + 1}</td>
              <td className="px-4 py-2.5 font-semibold text-slate-800">
                <a
                  href={`https://search.naver.com/search.naver?query=${encodeURIComponent(row.keyword)}+주식`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-blue-600 transition-colors"
                >
                  {row.keyword}
                </a>
              </td>
              <td className="px-4 py-2.5 text-right">
                <ScoreBadge score={getScore(row, dayFilter)} />
              </td>
              <td className={`px-4 py-2.5 text-right text-xs hidden md:table-cell ${dayFilter === "1d" ? "font-bold text-slate-700" : "text-slate-400"}`}>
                {(row.day1_score ?? 0).toFixed(0)}
              </td>
              <td className={`px-4 py-2.5 text-right text-xs hidden md:table-cell ${dayFilter === "3d" ? "font-bold text-slate-700" : "text-slate-400"}`}>
                {isDayOnly ? <span className="text-slate-300">–</span> : (row.day3_score ?? 0).toFixed(0)}
              </td>
              <td className={`px-4 py-2.5 text-right text-xs hidden md:table-cell ${dayFilter === "7d" ? "font-bold text-slate-700" : "text-slate-400"}`}>
                {isDayOnly ? <span className="text-slate-300">–</span> : (row.day7_score ?? 0).toFixed(0)}
              </td>
              <td className="px-4 py-2.5">
                <div className="flex flex-wrap gap-1">
                  {(row.signals ?? []).slice(0, 3).map((s) => (
                    <span key={s} className="text-xs bg-blue-50 text-blue-600 px-1.5 py-0.5 rounded-md">
                      {s}
                    </span>
                  ))}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

interface Props {
  analysis: AnalysisData | null;
  econNews: EconNewsData | null;
  naver: NaverData | null;
  market: MarketData | null;
  availableDates: string[];
  onRefreshMarket: () => Promise<void>;
  econUpdated: string;
}

export default function TrendTab({ analysis, econNews, naver, market, availableDates, onRefreshMarket, econUpdated }: Props) {
  const [dayFilter, setDayFilter] = useState<DayFilter>("total");
  const [showKosdaq, setShowKosdaq] = useState(false);
  const [kwTab, setKwTab] = useState<KwTab>("stock");
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [historyAnalysis, setHistoryAnalysis] = useState<AnalysisData | null>(null);
  const [historyNaver, setHistoryNaver] = useState<NaverData | null>(null);
  const [historyMarket, setHistoryMarket] = useState<MarketData | null>(null);
  const [historyLoading, setHistoryLoading] = useState(false);

  useEffect(() => {
    if (!selectedDate) {
      setHistoryAnalysis(null);
      setHistoryNaver(null);
      setHistoryMarket(null);
      return;
    }
    setHistoryLoading(true);
    const t = Date.now();
    const base = `${RAW}/trend/history/${selectedDate}`;
    Promise.all([
      fetch(`${base}/result_analysis.json?t=${t}`, { cache: "no-store" }).then((r) => r.ok ? r.json() : null).catch(() => null),
      fetch(`${base}/result_naver.json?t=${t}`,   { cache: "no-store" }).then((r) => r.ok ? r.json() : null).catch(() => null),
      fetch(`${base}/result_market.json?t=${t}`,  { cache: "no-store" }).then((r) => r.ok ? r.json() : null).catch(() => null),
    ]).then(([analysis, naver, market]) => {
      setHistoryAnalysis(analysis);
      setHistoryNaver(naver);
      setHistoryMarket(market);
      setHistoryLoading(false);
    });
  }, [selectedDate]);

  const activeAnalysis = selectedDate ? historyAnalysis : analysis;
  const activeNaver = selectedDate ? historyNaver : naver;
  const historyIsEmpty = selectedDate !== null && isMarketAllEmpty(historyMarket);
  const activeMarket = (selectedDate && !historyIsEmpty) ? historyMarket : market;
  const mkt = activeMarket ? (showKosdaq ? activeMarket.kosdaq : activeMarket.kospi) : null;

  const allSorted = activeAnalysis
    ? [...activeAnalysis.top50]
        .sort((a, b) => getScore(b, dayFilter) - getScore(a, dayFilter))
        .filter((row) => getScore(row, dayFilter) > 0)
    : [];

  const stockRows  = allSorted.filter((r) => r.is_stock === true);
  const sectorRows = allSorted.filter((r) => r.is_stock !== true);
  const displayRows = kwTab === "stock" ? stockRows : sectorRows;

  return (
    <div className="space-y-6">

      {/* 날짜 선택 */}
      {availableDates.length > 0 && (
        <div className="flex items-center gap-2">
          <label htmlFor="date-select" className="text-xs text-slate-500 font-medium shrink-0">날짜 선택</label>
          <select
            id="date-select"
            value={selectedDate ?? ""}
            onChange={(e) => setSelectedDate(e.target.value || null)}
            className="text-xs border border-slate-200 rounded-lg px-3 py-1.5 bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-400 shadow-sm"
          >
            <option value="">최신 (오늘)</option>
            {availableDates.map((date) => (
              <option key={date} value={date}>{date}</option>
            ))}
          </select>
          {selectedDate && (
            <button
              onClick={() => setSelectedDate(null)}
              className="text-xs text-slate-400 hover:text-slate-600 px-2 py-1 rounded-md hover:bg-slate-100 transition-colors"
            >
              최신으로
            </button>
          )}
        </div>
      )}

      {/* 시장 현황 */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold text-slate-600 uppercase tracking-wide">시장 현황</h2>
            {activeMarket && !historyIsEmpty && (
              <span className="text-xs text-slate-400">
                {!selectedDate ? "(실시간)" : `(${selectedDate} 마감 기준)`}
              </span>
            )}
            {historyIsEmpty && selectedDate && (
              <span className="text-xs text-amber-500">장마감(15:30) 후 업데이트 예정 — 전일 데이터 표시 중</span>
            )}
            {!selectedDate && isMarketAllEmpty(market) && market !== null && (
              <span className="text-xs text-amber-500">장 시작 전 — 09:00 이후 순차 업데이트</span>
            )}
            {!selectedDate && (
              <button
                onClick={onRefreshMarket}
                className="text-xs text-slate-400 hover:text-blue-500 transition-colors px-2 py-0.5 rounded-md hover:bg-blue-50"
              >
                ↻ 갱신
              </button>
            )}
          </div>
          {activeMarket && (
            <div className="flex bg-slate-200 rounded-lg p-0.5 gap-0.5">
              {["KOSPI", "KOSDAQ"].map((m) => (
                <button
                  key={m}
                  onClick={() => setShowKosdaq(m === "KOSDAQ")}
                  className={`text-xs px-3 py-1 rounded-md font-medium transition-colors ${
                    (m === "KOSDAQ") === showKosdaq
                      ? "bg-white text-slate-800 shadow-sm"
                      : "text-slate-500 hover:text-slate-700"
                  }`}
                >
                  {m}
                </button>
              ))}
            </div>
          )}
        </div>

        {!activeMarket ? (
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 text-center text-sm text-slate-400">
            시장 데이터 없음 — 다음 파이프라인 실행 후 자동 갱신됩니다.
          </div>
        ) : (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <MarketCard
              title="상한가" emoji="🔴"
              items={mkt?.상한가 ?? []}
              bgClass="border-red-200 bg-red-50"
              headerBg="bg-red-500" headerText="text-white"
              rateColor={() => "text-red-600"}
            />
            <MarketCard
              title="급등주" emoji="🟠"
              items={mkt?.급등 ?? []}
              bgClass="border-orange-200 bg-orange-50"
              headerBg="bg-orange-400" headerText="text-white"
              rateColor={() => "text-orange-600"}
            />
            <MarketCard
              title="급락주" emoji="🔵"
              items={mkt?.급락 ?? []}
              bgClass="border-blue-200 bg-blue-50"
              headerBg="bg-blue-500" headerText="text-white"
              rateColor={() => "text-blue-600"}
            />
            <MarketCard
              title="하한가" emoji="🟣"
              items={mkt?.하한가 ?? []}
              bgClass="border-indigo-200 bg-indigo-50"
              headerBg="bg-indigo-600" headerText="text-white"
              rateColor={() => "text-indigo-600"}
            />
          </div>
        )}
      </section>

      {/* 하단 2단 레이아웃 */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">

        {/* 키워드 패널 */}
        <div className="xl:col-span-2 bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-5 py-3 border-b border-slate-100 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="font-semibold text-slate-800">🔥 Top 키워드</h2>
              {activeAnalysis && (
                <p className="text-xs text-slate-400 mt-0.5">
                  {activeAnalysis.date} · {activeAnalysis.total_analyzed}개 분석 · {activeAnalysis.mode} 모드
                </p>
              )}
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              {/* 종목 / 섹터 탭 */}
              <div className="flex bg-slate-100 rounded-lg p-0.5 gap-0.5">
                <button
                  onClick={() => setKwTab("stock")}
                  className={`text-xs px-3 py-1.5 rounded-md font-medium transition-colors ${
                    kwTab === "stock"
                      ? "bg-white text-slate-800 shadow-sm"
                      : "text-slate-500 hover:text-slate-700"
                  }`}
                >
                  📈 종목 ({stockRows.length})
                </button>
                <button
                  onClick={() => setKwTab("sector")}
                  className={`text-xs px-3 py-1.5 rounded-md font-medium transition-colors ${
                    kwTab === "sector"
                      ? "bg-white text-slate-800 shadow-sm"
                      : "text-slate-500 hover:text-slate-700"
                  }`}
                >
                  🏭 섹터 ({sectorRows.length})
                </button>
              </div>
              {/* 기간 필터 */}
              <div className="flex bg-slate-100 rounded-lg p-0.5 gap-0.5">
                {DAY_FILTERS.map(({ key, label }) => (
                  <button
                    key={key}
                    onClick={() => setDayFilter(key)}
                    className={`text-xs px-3 py-1.5 rounded-md font-medium transition-colors ${
                      dayFilter === key
                        ? "bg-white text-slate-800 shadow-sm"
                        : "text-slate-500 hover:text-slate-700"
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {historyLoading ? (
            <p className="p-5 text-slate-400 text-sm text-center">불러오는 중...</p>
          ) : !activeAnalysis ? (
            <p className="p-5 text-slate-400 text-sm">데이터 없음</p>
          ) : (
            <KeywordTable rows={displayRows} dayFilter={dayFilter} mode={activeAnalysis.mode} />
          )}
        </div>

        {/* 오른쪽 패널 */}
        <div className="flex flex-col gap-5">

          {/* 네이버 검색 추이 */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-5 py-3 border-b border-slate-100 flex items-center justify-between">
              <h2 className="font-semibold text-slate-800">📈 네이버 검색 추이</h2>
              {activeNaver?.collected_at && (
                <span className="text-xs text-slate-400">{activeNaver.collected_at} 기준</span>
              )}
            </div>
            {!activeNaver?.datalab?.length ? (
              <p className="p-5 text-slate-400 text-sm">데이터 없음</p>
            ) : (
              <div className="divide-y divide-slate-50 max-h-72 overflow-auto">
                {[...activeNaver.datalab].sort((a, b) => b.recent - a.recent).map((item) => (
                  <div key={item.keyword} className="px-5 py-3 flex items-center justify-between gap-2">
                    <span className="text-sm font-medium text-slate-700">{item.keyword}</span>
                    <div className="flex items-center gap-2 shrink-0">
                      <span className="text-xs text-slate-400">{item.recent.toFixed(1)}</span>
                      <NaverChangeRate rate={item.change_rate} />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* 경제 뉴스 */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden flex-1">
            <div className="px-5 py-3 border-b border-slate-100 flex items-center justify-between">
              <h2 className="font-semibold text-slate-800">📰 경제 뉴스</h2>
              <div className="text-right">
                {econNews && (
                  <p className="text-xs text-slate-400">{econNews.matched_count}/{econNews.total_articles}건</p>
                )}
                {econNews?.collected_at && (
                  <p className="text-xs text-slate-400">{econNews.collected_at} 기준</p>
                )}
              </div>
            </div>
            {!econNews?.top_news?.length ? (
              <p className="p-5 text-slate-400 text-sm">데이터 없음</p>
            ) : (
              <div className="divide-y divide-slate-50 max-h-[500px] overflow-auto">
                {econNews.top_news.slice(0, 20).map((item, i) => (
                  <div key={i} className="px-5 py-3">
                    <a
                      href={item.link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-slate-700 hover:text-blue-600 transition-colors leading-snug block"
                    >
                      {item.title}
                    </a>
                    <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                      <span className="text-xs text-slate-400">{item.source}</span>
                      {item.pub && (
                        <span className="text-xs text-slate-400">{formatPub(item.pub)}</span>
                      )}
                      {(item.matched_keywords ?? []).slice(0, 2).map((kw) => (
                        <span key={kw} className="text-xs bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded">
                          {kw}
                        </span>
                      ))}
                      <span className="text-xs text-slate-300 ml-auto">점수 {item.score}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
