import { useState, useEffect, useRef } from "react";
import { Signal, Filters, filterSignals } from "@/lib/mockData";
import { fetchSignals, connectSignalStream, adaptSignal } from "@/lib/api";
import SignalCard from "@/components/SignalCard";
import { Flame, Loader2, WifiOff } from "lucide-react";

interface AlphaFeedProps {
  onSelectSignal: (signal: Signal) => void;
  filters: Filters;
}

const POLL_MS = 30_000;

const AlphaFeed = ({ onSelectSignal, filters }: AlphaFeedProps) => {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [newIds, setNewIds] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [wsConnected, setWsConnected] = useState(false);
  const seenRef = useRef<Set<string>>(new Set());

  function addSignal(s: Signal) {
    if (seenRef.current.has(s.id)) return;
    seenRef.current.add(s.id);
    setSignals((prev) => [s, ...prev.slice(0, 99)]);
    setNewIds((ids) => {
      const next = new Set(ids);
      next.add(s.id);
      setTimeout(() => setNewIds((i2) => { const n = new Set(i2); n.delete(s.id); return n; }), 3000);
      return next;
    });
  }

  // Initial load + polling
  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const raw = await fetchSignals(100);
        if (cancelled) return;
        const adapted = raw.map(adaptSignal);
        setSignals(adapted);
        adapted.forEach((s) => seenRef.current.add(s.id));
        setLoading(false);
      } catch {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    const timer = setInterval(load, POLL_MS);
    return () => { cancelled = true; clearInterval(timer); };
  }, []);

  // WebSocket for real-time push
  useEffect(() => {
    const disconnect = connectSignalStream(
      (msg) => {
        if (msg.type === "signal") {
          setWsConnected(true);
          addSignal(adaptSignal(msg.payload));
        } else if (msg.type === "ping") {
          setWsConnected(true);
        }
      },
      () => setWsConnected(false),
    );
    return disconnect;
  }, []);

  const filtered = filterSignals(signals, filters);

  return (
    <div className="h-full w-full overflow-y-auto">
      <div className="panel-header flex items-center gap-2">
        <Flame className="h-3.5 w-3.5 text-signal-high" />
        Alpha Feed
        <span className="ml-auto flex items-center gap-2 text-[10px] text-muted-foreground tabular-nums">
          {wsConnected ? (
            <span className="flex items-center gap-1 text-signal-high">
              <span className="h-1.5 w-1.5 rounded-full bg-signal-high pulse-dot" />
              LIVE
            </span>
          ) : (
            <span className="flex items-center gap-1 text-muted-foreground">
              <WifiOff className="h-3 w-3" />
              polling
            </span>
          )}
          {filtered.length}/{signals.length}
        </span>
      </div>

      <div className="p-3 space-y-2">
        {loading ? (
          <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
            <Loader2 className="h-8 w-8 mb-3 opacity-50 animate-spin" />
            <p className="text-sm">Loading signals…</p>
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
            <Flame className="h-8 w-8 mb-3 opacity-30" />
            <p className="text-sm">No signals yet</p>
            <p className="text-xs mt-1">Signals appear as smart wallets move</p>
          </div>
        ) : (
          filtered.map((signal, i) => (
            <div key={signal.id} className="fade-up" style={{ animationDelay: `${Math.min(i * 50, 300)}ms` }}>
              <SignalCard
                signal={signal}
                onSelect={onSelectSignal}
                isNew={newIds.has(signal.id)}
              />
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default AlphaFeed;
