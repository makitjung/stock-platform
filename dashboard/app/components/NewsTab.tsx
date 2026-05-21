"use client";

import type { NewsData, NewsItem } from "../page";

interface Props {
  news: NewsData | null;
}

function StockCard({
  name,
  sub,
  items,
}: {
  name: string;
  sub: string;
  items: NewsItem[];
}) {
  return (
    <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
      <div className="px-4 py-3 border-b border-slate-700 flex items-center justify-between">
        <h3 className="font-semibold text-white text-sm">{name}</h3>
        <div className="flex items-center gap-2">
          {sub && (
            <span className="text-xs text-slate-500">{sub}</span>
          )}
          <span className="text-xs bg-slate-700 text-slate-400 px-2 py-0.5 rounded-full">
            {items.length}건
          </span>
        </div>
      </div>
      {items.length === 0 ? (
        <p className="px-4 py-3 text-xs text-slate-500">수집된 뉴스 없음</p>
      ) : (
        <ul className="divide-y divide-slate-700/40">
          {items.slice(0, 5).map((it, i) => (
            <li key={i} className="px-4 py-2.5">
              <a
                href={it.link}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-slate-300 hover:text-blue-400 transition-colors leading-relaxed block"
              >
                {it.title}
              </a>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-xs text-slate-600">{it.date}</span>
                <span className="text-xs text-slate-600">{it.source}</span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function NewsTab({ news }: Props) {
  if (!news) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-400 text-sm">
        뉴스 데이터 없음 — GitHub push 후 자동 갱신됩니다.
      </div>
    );
  }

  const totalKr = news.kr.reduce((s, v) => s + v.items.length, 0);
  const totalUs = news.us.reduce((s, v) => s + v.items.length, 0);

  return (
    <div className="space-y-8">
      <div>
        <div className="flex items-center gap-3 mb-4">
          <h2 className="text-base font-semibold text-white">🇰🇷 국내 종목</h2>
          <span className="text-xs text-slate-400">{totalKr}건</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {news.kr.map((stock) => (
            <StockCard
              key={stock.name}
              name={stock.name}
              sub={stock.sector}
              items={stock.items}
            />
          ))}
        </div>
      </div>

      <div>
        <div className="flex items-center gap-3 mb-4">
          <h2 className="text-base font-semibold text-white">🇺🇸 미국 종목</h2>
          <span className="text-xs text-slate-400">{totalUs}건</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {news.us.map((stock) => (
            <StockCard
              key={stock.name}
              name={stock.name}
              sub={stock.ticker}
              items={stock.items}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
