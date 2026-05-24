import { Terminal, ChevronDown, ChevronUp } from "lucide-react";
import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import CopyableAddress from "@/components/CopyableAddress";
import { connectSignalStream } from "@/lib/api";

interface LogEntry {
  id: string;
  time: string;
  type: "scan" | "alert" | "wallet" | "signal";
  message: string;
  walletAddress?: string;
  ticker?: string;
}

interface ActivityLogProps {
  collapsed?: boolean;
  onToggleCollapsed?: () => void;
}

function nowHHMMSS(): string {
  const d = new Date();
  return [d.getHours(), d.getMinutes(), d.getSeconds()]
    .map((n) => String(n).padStart(2, "0"))
    .join(":");
}

const ActivityLog = ({ collapsed = false, onToggleCollapsed }: ActivityLogProps) => {
  const [logs, setLogs] = useState<LogEntry[]>([
    { id: "boot", time: nowHHMMSS(), type: "scan", message: "MemeScope connected — waiting for signals" },
  ]);

  useEffect(() => {
    const disconnect = connectSignalStream((msg) => {
      if (msg.type === "ping") return;
      if (msg.type === "signal") {
        const s = msg.payload;
        const shortMint = s.token_mint.slice(0, 6);
        const entry: LogEntry = {
          id: `ws-${s.id}`,
          time: nowHHMMSS(),
          type: "signal",
          message: `New ${s.signal_type} signal — ${shortMint}… (conf ${Math.round(s.confidence * 100)}%)`,
        };
        setLogs((prev) => [entry, ...prev.slice(0, 49)]);
      }
    });
    return disconnect;
  }, []);

  if (collapsed) {
    const tickerItems = [...logs, ...logs];
    return (
      <button
        type="button"
        onClick={onToggleCollapsed}
        aria-label="Expand activity log"
        className="group h-8 w-full border-t border-border bg-card flex items-center gap-2 pl-3 pr-2 overflow-hidden hover:bg-surface-hover transition-colors"
      >
        <div className="flex items-center gap-1.5 shrink-0 text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">
          <Terminal className="h-3 w-3" />
          <span className="hidden sm:inline">Activity</span>
          <span className="h-1.5 w-1.5 rounded-full bg-signal-high pulse-dot" />
        </div>
        <div className="flex-1 overflow-hidden relative">
          <div
            className="flex gap-8 whitespace-nowrap font-mono text-[11px] will-change-transform"
            style={{ animation: "ticker 60s linear infinite" }}
          >
            {tickerItems.map((log, i) => (
              <span key={`${log.id}-${i}`} className="flex items-center gap-2">
                <span className="text-muted-foreground">{log.time}</span>
                <span
                  className={
                    log.type === "signal" || log.type === "alert"
                      ? "text-signal-high"
                      : log.type === "wallet"
                        ? "text-accent"
                        : "text-muted-foreground"
                  }
                >
                  [{log.type.toUpperCase()}]
                </span>
                <span className="text-secondary-foreground">{log.message}</span>
                <span className="text-border">•</span>
              </span>
            ))}
          </div>
        </div>
        <ChevronUp className="h-3.5 w-3.5 text-muted-foreground group-hover:text-foreground shrink-0" />
      </button>
    );
  }

  return (
    <div className="h-full w-full border-t border-border bg-card flex flex-col">
      <div className="panel-header flex items-center gap-2 py-2 pr-2">
        <Terminal className="h-3 w-3" />
        <span className="flex-1">Activity Log</span>
        {onToggleCollapsed && (
          <button
            type="button"
            onClick={onToggleCollapsed}
            aria-label="Collapse activity log"
            className="inline-flex items-center justify-center h-6 w-6 rounded hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors"
          >
            <ChevronDown className="h-3.5 w-3.5" />
          </button>
        )}
      </div>
      <div className="flex-1 overflow-y-auto px-4 py-1 font-mono text-[11px]">
        {logs.map((log) => (
          <div key={log.id} className="flex items-center gap-2 py-0.5 slide-in">
            <span className="text-muted-foreground shrink-0">{log.time}</span>
            <span className={`shrink-0 ${
              log.type === "signal" || log.type === "alert"
                ? "text-signal-high"
                : log.type === "wallet"
                  ? "text-accent"
                  : "text-muted-foreground"
            }`}>
              [{log.type.toUpperCase()}]
            </span>
            <span className="text-secondary-foreground truncate">
              {log.walletAddress ? (
                <>
                  {log.message.split(log.walletAddress)[0]}
                  <CopyableAddress fullAddress={log.walletAddress} className="inline">
                    <Link
                      to={`/wallet/${encodeURIComponent(log.walletAddress)}`}
                      className="text-accent hover:text-primary underline underline-offset-2 transition-colors"
                    >
                      {log.walletAddress}
                    </Link>
                  </CopyableAddress>
                  {log.message.split(log.walletAddress)[1]}
                </>
              ) : log.ticker ? (
                <>
                  {log.message.split(log.ticker)[0]}
                  <Link
                    to={`/token/${encodeURIComponent(log.ticker)}`}
                    className="text-signal-high hover:text-primary underline underline-offset-2 transition-colors"
                  >
                    {log.ticker}
                  </Link>
                  {log.message.split(log.ticker)[1]}
                </>
              ) : (
                log.message
              )}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ActivityLog;
