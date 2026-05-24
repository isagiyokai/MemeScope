import { useState, useEffect } from "react";
import { Bell, MessageCircle, Send, Check, AlertCircle } from "lucide-react";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { Switch } from "@/components/ui/switch";
import { toast } from "@/hooks/use-toast";

interface AlertRule {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
}

interface AlertConfig {
  rules: AlertRule[];
  telegramChatId: string;
  discordWebhook: string;
}

const defaultRules: AlertRule[] = [
  { id: "convergence", name: "Wallet Convergence", description: "3+ smart wallets buy the same token within 1 hour", enabled: true },
  { id: "early-entry", name: "Early Entry Alert", description: "Top-scored wallet enters < 5 min after token launch", enabled: true },
  { id: "whale-dump", name: "Whale Dump Warning", description: "Top holder sells > 50% of position", enabled: false },
  { id: "fresh-wallet", name: "Fresh Wallet Activity", description: "New wallet with > 70% WR makes a trade", enabled: false },
];

const STORAGE_KEY = "memescope:alert-config";

function loadConfig(): AlertConfig {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { rules: defaultRules, telegramChatId: "", discordWebhook: "" };
    const parsed = JSON.parse(raw) as Partial<AlertConfig>;
    return {
      rules: parsed.rules ?? defaultRules,
      telegramChatId: parsed.telegramChatId ?? "",
      discordWebhook: parsed.discordWebhook ?? "",
    };
  } catch {
    return { rules: defaultRules, telegramChatId: "", discordWebhook: "" };
  }
}

function validateDiscordWebhook(url: string): string | null {
  if (!url) return null;
  if (!url.startsWith("https://discord.com/api/webhooks/")) {
    return "Must be a Discord webhook URL (https://discord.com/api/webhooks/...)";
  }
  return null;
}

function validateTelegramChatId(id: string): string | null {
  if (!id) return null;
  if (!/^-?\d{5,15}$/.test(id)) {
    return "Must be a numeric chat ID (e.g. -1001234567890)";
  }
  return null;
}

const AlertConfigSheet = () => {
  const [rules, setRules] = useState<AlertRule[]>(defaultRules);
  const [telegramChatId, setTelegramChatId] = useState("");
  const [discordWebhook, setDiscordWebhook] = useState("");
  const [saved, setSaved] = useState(false);
  const [discordError, setDiscordError] = useState<string | null>(null);
  const [telegramError, setTelegramError] = useState<string | null>(null);

  useEffect(() => {
    const cfg = loadConfig();
    setRules(cfg.rules);
    setTelegramChatId(cfg.telegramChatId);
    setDiscordWebhook(cfg.discordWebhook);
  }, []);

  const toggleRule = (id: string) => {
    setRules((prev) => prev.map((r) => (r.id === id ? { ...r, enabled: !r.enabled } : r)));
    setSaved(false);
  };

  const handleDiscordChange = (val: string) => {
    setDiscordWebhook(val);
    setDiscordError(validateDiscordWebhook(val));
    setSaved(false);
  };

  const handleTelegramChange = (val: string) => {
    setTelegramChatId(val);
    setTelegramError(validateTelegramChatId(val));
    setSaved(false);
  };

  const handleSave = () => {
    const de = validateDiscordWebhook(discordWebhook);
    const te = validateTelegramChatId(telegramChatId);
    setDiscordError(de);
    setTelegramError(te);
    if (de || te) return;

    const cfg: AlertConfig = { rules, telegramChatId, discordWebhook };
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(cfg));
      setSaved(true);
      toast({ title: "Alerts configured", description: "Preferences saved to this browser." });
    } catch {
      toast({ title: "Save failed", description: "Could not write to localStorage.", variant: "destructive" });
    }
  };

  const enabledCount = rules.filter((r) => r.enabled).length;

  return (
    <Sheet>
      <SheetTrigger asChild>
        <button className="inline-flex items-center gap-1.5 h-7 px-2.5 rounded-md bg-secondary hover:bg-surface-hover border border-border text-xs text-foreground transition-colors">
          <Bell className="h-3 w-3 text-primary" />
          Alerts
          <span className="text-[10px] bg-primary/15 text-primary px-1.5 py-0.5 rounded-full font-mono tabular-nums">{enabledCount}</span>
        </button>
      </SheetTrigger>
      <SheetContent side="right" className="w-[380px] sm:max-w-md bg-card border-l-border overflow-y-auto">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2 text-foreground">
            <Bell className="h-4 w-4 text-primary" />
            Smart Money Alerts
          </SheetTitle>
        </SheetHeader>

        <div className="mt-6 space-y-5">
          <div className="space-y-2">
            <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Alert Rules</p>
            {rules.map((rule) => (
              <div key={rule.id} className="flex items-center justify-between gap-3 p-3 rounded-md bg-secondary/40 border border-border">
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-foreground">{rule.name}</div>
                  <div className="text-xs text-muted-foreground">{rule.description}</div>
                </div>
                <Switch checked={rule.enabled} onCheckedChange={() => toggleRule(rule.id)} />
              </div>
            ))}
          </div>

          <div className="space-y-2">
            <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Notification Channels</p>

            <div className="p-3 rounded-md bg-secondary/40 border border-border space-y-2">
              <div className="flex items-center gap-2">
                <Send className="h-3.5 w-3.5 text-accent" />
                <span className="text-xs font-medium text-foreground">Telegram</span>
              </div>
              <input
                type="text"
                placeholder="Chat ID (e.g. -1001234567890)"
                value={telegramChatId}
                onChange={(e) => handleTelegramChange(e.target.value)}
                maxLength={16}
                className={`h-8 w-full bg-background rounded-md px-2.5 text-xs font-mono text-foreground placeholder:text-muted-foreground outline-none border focus:border-primary/50 ${telegramError ? "border-signal-low" : "border-border"}`}
              />
              {telegramError && (
                <div className="flex items-center gap-1 text-[10px] text-signal-low">
                  <AlertCircle className="h-3 w-3" />
                  {telegramError}
                </div>
              )}
            </div>

            <div className="p-3 rounded-md bg-secondary/40 border border-border space-y-2">
              <div className="flex items-center gap-2">
                <MessageCircle className="h-3.5 w-3.5 text-accent" />
                <span className="text-xs font-medium text-foreground">Discord</span>
              </div>
              <input
                type="url"
                placeholder="https://discord.com/api/webhooks/..."
                value={discordWebhook}
                onChange={(e) => handleDiscordChange(e.target.value)}
                maxLength={256}
                className={`h-8 w-full bg-background rounded-md px-2.5 text-xs font-mono text-foreground placeholder:text-muted-foreground outline-none border focus:border-primary/50 ${discordError ? "border-signal-low" : "border-border"}`}
              />
              {discordError && (
                <div className="flex items-center gap-1 text-[10px] text-signal-low">
                  <AlertCircle className="h-3 w-3" />
                  {discordError}
                </div>
              )}
            </div>
          </div>

          <button
            onClick={handleSave}
            className="w-full h-9 inline-flex items-center justify-center gap-2 rounded-md bg-primary text-primary-foreground text-sm font-semibold hover:bg-primary/90 transition-colors"
          >
            {saved ? <Check className="h-4 w-4" /> : <Bell className="h-4 w-4" />}
            {saved ? "Saved" : "Save Alert Configuration"}
          </button>

          <p className="text-[10px] text-muted-foreground text-center font-mono">
            Preferences saved locally — signal delivery via Telegram/Discord coming soon
          </p>
        </div>
      </SheetContent>
    </Sheet>
  );
};

export default AlertConfigSheet;
