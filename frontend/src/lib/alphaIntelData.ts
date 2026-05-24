// Deterministic mock data for the Alpha Intel-style main page.
// Mirrors the shapes used by the reference project but generated with
// stable values so the UI is consistent across renders.

export interface AIWallet {
  address: string;
  rank: number;
  totalTrades: number;
  winRate: number;
  totalPnl: number;
  avgEntry: number;
  avgHoldingHours: number;
  profitableTrades: number;
  losingTrades: number;
  firstSeen: string;
  walletAge: number;
  isFresh: boolean;
  smartScore: number;
  avgEntryDelay: number;
}

export interface AITrade {
  wallet: string;
  token: string;
  type: "buy" | "sell";
  amount: number;
  price: number;
  pnl: number;
  timestamp: string;
  holdingDuration: number;
}

export interface AITokenOverlap {
  token: string;
  walletCount: number;
  wallets: string[];
  avgPnl: number;
}

export interface AIWinRateBucket {
  range: string;
  count: number;
  wallets: string[];
  avgPnl: number;
}

export interface AIHoldingBucket {
  range: string;
  count: number;
}

export interface AIPnlPoint {
  date: string;
  cumulative: number;
}

const walletAddrs = [
  "7xKp...3nFd",
  "Dq4R...8mVx",
  "Fg9L...2wKt",
  "Bm3Y...6pNr",
  "Hs8W...1jQe",
  "Nx5T...9cAz",
  "Vr2E...4sLm",
  "Jk7P...5hBf",
  "Ct6U...0dWg",
  "Aw1Z...7yRi",
];

const tokens = [
  "BONK",
  "WIF",
  "POPCAT",
  "BOME",
  "MEW",
  "MYRO",
  "SLERF",
  "PONKE",
  "WEN",
  "BOOK",
];

// Stable PRNG (mulberry32) so values are deterministic across renders
const rng = (seed: number) => {
  let t = seed >>> 0;
  return () => {
    t += 0x6d2b79f5;
    let r = t;
    r = Math.imul(r ^ (r >>> 15), r | 1);
    r ^= r + Math.imul(r ^ (r >>> 7), r | 61);
    return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
  };
};

const r = rng(20250421);

export const topWallets: AIWallet[] = walletAddrs
  .map((addr, i) => {
    const winRate = 35 + r() * 45;
    const totalTrades = 40 + Math.floor(r() * 200);
    const profitableTrades = Math.floor(totalTrades * (winRate / 100));
    const walletAge =
      i < 3 ? Math.floor(r() * 14) + 1 : 60 + Math.floor(r() * 800);
    return {
      address: addr,
      rank: 0,
      totalTrades,
      winRate: Math.round(winRate * 10) / 10,
      totalPnl: Math.round((r() * 400 - 80) * 100) / 100,
      avgEntry: Math.round(r() * 0.05 * 10000) / 10000,
      avgHoldingHours: Math.round((2 + r() * 72) * 10) / 10,
      profitableTrades,
      losingTrades: totalTrades - profitableTrades,
      firstSeen: walletAge < 15 ? "2025-03-28" : "2023-06-15",
      walletAge,
      isFresh: walletAge < 15,
      smartScore: Math.round(20 + r() * 80),
      avgEntryDelay: Math.round((1 + r() * 30) * 10) / 10,
    };
  })
  .sort((a, b) => b.smartScore - a.smartScore)
  .map((w, i) => ({ ...w, rank: i + 1 }));

export const tradeRecords: AITrade[] = (() => {
  const out: AITrade[] = [];
  topWallets.forEach((w) => {
    const n = 3 + Math.floor(r() * 5);
    for (let i = 0; i < n; i++) {
      const tok = tokens[Math.floor(r() * tokens.length)];
      out.push({
        wallet: w.address,
        token: tok,
        type: r() > 0.5 ? "buy" : "sell",
        amount: Math.round(r() * 1000),
        price: Math.round(r() * 0.05 * 10000) / 10000,
        pnl: Math.round((r() * 60 - 20) * 100) / 100,
        timestamp: `2025-04-${10 + Math.floor(r() * 10)}`,
        holdingDuration: Math.round(r() * 48 * 10) / 10,
      });
    }
  });
  return out;
})();

export const tokenOverlaps: AITokenOverlap[] = (() => {
  const map = new Map<string, { wallets: Set<string>; pnls: number[] }>();
  tradeRecords.forEach((t) => {
    if (!map.has(t.token))
      map.set(t.token, { wallets: new Set(), pnls: [] });
    const e = map.get(t.token)!;
    e.wallets.add(t.wallet);
    e.pnls.push(t.pnl);
  });
  return Array.from(map.entries())
    .map(([token, e]) => ({
      token,
      walletCount: e.wallets.size,
      wallets: Array.from(e.wallets),
      avgPnl:
        Math.round((e.pnls.reduce((s, x) => s + x, 0) / e.pnls.length) * 100) /
        100,
    }))
    .filter((t) => t.walletCount >= 2)
    .sort((a, b) => b.walletCount - a.walletCount)
    .slice(0, 6);
})();

export const winRateBuckets: AIWinRateBucket[] = (() => {
  const buckets = [
    { range: "70%+", min: 70, max: 101 },
    { range: "50-70%", min: 50, max: 70 },
    { range: "<50%", min: 0, max: 50 },
  ];
  return buckets.map((b) => {
    const ws = topWallets.filter((w) => w.winRate >= b.min && w.winRate < b.max);
    const avgPnl = ws.length
      ? Math.round((ws.reduce((s, w) => s + w.totalPnl, 0) / ws.length) * 100) /
        100
      : 0;
    return {
      range: b.range,
      count: ws.length,
      wallets: ws.map((w) => w.address),
      avgPnl,
    };
  });
})();

export const holdingDistribution: AIHoldingBucket[] = (() => {
  const buckets = [
    { range: "<1h", min: 0, max: 1 },
    { range: "1-6h", min: 1, max: 6 },
    { range: "6-24h", min: 6, max: 24 },
    { range: "1-3d", min: 24, max: 72 },
    { range: ">3d", min: 72, max: Infinity },
  ];
  return buckets.map((b) => ({
    range: b.range,
    count: topWallets.filter(
      (w) => w.avgHoldingHours >= b.min && w.avgHoldingHours < b.max,
    ).length,
  }));
})();

export const pnlTimeline: AIPnlPoint[] = (() => {
  const out: AIPnlPoint[] = [];
  let cum = 0;
  for (let i = 0; i < 14; i++) {
    cum += r() * 80 - 20;
    out.push({
      date: `Apr ${i + 8}`,
      cumulative: Math.round(cum * 10) / 10,
    });
  }
  return out;
})();
