import { useEffect, useRef, useState } from "react";
import { useIsMobile } from "@/hooks/use-mobile";

const QUIPS = [
  "Bribing the blockchain... 🪙",
  "Sniffing alpha out of the mempool... 👃",
  "Asking whales nicely for their secrets... 🐋",
  "Front-running your FOMO... 🏃💨",
  "Counting rugs so you don't have to... 🧹",
  "Decoding ape behavior... 🦍",
  "Loading hopium reserves... 💊",
  "Calibrating moon math... 🌙",
  "Teaching candles to lie better... 🕯️",
  "Convincing the chart to go up... 📈",
  "Yelling 'WAGMI' at the void... 📣",
  "Polishing diamond hands... 💎🙌",
];

// Daily emoji rotation (desktop) — fresh every day
const DAILY_EMOJIS = ["🦍", "🐸", "🚀", "🌝", "🐕", "💎", "🤡", "👽"];

interface StartupSplashProps {
  onDone: () => void;
  /** total visible duration in ms (desktop only — mobile waits for double-tap) */
  duration?: number;
}

const StartupSplash = ({ onDone, duration = 2200 }: StartupSplashProps) => {
  const isMobile = useIsMobile();
  const [leaving, setLeaving] = useState(false);
  const [juggling, setJuggling] = useState(false);
  const [chestBeating, setChestBeating] = useState(false);
  const [quipIndex, setQuipIndex] = useState(() => Math.floor(Math.random() * QUIPS.length));
  const lastTapRef = useRef<number>(0);

  // Pick today's emoji deterministically based on the date
  const dailyEmoji = DAILY_EMOJIS[new Date().getDate() % DAILY_EMOJIS.length];
  // Mobile is always a monkey
  const splashEmoji = isMobile ? "🐒" : dailyEmoji;

  const finish = () => {
    setLeaving(true);
    setTimeout(onDone, 300);
  };

  useEffect(() => {
    // Rotate quip every 700ms while splash is visible
    const quipRotator = setInterval(() => {
      setQuipIndex((i) => (i + 1) % QUIPS.length);
    }, 700);

    // Desktop auto-dismisses; mobile waits for double-tap
    let leaveAt: number | undefined;
    let doneAt: number | undefined;
    if (!isMobile) {
      leaveAt = window.setTimeout(() => setLeaving(true), duration - 300);
      doneAt = window.setTimeout(onDone, duration);
    }

    return () => {
      clearInterval(quipRotator);
      if (leaveAt) clearTimeout(leaveAt);
      if (doneAt) clearTimeout(doneAt);
    };
  }, [duration, onDone, isMobile]);

  const handleApeClick = () => {
    if (chestBeating) return;

    if (isMobile) {
      // Detect double-tap (within 400ms)
      const now = Date.now();
      if (now - lastTapRef.current < 400) {
        lastTapRef.current = 0;
        setChestBeating(true);
        // Beat chest, then dismiss
        setTimeout(finish, 1100);
      } else {
        lastTapRef.current = now;
      }
      return;
    }

    // Desktop: juggle
    if (juggling) return;
    setJuggling(true);
    setTimeout(() => setJuggling(false), 900);
  };

  return (
    <div
      className={`fixed inset-0 z-[9999] flex flex-col items-center justify-center bg-background transition-opacity duration-300 ${
        leaving ? "opacity-0" : "opacity-100"
      }`}
      aria-hidden={leaving}
    >
      <div className="relative flex items-center justify-center h-40 w-40">
        <div className="absolute h-32 w-32 rounded-full bg-primary/30 blur-3xl animate-pulse" />
        <button
          type="button"
          onClick={handleApeClick}
          aria-label={isMobile ? "Double tap the monkey to enter" : "Poke the mascot"}
          className="relative z-10 select-none cursor-pointer bg-transparent border-0 p-0 leading-none touch-manipulation"
        >
          <span
            className={`text-8xl inline-block drop-shadow-[0_0_25px_hsl(var(--primary))] ${
              chestBeating
                ? "animate-[chest-beat_0.35s_ease-in-out_infinite]"
                : juggling
                  ? "animate-[ape-juggle_0.9s_cubic-bezier(0.34,1.56,0.64,1)_both]"
                  : "animate-[goofy-spin_1.2s_ease-in-out_infinite]"
            }`}
          >
            {splashEmoji}
          </span>
        </button>
      </div>
      <div className="mt-6 text-center">
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          MemeScope
        </h1>
        <p
          key={quipIndex}
          className="mt-2 text-sm text-muted-foreground max-w-xs animate-[fade-in_0.4s_ease-out]"
        >
          {chestBeating ? "OOH OOH AAH AAH! 🥁" : QUIPS[quipIndex]}
        </p>
        {isMobile && !chestBeating && (
          <p className="mt-3 text-xs text-primary/80 font-semibold tracking-wide animate-pulse">
            Double-tap the monkey to enter
          </p>
        )}
      </div>
      <div className="mt-6 flex gap-1.5">
        <span className="h-1.5 w-1.5 rounded-full bg-primary animate-bounce" style={{ animationDelay: "0ms" }} />
        <span className="h-1.5 w-1.5 rounded-full bg-primary animate-bounce" style={{ animationDelay: "120ms" }} />
        <span className="h-1.5 w-1.5 rounded-full bg-primary animate-bounce" style={{ animationDelay: "240ms" }} />
      </div>
    </div>
  );
};

export default StartupSplash;
