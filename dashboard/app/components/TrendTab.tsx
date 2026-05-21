"use client";

import { useState } from "react";
import type { AnalysisData, EconNewsData, NaverData, MarketData, MarketStock } from "../page";

type DayFilter = "total" | "1d" | "3d" | "7d";

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

function ChangeRate({ rate }: { rate: number }) {
  if (rate > 0)
    return <span className="text-sm font-bold text-red-500">▲{rate.toFixed(2)}%</span>;
  if (rate < 0)
    return <span className="text-sm font-bold text-blue-600">▼{Math.abs(rate).toFixed(2)}%</span>;
  return <span className="text-sm text-slate-400">-</span>;
}

function NaverChangeRate({ rate }: { rate: number }) {
  if (rate > 0)
    return <span className="text-xs font-semibold text-red-500">▲{Math.abs(rate).toFixed(1)}%</span>;
  if (rate < 0)
    return <span className="text-xs font-semibold text-blue-600">▼{Math.abs(rate).toFixed(1)}%</span>;
  return <span className="text-xs text-slate-400">-</span>;
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
            <div key={s.ticker} className="px-4 py-2 flex items-center justify-between gap-2">
              <div className="min-w-0">
                <span className="text-sm font-medium text-slate-800 truncate block">{s.name}</span>
                <span className="text-xs text-slate-400">{s.ticker}</span>
              </div>
              <span className={`text-sm font-bold shrink-0 ${rateColor(s.change_rate)}`}>
                {s.change_rate > 0 ? "▲" : "▼"}{Math.abs(s.change_rate).toFixed(2)}%
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

interface Props {
  analysis: AnalysisData | null;
  econNews: EconNewsData | null;
  naver: NaverData | null;
  market: MarketData | null;
}

export default function TrendTab({ analysis, econNews, naver, market }: Props) {
  const [dayFilter, setDayFilter] = useState<DayFilter>("total");
  const [showKosdaq, setShowKosdaq] = useState(false);

  const mkt = market ? (showKosdaq ? market.kosdaq : market.kospi) : null;

  const sortedKeywords = analysis
    ? [...analysis.top50]
        .sort((a, b) => getScore(b, dayFilter) - getScore(a, dayFilter))
        .filter((row) => getScore(row, dayFilter) > 0)
    : [];

  return (
    <div className="space-y-6">

      {/* ── 시장 현황 ── */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold text-slate-600 uppercase tracking-wide">시장 현황</h2>
            {market && (
              <span className="text-xs text-slate-400">({market.date} 전일 기준)</span>
            )}
          </div>
          {market && (
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

        {!market ? (
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

      {/* ── 하단 2단 레이아웃 ── */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">

        {/* Top 50 키워드 */}
        <div className="xl:col-span-2 bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-5 py-3 border-b border-slate-100 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="font-semibold text-slate-800">🔥 Top 50 키워드</h2>
              {analysis && (
                <p className="text-xs text-slate-400 mt-0.5">
                  {analysis.total_analyzed}개 분석 · {analysis.mode} 모드
                </p>
              )}
            </div>
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

          {!analysis ? (
            <p className="p-5 text-slate-400 text-sm">데이터 없음</p>
          ) : (
            <div className="overflow-auto max-h-[620px]">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-white border-b border-slate-100 text-xs text-slate-400 uppercase tracking-wide">
                  <tr>
                    <th className="px-4 py-2.5 text-left w-8">#</th>
                    <th className="px-4 py-2.5 text-left">키워드</th>
                    <th className="px-4 py-2.5 text-right">점수</th>
                    <th className="px-4 py-2.5 text-right hidden md:table-cell">1일</th>
                    <th className="px-4 py-2.5 text-right hidden md:table-cell">3일</th>
                    <th className="px-4 py-2.5 text-right hidden md:table-cell">7일</th>
                    <th className="px-4 py-2.5 text-left">시그널</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedKeywords.map((row, i) => (
                    <tr
                      key={row.keyword}
                      className="border-t border-slate-50 hover:bg-slate-50 transition-colors"
                    >
                      <td className="px-4 py-2.5 text-slate-300 text-xs">{i + 1}</td>
                      <td className="px-4 py-2.5 font-semibold text-slate-800">{row.keyword}</td>
                      <td className="px-4 py-2.5 text-right">
                        <ScoreBadge score={getScore(row, dayFilter)} />
                      </td>
                      <td className={`px-4 py-2.5 text-right text-xs hidden md:table-cell ${dayFilter === "1d" ? "font-bold text-slate-700" : "text-slate-400"}`}>
                        {(row.day1_score ?? 0).toFixed(0)}
                      </td>
                      <td className={`px-4 py-2.5 text-right text-xs hidden md:table-cell ${dayFilter === "3d" ? "font-bold text-slate-700" : "text-slate-400"}`}>
                        {(row.day3_score ?? 0).toFixed(0)}
                      </td>
                      <td className={`px-4 py-2.5 text-right text-xs hidden md:table-cell ${dayFilter === "7d" ? "font-bold text-slate-700" : "text-slate-400"}`}>
                        {(row.day7_score ?? 0).toFixed(0)}
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
          )}
        </div>

        {/* 오른쪽 패널 */}
        <div className="flex flex-col gap-5">

          {/* 네이버 검색 추이 */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-5 py-3 border-b border-slate-100">
              <h2 className="font-semibold text-slate-800">📈 네이버 검색 추이</h2>
            </div>
            {!naver?.datalab?.length ? (
              <p className="p-5 text-slate-400 text-sm">데이터 없음</p>
            ) : (
              <div className="divide-y divide-slate-50 max-h-72 overflow-auto">
                {naver.datalab.map((item) => (
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
              {econNews && (
                <span className="text-xs text-slate-400">
                  {econNews.matched_count}/{econNews.total_articles}건
                </span>
              )}
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
