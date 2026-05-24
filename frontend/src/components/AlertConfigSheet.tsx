import { useState } from "react";
import { Bell, MessageCircle, Send, Check } from "lucide-react";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { Switch } from "@/components/ui/switch";
import { toast } from "@/hooks/use-toast";

interface AlertRule {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
}

const defaultRules: AlertRule[] = [
  { id: "convergence", name: "Wallet Convergence", description: "3+ smart wallets buy the same token within 1 hour", enabled: true },
  { id: "early-entry", name: "Early Entry Alert", description: "Top-scored wallet enters < 5 min after token launch", enabled: true },
  { id: "whale-dump", name: "Whale Dump Warning", description: "Top holder sells > 50% of position", enabled: false },
  { id: "fresh-wallet", name: "Fresh Wallet Activity", description: "New wallet with > 70% WR makes a trade", enabled: false },
];

const AlertConfigSheet = () => {
  const [rules, setRules] = useState<AlertRule[]>(defaultRules);
  const [telegramChatId, setTelegramChatId] = useState("");
  const [discordWebhook, setDiscordWebhook] = useState("");
  const [saved, setSaved] = useState(false);

  const toggleRule = (id: string) => {
    setRules((prev) => prev.map((r) => (r.id === id ? { ...r, enabled: !r.enabled } : r)));
    setSaved(false);
  };

  const handleSave = () => {
    setSaved(true);
    toast({ title: "Alerts configured", description: "Your notification preferences have been saved" });
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
                onChange={(e) => { setTelegramChatId(e.target.value); setSaved(false); }}
                maxLength={64}
                className="h-8 w-full bg-background rounded-md px-2.5 text-xs font-mono text-foreground placeholder:text-muted-foreground outline-none border border-border focus:border-primary/50"
              />
            </div>

            <div className="p-3 rounded-md bg-secondary/40 border border-border space-y-2">
              <div className="flex items-center gap-2">
                <MessageCircle className="h-3.5 w-3.5 text-accent" />
                <span className="text-xs font-medium text-foreground">Discord</span>
              </div>
              <input
                type="url"
                placeholder="Webhook URL"
                value={discordWebhook}
                onChange={(e) => { setDiscordWebhook(e.target.value); setSaved(false); }}
                maxLength={256}
                className="h-8 w-full bg-background rounded-md px-2.5 text-xs font-mono text-foreground placeholder:text-muted-foreground outline-none border border-border focus:border-primary/50"
              />
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
            Alert delivery not yet implemented — configuration will not be saved
          </p>
        </div>
      </SheetContent>
    </Sheet>
  );
};

export default AlertConfigSheet;
