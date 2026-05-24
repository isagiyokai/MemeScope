import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Signal } from "@/lib/mockData";
import { Check, AlertTriangle, Eye, ArrowUpRight, Clock, Droplets, Users, Wallet, Zap } from "lucide-react";
import { useEffect, useRef } from "react";

interface SignalCardProps {
  signal: Signal;
  onSelect: (signal: Signal) => void;
  isNew?: boolean;
}

const SignalCard = ({ signal, onSelect, isNew }: SignalCardProps) => {
  const navigate = useNavigate();
  const confidenceConfig = getConfidenceConfig(signal.confidence);
  const timeSince = getTimeSince(signal.timestamp);

  return (
    <div
      onClick={() => onSelect(signal)}
      className={`signal-card group ${isNew ? "slide-in glow-green" : ""}`}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className={`inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${confidenceConfig.badgeClass}`}>
            {confidenceConfig.icon}
            SMART MONEY ALERT
          </span>
          {isNew && (
            <span className="text-[10px] font-medium text-primary animate-pulse">NEW</span>
          )}
        </div>
        <span className="text-[10px] text-muted-foreground">{timeSince}</span>
      </div>

      <div className="flex items-baseline gap-2 mb-3">
        <span
          className="text-xl font-bold text-foreground hover:text-primary transition-colors cursor-pointer"
          onClick={(e) => { e.stopPropagation(); navigate(`/token/${signal.ticker}`); }}
        >
          {signal.ticker}
        </span>
        <span className="text-xs text-muted-foreground">{signal.token}</span>
        {signal.priceChange > 0 && (
          <span className="text-xs font-semibold text-signal-high flex items-center gap-0.5">
            <ArrowUpRight className="h-3 w-3" />
            +{signal.priceChange}%
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 sm:gap-3 mb-3">
        <MiniStat icon={<Clock className="h-3 w-3" />} label="Age" value={signal.age} />
        <MiniStat icon={<Droplets className="h-3 w-3" />} label="Liq" value={signal.liquidity} />
        <MiniStat icon={<Users className="h-3 w-3" />} label="Holders" value={signal.holders.toString()} />
        <MiniStat icon={<Wallet className="h-3 w-3" />} label="Smart" value={signal.smartWallets.toString()} highlight />
      </div>

      <div className="space-y-1.5 mb-3">
        {signal.reasons.map((reason, i) => (
          <div key={i} className="flex items-start gap-1.5 text-xs text-secondary-foreground">
            <Check className="h-3 w-3 text-primary mt-0.5 shrink-0" />
            <span>{reason}</span>
          </div>
        ))}
      </div>

      <div className="flex items-center justify-between gap-2 pt-3 border-t border-border flex-wrap">
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground hidden sm:inline">Confidence:</span>
          <ConfidenceMeter value={confidenceConfig.value} color={confidenceConfig.color} />
          <span className={`text-xs font-bold ${confidenceConfig.textClass}`}>
            {signal.confidence}
          </span>
        </div>
        <span className={`text-xs font-bold px-2.5 py-1 rounded-md ${
          signal.actionBias === "ENTER"
            ? "bg-signal-high/15 text-signal-high"
            : signal.actionBias === "WATCH"
            ? "bg-signal-medium/15 text-signal-medium"
            : "bg-signal-low/15 text-signal-low"
        }`}>
          {signal.actionBias === "ENTER" ? "⚡" : signal.actionBias === "WATCH" ? "👁" : "⛔"} {signal.actionBias}
        </span>
      </div>
    </div>
  );
};

const MiniStat = ({ icon, label, value, highlight }: { icon: React.ReactNode; label: string; value: string; highlight?: boolean }) => (
  <div className="text-center">
    <div className="flex items-center justify-center gap-1 text-muted-foreground mb-0.5">
      {icon}
      <span className="text-[10px]">{label}</span>
    </div>
    <span className={`text-sm font-semibold tabular-nums ${highlight ? "text-primary" : "text-foreground"}`}>
      {value}
    </span>
  </div>
);

const ConfidenceMeter = ({ value, color }: { value: number; color: string }) => {
  const blocks = 8;
  const filled = Math.round((value / 100) * blocks);
  const [animated, setAnimated] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const timer = setTimeout(() => setAnimated(true), 100);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="flex gap-0.5" ref={ref}>
      {Array.from({ length: blocks }).map((_, i) => (
        <div
          key={i}
          className={`h-2.5 w-1.5 rounded-sm transition-all duration-300 ${
            animated && i < filled ? color : "bg-secondary"
          }`}
          style={{ transitionDelay: animated ? `${i * 50}ms` : "0ms" }}
        />
      ))}
    </div>
  );
};

function getConfidenceConfig(confidence: "HIGH" | "MEDIUM" | "LOW") {
  switch (confidence) {
    case "HIGH":
      return { value: 85, color: "bg-signal-high", textClass: "confidence-high", badgeClass: "badge-high", icon: <Zap className="h-2.5 w-2.5" /> };
    case "MEDIUM":
      return { value: 55, color: "bg-signal-medium", textClass: "confidence-medium", badgeClass: "badge-medium", icon: <Eye className="h-2.5 w-2.5" /> };
    case "LOW":
      return { value: 25, color: "bg-signal-low", textClass: "confidence-low", badgeClass: "badge-low", icon: <AlertTriangle className="h-2.5 w-2.5" /> };
  }
}

function getTimeSince(date: Date) {
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  return `${minutes}m ago`;
}

export default SignalCard;
