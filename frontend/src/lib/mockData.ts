// Type definitions shared across UI components.
// All runtime data comes from the backend — no mock arrays here.

export type Confidence = "HIGH" | "MEDIUM" | "LOW";

export interface Signal {
  id: string;
  token: string;
  ticker: string;
  age: string;
  ageMinutes: number;
  liquidity: string;
  liquidityK: number;
  holders: number;
  smartWallets: number;
  clusterDetected: boolean;
  earlyEntry: boolean;
  confidence: Confidence;
  actionBias: string;
  reasons: string[];
  timestamp: Date;
  priceChange: number;
  walletScoreAvg: number;
  winRateAvg: number;
}

export interface WalletTrade {
  token: string;
  ticker: string;
  action: "BUY" | "SELL";
  entryPrice: number;
  exitPrice?: number;
  pnl: number;
  pnlPct: number;
  time: string;
  holdTime: string;
}

export interface ClusterWallet {
  address: string;
  overlapPct: number;
  sharedTrades: number;
}

export interface Wallet {
  address: string;
  shortAddress: string;
  alphaScore: number;
  winRate: number;
  avgROI: number;
  type: string;
  avgEntry: string;
  avgHold: string;
  totalTrades: number;
  pnl: number;
  earlyEntryScore: number;
  holdingStyle: string;
  recentTrades: WalletTrade[];
  cluster: ClusterWallet[];
}

export interface TokenHolder {
  address: string;
  pct: number;
  pnl: number;
  entryTime: string;
  isSmart: boolean;
}

export interface PricePoint {
  time: string;
  price: number;
  volume: number;
}

export interface SmartMoneyEvent {
  wallet: string;
  action: "BUY" | "SELL";
  price: number;
  time: string;
  amount: string;
}

export interface TokenDetail {
  name: string;
  ticker: string;
  price: number;
  liquidity: number;
  age: string;
  holders: number;
  quickScore: number;
  priceHistory: PricePoint[];
  smartMoneyEvents: SmartMoneyEvent[];
  topHolders: TokenHolder[];
  buyPressure: number;
  devWalletLocked: boolean;
  contractVerified: boolean;
}

export interface Filters {
  minLiquidityK: number;
  maxAgeMin: number;
  minWinRate: number;
  minWalletScore: number;
  freshWalletsOnly: boolean;
}

export const defaultFilters: Filters = {
  minLiquidityK: 0,
  maxAgeMin: 1440,
  minWinRate: 0,
  minWalletScore: 0,
  freshWalletsOnly: false,
};

export function filterSignals(signals: Signal[], filters: Filters): Signal[] {
  return signals.filter((s) => {
    if (s.liquidityK > 0 && s.liquidityK < filters.minLiquidityK) return false;
    if (filters.maxAgeMin < 1440 && s.ageMinutes > filters.maxAgeMin) return false;
    if (s.winRateAvg > 0 && s.winRateAvg < filters.minWinRate) return false;
    if (s.walletScoreAvg > 0 && s.walletScoreAvg < filters.minWalletScore) return false;
    return true;
  });
}
