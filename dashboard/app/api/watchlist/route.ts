// watchlist.json을 GitHub Contents API로 편집해 Mac Mini 폴러가 받아갈 수 있게 하는 서버리스 엔드포인트
import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const runtime  = "nodejs";

const REPO       = "makitjung/stock-platform";
const FILE_PATH  = "watchlist.json";
const GH_API     = `https://api.github.com/repos/${REPO}/contents/${FILE_PATH}`;

type StockEntry = {
  name:    string;
  sector?: string;
  ticker?: string;
  folder?: string;
};

type Watchlist = { kr: StockEntry[]; us: StockEntry[] };

function bad(status: number, error: string, detail?: unknown) {
  return NextResponse.json({ error, detail }, { status });
}

async function ghHeaders() {
  const token = process.env.GITHUB_TOKEN;
  if (!token) throw new Error("GITHUB_TOKEN missing on server");
  return {
    Authorization: `Bearer ${token}`,
    Accept:        "application/vnd.github+json",
    "User-Agent":  "stock-platform-dashboard",
  } as Record<string, string>;
}

async function readWatchlist(): Promise<{ data: Watchlist; sha: string }> {
  const headers = await ghHeaders();
  const r = await fetch(`${GH_API}?ref=main`, { headers, cache: "no-store" });
  if (!r.ok) throw new Error(`github read failed (${r.status})`);
  const j = await r.json();
  const sha     = j.sha as string;
  const content = Buffer.from(j.content, "base64").toString("utf-8");
  const data    = JSON.parse(content) as Watchlist;
  if (!data.kr) data.kr = [];
  if (!data.us) data.us = [];
  return { data, sha };
}

async function writeWatchlist(data: Watchlist, sha: string, message: string) {
  const headers = await ghHeaders();
  const body = {
    message,
    sha,
    content: Buffer.from(JSON.stringify(data, null, 2) + "\n").toString("base64"),
    branch:  "main",
  };
  const r = await fetch(GH_API, {
    method: "PUT",
    headers: { ...headers, "Content-Type": "application/json" },
    body:    JSON.stringify(body),
  });
  if (!r.ok) {
    const detail = await r.text();
    throw new Error(`github write failed (${r.status}): ${detail.slice(0, 200)}`);
  }
  return r.json();
}

export async function POST(req: Request) {
  let body: Record<string, unknown>;
  try {
    body = await req.json();
  } catch {
    return bad(400, "invalid_json");
  }

  // 인증
  const pw = process.env.WATCHLIST_PASSWORD;
  if (!pw)                 return bad(500, "server_password_missing");
  if (body.password !== pw) return bad(401, "unauthorized");

  // 공통 필드
  const action = body.action;
  const name   = typeof body.name === "string" ? body.name.trim() : "";
  if (!name)                             return bad(400, "name_required");
  if (action !== "add" && action !== "remove") return bad(400, "bad_action");

  let watchlist: Watchlist;
  let sha: string;
  try {
    ({ data: watchlist, sha } = await readWatchlist());
  } catch (e) {
    return bad(502, "github_read_failed", String(e));
  }

  let commitMsg = "";

  if (action === "add") {
    const market = body.market === "kr" || body.market === "us" ? body.market : null;
    if (!market) return bad(400, "bad_market");
    const ticker = typeof body.ticker === "string" ? body.ticker.trim().toUpperCase() : "";
    const sector = typeof body.sector === "string" ? body.sector.trim() : "";
    const folder = typeof body.folder === "string" ? body.folder.trim() : "";
    if (market === "us" && !ticker) return bad(400, "ticker_required_for_us");

    const list = watchlist[market];
    if (list.some(s => s.name === name)) return bad(409, "duplicate");

    const entry: StockEntry = { name };
    if (sector) entry.sector = sector;
    if (market === "us") {
      entry.ticker = ticker;
      entry.folder = folder || `${ticker}_${name}`;
    } else if (folder) {
      entry.folder = folder;
    }
    list.push(entry);
    commitMsg = `watchlist: +${name}${market === "us" ? ` (${ticker})` : ""}`;
  } else {
    // remove: kr/us 어느 쪽이든 찾으면 제거
    let removed = false;
    for (const key of ["kr", "us"] as const) {
      const idx = watchlist[key].findIndex(s => s.name === name);
      if (idx >= 0) {
        watchlist[key].splice(idx, 1);
        removed = true;
        commitMsg = `watchlist: -${name}`;
        break;
      }
    }
    if (!removed) return bad(404, "not_found");
  }

  try {
    await writeWatchlist(watchlist, sha, commitMsg);
  } catch (e) {
    return bad(502, "github_write_failed", String(e));
  }

  return NextResponse.json({ ok: true, commit: commitMsg });
}

// 대시보드 폼이 현재 워치리스트를 읽을 때 사용
export async function GET() {
  try {
    const { data } = await readWatchlist();
    return NextResponse.json(data, {
      headers: { "Cache-Control": "no-store" },
    });
  } catch (e) {
    return bad(502, "github_read_failed", String(e));
  }
}
