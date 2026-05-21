"use client";

import type { AnalysisData, EconNewsData, NaverData } from "../page";

interface Props {
  analysis: AnalysisData | null;
  econNews: EconNewsData | null;
  naver: NaverData | null;
}

function ScoreBadge({ score }: { score: number }) {
  const color =
    score >= 70 ? "bg-red-900 text-red-300" :
    score >= 40 ? "bg-yellow-900 text-yellow-300" :
    "bg-slate-700 text-slate-300";
  return (
    <span className={`inline-block text-xs font-bold px-2 py-0.5 rounded ${color}`}>
      {score.toFixed(0)}
    </span>
  );
}

function ChangeRate({ rate }: { rate: number }) {
  const color = rate > 0 ? "text-green-400" : rate < 0 ? "text-red-400" : "text-slate-400";
  const prefix = rate > 0 ? "▲" : rate < 0 ? "▼" : "—";
  return (
    <span className={`text-xs font-medium ${color}`}>
      {prefix} {Math.abs(rate).toFixed(1)}%
    </span>
  );
}

export default function TrendTab({ analysis, econNews, naver }: Props) {
  return (
    <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
      {/* Top 50 키워드 */}
      <div className="xl:col-span-2 bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
        <div className="px-5 py-3 border-b border-slate-700 flex items-center justify-between">
          <h2 className="font-semibold text-white">🔥 Top 50 키워드</h2>
          {analysis && (
            <span className="text-xs text-slate-400">
              {analysis.total_analyzed}개 분석 · {analysis.mode} 모드
            </span>
          )}
        </div>
        {!analysis ? (
          <p className="p-5 text-slate-400 text-sm">데이터 없음</p>
        ) : (
          <div className="overflow-auto max-h-[600px]">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-slate-800/90 backdrop-blur text-xs text-slate-400 uppercase">
                <tr>
                  <th className="px-4 py-2 text-left w-6">#</th>
                  <th className="px-4 py-2 text-left">키워드</th>
                  <th className="px-4 py-2 text-right">총점</th>
                  <th className="px-4 py-2 text-right">1일</th>
                  <th className="px-4 py-2 text-right">3일</th>
                  <th className="px-4 py-2 text-right">7일</th>
                  <th className="px-4 py-2 text-left">시그널</th>
                </tr>
              </thead>
              <tbody>
                {analysis.top50.map((row, i) => (
                  <tr
                    key={row.keyword}
                    className="border-t border-slate-700/50 hover:bg-slate-700/30 transition-colors"
                  >
                    <td className="px-4 py-2 text-slate-500 text-xs">{i + 1}</td>
                    <td className="px-4 py-2 font-medium text-white">{row.keyword}</td>
                    <td className="px-4 py-2 text-right">
                      <ScoreBadge score={row.total_score} />
                    </td>
                    <td className="px-4 py-2 text-right text-slate-300 text-xs">
                      {row.day1_score?.toFixed(0) ?? "—"}
                    </td>
                    <td className="px-4 py-2 text-right text-slate-300 text-xs">
                      {row.day3_score?.toFixed(0) ?? "—"}
                    </td>
                    <td className="px-4 py-2 text-right text-slate-300 text-xs">
                      {row.day7_score?.toFixed(0) ?? "—"}
                    </td>
                    <td className="px-4 py-2">
                      <div className="flex flex-wrap gap-1">
                        {(row.signals ?? []).slice(0, 3).map((s) => (
                          <span
                            key={s}
                            className="text-xs bg-blue-900/50 text-blue-300 px-1.5 py-0.5 rounded"
                          >
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

      {/* 오른쪽 컬럼 */}
      <div className="flex flex-col gap-6">
        {/* 네이버 데이터랩 */}
        <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
          <div className="px-5 py-3 border-b border-slate-700">
            <h2 className="font-semibold text-white">📈 네이버 검색 추이</h2>
          </div>
          {!naver?.datalab?.length ? (
            <p className="p-5 text-slate-400 text-sm">데이터 없음</p>
          ) : (
            <div className="divide-y divide-slate-700/50 max-h-64 overflow-auto">
              {naver.datalab.map((item) => (
                <div key={item.keyword} className="px-5 py-3 flex items-center justify-between">
                  <span className="text-sm text-white">{item.keyword}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-400">{item.recent.toFixed(1)}</span>
                    <ChangeRate rate={item.change_rate} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 경제 뉴스 */}
        <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden flex-1">
          <div className="px-5 py-3 border-b border-slate-700 flex items-center justify-between">
            <h2 className="font-semibold text-white">📰 경제 뉴스</h2>
            {econNews && (
              <span className="text-xs text-slate-400">
                {econNews.matched_count}/{econNews.total_articles}건
              </span>
            )}
          </div>
          {!econNews?.top_news?.length ? (
            <p className="p-5 text-slate-400 text-sm">데이터 없음</p>
          ) : (
            <div className="divide-y divide-slate-700/50 max-h-96 overflow-auto">
              {econNews.top_news.slice(0, 15).map((item, i) => (
                <div key={i} className="px-5 py-3">
                  <a
                    href={item.link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-slate-200 hover:text-blue-400 transition-colors leading-snug block"
                  >
                    {item.title}
                  </a>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-xs text-slate-500">{item.source}</span>
                    {item.matched_keywords?.slice(0, 2).map((kw) => (
                      <span
                        key={kw}
                        className="text-xs bg-slate-700 text-slate-400 px-1.5 py-0.5 rounded"
                      >
                        {kw}
                      </span>
                    ))}
                    <span className="text-xs text-slate-500 ml-auto">
                      점수 {item.score}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
