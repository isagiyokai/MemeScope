import { useEffect, useState } from "react";
import { Search, Activity, Zap, Radio } from "lucide-react";
import { fetchStats, ApiStats } from "@/lib/api";
import AlertConfigSheet from "@/components/AlertConfigSheet";
import HamburgerMenu from "@/components/HamburgerMenu";

const POLL_MS = 60_000;

const TopBar = () => {
  const [stats, setStats] = useState<ApiStats>({
    active_signals: 0,
    tracked_wallets: 0,
    tokens_scanned: 0,
    avg_confidence: 0,
  });

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const s = await fetchStats();
        if (!cancelled) setStats(s);
      } catch {
        // keep previous values on error
      }
    }
    load();
    const timer = setInterval(load, POLL_MS);
    return () => { cancelled = true; clearInterval(timer); };
  }, []);

  return (
    <header className="h-14 border-b border-border bg-card flex items-center justify-between px-3 sm:px-4 shrink-0 gap-2">
      <div className="flex items-center gap-2 sm:gap-3 min-w-0">
        <HamburgerMenu />
        <div className="flex items-center gap-2 shrink-0">
          <Zap className="h-5 w-5 text-primary" />
          <span className="font-bold text-base sm:text-lg tracking-tight text-foreground">MemeScope</span>
        </div>
        <div className="hidden md:block h-6 w-px bg-border mx-2" />
        <div className="relative hidden md:block">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search token or wallet..."
            className="h-8 w-48 lg:w-64 bg-secondary rounded-md pl-9 pr-3 text-sm text-foreground placeholder:text-muted-foreground outline-none border border-border focus:border-primary/50 transition-colors"
          />
        </div>
      </div>

      <div className="flex lg:hidden flex-1 min-w-0 overflow-hidden mx-2 justify-center">
        <div className="flex items-center gap-3 sm:gap-5 text-xs whitespace-nowrap overflow-hidden">
          <TickerItem label="LIVE" value="●" accent />
          <TickerItem label="Signals" value={String(stats.active_signals)} />
          <TickerItem label="Wallets" value={stats.tracked_wallets.toLocaleString()} />
          <TickerItem label="Scanned" value={String(stats.tokens_scanned)} />
        </div>
      </div>

      <div className="flex items-center gap-3 sm:gap-6 shrink-0">
        <div className="hidden lg:flex items-center gap-1.5">
          <div className="h-2 w-2 rounded-full bg-primary pulse-dot" />
          <span className="text-xs text-muted-foreground">LIVE</span>
        </div>
        <div className="hidden lg:flex items-center gap-5 text-xs">
          <Stat icon={<Activity className="h-3 w-3" />} label="Signals" value={stats.active_signals} />
          <Stat icon={<Radio className="h-3 w-3" />} label="Wallets" value={stats.tracked_wallets.toLocaleString()} />
          <Stat label="Scanned" value={String(stats.tokens_scanned)} />
        </div>
        <AlertConfigSheet />
      </div>
    </header>
  );
};

const Stat = ({ icon, label, value }: { icon?: React.ReactNode; label: string; value: string | number }) => (
  <div className="flex items-center gap-1.5 text-muted-foreground">
    {icon}
    <span>{label}</span>
    <span className="text-foreground font-semibold tabular-nums">{value}</span>
  </div>
);

const TickerItem = ({ label, value, accent }: { label: string; value: string; accent?: boolean }) => (
  <div className="flex items-center gap-1.5">
    <span className={accent ? "text-primary" : "text-muted-foreground"}>{label}</span>
    <span className={`font-semibold tabular-nums ${accent ? "text-primary" : "text-foreground"}`}>{value}</span>
  </div>
);

export default TopBar;
