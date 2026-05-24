import { useParams, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { fetchWalletProfile, fetchWalletTrades, ApiWalletProfile, ApiTrade } from "@/lib/api";
import {
  ArrowLeft, Trophy, Target, TrendingUp, Clock, BarChart3,
  Zap, Users, ArrowUpRight, ArrowDownRight, Network, Loader2, AlertCircle
} from "lucide-react";
import CopyableAddress from "@/components/CopyableAddress";

function shortAddr(a: string): string {
  return a.slice(0, 4) + "…" + a.slice(-4);
}

function fmtDuration(hours: number): string {
  if (hours < 1) return `${Math.round(hours * 60)} min`;
  if (hours < 24) return `${hours.toFixed(1)}h`;
  return `${(hours / 24).toFixed(1)}d`;
}

function walletType(score: number): string {
  if (score >= 85) return "Alpha Whale";
  if (score >= 70) return "Smart Money";
  if (score >= 50) return "Swing Trader";
  return "Retail";
}

const WalletPage = () => {
  const { address } = useParams<{ address: string }>();
  const navigate = useNavigate();
  const [profile, setProfile] = useState<ApiWalletProfile | null>(null);
  const [trades, setTrades] = useState<ApiTrade[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!address) return;
    setLoading(true);
    setError(null);

    Promise.all([
      fetchWalletProfile(decodeURIComponent(address)),
      fetchWalletTrades(decodeURIComponent(address), 20),
    ])
      .then(([p, t]) => {
        setProfile(p);
        setTrades(t);
        setLoading(false);
      })
      .catch((e) => {
        setError((e as Error).message === "not_found" ? "Wallet not found" : "Failed to load wallet");
        setLoading(false);
      });
  }, [address]);

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (error || !profile) {
    return (
      <div className="h-screen flex flex-col items-center justify-center bg-background gap-3">
        <AlertCircle className="h-8 w-8 text-signal-low" />
        <p className="text-muted-foreground">{error ?? "Wallet not found"}</p>
        <button onClick={() => navigate("/")} className="text-primary text-sm underline">← Back</button>
      </div>
    );
  }

  const score = Math.round(profile.composite_score ?? 0);
  const winRatePct = Math.round((profile.win_rate ?? 0) * 100);
  const avgROI = Math.round(profile.avg_roi ?? 0);
  const entryScore = Math.round((profile.entry_timing_score ?? 0) * 100);
  const consistency = Math.round((profile.consistency_score ?? 0) * 100);
  const avgHoldLabel = profile.hold_duration_avg ? fmtDuration(profile.hold_duration_avg) : "—";

  const scoreColor = score >= 80 ? "text-signal-high" : score >= 60 ? "text-signal-medium" : "text-signal-low";
  const scoreRingColor = score >= 80 ? "hsl(var(--signal-high))" : score >= 60 ? "hsl(var(--signal-medium))" : "hsl(var(--signal-low))";

  return (
    <div className="h-screen flex flex-col bg-background overflow-hidden">
      <header className="h-14 border-b border-border bg-card flex items-center px-3 sm:px-4 shrink-0 gap-2 sm:gap-3">
        <button onClick={() => navigate("/")} className="text-muted-foreground hover:text-foreground transition-colors shrink-0">
          <ArrowLeft className="h-4 w-4" />
        </button>
        <div className="h-6 w-px bg-border shrink-0" />
        <Zap className="h-5 w-5 text-primary shrink-0" />
        <span className="font-bold text-base sm:text-lg text-foreground shrink-0">Wallet</span>
        <CopyableAddress fullAddress={profile.address} className="font-mono text-xs sm:text-sm text-muted-foreground ml-1 sm:ml-2 truncate">
          {profile.address}
        </CopyableAddress>
      </header>

      <div className="flex-1 overflow-y-auto p-3 sm:p-6">
        <div className="max-w-6xl mx-auto space-y-4 sm:space-y-6 fade-up">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-3 sm:gap-4">
            <div className="lg:col-span-1 bg-card border border-border rounded-lg p-4 sm:p-5 glow-green">
              <div className="text-xs text-muted-foreground uppercase tracking-wider mb-3">Wallet Personality</div>
              <div className="flex items-center gap-4 mb-4">
                <div className="relative h-16 w-16">
                  <svg className="h-16 w-16 -rotate-90" viewBox="0 0 36 36">
                    <path d="M18 2.0845a15.9155 15.9155 0 0 1 0 31.831a15.9155 15.9155 0 0 1 0-31.831" fill="none" stroke="hsl(var(--border))" strokeWidth="2.5" />
                    <path d="M18 2.0845a15.9155 15.9155 0 0 1 0 31.831a15.9155 15.9155 0 0 1 0-31.831" fill="none" stroke={scoreRingColor} strokeWidth="2.5" strokeDasharray={`${score}, 100`} strokeLinecap="round" />
                  </svg>
                  <span className={`absolute inset-0 flex items-center justify-center text-lg font-bold ${scoreColor}`}>{score}</span>
                </div>
                <div>
                  <div className="text-xl font-bold text-foreground">{walletType(score)}</div>
                  <div className="text-xs text-muted-foreground">Alpha Score</div>
                </div>
              </div>
              <div className="space-y-2 text-xs">
                <div className="flex items-center gap-2 text-secondary-foreground">
                  <Target className="h-3 w-3 text-primary shrink-0" />
                  <span>Trades: <span className="text-foreground font-medium">{profile.total_trades}</span></span>
                </div>
                <div className="flex items-center gap-2 text-secondary-foreground">
                  <Clock className="h-3 w-3 text-accent shrink-0" />
                  <span>Avg Hold: <span className="text-foreground font-medium">{avgHoldLabel}</span></span>
                </div>
                <div className="flex items-center gap-2 text-secondary-foreground">
                  <BarChart3 className="h-3 w-3 text-signal-medium shrink-0" />
                  <span>Volume: <span className="text-foreground font-medium">${profile.total_volume_usd.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span></span>
                </div>
                {profile.cluster_id && (
                  <div className="flex items-center gap-2 text-secondary-foreground">
                    <Users className="h-3 w-3 text-signal-high shrink-0" />
                    <span>Cluster: <span className="text-primary font-mono text-[10px]">{profile.cluster_id.slice(0, 8)}…</span></span>
                  </div>
                )}
              </div>
            </div>

            <div className="lg:col-span-2 grid grid-cols-2 sm:grid-cols-4 gap-2 sm:gap-3">
              <StatCard label="Win Rate" value={`${winRatePct}%`} icon={<Trophy className="h-4 w-4" />} color={winRatePct >= 60 ? "text-signal-high" : "text-signal-medium"} />
              <StatCard label="Avg ROI" value={avgROI !== 0 ? `${avgROI}%` : "—"} icon={<TrendingUp className="h-4 w-4" />} color="text-signal-high" />
              <StatCard label="Tokens" value={profile.total_tokens_traded.toString()} icon={<BarChart3 className="h-4 w-4" />} color="text-primary" />
              <StatCard label="Total Trades" value={profile.total_trades.toString()} icon={<Target className="h-4 w-4" />} color="text-accent" />
              <StatCard label="Early Entry" value={entryScore > 0 ? `${entryScore}/100` : "—"} icon={<Zap className="h-4 w-4" />} color="text-signal-high" />
              <StatCard label="Avg Hold" value={avgHoldLabel} icon={<Clock className="h-4 w-4" />} color="text-muted-foreground" />
              <div className="col-span-2 bg-card border border-border rounded-lg p-4">
                <div className="stat-label mb-2">Alpha Score Breakdown</div>
                <div className="space-y-2">
                  <ScoreBar label="Win Rate" value={winRatePct} max={100} />
                  <ScoreBar label="Early Entry" value={entryScore} max={100} />
                  <ScoreBar label="Consistency" value={consistency} max={100} />
                  <ScoreBar label="Composite" value={score} max={100} />
                </div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-3 sm:gap-4">
            <div className="lg:col-span-2 bg-card border border-border rounded-lg overflow-hidden">
              <div className="panel-header">Recent Trades</div>
              {trades.length === 0 ? (
                <div className="p-6 text-center text-sm text-muted-foreground">No trades recorded yet</div>
              ) : (
                <div className="p-3 sm:p-4 overflow-x-auto">
                  <table className="w-full min-w-[520px]">
                    <thead>
                      <tr className="text-[10px] text-muted-foreground uppercase tracking-wider">
                        <th className="text-left pb-2">Token</th>
                        <th className="text-left pb-2">Side</th>
                        <th className="text-right pb-2">Amount</th>
                        <th className="text-right pb-2">Price USD</th>
                        <th className="text-right pb-2">Time</th>
                      </tr>
                    </thead>
                    <tbody>
                      {trades.map((t) => (
                        <tr key={t.id} className="border-t border-border/50 text-xs hover:bg-surface-hover transition-colors">
                          <td className="py-2.5 font-mono text-muted-foreground">{t.token_mint.slice(0, 8)}…</td>
                          <td className="py-2.5">
                            <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                              t.side === "BUY" ? "bg-signal-high/15 text-signal-high" : "bg-accent/15 text-accent"
                            }`}>
                              {t.side}
                            </span>
                          </td>
                          <td className="py-2.5 text-right tabular-nums text-foreground">
                            {t.amount_token.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                          </td>
                          <td className="py-2.5 text-right tabular-nums text-muted-foreground">
                            {t.price_usd != null ? `$${t.price_usd.toFixed(6)}` : "—"}
                          </td>
                          <td className="py-2.5 text-right text-muted-foreground">
                            {new Date(t.timestamp).toLocaleTimeString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            <div className="lg:col-span-1 bg-card border border-border rounded-lg">
              <div className="panel-header flex items-center gap-2">
                <Network className="h-3 w-3" />
                Stats
              </div>
              <div className="p-4 space-y-3 text-xs">
                <Row label="Profitable tokens" value={profile.profitable_tokens} />
                <Row label="Unprofitable tokens" value={profile.unprofitable_tokens} />
                <Row label="Tokens traded" value={profile.total_tokens_traded} />
                <Row label="Avg trade size" value={`$${profile.avg_trade_size_usd.toFixed(2)}`} />
                {profile.first_seen && (
                  <Row label="First seen" value={new Date(profile.first_seen).toLocaleDateString()} />
                )}
                {profile.last_active && (
                  <Row label="Last active" value={new Date(profile.last_active).toLocaleDateString()} />
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

const StatCard = ({ label, value, icon, color }: { label: string; value: string; icon: React.ReactNode; color: string }) => (
  <div className="bg-card border border-border rounded-lg p-4">
    <div className="flex items-center gap-1.5 text-muted-foreground mb-2">
      {icon}
      <span className="stat-label !p-0">{label}</span>
    </div>
    <span className={`stat-value ${color}`}>{value}</span>
  </div>
);

const ScoreBar = ({ label, value, max }: { label: string; value: number; max: number }) => (
  <div>
    <div className="flex justify-between text-[10px] mb-0.5">
      <span className="text-muted-foreground">{label}</span>
      <span className="text-foreground font-medium tabular-nums">{Math.round(value)}</span>
    </div>
    <div className="h-1.5 bg-secondary rounded-full overflow-hidden">
      <div className="h-full bg-primary rounded-full transition-all duration-1000 ease-out" style={{ width: `${(value / max) * 100}%` }} />
    </div>
  </div>
);

const Row = ({ label, value }: { label: string; value: string | number }) => (
  <div className="flex justify-between">
    <span className="text-muted-foreground">{label}</span>
    <span className="text-foreground font-medium">{value}</span>
  </div>
);

export default WalletPage;
