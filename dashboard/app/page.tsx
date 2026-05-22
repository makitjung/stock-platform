// 주식 플랫폼 대시보드 — 트렌드 분석 + 뉴스 브리핑 메인 페이지
"use client";

import { useEffect, useState, useCallback } from "react";
import TrendTab from "./components/TrendTab";
import NewsTab from "./components/NewsTab";

const RAW = "https://raw.githubusercontent.com/makitjung/stock-platform/main";

export interface AnalysisData {
  date: string;
  mode: string;
  total_analyzed: number;
  top50: Array<{
    keyword: string;
    total_score: number;
    signals: string[];
    day1_score: number;
    day3_score: number;
    day7_score: number;
    is_stock?: boolean;
  }>;
}

export interface EconNewsItem {
  source: string;
  title: string;
  link: string;
  desc: string;
  pub: string;
  via: string;
  importance: number;
  matched_keywords: string[];
  score: number;
}

export interface EconNewsData {
  date: string;
  collected_at?: string;
  total_articles: number;
  matched_count: number;
  top_news: EconNewsItem[];
}

export interface NaverData {
  date: string;
  collected_at?: string;
  datalab: Array<{
    keyword: string;
    recent: number;
    previous: number;
    change_rate: number;
    source: string;
  }>;
}

export interface NewsItem {
  title: string;
  link: string;
  date: string;
  source: string;
}

export interface NewsData {
  date: string;
  kr: Array<{ name: string; sector: string; items: NewsItem[] }>;
  us: Array<{ name: string; ticker: string; sector: string; items: NewsItem[] }>;
}

export interface MarketStock {
  ticker: string;
  name: string;
  close: number;
  change_rate: number;
}

export interface MarketSection {
  상한가: MarketStock[];
  하한가: MarketStock[];
  급등: MarketStock[];
  급락: MarketStock[];
}

export interface MarketData {
  date: string;
  kospi: MarketSection;
  kosdaq: MarketSection;
}

type Tab = "trend" | "news";

