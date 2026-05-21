"use client";

import { useEffect, useState } from "react";
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
  total_articles: number;
  matched_count: number;
  top_news: EconNewsItem[];
}

export interface NaverData {
  date: string;
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

export default function Dashboard() {
  const [tab, setTab] = useState<Tab>("trend");
  const [analysis, setAnalysis] = useState<AnalysisData | null>(null);
  const [econNews, setEconNews] = useState<EconNewsData | null>(null);
  const [naver, setNaver] = useState<NaverData | null>(null);
  const [news, setNews] = useState<NewsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastFetch, setLastFetch] = useState<string>("");

  async function loadData() {
    setLoading(true);
    const [a, e, n, ns] = await Promise.all([
      fetchJson<AnalysisData>(`${RAW}/trend/result_analysis.json`),
      fetchJson<EconNewsData>(`${RAW}/trend/result_econ_news.json`),
      fetchJson<NaverData>(`${RAW}/trend/result_naver.json`),
      fetchJson<NewsData>(`${RAW}/news/latest_news.json`),
    ]);
    setAnalysis(a);
    setEconNews(e);
    setNaver(n);
    setNews(ns);
    setLastFetch(new Date().toLocaleTimeString("ko-KR"));
    setLoading(false);
  }

  useEffect(() => { loadData(); }, []);

  const dataDate = analysis?.date ?? news?.date ?? "";

  return (
    <div className="min-h-screen bg-slate-900 text-slate-200">
      <header className="border-b border-slate-700 px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">📈 Stock Platform</h1>
          {dataDate && (
            <p className="text-xs text-slate-400 mt-0.5">데이터 기준: {dataDate}</p>
          )}
        </div>
        <div className="flex items-center gap-3">
          {lastFetch && (
            <span className="text-xs text-slate-500">갱신 {lastFetch}</span>
          )}
          <button
            onClick={loadData}
            className="text-xs bg-slate-700 hover:bg-slate-600 px-3 py-1.5 rounded-md transition-colors"
          >
            새로고침
          </button>
        </div>
      </header>

      <nav className="border-b border-slate-700 px-6">
        <div className="flex gap-0">
          {(["trend", "news"] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-5 py-3 text-sm font-medium border-b-2 transition-colors ${
                tab === t
                  ? "border-blue-500 text-blue-400"
                  : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
            >
              {t === "trend" ? "📊 트렌드 분석" : "📰 뉴스 브리핑"}
            </button>
          ))}
        </div>
      </nav>

      <main className="px-6 py-6">
        {loading ? (
          <div className="flex items-center justify-center h-64 text-slate-400">
            데이터 로딩 중...
          </div>
        ) : tab === "trend" ? (
          <TrendTab analysis={analysis} econNews={econNews} naver={naver} />
        ) : (
          <NewsTab news={news} />
        )}
      </main>
    </div>
  );
}
