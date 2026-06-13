// 워치리스트 추가/제거 패널 — /api/watchlist로 POST해 GitHub에 커밋한다
"use client";

import { useEffect, useState } from "react";

type Stock = { name: string; sector?: string; ticker?: string; folder?: string };
type Watchlist = { kr: Stock[]; us: Stock[] };

interface Props {
  open: boolean;
  onClose: () => void;
}

export default function WatchlistEditor({ open, onClose }: Props) {
  const [pw, setPw]           = useState("");
  const [list, setList]       = useState<Watchlist | null>(null);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg]         = useState<string | null>(null);
  const [err, setErr]         = useState<string | null>(null);

  // Add 폼 상태
  const [name, setName]     = useState("");
  const [market, setMarket] = useState<"kr" | "us">("kr");
  const [ticker, setTicker] = useState("");
  const [sector, setSector] = useState("");
  const [folder, setFolder] = useState("");

  useEffect(() => {
    if (!open) return;
    setMsg(null);
    setErr(null);
    fetch("/api/watchlist", { cache: "no-store" })
      .then(r => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((j: Watchlist) => setList(j))
      .catch(() => setErr("워치리스트를 불러오지 못했습니다."));
  }, [open]);

  async function submit(body: Record<string, unknown>) {
    setLoading(true);
    setMsg(null);
    setErr(null);
    try {
      const r = await fetch("/api/watchlist", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ password: pw, ...body }),
      });
      const j = await r.json();
      if (!r.ok) {
        setErr(`실패: ${j.error || r.status}${j.detail ? ` (${String(j.detail).slice(0, 120)})` : ""}`);
      } else {
        setMsg(`완료 — ${j.commit}. 3~5분 후 새로고침 버튼을 눌러주세요.`);
        // refresh list inline
        const r2 = await fetch("/api/watchlist", { cache: "no-store" });
        if (r2.ok) setList(await r2.json());
        // reset add form
        setName(""); setTicker(""); setSector(""); setFolder("");
      }
    } catch (e) {
      setErr(`네트워크 오류: ${String(e)}`);
    } finally {
      setLoading(false);
    }
  }

  function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    if (!pw)   { setErr("비밀번호를 입력하세요."); return; }
    if (!name) { setErr("종목명을 입력하세요."); return; }
    if (market === "us" && !ticker) { setErr("US 종목은 티커가 필요합니다."); return; }
    submit({ action: "add", name, market, ticker, sector, folder });
  }

  function handleRemove(stockName: string) {
    if (!pw) { setErr("비밀번호를 입력하세요."); return; }
    if (!confirm(`'${stockName}'을(를) 워치리스트에서 제거합니다. 진행할까요?`)) return;
    submit({ action: "remove", name: stockName });
  }

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-40 bg-black/40 flex items-center justify-center p-4" onClick={onClose}>
      <div
        className="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-auto"
        onClick={e => e.stopPropagation()}
      >
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between sticky top-0 bg-white">
          <h2 className="text-base font-semibold text-slate-800">⚙️ 워치리스트 편집</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700 text-sm">닫기</button>
        </div>

        <div className="px-6 py-4 space-y-4">
          {/* 비밀번호 */}
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">관리자 비밀번호</label>
            <input
              type="password"
              value={pw}
              onChange={e => setPw(e.target.value)}
              placeholder="Vercel WATCHLIST_PASSWORD"
              className="w-full px-3 py-1.5 text-sm rounded-lg border border-slate-200 focus:border-blue-400 outline-none"
              autoComplete="off"
            />
            <p className="text-xs text-slate-400 mt-1">세션 동안만 메모리에 보관됩니다.</p>
          </div>

          {/* Add 폼 */}
          <form onSubmit={handleAdd} className="border border-slate-200 rounded-xl p-4 space-y-3">
            <h3 className="text-sm font-semibold text-slate-700">➕ 종목 추가</h3>
            <div className="grid grid-cols-2 gap-3">
              <div className="col-span-2 sm:col-span-1">
                <label className="block text-xs text-slate-500 mb-1">종목명 (한국어)</label>
                <input value={name} onChange={e => setName(e.target.value)}
                       placeholder="예: 엔비디아"
                       className="w-full px-3 py-1.5 text-sm rounded-lg border border-slate-200 outline-none focus:border-blue-400" />
              </div>
              <div className="col-span-2 sm:col-span-1">
                <label className="block text-xs text-slate-500 mb-1">시장</label>
                <div className="flex gap-2">
                  {(["kr", "us"] as const).map(m => (
                    <button type="button" key={m}
                      onClick={() => setMarket(m)}
                      className={`flex-1 px-3 py-1.5 text-sm rounded-lg border transition-colors ${
                        market === m
                          ? "border-blue-500 bg-blue-50 text-blue-600 font-medium"
                          : "border-slate-200 text-slate-600 hover:bg-slate-50"
                      }`}>
                      {m === "kr" ? "🇰🇷 국내" : "🇺🇸 미국"}
                    </button>
                  ))}
                </div>
              </div>
              {market === "us" && (
                <div className="col-span-2 sm:col-span-1">
                  <label className="block text-xs text-slate-500 mb-1">티커 (필수)</label>
                  <input value={ticker} onChange={e => setTicker(e.target.value)}
                         placeholder="NVDA"
                         className="w-full px-3 py-1.5 text-sm rounded-lg border border-slate-200 outline-none focus:border-blue-400" />
                </div>
              )}
              <div className="col-span-2 sm:col-span-1">
                <label className="block text-xs text-slate-500 mb-1">섹터</label>
                <input value={sector} onChange={e => setSector(e.target.value)}
                       placeholder="반도체/AI"
                       className="w-full px-3 py-1.5 text-sm rounded-lg border border-slate-200 outline-none focus:border-blue-400" />
              </div>
              <div className="col-span-2">
                <label className="block text-xs text-slate-500 mb-1">폴더명 (생략 시 자동)</label>
                <input value={folder} onChange={e => setFolder(e.target.value)}
                       placeholder={market === "us" && ticker ? `${ticker}_${name || "종목"}` : name || "종목명"}
                       className="w-full px-3 py-1.5 text-sm rounded-lg border border-slate-200 outline-none focus:border-blue-400" />
              </div>
            </div>
            <button type="submit" disabled={loading}
                    className="w-full py-2 text-sm font-medium rounded-lg bg-blue-500 text-white hover:bg-blue-600 disabled:bg-slate-300 transition-colors">
              {loading ? "처리 중..." : "추가 요청"}
            </button>
            <p className="text-xs text-slate-400">
              GitHub에 즉시 커밋되고, Mac Mini가 3분 이내에 1년치 핵심 기사를 자동 수집합니다.
            </p>
          </form>

          {/* Remove 목록 */}
          {list && (
            <div className="border border-slate-200 rounded-xl p-4 space-y-3">
              <h3 className="text-sm font-semibold text-slate-700">➖ 등록된 종목</h3>
              {(["kr", "us"] as const).map(key => (
                <div key={key}>
                  <p className="text-xs text-slate-500 mb-1">{key === "kr" ? "🇰🇷 국내" : "🇺🇸 미국"} ({list[key].length})</p>
                  <div className="flex flex-wrap gap-1.5">
                    {list[key].map(s => (
                      <button key={s.name}
                              onClick={() => handleRemove(s.name)}
                              disabled={loading}
                              className="text-xs px-2 py-1 rounded-md bg-slate-100 hover:bg-red-100 hover:text-red-600 text-slate-600 transition-colors disabled:opacity-50">
                        {s.name}{s.ticker ? ` (${s.ticker})` : ""} ×
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}

          {msg && <div className="p-3 rounded-lg bg-emerald-50 text-emerald-700 text-sm">{msg}</div>}
          {err && <div className="p-3 rounded-lg bg-red-50 text-red-700 text-sm">{err}</div>}
        </div>
      </div>
    </div>
  );
}
