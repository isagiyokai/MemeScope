import { useParams, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { fetchTokenHolders, ApiTop10Response } from "@/lib/api";
import {
  ArrowLeft, Zap, Droplets, Users, Clock, Shield,
  ArrowUpRight, TrendingUp, Loader2, AlertCircle
} from "lucide-react";

function shortAddr(a: string): string {
  if (!a || a.length < 8) return a;
  return a.slice(0, 4) + "…" + a.slice(-4);
}

function ageLabel(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diffMs / 60_000);
  if (m < 60) return `${m} min`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h`;
  return `${Math.floor(h / 24)}d`;
}

const TokenPage = () => {
  const { ticker } = useParams<{ ticker: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<ApiTop10Response | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const mint = ticker ? decodeURIComponent(ticker) : "";

  useEffect(() => {
    if (!mint) return;
    setLoading(true);
    fetchTokenHolders(mint)
      .then((d) => { setData(d); setLoading(false); })
      .catch((e) => {
        setError((e as Error).message.includes("404") ? "No holder data" : "Failed to load");
        setLoading(false);
      });
  }, [mint]);

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="h-screen flex flex-col items-center justify-center bg-background gap-3">
        <AlertCircle className="h-8 w-8 text-signal-low" />
        <p className="text-muted-foreground">{error ?? "No data found"}</p>
        <p className="text-xs text-muted-foreground font-mono">{shortAddr(mint)}</p>
        <button onClick={() => navigate("/")} className="text-primary text-sm underline">← Back</button>
      </div>
    );
  }

  const concentration = Math.round(data.top10_concentration * 100) / 100;
  const age = ageLabel(data.snapshot_at);

  return (
    <div className="h-screen flex flex-col bg-background overflow-hidden">
      <header className="h-14 border-b border-border bg-card flex items-center px-3 sm:px-4 shrink-0 gap-2 sm:gap-3">
        <button onClick={() => navigate("/")} className="text-muted-foreground hover:text-foreground transition-colors shrink-0">
          <ArrowLeft className="h-4 w-4" />
        </button>
        <div className="h-6 w-px bg-border shrink-0" />
        <Zap className="h-5 w-5 text-primary shrink-0" />
        <span className="font-bold text-base sm:text-lg text-foreground truncate">Token Deep Dive</span>
      </header>

      <div className="flex-1 overflow-y-auto p-3 sm:p-6">
        <div className="max-w-6xl mx-auto space-y-4 sm:space-y-6 fade-up">
          {/* Token Header */}
          <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
            <div>
              <div className="flex items-baseline gap-2 sm:gap-3 mb-1 flex-wrap">
                <span className="text-2xl sm:text-3xl font-bold text-foreground font-mono">
                  {shortAddr(data.token_mint)}
                </span>
              </div>
              <p className="text-xs text-muted-foreground font-mono break-all">{data.token_mint}</p>
            </div>
          </div>

          {/* Stats Row */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2 sm:gap-3">
            <MiniStatCard icon={<Clock className="h-3.5 w-3.5" />} label="Snapshot" value={age} />
            <MiniStatCard icon={<Users className="h-3.5 w-3.5" />} label="Holders (top10)" value={data.holders.length.toString()} />
            <MiniStatCard icon={<TrendingUp className="h-3.5 w-3.5" />} label="Top10 Concentration" value={`${concentration}%`} accent />
            <MiniStatCard
              icon={<Shield className="h-3.5 w-3.5" />}
              label="Total Supply"
              value={data.total_supply != null ? data.total_supply.toLocaleString(undefined, { maximumFractionDigits: 0 }) : "—"}
            />
          </div>

          {/* Holder Table */}
          <div className="bg-card border border-border rounded-lg overflow-hidden">
            <div className="panel-header">Top 10 Holders</div>
            <div className="p-3 sm:p-4 overflow-x-auto">
              {data.holders.length === 0 ? (
                <div className="py-8 text-center text-sm text-muted-foreground">No holder snapshots recorded</div>
              ) : (
                <table className="w-full min-w-[480px]">
                  <thead>
                    <tr className="text-[10px] text-muted-foreground uppercase tracking-wider">
                      <th className="text-left pb-2">#</th>
                      <th className="text-left pb-2">Address</th>
                      <th className="text-right pb-2">% Supply</th>
                      <th className="text-right pb-2">Balance</th>
                      <th className="text-right pb-2">Snapshot</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.holders
                      .slice()
                      .sort((a, b) => a.rank - b.rank)
                      .map((h, i) => (
                        <tr
                          key={h.wallet_address}
                          className="border-t border-border/50 text-xs hover:bg-surface-hover transition-colors cursor-pointer"
                          onClick={() => navigate(`/wallet/${encodeURIComponent(h.wallet_address)}`)}
                        >
                          <td className="py-2.5 text-muted-foreground">{h.rank || i + 1}</td>
                          <td className="py-2.5">
                            <span className="font-mono text-primary hover:underline">
                              {shortAddr(h.wallet_address)}
                            </span>
                          </td>
                          <td className="py-2.5 text-right tabular-nums text-foreground font-medium">
                            {h.pct_supply.toFixed(2)}%
                          </td>
                          <td className="py-2.5 text-right tabular-nums text-muted-foreground">
                            {h.balance.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                          </td>
                          <td className="py-2.5 text-right text-muted-foreground">
                            {new Date(h.snapshot_at).toLocaleTimeString()}
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>

          {/* Concentration bar */}
          <div className="bg-card border border-border rounded-lg p-4">
            <div className="text-xs text-muted-foreground uppercase tracking-wider mb-3">Supply Concentration</div>
            <div className="flex items-center gap-3 text-sm">
              <div className="flex-1 h-3 bg-secondary rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary rounded-full transition-all duration-1000"
                  style={{ width: `${Math.min(concentration, 100)}%` }}
                />
              </div>
              <span className={`font-bold tabular-nums ${concentration > 50 ? "text-signal-low" : concentration > 30 ? "text-signal-medium" : "text-signal-high"}`}>
                {concentration}%
              </span>
              <span className="text-muted-foreground">top 10</span>
            </div>
            <p className="text-[10px] text-muted-foreground mt-2">
              {concentration > 50 ? "High concentration — potential dump risk" : concentration > 30 ? "Moderate concentration" : "Well distributed"}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

const MiniStatCard = ({ icon, label, value, accent }: { icon: React.ReactNode; label: string; value: string; accent?: boolean }) => (
  <div className="bg-card border border-border rounded-lg p-3">
    <div className="flex items-center gap-1 text-muted-foreground mb-1">
      {icon}
      <span className="text-[10px]">{label}</span>
    </div>
    <span className={`text-lg font-bold tabular-nums ${accent ? "text-primary" : "text-foreground"}`}>{value}</span>
  </div>
);

export default TokenPage;
