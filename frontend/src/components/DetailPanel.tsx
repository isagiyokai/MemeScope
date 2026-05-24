import { Signal } from "@/lib/mockData";
import { X, Clock, Droplets, Users, Wallet, TrendingUp, Shield, Eye, ExternalLink } from "lucide-react";
import { useNavigate } from "react-router-dom";

interface DetailPanelProps {
  signal: Signal | null;
  onClose: () => void;
}

const CONF_SCORE: Record<string, number> = { HIGH: 85, MEDIUM: 55, LOW: 25 };
const CONF_COLOR: Record<string, string> = {
  HIGH: "hsl(var(--signal-high))",
  MEDIUM: "hsl(var(--signal-medium))",
  LOW: "hsl(var(--signal-low))",
};
const CONF_TEXT: Record<string, string> = {
  HIGH: "text-signal-high",
  MEDIUM: "text-signal-medium",
  LOW: "text-signal-low",
};

const DetailPanel = ({ signal, onClose }: DetailPanelProps) => {
  const navigate = useNavigate();

  if (!signal) {
    return (
      <aside className="h-full w-full border-l border-border bg-card flex flex-col items-center justify-center">
        <Eye className="h-8 w-8 text-muted-foreground/30 mb-3" />
        <p className="text-sm text-muted-foreground">Select a signal to inspect</p>
      </aside>
    );
  }

  const score = CONF_SCORE[signal.confidence] ?? 50;
  const ringColor = CONF_COLOR[signal.confidence] ?? "hsl(var(--muted))";
  const textColor = CONF_TEXT[signal.confidence] ?? "text-muted-foreground";

  const actionText =
    signal.actionBias === "ENTER" ? "Strong entry signal"
    : signal.actionBias === "WATCH" ? "Monitor closely"
    : "High risk — avoid";

  return (
    <aside className="h-full w-full border-l border-border bg-card flex flex-col overflow-y-auto fade-up">
      <div className="panel-header flex items-center justify-between">
        <span>Signal Detail</span>
        <button onClick={onClose} className="text-muted-foreground hover:text-foreground transition-colors">
          <X className="h-3.5 w-3.5" />
        </button>
      </div>

      <div className="p-4 space-y-4">
        {/* Token header */}
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-2xl font-bold text-foreground font-mono">{signal.ticker}</span>
            <span className="text-xs text-muted-foreground truncate">{signal.token}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className={`text-xs font-bold px-2 py-0.5 rounded ${
              signal.actionBias === "ENTER" ? "bg-signal-high/15 text-signal-high"
              : signal.actionBias === "WATCH" ? "bg-signal-medium/15 text-signal-medium"
              : "bg-signal-low/15 text-signal-low"
            }`}>
              {signal.actionBias}
            </span>
            <span className="text-xs text-muted-foreground">{signal.age} ago</span>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-3">
          <StatBox icon={<Clock className="h-3.5 w-3.5" />} label="Age" value={signal.age} />
          <StatBox icon={<Droplets className="h-3.5 w-3.5" />} label="Liquidity" value={signal.liquidity} />
          <StatBox icon={<Users className="h-3.5 w-3.5" />} label="Holders" value={signal.holders > 0 ? signal.holders.toString() : "—"} />
          <StatBox icon={<Wallet className="h-3.5 w-3.5" />} label="Smart Wallets" value={signal.smartWallets > 0 ? signal.smartWallets.toString() : "—"} accent />
        </div>

        {/* Confidence gauge */}
        <div className="bg-secondary rounded-lg p-3">
          <div className="text-xs text-muted-foreground mb-2">Confidence</div>
          <div className="flex items-center gap-3">
            <div className="relative h-12 w-12 shrink-0">
              <svg className="h-12 w-12 -rotate-90" viewBox="0 0 36 36">
                <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="hsl(var(--border))" strokeWidth="3" />
                <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke={ringColor} strokeWidth="3" strokeDasharray={`${score}, 100`} strokeLinecap="round" />
              </svg>
              <span className="absolute inset-0 flex items-center justify-center text-sm font-bold text-foreground">{score}</span>
            </div>
            <div>
              <div className={`text-sm font-bold ${textColor}`}>{signal.confidence} Confidence</div>
              <div className="text-xs text-muted-foreground">{actionText}</div>
            </div>
          </div>
        </div>

        {/* Why */}
        {signal.reasons.length > 0 && (
          <div>
            <div className="text-xs text-muted-foreground uppercase tracking-wider mb-2">Why This Signal?</div>
            <div className="space-y-2">
              {signal.reasons.map((reason, i) => (
                <div key={i} className="flex items-start gap-2 text-xs">
                  <Shield className="h-3 w-3 text-primary mt-0.5 shrink-0" />
                  <span className="text-secondary-foreground">{reason}</span>
                </div>
              ))}
              {signal.clusterDetected && (
                <div className="flex items-start gap-2 text-xs">
                  <TrendingUp className="h-3 w-3 text-accent mt-0.5 shrink-0" />
                  <span className="text-accent">Wallet cluster activity detected</span>
                </div>
              )}
              {signal.earlyEntry && (
                <div className="flex items-start gap-2 text-xs">
                  <Shield className="h-3 w-3 text-signal-high mt-0.5 shrink-0" />
                  <span className="text-signal-high">Early entry detected</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Navigate to token detail */}
        <button
          onClick={() => navigate(`/token/${encodeURIComponent(signal.ticker)}`)}
          className="w-full flex items-center justify-center gap-2 py-2 rounded-md bg-secondary hover:bg-surface-hover text-xs text-foreground transition-colors"
        >
          <ExternalLink className="h-3.5 w-3.5" />
          View token detail
        </button>
      </div>
    </aside>
  );
};

const StatBox = ({
  icon, label, value, accent,
}: {
  icon: React.ReactNode; label: string; value: string; accent?: boolean;
}) => (
  <div className="bg-secondary rounded-lg p-2.5">
    <div className="flex items-center gap-1 text-muted-foreground mb-1">
      {icon}
      <span className="text-[10px]">{label}</span>
    </div>
    <span className={`text-sm font-bold tabular-nums ${accent ? "text-primary" : "text-foreground"}`}>{value}</span>
  </div>
);

export default DetailPanel;
