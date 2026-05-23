// 뉴스 브리핑 탭 — 종목별 필터 사이드바 + 1년치 핵심 기사 펼치기 + 워치리스트 편집 패널
"use client";

import { useState } from "react";
import type { NewsData, NewsItem, BackfillIndex, BackfillItem } from "../page";
import WatchlistEditor from "./WatchlistEditor";

interface Props {
  news:     NewsData | null;
  backfill: BackfillIndex | null;
}

function BackfillPanel({ items }: { items: BackfillItem[] }) {
  if (!items || items.length === 0) {
    return <p className="px-4 py-3 text-xs text-slate-400">수집 대기 중 — Mac Mini가 3분 내에 백필합니다.</p>;
  }
  return (
    <ul className="divide-y divide-slate-50 bg-amber-50/30">
      {items.map((it, i) => (
        <li key={i} className="px-4 py-2">
          <a
            href={it.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-slate-700 hover:text-blue-600 transition-colors leading-relaxed block"
          >
            <span className="inline-block min-w-[1.5rem] text-amber-600 font-semibold">{i + 1}.</span>
            {it.title}
          </a>
          <div className="flex items-center gap-2 mt-1 ml-6">
            <span className="text-xs text-slate-400">{it.date}</span>
            <span className="text-xs text-amber-600">중요도 {it.score}</span>
            <span className="text-xs text-slate-400 ml-auto">{it.source}</span>
          </div>
        </li>
      ))}
    </ul>
  );
}

function NewsCard({
  name,
  sub,
  items,
  backfillItems,
}: {
  name: string;
  sub: string;
  items: NewsItem[];
  backfillItems: BackfillItem[];
}) {
  const [showBackfill, setShowBackfill] = useState(false);
  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
      <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
        <h3 className="font-semibold text-slate-800 text-sm">{name}</h3>
        <div className="flex items-center gap-2">
          {sub && <span className="text-xs text-slate-400">{sub}</span>}
          <span className="text-xs bg-slate-100 text-slate-500 px-2 py-0.5 rounded-full">
            {items.length}건
          </span>
        </div>
      </div>
      {items.length === 0 ? (
        <p className="px-4 py-3 text-xs text-slate-400">수집된 뉴스 없음</p>
      ) : (
        <ul className="divide-y divide-slate-50">
          {items.slice(0, 5).map((it, i) => (
            <li key={i} className="px-4 py-2.5">
              <a
                href={it.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-slate-700 hover:text-blue-600 transition-colors leading-relaxed block"
              >
                {it.title}
              </a>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-xs text-slate-400">{it.date}</span>
                <span className="text-xs text-slate-400">{it.source}</span>
              </div>
            </li>
          ))}
        </ul>
      )}

      <button
        onClick={() => setShowBackfill(v => !v)}
        className="w-full px-4 py-2 text-xs text-amber-700 hover:bg-amber-50 border-t border-slate-100 transition-colors flex items-center justify-between"
      >
        <span>📚 1년치 핵심 기사 {backfillItems.length > 0 ? `(${backfillItems.length})` : ""}</span>
        <span>{showBackfill ? "접기 ▲" : "펼치기 ▼"}</span>
      </button>
      {showBackfill && <BackfillPanel items={backfillItems} />}
    </div>
  );
}

export default function NewsTab({ news, backfill }: Props) {
  const [selected, setSelected] = useState<string | null>(null);
  const [editorOpen, setEditorOpen] = useState(false);

  if (!news) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-400 text-sm">
        뉴스 데이터 없음 — GitHub push 후 자동 갱신됩니다.
      </div>
    );
  }

  // 백필 인덱스를 종목명으로 빠르게 조회할 수 있도록 맵으로 변환
  const backfillByName = new Map<string, BackfillItem[]>();
  (backfill?.kr ?? []).forEach(s => backfillByName.set(s.name, s.items));
  (backfill?.us ?? []).forEach(s => backfillByName.set(s.name, s.items));

  type StockEntry = { name: string; sub: string; items: NewsItem[]; region: "kr" | "us" };
  const allStocks: StockEntry[] = [
    ...news.kr.map((s) => ({ name: s.name, sub: s.sector, items: s.items, region: "kr" as const })),
    ...news.us.map((s) => ({ name: s.name, sub: s.ticker, items: s.items, region: "us" as const })),
  ];

  const displayStocks = selected
    ? allStocks.filter((s) => s.name === selected)
    : allStocks;

  const totalCount = allStocks.reduce((sum, s) => sum + s.items.length, 0);
  const krStocks = allStocks.filter((s) => s.region === "kr");
  const usStocks = allStocks.filter((s) => s.region === "us");

  return (
    <div className="flex gap-4 h-full">

      {/* 종목 선택 사이드바 */}
      <aside className="w-44 shrink-0 bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden self-start sticky top-6">
        <div className="px-3 py-2.5 border-b border-slate-100 flex items-center justify-between gap-1">
          <p className="text-xs font-semibold text-slate-600 uppercase tracking-wide">종목 선택</p>
          <button
            onClick={() => setEditorOpen(true)}
            title="워치리스트 편집"
            className="text-xs px-1.5 py-0.5 rounded-md bg-blue-50 text-blue-600 hover:bg-blue-100 transition-colors"
          >
            ⚙️ 편집
          </button>
        </div>
        <div className="overflow-auto max-h-[calc(100vh-200px)]">
          <button
            onClick={() => setSelected(null)}
            className={`w-full text-left px-3 py-2 text-xs font-medium transition-colors ${
              !selected
                ? "bg-blue-50 text-blue-600"
                : "text-slate-600 hover:bg-slate-50"
            }`}
          >
            전체 ({allStocks.length}종목 / {totalCount}건)
          </button>

          {krStocks.length > 0 && (
            <div className="px-3 py-1.5 text-xs text-slate-400 font-medium bg-slate-50 border-t border-slate-100">
              🇰🇷 국내
            </div>
          )}
          {krStocks.map((s) => (
            <button
              key={s.name}
              onClick={() => setSelected(s.name === selected ? null : s.name)}
              className={`w-full text-left px-3 py-2 text-xs transition-colors flex items-center justify-between gap-1 ${
                selected === s.name
                  ? "bg-blue-50 text-blue-600 font-medium"
                  : "text-slate-700 hover:bg-slate-50"
              }`}
            >
              <span className="truncate">{s.name}</span>
              <span className={`shrink-0 text-xs px-1 py-0.5 rounded ${
                selected === s.name ? "bg-blue-100 text-blue-600" : "bg-slate-100 text-slate-400"
              }`}>
                {s.items.length}
              </span>
            </button>
          ))}

          {usStocks.length > 0 && (
            <div className="px-3 py-1.5 text-xs text-slate-400 font-medium bg-slate-50 border-t border-slate-100">
              🇺🇸 미국
            </div>
          )}
          {usStocks.map((s) => (
            <button
              key={s.name}
              onClick={() => setSelected(s.name === selected ? null : s.name)}
              className={`w-full text-left px-3 py-2 text-xs transition-colors flex items-center justify-between gap-1 ${
                selected === s.name
                  ? "bg-blue-50 text-blue-600 font-medium"
                  : "text-slate-700 hover:bg-slate-50"
              }`}
            >
              <span className="truncate">{s.name}</span>
              <span className={`shrink-0 text-xs px-1 py-0.5 rounded ${
                selected === s.name ? "bg-blue-100 text-blue-600" : "bg-slate-100 text-slate-400"
              }`}>
                {s.items.length}
              </span>
            </button>
          ))}
        </div>
      </aside>

      {/* 뉴스 본문 */}
      <div className="flex-1 min-w-0">
        {selected ? (
          /* 선택된 종목 단일 뷰 */
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <h2 className="text-base font-semibold text-slate-800">{selected}</h2>
              <button
                onClick={() => setSelected(null)}
                className="text-xs text-slate-400 hover:text-slate-600 bg-slate-100 px-2 py-0.5 rounded-full"
              >
                전체 보기
              </button>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {displayStocks.map((s) => (
                <NewsCard key={s.name} name={s.name} sub={s.sub} items={s.items} backfillItems={backfillByName.get(s.name) ?? []} />
              ))}
            </div>
          </div>
        ) : (
          /* 전체 보기 */
          <div className="space-y-8">
            {krStocks.length > 0 && (
              <div>
                <div className="flex items-center gap-3 mb-4">
                  <h2 className="text-base font-semibold text-slate-800">🇰🇷 국내 종목</h2>
                  <span className="text-xs text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full">
                    {krStocks.reduce((s, v) => s + v.items.length, 0)}건
                  </span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                  {krStocks.map((s) => (
                    <NewsCard key={s.name} name={s.name} sub={s.sub} items={s.items} backfillItems={backfillByName.get(s.name) ?? []} />
                  ))}
                </div>
              </div>
            )}
            {usStocks.length > 0 && (
              <div>
                <div className="flex items-center gap-3 mb-4">
                  <h2 className="text-base font-semibold text-slate-800">🇺🇸 미국 종목</h2>
                  <span className="text-xs text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full">
                    {usStocks.reduce((s, v) => s + v.items.length, 0)}건
                  </span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                  {usStocks.map((s) => (
                    <NewsCard key={s.name} name={s.name} sub={s.sub} items={s.items} backfillItems={backfillByName.get(s.name) ?? []} />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      <WatchlistEditor open={editorOpen} onClose={() => setEditorOpen(false)} />
    </div>
  );
}
