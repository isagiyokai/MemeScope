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
  Bell,
  MessageCircle,
  Send,
  Check,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { toast } from "@/hooks/use-toast";
import CopyableAddress from "@/components/CopyableAddress";
import {
  topWallets,
  tradeRecords,
  tokenOverlaps,
  winRateBuckets,
  holdingDistribution,
  pnlTimeline,
} from "@/lib/alphaIntelData";

/**
 * Alpha Intel-style main view — feature parity with the reference project,
 * but using MemeScope's existing semantic tokens / mood (no neon-green/blue
 * custom CSS vars; everything maps to primary/accent/destructive/muted).
 */
const AlphaIntelView = () => {
  const [analyzedToken, setAnalyzedToken] = useState<string | null>(null);

  const avgWR =
    Math.round(
      (topWallets.reduce((s, w) => s + w.winRate, 0) / topWallets.length) * 10,
    ) / 10;
  const totalPnl =
    Math.round(topWallets.reduce((s, w) => s + w.totalPnl, 0) * 100) / 100;
  const avgHold =
    Math.round(
      (topWallets.reduce((s, w) => s + w.avgHoldingHours, 0) /
        topWallets.length) *
        10,
    ) / 10;
  const avgScore = Math.round(
    topWallets.reduce((s, w) => s + w.smartScore, 0) / topWallets.length,
  );

  return (
    <div className="min-h-full bg-background">
      <div className="border-b border-border bg-card/40 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-3 sm:px-6 py-3 flex items-center justify-between gap-3">
          <div>
            <h1 className="text-sm font-semibold text-foreground">
              Alpha Intel
            </h1>
            <p className="text-[10px] text-muted-foreground uppercase tracking-widest">
              Solana Smart Money Intelligence
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-primary pulse-dot" />
            <span className="text-xs text-muted-foreground font-mono">
              {analyzedToken
                ? `Analyzing ${analyzedToken.slice(0, 6)}...${analyzedToken.slice(-4)}`
                : "LIVE"}
            </span>
          </div>
        </div>
      </div>

      <main className="max-w-7xl mx-auto px-3 sm:px-6 py-4 sm:py-6 space-y-4 sm:space-y-6">
        <TokenSearch onSearch={setAnalyzedToken} />

        <section className="grid grid-cols-2 md:grid-cols-4 gap-3 sm:gap-4">
          <StatCard
            label="Avg Win Rate"
            value={`${avgWR}%`}
            icon="target"
            variant="primary"
          />
          <StatCard
            label="Total PnL"
            value={`${totalPnl >= 0 ? "+" : ""}${totalPnl} SOL`}
            icon="trending"
            variant={totalPnl >= 0 ? "primary" : "destructive"}
          />
          <StatCard
            label="Avg Hold Time"
            value={`${avgHold}h`}
            icon="clock"
            variant="accent"
          />
          <StatCard
            label="Avg Smart Score"
            value={`${avgScore}/100`}
            icon="zap"
            variant="primary"
          />
        </section>

        <PnlChart />

        <WalletTable />

        <div className="grid md:grid-cols-2 gap-3 sm:gap-4">
          <TokenOverlapChart />
          <WinRateBreakdown />
        </div>

        <div className="grid md:grid-cols-3 gap-3 sm:gap-4">
          <HoldingDuration />
          <FreshVsOg />
          <EarlyEntryWallets />
        </div>


        <footer className="border-t border-border pt-4 mt-8">
          <div className="text-center text-[10px] text-muted-foreground font-mono">
            MemeScope • Alpha Intel mode
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
      <div className="text-2xl font-bold font-mono tracking-tight text-foreground">
        {value}
      </div>
    </div>
  );
};

/* ----------------------------- TokenSearch ---------------------------- */

