import { useState, useEffect } from "react";
import { Signal, Filters, defaultFilters } from "@/lib/mockData";
import TopBar from "@/components/TopBar";
import FilterPanel from "@/components/FilterPanel";
import AlphaFeed from "@/components/AlphaFeed";
import DetailPanel from "@/components/DetailPanel";
import ActivityLog from "@/components/ActivityLog";
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";
import { useIsMobile } from "@/hooks/use-mobile";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { SlidersHorizontal, Sparkles } from "lucide-react";

const Index = () => {
  const [selectedSignal, setSelectedSignal] = useState<Signal | null>(null);
  const [filters, setFilters] = useState<Filters>(defaultFilters);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [filterRailCollapsed, setFilterRailCollapsed] = useState(false);
  const [activityCollapsed, setActivityCollapsed] = useState(false);
  const [isTablet, setIsTablet] = useState(false);
  const isMobile = useIsMobile();

  // Tablet = >= 768 and < 1280 (use detail as overlay instead of column)
  useEffect(() => {
    const mql = window.matchMedia("(min-width: 768px) and (max-width: 1279px)");
    const on = () => setIsTablet(mql.matches);
    on();
    mql.addEventListener("change", on);
    return () => mql.removeEventListener("change", on);
  }, []);

  if (isMobile) {
    return (
      <div className="h-screen flex flex-col bg-background overflow-hidden">
        <TopBar />
        <div className="flex items-center justify-between border-b border-border bg-card px-3 py-2 shrink-0 gap-2">
          <Sheet open={filtersOpen} onOpenChange={setFiltersOpen}>
            <SheetTrigger asChild>
              <button
                aria-label="Open filters"
                className="inline-flex items-center gap-2 h-8 px-3 rounded-md bg-secondary hover:bg-surface-hover text-foreground text-xs"
              >
                <SlidersHorizontal className="h-3.5 w-3.5" />
                Filters
              </button>
            </SheetTrigger>
            <SheetContent side="left" className="p-0 w-[85vw] sm:max-w-xs bg-card border-r-border overflow-y-auto">
              <FilterPanel filters={filters} onChange={setFilters} />
            </SheetContent>
          </Sheet>
          <button
            onClick={() => setFilters({ ...filters, freshWalletsOnly: !filters.freshWalletsOnly })}
            aria-pressed={filters.freshWalletsOnly}
            aria-label="Toggle fresh wallets only"
            title="Fresh wallets only"
            className={`inline-flex items-center gap-1.5 h-8 px-3 rounded-md text-xs transition-all ${
              filters.freshWalletsOnly
                ? "bg-primary/15 text-primary border border-primary/40 shadow-[0_0_12px_hsl(var(--primary)/0.5)]"
                : "bg-secondary hover:bg-surface-hover text-foreground border border-transparent"
            }`}
          >
            <Sparkles
              className={`h-3.5 w-3.5 transition-all ${
                filters.freshWalletsOnly
                  ? "text-primary drop-shadow-[0_0_6px_hsl(var(--primary))]"
                  : "text-muted-foreground"
              }`}
            />
            Fresh
          </button>
        </div>
        <div className="flex-1 overflow-hidden flex flex-col">
          {activityCollapsed ? (
            <>
              <div className="flex-1 overflow-hidden">
                <AlphaFeed onSelectSignal={setSelectedSignal} filters={filters} />
              </div>
              <ActivityLog
                collapsed
                onToggleCollapsed={() => setActivityCollapsed(false)}
              />
            </>
          ) : (
            <ResizablePanelGroup direction="vertical" autoSaveId="memescope-mobile-v">
              <ResizablePanel defaultSize={70} minSize={30}>
                <AlphaFeed onSelectSignal={setSelectedSignal} filters={filters} />
              </ResizablePanel>
              <ResizableHandle withHandle />
              <ResizablePanel defaultSize={30} minSize={10} maxSize={70}>
                <ActivityLog onToggleCollapsed={() => setActivityCollapsed(true)} />
              </ResizablePanel>
            </ResizablePanelGroup>
          )}
        </div>

        {/* Detail as slide-in overlay on mobile */}
        <Sheet open={!!selectedSignal} onOpenChange={(o) => !o && setSelectedSignal(null)}>
          <SheetContent side="right" className="p-0 w-full sm:max-w-md bg-card border-l-border overflow-y-auto">
            {selectedSignal && (
              <DetailPanel signal={selectedSignal} onClose={() => setSelectedSignal(null)} />
            )}
          </SheetContent>
        </Sheet>
      </div>
    );
  }

  // Tablet: filter rail collapsed by default, detail panel as slide-in overlay
  if (isTablet) {
    return (
      <div className="h-screen flex flex-col bg-background overflow-hidden">
        <TopBar />
        <div className="flex-1 overflow-hidden flex">
          <div className={filterRailCollapsed ? "w-12 shrink-0" : "w-64 shrink-0"}>
            <FilterPanel
              filters={filters}
              onChange={setFilters}
              collapsed={filterRailCollapsed}
              onToggleCollapsed={() => setFilterRailCollapsed(!filterRailCollapsed)}
            />
          </div>
          <div className="flex-1 overflow-hidden flex flex-col">
            {activityCollapsed ? (
              <>
                <div className="flex-1 overflow-hidden">
                  <AlphaFeed onSelectSignal={setSelectedSignal} filters={filters} />
                </div>
                <ActivityLog
                  collapsed
                  onToggleCollapsed={() => setActivityCollapsed(false)}
                />
              </>
            ) : (
              <ResizablePanelGroup direction="vertical" autoSaveId="memescope-tablet-v">
                <ResizablePanel defaultSize={78} minSize={30}>
                  <AlphaFeed onSelectSignal={setSelectedSignal} filters={filters} />
                </ResizablePanel>
                <ResizableHandle withHandle />
                <ResizablePanel defaultSize={22} minSize={8} maxSize={60}>
                  <ActivityLog onToggleCollapsed={() => setActivityCollapsed(true)} />
                </ResizablePanel>
              </ResizablePanelGroup>
            )}
          </div>
        </div>

        <Sheet open={!!selectedSignal} onOpenChange={(o) => !o && setSelectedSignal(null)}>
          <SheetContent side="right" className="p-0 w-[90vw] sm:max-w-md bg-card border-l-border overflow-y-auto">
            {selectedSignal && (
              <DetailPanel signal={selectedSignal} onClose={() => setSelectedSignal(null)} />
            )}
          </SheetContent>
        </Sheet>
      </div>
    );
  }

  // Desktop: hybrid collapsible rail
  return (
    <div className="h-screen flex flex-col bg-background overflow-hidden">
      <TopBar />
      <div className="flex-1 overflow-hidden flex">
        {filterRailCollapsed ? (
          <div className="w-12 shrink-0">
            <FilterPanel
              filters={filters}
              onChange={setFilters}
              collapsed
              onToggleCollapsed={() => setFilterRailCollapsed(false)}
            />
          </div>
        ) : null}

        <div className="flex-1 overflow-hidden">
          <ResizablePanelGroup direction="horizontal" autoSaveId="memescope-main-h">
            {!filterRailCollapsed && (
              <>
                <ResizablePanel defaultSize={16} minSize={12} maxSize={30}>
                  <FilterPanel
                    filters={filters}
                    onChange={setFilters}
                    onToggleCollapsed={() => setFilterRailCollapsed(true)}
                  />
                </ResizablePanel>
                <ResizableHandle withHandle />
              </>
            )}

            <ResizablePanel defaultSize={84} minSize={40}>
              {activityCollapsed ? (
                <div className="h-full flex flex-col">
                  <div className="flex-1 overflow-hidden">
                    <ResizablePanelGroup direction="horizontal" autoSaveId="memescope-feed-h">
                      <ResizablePanel defaultSize={selectedSignal ? 70 : 100} minSize={30}>
                        <AlphaFeed onSelectSignal={setSelectedSignal} filters={filters} />
                      </ResizablePanel>
                      {selectedSignal && (
                        <>
                          <ResizableHandle withHandle />
                          <ResizablePanel defaultSize={30} minSize={20} maxSize={50}>
                            <DetailPanel
                              signal={selectedSignal}
                              onClose={() => setSelectedSignal(null)}
                            />
                          </ResizablePanel>
                        </>
                      )}
                    </ResizablePanelGroup>
                  </div>
                  <ActivityLog
                    collapsed
                    onToggleCollapsed={() => setActivityCollapsed(false)}
                  />
                </div>
              ) : (
                <ResizablePanelGroup direction="vertical" autoSaveId="memescope-main-v">
                  <ResizablePanel defaultSize={78} minSize={30}>
                    <ResizablePanelGroup direction="horizontal" autoSaveId="memescope-feed-h">
                      <ResizablePanel defaultSize={selectedSignal ? 70 : 100} minSize={30}>
                        <AlphaFeed onSelectSignal={setSelectedSignal} filters={filters} />
                      </ResizablePanel>
                      {selectedSignal && (
                        <>
                          <ResizableHandle withHandle />
                          <ResizablePanel defaultSize={30} minSize={20} maxSize={50}>
                            <DetailPanel
                              signal={selectedSignal}
                              onClose={() => setSelectedSignal(null)}
                            />
                          </ResizablePanel>
                        </>
                      )}
                    </ResizablePanelGroup>
                  </ResizablePanel>
                  <ResizableHandle withHandle />
                  <ResizablePanel defaultSize={22} minSize={8} maxSize={60}>
                    <ActivityLog onToggleCollapsed={() => setActivityCollapsed(true)} />
                  </ResizablePanel>
                </ResizablePanelGroup>
              )}
            </ResizablePanel>
          </ResizablePanelGroup>
        </div>
      </div>
    </div>
  );
};

export default Index;
