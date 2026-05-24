import { useState } from "react";
import { Link } from "react-router-dom";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import {
  Activity,
  TrendingUp,
  Clock,
  Wallet,
  Zap,
  Target,
  Search,
  Loader2,
  ExternalLink,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "@/hooks/use-toast";
import CopyableAddress from "@/components/CopyableAddress";
import {
  fetchTokenHolders,
  fetchWalletProfile,
  type ApiTop10Response,
  type ApiWalletProfile,
  type ApiHolderSnapshot,
} from "@/lib/api";

// Animated chart data: rises to peak then collapses to flat — "waiting for data" visual
const PULSE_DATA = [
  { t: "", v: 0 }, { t: "", v: 6 }, { t: "", v: 22 },
  { t: "", v: 50 }, { t: "", v: 78 }, { t: "", v: 94 },
  { t: "", v: 82 }, { t: "", v: 55 }, { t: "", v: 25 },
  { t: "", v: 8 }, { t: "", v: 0 }, { t: "", v: 0 },
  { t: "", v: 0 }, { t: "", v: 0 },
];

function isFresh(profile: ApiWalletProfile): boolean {
  if (!profile.first_seen) return false;
  const days = (Date.now() - new Date(profile.first_seen).getTime()) / 86_400_000;
  return days < 14;
}

function fmtHours(h: number | null): string {
  if (h === null) return "—";
  if (h < 1) return `${Math.round(h * 60)}m`;
  if (h < 24) return `${h.toFixed(1)}h`;
  return `${(h / 24).toFixed(1)}d`;
}

function fmtPct(v: number | null, digits = 1): string {
  if (v === null) return "—";
  return `${(v * 100).toFixed(digits)}%`;
}

const AlphaIntelView = () => {
  const [analyzedToken, setAnalyzedToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [holderData, setHolderData] = useState<ApiTop10Response | null>(null);
  const [walletProfiles, setWalletProfiles] = useState<Record<string, ApiWalletProfile>>({});
  const [dataError, setDataError] = useState<string | null>(null);

  const handleSearch = async (mint: string) => {
    setLoading(true);
    setHolderData(null);
    setWalletProfiles({});
    setDataError(null);
    setAnalyzedToken(mint);

    try {
      const holders = await fetchTokenHolders(mint);
      setHolderData(holders);

      const results = await Promise.allSettled(
        holders.holders.map((h) => fetchWalletProfile(h.wallet_address))
      );
      const profiles: Record<string, ApiWalletProfile> = {};
      holders.holders.forEach((h, i) => {
        const r = results[i];
        if (r.status === "fulfilled") profiles[h.wallet_address] = r.value;
      });
      setWalletProfiles(profiles);

      toast({
        title: "Analysis complete",
        description: `${holders.holders.length} holders loaded for ${mint.slice(0, 6)}…${mint.slice(-4)}`,
      });
    } catch {
      setDataError("No holder data found for this token. It may not be tracked yet — try again after some trades are indexed.");
      toast({
        title: "No data found",
        description: "Token not tracked or no snapshot available yet.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const hasHolders = holderData !== null && holderData.holders.length > 0;
  const profileList = Object.values(walletProfiles);
  const hasProfiles = profileList.length > 0;

  // Compute stats from real wallet profiles
  const profilesWithWR = profileList.filter((p) => p.win_rate !== null);
  const avgWR = profilesWithWR.length
    ? (profilesWithWR.reduce((s, p) => s + p.win_rate!, 0) / profilesWithWR.length)
    : null;
  const profilesWithROI = profileList.filter((p) => p.avg_roi !== null);
  const avgROI = profilesWithROI.length
    ? (profilesWithROI.reduce((s, p) => s + p.avg_roi!, 0) / profilesWithROI.length)
    : null;
  const profilesWithHold = profileList.filter((p) => p.hold_duration_avg !== null);
  const avgHold = profilesWithHold.length
    ? (profilesWithHold.reduce((s, p) => s + p.hold_duration_avg!, 0) / profilesWithHold.length)
    : null;
  const profilesWithScore = profileList.filter((p) => p.composite_score !== null);
  const avgScore = profilesWithScore.length
    ? Math.round(profilesWithScore.reduce((s, p) => s + p.composite_score!, 0) / profilesWithScore.length)
    : null;

  const statusDot = loading
    ? "bg-accent animate-pulse"
    : hasHolders
    ? "bg-primary pulse-dot"
    : "bg-muted-foreground/40";

  return (
    <div className="min-h-full bg-background">
      <div className="border-b border-border bg-card/40 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-3 sm:px-6 py-3 flex items-center justify-between gap-3">
          <div>
            <h1 className="text-sm font-semibold text-foreground">Alpha Intel</h1>
            <p className="text-[10px] text-muted-foreground uppercase tracking-widest">
              Solana Smart Money Intelligence
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${statusDot}`} />
            <span className="text-xs text-muted-foreground font-mono">
              {loading
                ? "Analyzing…"
                : analyzedToken
                ? `${analyzedToken.slice(0, 6)}…${analyzedToken.slice(-4)}`
                : "IDLE"}
            </span>
          </div>
        </div>
      </div>

      <main className="max-w-7xl mx-auto px-3 sm:px-6 py-4 sm:py-6 space-y-4 sm:space-y-6">
        <TokenSearch onSearch={handleSearch} loading={loading} />

        {/* Stat cards */}
        <section className="grid grid-cols-2 md:grid-cols-4 gap-3 sm:gap-4">
          <StatCard
            label="Avg Win Rate"
            value={avgWR !== null ? `${(avgWR * 100).toFixed(1)}%` : "—"}
            icon="target"
            variant={avgWR !== null ? "primary" : "muted"}
          />
          <StatCard
            label="Avg ROI"
            value={avgROI !== null ? `${avgROI >= 1 ? "+" : ""}${((avgROI - 1) * 100).toFixed(1)}%` : "—"}
            icon="trending"
            variant={avgROI !== null ? (avgROI >= 1 ? "primary" : "destructive") : "muted"}
          />
          <StatCard
            label="Avg Hold Time"
            value={fmtHours(avgHold)}
            icon="clock"
            variant={avgHold !== null ? "accent" : "muted"}
          />
          <StatCard
            label="Avg Smart Score"
            value={avgScore !== null ? `${avgScore}/100` : "—"}
            icon="zap"
            variant={avgScore !== null ? "primary" : "muted"}
          />
        </section>

        {/* PnL chart — animated placeholder until real timeline data is available */}
        <PnlChart loading={loading} hasToken={analyzedToken !== null} />

        {/* Error state */}
        {dataError && (
          <div className="rounded-lg border border-border bg-card p-8 text-center space-y-2">
            <p className="text-sm font-medium text-foreground">No data available</p>
            <p className="text-xs text-muted-foreground max-w-md mx-auto">{dataError}</p>
          </div>
        )}

        {/* Wallet table */}
        {!dataError && (
          <WalletTable
            holders={holderData?.holders ?? null}
            profiles={walletProfiles}
            loading={loading}
            concentration={holderData?.top10_concentration}
          />
        )}

        {/* Analytics grid — shown when profiles are loaded */}
        {hasProfiles && (
          <>
            <div className="grid md:grid-cols-2 gap-3 sm:gap-4">
              <WinRateBreakdown profiles={profileList} />
              <HoldingDuration profiles={profileList} />
            </div>
            <div className="grid md:grid-cols-2 gap-3 sm:gap-4">
              <FreshVsOg profiles={profileList} holders={holderData!.holders} />
              <TopScoreWallets profiles={profileList} holders={holderData!.holders} />
            </div>
          </>
        )}

        {/* Empty analytics placeholder when waiting for data */}
        {!hasProfiles && !loading && (
          <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-3 sm:gap-4">
            {["Win Rate Distribution", "Holding Duration", "Wallet Classification"].map((title) => (
              <EmptyCard key={title} title={title} />
            ))}
          </div>
        )}

        <footer className="border-t border-border pt-4 mt-8">
          <div className="text-center text-[10px] text-muted-foreground font-mono">
            MemeScope • Alpha Intel
          </div>
        </footer>
      </main>
    </div>
  );
};

/* ------------------------------ StatCard ------------------------------ */

const STAT_ICONS = {
  activity: Activity,
  trending: TrendingUp,
  clock: Clock,
  wallet: Wallet,
  zap: Zap,
  target: Target,
};

const StatCard = ({
  label,
  value,
  icon,
  variant = "primary",
}: {
  label: string;
  value: string;
  icon: keyof typeof STAT_ICONS;
  variant?: "primary" | "accent" | "destructive" | "muted";
}) => {
  const Icon = STAT_ICONS[icon];
  const tone = {
    primary: "border-primary/30 text-primary",
    accent: "border-accent/30 text-accent",
    destructive: "border-destructive/30 text-destructive",
    muted: "border-border text-muted-foreground",
  }[variant];

  return (
    <div className={`rounded-lg border bg-card p-4 ${tone.split(" ")[0]}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">
          {label}
        </span>
        <Icon className={`h-4 w-4 ${tone.split(" ")[1]}`} />
      </div>
      <div className={`text-2xl font-bold font-mono tracking-tight ${value === "—" ? "text-muted-foreground/40" : "text-foreground"}`}>
        {value}
      </div>
    </div>
  );
};

/* ----------------------------- TokenSearch ---------------------------- */

const TokenSearch = ({
  onSearch,
  loading,
}: {
  onSearch: (address: string) => void;
  loading: boolean;
}) => {
  const [address, setAddress] = useState("");

  const handleSearch = () => {
    const trimmed = address.trim();
    if (!trimmed) {
      toast({ title: "Enter a token address", description: "Paste a Solana token mint address to analyze", variant: "destructive" });
      return;
    }
    if (trimmed.length < 32) {
      toast({ title: "Invalid address", description: "Solana addresses are 32–44 characters", variant: "destructive" });
      return;
    }
    onSearch(trimmed);
  };

  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            className="pl-9 bg-secondary border-border font-mono text-sm placeholder:text-muted-foreground/60"
            placeholder="Paste Solana token mint address…"
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !loading && handleSearch()}
          />
        </div>
        <Button
          onClick={handleSearch}
          disabled={loading}
          className="bg-primary text-primary-foreground hover:bg-primary/90 font-semibold gap-2 shrink-0"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
          {loading ? "Analyzing…" : "Analyze Top 10"}
        </Button>
      </div>
      <p className="text-[10px] text-muted-foreground mt-2 font-mono">
        Enter any SPL token mint → fetches top 10 holders → runs full alpha analysis
      </p>
    </div>
  );
};

/* ------------------------------ PnlChart ------------------------------ */

const PnlChart = ({ loading, hasToken }: { loading: boolean; hasToken: boolean }) => (
  <div className="rounded-lg border border-border bg-card p-4">
    <h3 className="text-sm font-semibold text-foreground mb-1">
      Cumulative PnL — Top 10 Aggregate
    </h3>
    <p className="text-xs text-muted-foreground mb-4">
      {loading
        ? "Fetching holder trade history…"
        : hasToken
        ? "Historical PnL timeline — live data coming soon"
        : "Enter a token address above to begin analysis"}
    </p>
    <div className="h-48 relative">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={PULSE_DATA} key={String(hasToken)}>
          <defs>
            <linearGradient id="aiPulseGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity={hasToken ? 0.25 : 0.18} />
              <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis dataKey="t" tick={false} axisLine={false} tickLine={false} />
          <YAxis tick={false} axisLine={false} tickLine={false} width={0} />
          <Tooltip
            content={() => null}
            cursor={false}
          />
          <Area
            type="monotone"
            dataKey="v"
            stroke="hsl(var(--primary))"
            strokeWidth={2}
            strokeOpacity={hasToken ? 0.4 : 0.6}
            fill="url(#aiPulseGradient)"
            isAnimationActive
            animationDuration={2800}
            animationEasing="ease-out"
            dot={false}
          />
        </AreaChart>
      </ResponsiveContainer>
      {/* Overlay label when no real data */}
      <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
        <span className="text-[10px] font-mono text-muted-foreground/60 tracking-widest uppercase">
          {loading ? "loading…" : "awaiting data"}
        </span>
      </div>
    </div>
  </div>
);

/* ----------------------------- WalletTable ---------------------------- */

const WalletTable = ({
  holders,
  profiles,
  loading,
  concentration,
}: {
  holders: ApiHolderSnapshot[] | null;
  profiles: Record<string, ApiWalletProfile>;
  loading: boolean;
  concentration?: number;
}) => (
  <div className="rounded-lg border border-border bg-card overflow-hidden">
    <div className="p-4 border-b border-border flex items-start justify-between gap-4">
      <div>
        <h2 className="text-sm font-semibold text-foreground">
          Top 10 Holders — Smart Money Ranking
        </h2>
        <p className="text-xs text-muted-foreground mt-1">
          {holders
            ? `Ranked by Smart Score • ${holders.length} holders`
            : "Enter a token address to load holder data"}
        </p>
      </div>
      {concentration !== undefined && (
        <span className="shrink-0 text-xs font-mono text-muted-foreground">
          Top-10 concentration:{" "}
          <span className={concentration > 0.5 ? "text-destructive" : "text-primary"}>
            {(concentration * 100).toFixed(1)}%
          </span>
        </span>
      )}
    </div>
    <div className="overflow-x-auto">
      {holders && !loading ? (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-[10px] text-muted-foreground uppercase tracking-wider">
              <th className="p-3 text-left">#</th>
              <th className="p-3 text-left">Wallet</th>
              <th className="p-3 text-right">Score</th>
              <th className="p-3 text-right">Win Rate</th>
              <th className="p-3 text-right">% Supply</th>
              <th className="p-3 text-right">Trades</th>
              <th className="p-3 text-right">Avg Hold</th>
              <th className="p-3 text-center">Type</th>
            </tr>
          </thead>
          <tbody>
            {holders.map((h) => {
              const p = profiles[h.wallet_address];
              const score = p?.composite_score ?? null;
              const wr = p?.win_rate ?? null;
              const fresh = p ? isFresh(p) : null;
              return (
                <tr
                  key={h.wallet_address}
                  className="border-b border-border/40 hover:bg-secondary/40 transition-colors"
                >
                  <td className="p-3 font-mono text-muted-foreground">{h.rank}</td>
                  <td className="p-3">
                    <CopyableAddress fullAddress={h.wallet_address} className="inline-block">
                      <Link
                        to={`/wallet/${encodeURIComponent(h.wallet_address)}`}
                        className="font-mono text-primary hover:underline flex items-center gap-1.5 text-xs"
                      >
                        {h.wallet_address.slice(0, 4)}…{h.wallet_address.slice(-4)}
                        <ExternalLink className="w-3 h-3 opacity-50" />
                      </Link>
                    </CopyableAddress>
                  </td>
                  <td className="p-3 text-right">
                    {score !== null ? (
                      <span className={`font-mono font-bold ${score >= 70 ? "text-primary" : score >= 40 ? "text-accent" : "text-muted-foreground"}`}>
                        {score}
                      </span>
                    ) : (
                      <span className="text-muted-foreground/40 font-mono">—</span>
                    )}
                  </td>
                  <td className="p-3 text-right font-mono">
                    {wr !== null ? (
                      <span className={wr >= 0.5 ? "text-primary" : "text-destructive"}>
                        {(wr * 100).toFixed(1)}%
                      </span>
                    ) : (
                      <span className="text-muted-foreground/40">—</span>
                    )}
                  </td>
                  <td className="p-3 text-right font-mono text-foreground">
                    {(h.pct_supply * 100).toFixed(2)}%
                  </td>
                  <td className="p-3 text-right font-mono text-foreground">
                    {p?.total_trades ?? <span className="text-muted-foreground/40">—</span>}
                  </td>
                  <td className="p-3 text-right font-mono text-foreground">
                    {fmtHours(p?.hold_duration_avg ?? null)}
                  </td>
                  <td className="p-3 text-center">
                    {fresh !== null ? (
                      <Badge
                        className={fresh
                          ? "bg-accent/20 text-accent border-accent/30 text-[10px]"
                          : "bg-secondary text-foreground text-[10px]"}
                      >
                        {fresh ? "FRESH" : "OG"}
                      </Badge>
                    ) : (
                      <span className="text-muted-foreground/40 font-mono text-[10px]">—</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      ) : (
        <WalletSkeleton />
      )}
    </div>
  </div>
);

/* -------------------------- WalletSkeleton ---------------------------- */

const WalletSkeleton = () => (
  <div className="divide-y divide-border/40">
    {Array.from({ length: 10 }).map((_, i) => (
      <div key={i} className="flex items-center gap-3 px-4 py-3 animate-pulse">
        <div className="h-3 w-4 rounded bg-secondary/80" />
        <div className="h-3 flex-1 rounded bg-secondary/80" />
        <div className="h-3 w-8 rounded bg-secondary/80" />
        <div className="h-3 w-12 rounded bg-secondary/80" />
        <div className="h-3 w-14 rounded bg-secondary/80" />
        <div className="h-3 w-8 rounded bg-secondary/80" />
        <div className="h-3 w-10 rounded bg-secondary/80" />
        <div className="h-5 w-12 rounded-full bg-secondary/80" />
      </div>
    ))}
  </div>
);

/* -------------------------- EmptyCard --------------------------------- */

const EmptyCard = ({ title }: { title: string }) => (
  <div className="rounded-lg border border-border bg-card p-4">
    <h3 className="text-sm font-semibold text-foreground mb-1">{title}</h3>
    <div className="h-24 flex items-center justify-center">
      <span className="text-xs text-muted-foreground/50 font-mono">awaiting data</span>
    </div>
  </div>
);

/* -------------------------- WinRateBreakdown -------------------------- */

const WinRateBreakdown = ({ profiles }: { profiles: ApiWalletProfile[] }) => {
  const buckets = [
    { range: "70%+", min: 0.7, max: 1.01, color: "bg-primary" },
    { range: "50–70%", min: 0.5, max: 0.7, color: "bg-accent" },
    { range: "<50%", min: 0, max: 0.5, color: "bg-destructive/60" },
  ];
  const withWR = profiles.filter((p) => p.win_rate !== null);
  const total = withWR.length || 1;

  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <h3 className="text-sm font-semibold text-foreground mb-1">Win Rate Distribution</h3>
      <p className="text-xs text-muted-foreground mb-4">Wallet performance buckets</p>
      <div className="space-y-4">
        {buckets.map((b) => {
          const ws = withWR.filter((p) => p.win_rate! >= b.min && p.win_rate! < b.max);
          const pct = Math.round((ws.length / total) * 100);
          const avgROI = ws.length
            ? ws.reduce((s, p) => s + (p.avg_roi ?? 1), 0) / ws.length
            : 1;
          return (
            <div key={b.range}>
              <div className="flex justify-between items-center mb-1">
                <span className="text-sm font-mono text-foreground">{b.range}</span>
                <span className="text-xs text-muted-foreground">
                  {ws.length} wallets •{" "}
                  <span className={avgROI >= 1 ? "text-primary" : "text-destructive"}>
                    avg {avgROI >= 1 ? "+" : ""}{((avgROI - 1) * 100).toFixed(0)}% ROI
                  </span>
                </span>
              </div>
              <div className="h-3 bg-secondary rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full ${b.color} transition-all duration-700`}
                  style={{ width: `${Math.max(pct, ws.length ? 5 : 0)}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

/* -------------------------- HoldingDuration --------------------------- */

const HoldingDuration = ({ profiles }: { profiles: ApiWalletProfile[] }) => {
  const buckets = [
    { range: "<1h", min: 0, max: 1 },
    { range: "1–6h", min: 1, max: 6 },
    { range: "6–24h", min: 6, max: 24 },
    { range: "1–3d", min: 24, max: 72 },
    { range: ">3d", min: 72, max: Infinity },
  ];
  const withHold = profiles.filter((p) => p.hold_duration_avg !== null);
  const counts = buckets.map((b) =>
    withHold.filter((p) => p.hold_duration_avg! >= b.min && p.hold_duration_avg! < b.max).length
  );
  const maxCount = Math.max(...counts, 1);

  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <h3 className="text-sm font-semibold text-foreground mb-1">Avg Holding Duration</h3>
      <p className="text-xs text-muted-foreground mb-4">How long Top 10 hold positions</p>
      <div className="flex items-end gap-2 h-32">
        {buckets.map((b, i) => (
          <div key={b.range} className="flex-1 flex flex-col items-center gap-1">
            <span className="text-xs font-mono text-primary">{counts[i]}</span>
            <div
              className="w-full rounded-t bg-gradient-to-t from-accent/30 to-primary/70 transition-all duration-500"
              style={{ height: `${counts[i] > 0 ? (counts[i] / maxCount) * 100 : 4}%` }}
            />
            <span className="text-[10px] text-muted-foreground font-mono">{b.range}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

/* ------------------------------ FreshVsOg ----------------------------- */

const FreshVsOg = ({
  profiles,
  holders,
}: {
  profiles: ApiWalletProfile[];
  holders: ApiHolderSnapshot[];
}) => {
  const fresh = profiles.filter(isFresh);
  const og = profiles.filter((p) => !isFresh(p));
  const freshAvg = fresh.length
    ? Math.round(fresh.reduce((s, p) => s + p.total_trades, 0) / fresh.length)
    : 0;
  const ogAvg = og.length
    ? Math.round(og.reduce((s, p) => s + p.total_trades, 0) / og.length)
    : 0;

  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <h3 className="text-sm font-semibold text-foreground mb-1">Fresh vs OG Wallets</h3>
      <p className="text-xs text-muted-foreground mb-4">Wallet age classification</p>
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-accent/10 border border-accent/20 rounded-lg p-3 text-center">
          <div className="text-2xl font-bold font-mono text-accent">{fresh.length}</div>
          <div className="text-xs text-muted-foreground mt-1">Fresh Wallets</div>
          <div className="text-xs font-mono text-foreground mt-2">avg {freshAvg} trades</div>
          <div className="text-[10px] text-muted-foreground">{"< 14 days old"}</div>
        </div>
        <div className="bg-secondary/40 border border-border rounded-lg p-3 text-center">
          <div className="text-2xl font-bold font-mono text-foreground">{og.length}</div>
          <div className="text-xs text-muted-foreground mt-1">OG Wallets</div>
          <div className="text-xs font-mono text-foreground mt-2">avg {ogAvg} trades</div>
          <div className="text-[10px] text-muted-foreground">{"> 14 days old"}</div>
        </div>
      </div>
      {holders.length > 0 && (
        <div className="mt-3 pt-3 border-t border-border">
          <div className="text-[10px] text-muted-foreground">
            Top-10 concentration:{" "}
            {holders.map((h) => (
              <span key={h.wallet_address} title={h.wallet_address} />
            ))}
            {holders.length} wallets tracked
          </div>
        </div>
      )}
    </div>
  );
};

/* -------------------------- TopScoreWallets --------------------------- */

const TopScoreWallets = ({
  profiles,
  holders,
}: {
  profiles: ApiWalletProfile[];
  holders: ApiHolderSnapshot[];
}) => {
  const ranked = [...profiles]
    .filter((p) => p.composite_score !== null)
    .sort((a, b) => b.composite_score! - a.composite_score!)
    .slice(0, 5);

  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <h3 className="text-sm font-semibold text-foreground mb-1">Top Scored Wallets</h3>
      <p className="text-xs text-muted-foreground mb-4">Highest composite intelligence scores</p>
      {ranked.length === 0 ? (
        <p className="text-xs text-muted-foreground">No scoring data available</p>
      ) : (
        <div className="space-y-2">
          {ranked.map((p) => {
            const holderInfo = holders.find((h) => h.wallet_address === p.address);
            return (
              <div
                key={p.address}
                className="flex items-center justify-between p-2 rounded bg-secondary/40 border border-border"
              >
                <div>
                  <Link
                    to={`/wallet/${encodeURIComponent(p.address)}`}
                    className="font-mono text-xs text-primary hover:underline flex items-center gap-1"
                  >
                    {p.address.slice(0, 4)}…{p.address.slice(-4)}
                    <ExternalLink className="w-3 h-3 opacity-50" />
                  </Link>
                  {holderInfo && (
                    <div className="text-[10px] text-muted-foreground mt-0.5">
                      {(holderInfo.pct_supply * 100).toFixed(2)}% supply
                    </div>
                  )}
                </div>
                <div className="text-right">
                  <div className={`text-sm font-bold font-mono ${p.composite_score! >= 70 ? "text-primary" : "text-accent"}`}>
                    {p.composite_score}
                  </div>
                  <div className="text-[10px] text-muted-foreground">
                    {fmtPct(p.win_rate)} WR
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default AlphaIntelView;