const TokenSearch = ({
  onSearch,
}: {
  onSearch: (address: string) => void;
}) => {
  const [address, setAddress] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSearch = () => {
    const trimmed = address.trim();
    if (!trimmed) {
      toast({
        title: "Enter a token address",
        description: "Paste a Solana token mint address to analyze",
        variant: "destructive",
      });
      return;
    }
    if (trimmed.length < 32) {
      toast({
        title: "Invalid address",
        description: "Solana addresses are 32-44 characters",
        variant: "destructive",
      });
      return;
    }
    setLoading(true);
    setTimeout(() => {
      setLoading(false);
      onSearch(trimmed);
      toast({
        title: "Analysis Complete",
        description: `Top 10 holders analyzed for ${trimmed.slice(0, 6)}...${trimmed.slice(-4)}`,
      });
    }, 1500);
  };

  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            className="pl-9 bg-secondary border-border font-mono text-sm placeholder:text-muted-foreground/60"
            placeholder="Paste Solana token mint address (e.g. DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263)"
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          />
        </div>
        <Button
          onClick={handleSearch}
          disabled={loading}
          className="bg-primary text-primary-foreground hover:bg-primary/90 font-semibold gap-2 shrink-0"
        >
          {loading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Search className="w-4 h-4" />
          )}
          Analyze Top 10
        </Button>
      </div>
      <p className="text-[10px] text-muted-foreground mt-2 font-mono">
        Enter any SPL token mint → fetches top 10 holders → runs full alpha
        analysis
      </p>
    </div>
  );
};

/* ------------------------------ PnlChart ------------------------------ */

const PnlChart = () => (
  <div className="rounded-lg border border-border bg-card p-4">
    <h3 className="text-sm font-semibold text-foreground mb-1">
      Cumulative PnL — Top 10 Aggregate
    </h3>
    <p className="text-xs text-muted-foreground mb-4">
      Combined performance over time (SOL)
    </p>
    <div className="h-48">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={pnlTimeline}>
          <defs>
            <linearGradient id="aiPnlGradient" x1="0" y1="0" x2="0" y2="1">
              <stop
                offset="0%"
                stopColor="hsl(var(--primary))"
                stopOpacity={0.4}
              />
              <stop
                offset="100%"
                stopColor="hsl(var(--primary))"
                stopOpacity={0}
              />
            </linearGradient>
          </defs>
          <XAxis
            dataKey="date"
            tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
            axisLine={false}
            tickLine={false}
            width={40}
          />
          <Tooltip
            contentStyle={{
              background: "hsl(var(--card))",
              border: "1px solid hsl(var(--border))",
              borderRadius: "8px",
              fontSize: "12px",
            }}
            labelStyle={{ color: "hsl(var(--foreground))" }}
          />
          <Area
            type="monotone"
            dataKey="cumulative"
            stroke="hsl(var(--primary))"
            strokeWidth={2}
            fill="url(#aiPnlGradient)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  </div>
);

/* ----------------------------- WalletTable ---------------------------- */

