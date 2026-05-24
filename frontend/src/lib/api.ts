// Central API client — all backend calls go through here.
// Set VITE_API_URL in your .env file. Must use https:// in production.

const _configuredUrl = import.meta.env.VITE_API_URL as string | undefined;
if (!_configuredUrl) {
  console.warn("[MemeScope] VITE_API_URL is not set — falling back to http://localhost:8000");
}
const API_BASE = _configuredUrl ?? "http://localhost:8000";
const WS_BASE = API_BASE.replace(/^http/, "ws");

// ── Raw backend types ──────────────────────────────────────────────────────

export interface ApiSignal {
  id: string;
  token_mint: string;
  signal_type: "BUY" | "WATCH" | "AVOID" | "ALERT";
  confidence: number; // 0–1
  reason: string;
  source_rule: string;
  historical_success_rate: number | null;
  triggered_at: string;
  expires_at: string | null;
  is_active: boolean;
  created_at: string;
}

export interface ApiWalletProfile {
  id: string;
  address: string;
  first_seen: string | null;
  last_active: string | null;
  total_trades: number;
  total_tokens_traded: number;
  total_volume_usd: number;
  avg_trade_size_usd: number;
  win_rate: number | null;
  avg_roi: number | null;
  entry_timing_score: number | null;
  hold_duration_avg: number | null;
  consistency_score: number | null;
  composite_score: number | null;
  cluster_id: string | null;
  tags: string | null;
  recent_trades: number;
  profitable_tokens: number;
  unprofitable_tokens: number;
}

export interface ApiTrade {
  id: string;
  token_mint: string;
  wallet_address: string;
  side: "BUY" | "SELL" | "TRANSFER_IN" | "TRANSFER_OUT";
  amount_token: number;
  amount_sol: number | null;
  price_usd: number | null;
  value_usd: number | null;
  tx_signature: string;
  slot: number | null;
  timestamp: string;
  created_at: string;
}

export interface ApiHolderSnapshot {
  wallet_address: string;
  rank: number;
  balance: number;
  pct_supply: number;
  snapshot_at: string;
}

export interface ApiTop10Response {
  token_mint: string;
  holders: ApiHolderSnapshot[];
  total_supply: number | null;
  top10_concentration: number;
  snapshot_at: string;
}

export interface ApiStats {
  active_signals: number;
  tracked_wallets: number;
  tokens_scanned: number;
  avg_confidence: number;
}

// ── Fetch helpers ──────────────────────────────────────────────────────────

async function apiFetch<T>(path: string, params?: Record<string, string | number>): Promise<T> {
  const url = new URL(`${API_BASE}${path}`);
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      url.searchParams.set(k, String(v));
    }
  }
  const res = await fetch(url.toString());
  if (!res.ok) {
    const err = new Error(`API ${res.status}: ${path}`);
    (err as any).status = res.status;
    throw err;
  }
  return res.json() as Promise<T>;
}

// ── Public API ─────────────────────────────────────────────────────────────

export async function fetchSignals(limit = 100, minConfidence?: number): Promise<ApiSignal[]> {
  const params: Record<string, string | number> = { limit };
  if (minConfidence !== undefined) params.min_confidence = minConfidence;
  return apiFetch<ApiSignal[]>("/api/v1/signals", params);
}

export async function fetchWalletProfile(address: string): Promise<ApiWalletProfile> {
  return apiFetch<ApiWalletProfile>(`/api/v1/wallets/${encodeURIComponent(address)}`);
}

export async function fetchWalletTrades(address: string, limit = 50): Promise<ApiTrade[]> {
  return apiFetch<ApiTrade[]>(`/api/v1/wallets/${encodeURIComponent(address)}/trades`, { limit });
}

export async function fetchTokenHolders(mint: string): Promise<ApiTop10Response> {
  return apiFetch<ApiTop10Response>(`/api/v1/holders/${encodeURIComponent(mint)}/top10`);
}

export async function fetchTokenSignals(mint: string): Promise<ApiSignal[]> {
  return apiFetch<ApiSignal[]>(`/api/v1/signals/${encodeURIComponent(mint)}`);
}

export async function fetchStats(): Promise<ApiStats> {
  return apiFetch<ApiStats>("/api/v1/stats");
}

// ── WebSocket ──────────────────────────────────────────────────────────────

export type WsMessage =
  | { type: "signal"; payload: ApiSignal }
  | { type: "ping"; ts: string }
  | { type: "raw"; data: unknown };

export function connectSignalStream(
  onMessage: (msg: WsMessage) => void,
  onError?: (e: Event) => void,
): () => void {
  let ws: WebSocket | null = null;
  let retryTimeout: ReturnType<typeof setTimeout> | null = null;
  let closed = false;

  function connect() {
    if (closed) return;
    ws = new WebSocket(`${WS_BASE}/ws/signals`);

    ws.onmessage = (e) => {
      try {
        const raw = JSON.parse(e.data as string);
        if (raw?.type === "ping") {
          onMessage({ type: "ping", ts: raw.ts });
        } else if (raw?.token_mint) {
          onMessage({ type: "signal", payload: raw as ApiSignal });
        } else {
          onMessage({ type: "raw", data: raw });
        }
      } catch {
        // ignore malformed frames
      }
    };

    ws.onerror = (e) => onError?.(e);

    ws.onclose = () => {
      if (!closed) {
        retryTimeout = setTimeout(connect, 5000);
      }
    };
  }

  connect();

  return () => {
    closed = true;
    if (retryTimeout) clearTimeout(retryTimeout);
    ws?.close();
  };
}

// ── Adapters: ApiSignal → UI Signal ───────────────────────────────────────

import type { Signal, Confidence } from "./mockData";

function ageLabel(iso: string): { label: string; minutes: number } {
  const diffMs = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(diffMs / 60_000);
  if (minutes < 60) return { label: `${minutes} min`, minutes };
  const hours = Math.floor(minutes / 60);
  return { label: `${hours}h`, minutes };
}

function confidenceFromFloat(v: number): Confidence {
  if (v >= 0.7) return "HIGH";
  if (v >= 0.4) return "MEDIUM";
  return "LOW";
}

function actionBiasFromType(t: ApiSignal["signal_type"]): string {
  if (t === "BUY") return "ENTER";
  if (t === "WATCH") return "WATCH";
  if (t === "AVOID") return "SKIP";
  return "WATCH";
}

export function adaptSignal(s: ApiSignal): Signal {
  const { label, minutes } = ageLabel(s.triggered_at);
  const conf = confidenceFromFloat(s.confidence);
  // reason may be a pipe-delimited string like "3 high WR wallets entered | Cluster detected"
  const reasons = s.reason.split(/[|;]/).map((r) => r.trim()).filter(Boolean);
  const shortMint = s.token_mint.slice(0, 4).toUpperCase();
  return {
    id: s.id,
    token: s.token_mint.slice(0, 8) + "…",
    ticker: `$${shortMint}`,
    age: label,
    ageMinutes: minutes,
    liquidity: "—",
    liquidityK: 0,
    holders: 0,
    smartWallets: 0,
    clusterDetected: s.source_rule.toLowerCase().includes("cluster"),
    earlyEntry: s.source_rule.toLowerCase().includes("entry") || s.source_rule.toLowerCase().includes("smart"),
    confidence: conf,
    actionBias: actionBiasFromType(s.signal_type),
    reasons,
    timestamp: new Date(s.triggered_at),
    priceChange: 0,
    walletScoreAvg: 0,
    winRateAvg: 0,
  };
}