async function fetchJson<T>(url: string): Promise<T | null> {
  try {
    const res = await fetch(url + `?t=${Date.now()}`, { cache: "no-store" });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

function getKstParts() {
  const now = new Date();
  const kst = new Date(now.toLocaleString("en-US", { timeZone: "Asia/Seoul" }));
  const day = kst.getDay();
  const h = kst.getHours();
  const m = kst.getMinutes();
  const minutes = h * 60 + m;
  const open = day >= 1 && day <= 5 && minutes >= 540 && minutes < 930;
  const timeStr = kst.toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  return { open, timeStr };
}

export default function Dashboard() {
  const [tab, setTab] = useState<Tab>("trend");
  const [analysis, setAnalysis] = useState<AnalysisData | null>(null);
  const [econNews, setEconNews] = useState<EconNewsData | null>(null);
  const [naver, setNaver] = useState<NaverData | null>(null);
  const [news, setNews] = useState<NewsData | null>(null);
  const [market, setMarket] = useState<MarketData | null>(null);
  const [availableDates, setAvailableDates] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastFetch, setLastFetch] = useState<string>("");
  const [econUpdated, setEconUpdated] = useState<string>("");
  const [kstTime, setKstTime] = useState<string>("");
  const [marketOpen, setMarketOpen] = useState(false);

  // KST 실시간 시계
  useEffect(() => {
    const tick = () => {
      const { open, timeStr } = getKstParts();
      setKstTime(timeStr);
      setMarketOpen(open);
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  async function loadData() {
    setLoading(true);
    const [a, e, n, ns, mk, dates] = await Promise.all([
      fetchJson<AnalysisData>(`${RAW}/trend/result_analysis.json`),
      fetchJson<EconNewsData>(`${RAW}/trend/result_econ_news.json`),
      fetchJson<NaverData>(`${RAW}/trend/result_naver.json`),
      fetchJson<NewsData>(`${RAW}/news/latest_news.json`),
      fetchJson<MarketData>(`${RAW}/trend/result_market.json`),
      fetchJson<{ dates: string[] }>(`${RAW}/trend/result_dates.json`),
    ]);
    setAnalysis(a);
    setEconNews(e);
    setNaver(n);
    setNews(ns);
    setMarket(mk);
    setAvailableDates(dates?.dates ?? []);
    const now = new Date().toLocaleTimeString("ko-KR");
    setLastFetch(now);
    setEconUpdated(now);
    setLoading(false);
  }

  // 시장 데이터 단독 갱신 (네이버 검색추이 + 시장 현황)
  const refreshMarket = useCallback(async () => {
    const [mk, n] = await Promise.all([
      fetchJson<MarketData>(`${RAW}/trend/result_market.json`),
      fetchJson<NaverData>(`${RAW}/trend/result_naver.json`),
    ]);
    if (mk) setMarket(mk);
    if (n) setNaver(n);
    setLastFetch(new Date().toLocaleTimeString("ko-KR"));
  }, []);

  // 경제 뉴스 단독 갱신
  const refreshEconNews = useCallback(async () => {
    const e = await fetchJson<EconNewsData>(`${RAW}/trend/result_econ_news.json`);
    if (e) setEconNews(e);
    setEconUpdated(new Date().toLocaleTimeString("ko-KR"));
  }, []);

  useEffect(() => { loadData(); }, []);

  // 장중(09:00-15:30 KST)에는 10분, 장외에는 30분마다 시장 + 네이버 자동 갱신
  useEffect(() => {
    const intervalMs = marketOpen ? 10 * 60 * 1000 : 30 * 60 * 1000;
    const id = setInterval(refreshMarket, intervalMs);
    return () => clearInterval(id);
  }, [refreshMarket, marketOpen]);

  // 1시간마다 경제 뉴스 자동 갱신
  useEffect(() => {
    const id = setInterval(refreshEconNews, 60 * 60 * 1000);
    return () => clearInterval(id);
  }, [refreshEconNews]);

  const dataDate = analysis?.date ?? news?.date ?? "";

  return (
    <div className="min-h-screen bg-slate-100">
      {/* 헤더 */}
      <header className="bg-white border-b border-slate-200 shadow-sm px-6 py-3 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold text-slate-900">📈 Stock Platform</h1>
          <div className="flex items-center gap-3 mt-0.5">
            {dataDate && (
              <p className="text-xs text-slate-400">데이터 기준: {dataDate}</p>
            )}
            <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
              marketOpen
                ? "bg-green-100 text-green-700"
                : "bg-slate-100 text-slate-400"
            }`}>
              {marketOpen ? "● 장중" : "○ 장마감"} {kstTime}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-right hidden sm:block">
            {lastFetch && (
              <p className="text-xs text-slate-400">시장 갱신 {lastFetch}</p>
            )}
            {econUpdated && econUpdated !== lastFetch && (
              <p className="text-xs text-slate-300">뉴스 갱신 {econUpdated}</p>
            )}
          </div>
          <button
            onClick={loadData}
            disabled={loading}
            className="text-xs bg-blue-500 hover:bg-blue-600 disabled:bg-slate-200 text-white px-3 py-1.5 rounded-lg transition-colors font-medium"
          >
            {loading ? "갱신중..." : "새로고침"}
          </button>
        </div>
      </header>

      {/* 탭 */}
      <nav className="bg-white border-b border-slate-200 px-6">
        <div className="flex gap-0">
          {(["trend", "news"] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-5 py-3 text-sm font-medium border-b-2 transition-colors ${
                tab === t
                  ? "border-blue-500 text-blue-600"
                  : "border-transparent text-slate-500 hover:text-slate-700"
              }`}
            >
              {t === "trend" ? "📊 트렌드 분석" : "📰 뉴스 브리핑"}
            </button>
          ))}
        </div>
      </nav>

      {/* 본문 */}
      <main className="px-6 py-6 max-w-screen-2xl mx-auto">
        {loading ? (
          <div className="flex items-center justify-center h-64 text-slate-400 text-sm">
            데이터 불러오는 중...
          </div>
        ) : tab === "trend" ? (
          <TrendTab
            analysis={analysis}
            econNews={econNews}
            naver={naver}
            market={market}
            availableDates={availableDates}
            onRefreshMarket={refreshMarket}
            econUpdated={econUpdated}
          />
        ) : (
          <NewsTab news={news} />
        )}
      </main>
    </div>
  );
}
