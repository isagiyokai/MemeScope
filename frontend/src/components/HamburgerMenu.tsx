import { useState } from "react";
import { Link } from "react-router-dom";
import {
  Menu,
  LayoutDashboard,
  Wallet as WalletIcon,
  Coins,
  Bell,
  Settings as SettingsIcon,
  ChevronLeft,
  Github,
  BookOpen,
  Bookmark,
  Download,
  Keyboard,
  Sparkles,
} from "lucide-react";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { Switch } from "@/components/ui/switch";
import { toast } from "@/hooks/use-toast";

type View = "menu" | "settings";

const HamburgerMenu = () => {
  const [open, setOpen] = useState(false);
  const [view, setView] = useState<View>("menu");

  const closeAfter = (fn?: () => void) => {
    fn?.();
    setOpen(false);
    setView("menu");
  };

  return (
    <Sheet
      open={open}
      onOpenChange={(o) => {
        setOpen(o);
        if (!o) setView("menu");
      }}
    >
      <SheetTrigger asChild>
        <button
          aria-label="Open menu"
          className="inline-flex items-center justify-center h-8 w-8 rounded-md hover:bg-secondary text-foreground transition-colors"
        >
          <Menu className="h-4 w-4" />
        </button>
      </SheetTrigger>
      <SheetContent
        side="left"
        className="w-[300px] sm:max-w-sm bg-card border-r-border p-0 overflow-y-auto"
      >
        {view === "menu" ? (
          <div className="flex flex-col h-full">
            <div className="px-5 py-4 border-b border-border">
              <div className="text-[10px] uppercase tracking-widest text-muted-foreground">
                Menu
              </div>
              <div className="text-sm font-semibold text-foreground mt-0.5">
                MemeScope Terminal
              </div>
            </div>

            <Section label="Navigate">
              <RowLink
                to="/"
                icon={<LayoutDashboard className="h-4 w-4 text-primary" />}
                label="Alpha Feed"
                onClick={() => closeAfter()}
              />
              <RowLink
                to="/alpha-intel"
                icon={<Sparkles className="h-4 w-4 text-accent" />}
                label="Alpha Intel"
                onClick={() => closeAfter()}
              />
              <RowLink
                to="/wallet/0xSmart01"
                icon={<WalletIcon className="h-4 w-4 text-primary" />}
                label="Wallet Explorer"
                onClick={() => closeAfter()}
              />
              <RowLink
                to="/token/SCAT"
                icon={<Coins className="h-4 w-4 text-primary" />}
                label="Token Pages"
                onClick={() => closeAfter()}
              />
            </Section>

            <Section label="Quick Actions">
              <RowButton
                icon={<Bell className="h-4 w-4 text-accent" />}
                label="Mute all alerts (1h)"
                onClick={() =>
                  closeAfter(() =>
                    toast({
                      title: "Alerts muted",
                      description: "All alerts paused for 1 hour",
                    }),
                  )
                }
              />
              <RowButton
                icon={<Bookmark className="h-4 w-4 text-accent" />}
                label="Watchlist"
                hint="0 tokens"
                onClick={() =>
                  closeAfter(() =>
                    toast({
                      title: "Watchlist",
                      description: "No tokens saved yet",
                    }),
                  )
                }
              />
              <RowButton
                icon={<Download className="h-4 w-4 text-accent" />}
                label="Export signals (CSV)"
                onClick={() =>
                  closeAfter(() =>
                    toast({
                      title: "Export queued",
                      description: "CSV export will be ready shortly",
                    }),
                  )
                }
              />
              <RowButton
                icon={<Keyboard className="h-4 w-4 text-accent" />}
                label="Keyboard shortcuts"
                hint="?"
                onClick={() =>
                  closeAfter(() =>
                    toast({
                      title: "Shortcuts",
                      description: "F = filter • A = alerts • / = search",
                    }),
                  )
                }
              />
            </Section>

            <Section label="Resources">
              <RowAnchor
                href="https://docs.lovable.dev"
                icon={<BookOpen className="h-4 w-4 text-muted-foreground" />}
                label="Documentation"
              />
              <RowAnchor
                href="https://github.com"
                icon={<Github className="h-4 w-4 text-muted-foreground" />}
                label="GitHub"
              />
            </Section>

            <div className="mt-auto p-3 border-t border-border">
              <button
                onClick={() => setView("settings")}
                className="w-full flex items-center justify-between gap-2 px-3 py-2.5 rounded-md bg-secondary/60 hover:bg-secondary border border-border text-sm text-foreground transition-colors"
              >
                <span className="flex items-center gap-2">
                  <SettingsIcon className="h-4 w-4 text-primary" />
                  Settings
                </span>
              </button>
            </div>
          </div>
        ) : (
          <div className="flex flex-col h-full">
            <div className="px-3 py-3 border-b border-border flex items-center gap-2">
              <button
                onClick={() => setView("menu")}
                className="inline-flex items-center justify-center h-7 w-7 rounded-md hover:bg-secondary text-foreground"
                aria-label="Back"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <div className="text-sm font-semibold text-foreground flex items-center gap-2">
                <SettingsIcon className="h-4 w-4 text-primary" /> Settings
              </div>
            </div>

            <Section label="Preferences">
              <ToggleRow
                label="Sound on new HIGH signals"
                defaultChecked={false}
              />
              <ToggleRow label="Auto-scroll activity log" defaultChecked />
              <ToggleRow label="Compact card density" defaultChecked />
            </Section>

            <div className="px-5 py-3 text-[10px] text-muted-foreground font-mono border-t border-border mt-auto">
              MemeScope v0.2
            </div>
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
};

const Section = ({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) => (
  <div className="px-3 py-3 border-b border-border/60">
    <div className="text-[10px] uppercase tracking-widest text-muted-foreground px-2 pb-1.5">
      {label}
    </div>
    <div className="space-y-0.5">{children}</div>
  </div>
);

const RowLink = ({
  to,
  icon,
  label,
  hint,
  onClick,
}: {
  to: string;
  icon: React.ReactNode;
  label: string;
  hint?: string;
  onClick?: () => void;
}) => (
  <Link
    to={to}
    onClick={onClick}
    className="flex items-center justify-between gap-2 px-2 py-2 rounded-md hover:bg-secondary text-sm text-foreground transition-colors"
  >
    <span className="flex items-center gap-2">
      {icon}
      {label}
    </span>
    {hint && (
      <span className="text-[10px] font-mono text-muted-foreground">{hint}</span>
    )}
  </Link>
);

const RowButton = ({
  icon,
  label,
  hint,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  hint?: string;
  onClick?: () => void;
}) => (
  <button
    onClick={onClick}
    className="w-full flex items-center justify-between gap-2 px-2 py-2 rounded-md hover:bg-secondary text-sm text-foreground transition-colors"
  >
    <span className="flex items-center gap-2">
      {icon}
      {label}
    </span>
    {hint && (
      <span className="text-[10px] font-mono text-muted-foreground">{hint}</span>
    )}
  </button>
);

const RowAnchor = ({
  href,
  icon,
  label,
}: {
  href: string;
  icon: React.ReactNode;
  label: string;
}) => (
  <a
    href={href}
    target="_blank"
    rel="noreferrer"
    className="flex items-center gap-2 px-2 py-2 rounded-md hover:bg-secondary text-sm text-muted-foreground hover:text-foreground transition-colors"
  >
    {icon}
    {label}
  </a>
);

const ToggleRow = ({
  label,
  defaultChecked = false,
}: {
  label: string;
  defaultChecked?: boolean;
}) => {
  const [on, setOn] = useState(defaultChecked);
  return (
    <div className="flex items-center justify-between px-2 py-2 rounded-md hover:bg-secondary/60">
      <span className="text-sm text-foreground">{label}</span>
      <Switch checked={on} onCheckedChange={setOn} />
    </div>
  );
};

export default HamburgerMenu;
