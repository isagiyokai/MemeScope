import { useState } from "react";
import { SlidersHorizontal, ChevronLeft, ChevronRight, Droplets, Clock, Target, Wallet, Sparkles } from "lucide-react";
import { Filters } from "@/lib/mockData";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";

interface FilterPanelProps {
  filters: Filters;
  onChange: (filters: Filters) => void;
  collapsed?: boolean;
  onToggleCollapsed?: () => void;
}

type DrawerId = "liquidity" | "age" | "winrate" | "score";

const FilterPanel = ({ filters, onChange, collapsed = false, onToggleCollapsed }: FilterPanelProps) => {
  const [activeDrawer, setActiveDrawer] = useState<DrawerId | null>(null);

  if (!filters) return null;
  const update = (partial: Partial<Filters>) => onChange({ ...filters, ...partial });

  const applyPreset = (preset: "aggressive" | "balanced" | "conservative") => {
    switch (preset) {
      case "aggressive":
        onChange({ minLiquidityK: 0, maxAgeMin: 5, minWinRate: 40, minWalletScore: 50, freshWalletsOnly: false });
        break;
      case "balanced":
        onChange({ minLiquidityK: 10, maxAgeMin: 15, minWinRate: 55, minWalletScore: 70, freshWalletsOnly: false });
        break;
      case "conservative":
        onChange({ minLiquidityK: 25, maxAgeMin: 30, minWinRate: 65, minWalletScore: 80, freshWalletsOnly: false });
        break;
    }
  };

  const drawerConfigs: Array<{
    id: DrawerId;
    Icon: typeof Droplets;
    label: string;
    active: boolean;
    title: string;
    description: string;
    node: React.ReactNode;
  }> = [
    {
      id: "liquidity",
      Icon: Droplets,
      label: `Liq $${filters.minLiquidityK}K`,
      active: filters.minLiquidityK > 0,
      title: "Min Liquidity",
      description: "Filter signals by minimum token liquidity",
      node: <FilterSlider label="Min Liquidity" value={filters.minLiquidityK} onChange={(v) => update({ minLiquidityK: v })} min={0} max={100} unit="K" prefix="$" />,
    },
    {
      id: "age",
      Icon: Clock,
      label: `Age ${filters.maxAgeMin}m`,
      active: filters.maxAgeMin < 60,
      title: "Token Age",
      description: "Maximum token age to include in signals",
      node: <FilterSlider label="Max Token Age" value={filters.maxAgeMin} onChange={(v) => update({ maxAgeMin: v })} min={1} max={60} unit="min" />,
    },
    {
      id: "winrate",
      Icon: Target,
      label: `WR ${filters.minWinRate}%`,
      active: filters.minWinRate > 0,
      title: "Win Rate",
      description: "Minimum wallet win rate to qualify",
      node: <FilterSlider label="Min Win Rate" value={filters.minWinRate} onChange={(v) => update({ minWinRate: v })} min={0} max={100} unit="%" />,
    },
    {
      id: "score",
      Icon: Wallet,
      label: `Score ${filters.minWalletScore}`,
      active: filters.minWalletScore > 0,
      title: "Wallet Score",
      description: "Minimum composite wallet intelligence score",
      node: <FilterSlider label="Min Wallet Score" value={filters.minWalletScore} onChange={(v) => update({ minWalletScore: v })} min={0} max={100} unit="" />,
    },
  ];

  if (collapsed) {
    return (
      <>
        <aside className="h-full w-full border-r border-border bg-card flex flex-col items-center py-2 gap-1">
          <button
            onClick={onToggleCollapsed}
            aria-label="Expand filters"
            title="Expand filters"
            className="h-9 w-9 flex items-center justify-center rounded-md hover:bg-surface-hover text-muted-foreground hover:text-foreground transition-colors"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
          <div className="h-px w-8 bg-border my-1" />
          <button
            onClick={onToggleCollapsed}
            title="Filters"
            className="h-9 w-9 flex items-center justify-center rounded-md hover:bg-surface-hover text-primary transition-colors"
          >
            <SlidersHorizontal className="h-4 w-4" />
          </button>
          {drawerConfigs.map(({ id, Icon, label, active }) => (
            <button
              key={id}
              onClick={() => setActiveDrawer(id)}
              title={label}
              className={`h-9 w-9 flex items-center justify-center rounded-md hover:bg-surface-hover transition-all relative ${
                active ? "text-foreground" : "text-muted-foreground/50"
              }`}
            >
              <Icon className="h-4 w-4" />
              {active && <span className="absolute top-1.5 right-1.5 h-1.5 w-1.5 rounded-full bg-primary" />}
            </button>
          ))}
          <button
            onClick={() => update({ freshWalletsOnly: !filters.freshWalletsOnly })}
            title={`Fresh wallets only: ${filters.freshWalletsOnly ? "on" : "off"}`}
            aria-pressed={filters.freshWalletsOnly}
            className={`h-9 w-9 flex items-center justify-center rounded-md hover:bg-surface-hover transition-all relative ${
              filters.freshWalletsOnly
                ? "bg-primary/15 text-primary shadow-[0_0_12px_hsl(var(--primary)/0.5)]"
                : "text-muted-foreground/50"
            }`}
          >
            <Sparkles
              className={`h-4 w-4 transition-all ${
                filters.freshWalletsOnly ? "text-primary drop-shadow-[0_0_6px_hsl(var(--primary))]" : ""
              }`}
            />
          </button>
        </aside>

        {drawerConfigs.map(({ id, Icon, title, description, node }) => (
          <Sheet key={id} open={activeDrawer === id} onOpenChange={(o) => !o && setActiveDrawer(null)}>
            <SheetContent side="left" className="w-72 p-0 bg-card border-r border-border">
              <SheetHeader className="px-4 py-3 border-b border-border">
                <SheetTitle className="flex items-center gap-2 text-sm font-medium text-foreground">
                  <Icon className="h-3.5 w-3.5 text-primary" />
                  {title}
                </SheetTitle>
                <p className="text-[11px] text-muted-foreground">{description}</p>
              </SheetHeader>
              <div className="p-4">{node}</div>
            </SheetContent>
          </Sheet>
        ))}
      </>
    );
  }

  return (
    <aside className="h-full w-full border-r border-border bg-card flex flex-col overflow-y-auto">
      <div className="panel-header flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <SlidersHorizontal className="h-3 w-3" />
          Filters
        </div>
        {onToggleCollapsed && (
          <button
            onClick={onToggleCollapsed}
            aria-label="Collapse filters"
            title="Collapse"
            className="h-6 w-6 flex items-center justify-center rounded hover:bg-surface-hover text-muted-foreground hover:text-foreground transition-colors"
          >
            <ChevronLeft className="h-3.5 w-3.5" />
          </button>
        )}
      </div>

      <div className="p-4 space-y-5">
        <FilterSlider label="Min Liquidity" value={filters.minLiquidityK} onChange={(v) => update({ minLiquidityK: v })} min={0} max={100} unit="K" prefix="$" />
        <FilterSlider label="Token Age" value={filters.maxAgeMin} onChange={(v) => update({ maxAgeMin: v })} min={1} max={60} unit="min" />
        <FilterSlider label="Win Rate" value={filters.minWinRate} onChange={(v) => update({ minWinRate: v })} min={0} max={100} unit="%" />
        <FilterSlider label="Wallet Score" value={filters.minWalletScore} onChange={(v) => update({ minWalletScore: v })} min={0} max={100} unit="" />

        <div className="flex items-center justify-between">
          <span className="text-xs text-muted-foreground">Fresh wallets only</span>
          <button
            onClick={() => update({ freshWalletsOnly: !filters.freshWalletsOnly })}
            className={`h-5 w-9 rounded-full transition-colors ${filters.freshWalletsOnly ? "bg-primary" : "bg-secondary"} relative`}
          >
            <div className={`h-3.5 w-3.5 rounded-full bg-foreground absolute top-0.5 transition-transform ${filters.freshWalletsOnly ? "translate-x-4" : "translate-x-0.5"}`} />
          </button>
        </div>

        <div className="pt-2 border-t border-border">
          <div className="text-xs text-muted-foreground mb-2">Quick Presets</div>
          <div className="space-y-1.5">
            <PresetButton label="🔥 Aggressive" onClick={() => applyPreset("aggressive")} />
            <PresetButton label="⚖️ Balanced" onClick={() => applyPreset("balanced")} />
            <PresetButton label="🛡️ Conservative" onClick={() => applyPreset("conservative")} />
          </div>
        </div>
      </div>
    </aside>
  );
};

const FilterSlider = ({ label, value, onChange, min, max, unit, prefix = "" }: {
  label: string; value: number; onChange: (v: number) => void; min: number; max: number; unit: string; prefix?: string;
}) => (
  <div>
    <div className="flex items-center justify-between mb-1.5">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className="text-xs font-medium text-foreground tabular-nums">{prefix}{value}{unit}</span>
    </div>
    <input
      type="range" min={min} max={max} value={value}
      onChange={(e) => onChange(Number(e.target.value))}
      className="w-full h-1 bg-secondary rounded-full appearance-none cursor-pointer accent-primary [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-primary"
    />
  </div>
);

const PresetButton = ({ label, onClick }: { label: string; onClick: () => void }) => (
  <button onClick={onClick} className="w-full text-left text-xs px-2.5 py-1.5 rounded-md bg-secondary hover:bg-surface-hover text-secondary-foreground transition-colors">
    {label}
  </button>
);

export default FilterPanel;