const WalletTable = () => (
  <div className="rounded-lg border border-border bg-card overflow-hidden">
    <div className="p-4 border-b border-border">
      <h2 className="text-sm font-semibold text-foreground">
        Top 10 Holders — Smart Money Ranking
      </h2>
      <p className="text-xs text-muted-foreground mt-1">
        Ranked by Smart Score • Click wallet to view profile
      </p>
    </div>
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-[10px] text-muted-foreground uppercase tracking-wider">
            <th className="p-3 text-left">#</th>
            <th className="p-3 text-left">Wallet</th>
            <th className="p-3 text-right">Score</th>
            <th className="p-3 text-right">Win Rate</th>
            <th className="p-3 text-right">PnL (SOL)</th>
            <th className="p-3 text-right">Trades</th>
            <th className="p-3 text-right">Avg Hold</th>
            <th className="p-3 text-right">Entry Delay</th>
            <th className="p-3 text-center">Type</th>
          </tr>
        </thead>
        <tbody>
          {topWallets.map((w) => (
            <tr
              key={w.address}
              className="border-b border-border/40 hover:bg-secondary/40 transition-colors"
            >
              <td className="p-3 font-mono text-muted-foreground">{w.rank}</td>
              <td className="p-3">
                <CopyableAddress fullAddress={w.address} className="inline-block">
                  <Link
                    to={`/wallet/${encodeURIComponent(w.address)}`}
                    className="font-mono text-primary hover:underline flex items-center gap-1.5"
                  >
                    {w.address}
                    <ExternalLink className="w-3 h-3 opacity-50" />
                  </Link>
                </CopyableAddress>
              </td>
              <td className="p-3 text-right">
                <span
                  className={`font-mono font-bold ${
                    w.smartScore >= 70
                      ? "text-primary"
                      : w.smartScore >= 40
                        ? "text-accent"
                        : "text-muted-foreground"
                  }`}
                >
                  {w.smartScore}
                </span>
              </td>
              <td className="p-3 text-right font-mono">
                <span
                  className={
                    w.winRate >= 50 ? "text-primary" : "text-destructive"
                  }
                >
                  {w.winRate}%
                </span>
              </td>
              <td className="p-3 text-right font-mono">
                <span
                  className={
                    w.totalPnl >= 0 ? "text-primary" : "text-destructive"
                  }
                >
                  {w.totalPnl >= 0 ? "+" : ""}
                  {w.totalPnl.toFixed(2)}
                </span>
              </td>
              <td className="p-3 text-right font-mono text-foreground">
                {w.totalTrades}
              </td>
              <td className="p-3 text-right font-mono text-foreground">
                {w.avgHoldingHours}h
              </td>
              <td className="p-3 text-right font-mono">
                <span
                  className={
                    w.avgEntryDelay < 5
                      ? "text-primary"
                      : "text-muted-foreground"
                  }
                >
                  {w.avgEntryDelay}m
                </span>
              </td>
              <td className="p-3 text-center">
                <Badge
                  className={
                    w.isFresh
                      ? "bg-accent/20 text-accent border-accent/30 text-[10px]"
                      : "bg-secondary text-foreground text-[10px]"
                  }
                >
                  {w.isFresh ? "FRESH" : "OG"}
                </Badge>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  </div>
);

/* -------------------------- TokenOverlapChart ------------------------- */

const TokenOverlapChart = () => {
  const maxCount = Math.max(...tokenOverlaps.map((t) => t.walletCount), 1);
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <h3 className="text-sm font-semibold text-foreground mb-1">
        Token Overlap — Multi-Wallet Convergence
      </h3>
      <p className="text-xs text-muted-foreground mb-4">
        Tokens traded by multiple Top 10 wallets
      </p>
      <div className="space-y-3">
        {tokenOverlaps.map((t) => (
          <div key={t.token} className="flex items-center gap-3">
            <span className="font-mono text-sm w-16 text-primary">
              {t.token}
            </span>
            <div className="flex-1 h-6 bg-secondary rounded-sm overflow-hidden relative">
              <div
                className="h-full rounded-sm transition-all duration-700 bg-gradient-to-r from-primary/60 to-accent/60"
                style={{ width: `${(t.walletCount / maxCount) * 100}%` }}
              />
              <span className="absolute inset-0 flex items-center px-2 text-xs font-mono font-bold text-foreground">
                {t.walletCount} wallets
              </span>
            </div>
            <span
              className={`font-mono text-xs w-20 text-right ${
                t.avgPnl >= 0 ? "text-primary" : "text-destructive"
              }`}
            >
              {t.avgPnl >= 0 ? "+" : ""}
              {t.avgPnl} SOL
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

/* --------------------------- WinRateBreakdown ------------------------- */

const WinRateBreakdown = () => {
  const total = winRateBuckets.reduce((s, b) => s + b.count, 0) || 1;
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <h3 className="text-sm font-semibold text-foreground mb-1">
        Win Rate Distribution
      </h3>
      <p className="text-xs text-muted-foreground mb-4">
        Wallet performance buckets
      </p>
      <div className="space-y-4">
        {winRateBuckets.map((b) => {
          const pct = Math.round((b.count / total) * 100);
          const color =
            b.range === "70%+"
              ? "bg-primary"
              : b.range === "50-70%"
                ? "bg-accent"
                : "bg-destructive/60";
          return (
            <div key={b.range}>
              <div className="flex justify-between items-center mb-1">
                <span className="text-sm font-mono text-foreground">
                  {b.range}
                </span>
                <span className="text-xs text-muted-foreground">
                  {b.count} wallets • avg PnL:{" "}
                  <span
                    className={
                      b.avgPnl >= 0 ? "text-primary" : "text-destructive"
                    }
                  >
                    {b.avgPnl >= 0 ? "+" : ""}
                    {b.avgPnl} SOL
                  </span>
                </span>
              </div>
              <div className="h-3 bg-secondary rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full ${color} transition-all duration-700`}
                  style={{ width: `${Math.max(pct, 5)}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

/* --------------------------- HoldingDuration -------------------------- */

const HoldingDuration = () => {
  const maxCount = Math.max(...holdingDistribution.map((d) => d.count), 1);
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <h3 className="text-sm font-semibold text-foreground mb-1">
        Avg Holding Duration
      </h3>
      <p className="text-xs text-muted-foreground mb-4">
        How long Top 10 hold positions
      </p>
      <div className="flex items-end gap-2 h-32">
        {holdingDistribution.map((d) => (
          <div
            key={d.range}
            className="flex-1 flex flex-col items-center gap-1"
          >
            <span className="text-xs font-mono text-primary">{d.count}</span>
            <div
              className="w-full rounded-t bg-gradient-to-t from-accent/30 to-primary/70 transition-all duration-500"
              style={{ height: `${(d.count / maxCount) * 100}%` }}
            />
            <span className="text-[10px] text-muted-foreground font-mono">
              {d.range}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

/* ------------------------------ FreshVsOg ----------------------------- */

const FreshVsOg = () => {
  const fresh = topWallets.filter((w) => w.isFresh);
  const og = topWallets.filter((w) => !w.isFresh);
  const freshAvgTrades = fresh.length
    ? Math.round(fresh.reduce((s, w) => s + w.totalTrades, 0) / fresh.length)
    : 0;
  const ogAvgTrades = og.length
    ? Math.round(og.reduce((s, w) => s + w.totalTrades, 0) / og.length)
    : 0;

  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <h3 className="text-sm font-semibold text-foreground mb-1">
        Fresh vs OG Wallets
      </h3>
      <p className="text-xs text-muted-foreground mb-4">
        Wallet age classification
      </p>
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-accent/10 border border-accent/20 rounded-lg p-3 text-center">
          <div className="text-2xl font-bold font-mono text-accent">
            {fresh.length}
          </div>
          <div className="text-xs text-muted-foreground mt-1">
            Fresh Wallets
          </div>
          <div className="text-xs font-mono text-foreground mt-2">
            avg {freshAvgTrades} trades
          </div>
          <div className="text-[10px] text-muted-foreground">
            {"< 14 days old"}
          </div>
        </div>
        <div className="bg-secondary/40 border border-border rounded-lg p-3 text-center">
          <div className="text-2xl font-bold font-mono text-foreground">
            {og.length}
          </div>
          <div className="text-xs text-muted-foreground mt-1">OG Wallets</div>
          <div className="text-xs font-mono text-foreground mt-2">
            avg {ogAvgTrades} trades
          </div>
          <div className="text-[10px] text-muted-foreground">
            {"> 60 days old"}
          </div>
        </div>
      </div>
    </div>
  );
};

/* -------------------------- EarlyEntryWallets ------------------------- */

const EarlyEntryWallets = () => {
  const earlyWallets = topWallets
    .filter((w) => w.avgEntryDelay < 10 && w.winRate >= 30)
    .sort((a, b) => a.avgEntryDelay - b.avgEntryDelay);

  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <h3 className="text-sm font-semibold text-foreground mb-1">
        Early Entry Alpha Wallets
      </h3>
      <p className="text-xs text-muted-foreground mb-4">
        Wallets entering {"<"} 10 min after launch with 30%+ WR
      </p>
      {earlyWallets.length === 0 ? (
        <p className="text-xs text-muted-foreground">
          No wallets match criteria
        </p>
      ) : (
        <div className="space-y-2">
          {earlyWallets.map((w) => {
            const wTrades = tradeRecords.filter((t) => t.wallet === w.address);
            const recentTokens = [...new Set(wTrades.map((t) => t.token))].slice(
              0,
              3,
            );
            return (
              <div
                key={w.address}
                className="flex items-center justify-between p-2 rounded bg-secondary/40 border border-border"
              >
                <div>
                  <Link
                    to={`/wallet/${encodeURIComponent(w.address)}`}
                    className="font-mono text-sm text-primary hover:underline"
                  >
                    {w.address}
                  </Link>
                  <div className="flex gap-1 mt-1">
                    {recentTokens.map((t) => (
                      <span
                        key={t}
                        className="text-[10px] bg-primary/10 text-primary px-1.5 py-0.5 rounded font-mono"
                      >
                        {t}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-xs font-mono">
                    <span className="text-primary">{w.avgEntryDelay}m</span>{" "}
                    <span className="text-muted-foreground">avg delay</span>
                  </div>
                  <div className="text-xs font-mono">
                    <span
                      className={
                        w.winRate >= 50 ? "text-primary" : "text-accent"
                      }
                    >
                      {w.winRate}% WR
                    </span>
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

/* ----------------------------- AlertConfig ---------------------------- */

interface AlertRule {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
}

const defaultRules: AlertRule[] = [
  {
    id: "convergence",
    name: "Wallet Convergence",
    description: "3+ smart wallets buy the same token within 1 hour",
    enabled: true,
  },
  {
    id: "early-entry",
    name: "Early Entry Alert",
    description: "Top-scored wallet enters < 5 min after token launch",
    enabled: true,
  },
  {
    id: "whale-dump",
    name: "Whale Dump Warning",
    description: "Top holder sells > 50% of position",
    enabled: false,
  },
  {
    id: "fresh-wallet",
    name: "Fresh Wallet Activity",
    description: "New wallet with > 70% WR makes a trade",
    enabled: false,
  },
];

const AlertConfig = () => {
  const [rules, setRules] = useState<AlertRule[]>(defaultRules);
  const [telegramChatId, setTelegramChatId] = useState("");
  const [discordWebhook, setDiscordWebhook] = useState("");
  const [saved, setSaved] = useState(false);

  const toggleRule = (id: string) => {
    setRules((prev) =>
      prev.map((r) => (r.id === id ? { ...r, enabled: !r.enabled } : r)),
    );
    setSaved(false);
  };

  const handleSave = () => {
    setSaved(true);
    toast({
      title: "Alerts Configured",
      description: "Your notification preferences have been saved",
    });
  };

  return (
    <div className="rounded-lg border border-border bg-card p-4 space-y-5">
      <div className="flex items-center gap-2">
        <Bell className="w-4 h-4 text-primary" />
        <h3 className="text-sm font-semibold text-foreground">
          Smart Money Alerts
        </h3>
      </div>

      <div className="space-y-3">
        <p className="text-[10px] text-muted-foreground uppercase tracking-wider">
          Alert Rules
        </p>
        {rules.map((rule) => (
          <div
            key={rule.id}
            className="flex items-center justify-between p-3 rounded-lg bg-secondary/40 border border-border"
          >
            <div className="flex-1 mr-3">
              <div className="text-sm font-medium text-foreground">
                {rule.name}
              </div>
              <div className="text-xs text-muted-foreground">
                {rule.description}
              </div>
            </div>
            <Switch
              checked={rule.enabled}
              onCheckedChange={() => toggleRule(rule.id)}
            />
          </div>
        ))}
      </div>

      <div className="space-y-3">
        <p className="text-[10px] text-muted-foreground uppercase tracking-wider">
          Notification Channels
        </p>

        <div className="p-3 rounded-lg bg-secondary/40 border border-border space-y-2">
          <div className="flex items-center gap-2">
            <Send className="w-4 h-4 text-accent" />
            <span className="text-sm font-medium text-foreground">
              Telegram
            </span>
          </div>
          <Input
            placeholder="Chat ID (e.g. -1001234567890)"
            value={telegramChatId}
            onChange={(e) => {
              setTelegramChatId(e.target.value);
              setSaved(false);
            }}
            className="bg-background border-border font-mono text-xs"
          />
          <p className="text-[10px] text-muted-foreground">
            Get your Chat ID from{" "}
            <span className="text-primary">@userinfobot</span> on Telegram
          </p>
        </div>

        <div className="p-3 rounded-lg bg-secondary/40 border border-border space-y-2">
          <div className="flex items-center gap-2">
            <MessageCircle className="w-4 h-4 text-accent" />
            <span className="text-sm font-medium text-foreground">Discord</span>
          </div>
          <Input
            placeholder="Webhook URL (https://discord.com/api/webhooks/...)"
            value={discordWebhook}
            onChange={(e) => {
              setDiscordWebhook(e.target.value);
              setSaved(false);
            }}
            className="bg-background border-border font-mono text-xs"
          />
          <p className="text-[10px] text-muted-foreground">
            Create a webhook in your Discord channel settings → Integrations
          </p>
        </div>
      </div>

      <Button
        onClick={handleSave}
        className="w-full bg-primary text-primary-foreground hover:bg-primary/90 gap-2"
      >
        {saved ? <Check className="w-4 h-4" /> : <Bell className="w-4 h-4" />}
        {saved ? "Saved" : "Save Alert Configuration"}
      </Button>

      <p className="text-[10px] text-muted-foreground text-center font-mono">
        Alerts require Lovable Cloud backend • Connect to enable live
        notifications
      </p>
    </div>
  );
};

export default AlphaIntelView;
