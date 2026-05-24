import { Zap, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";

interface LoadIconProps {
  /** ms before we assume there's a network/slow issue and switch to classic spinner */
  slowAfter?: number;
  size?: number;
  className?: string;
  /** force classic spinner (e.g. when offline) */
  forceClassic?: boolean;
}

/**
 * Consistent load icon:
 * - Pops in and rotates, then fades away (fast path)
 * - If still mounted past `slowAfter` OR offline -> falls back to classic spinner
 */
const LoadIcon = ({ slowAfter = 1200, size = 32, className = "", forceClassic = false }: LoadIconProps) => {
  const [isSlow, setIsSlow] = useState(forceClassic || (typeof navigator !== "undefined" && !navigator.onLine));

  useEffect(() => {
    if (forceClassic) return;
    const t = setTimeout(() => setIsSlow(true), slowAfter);
    const onOffline = () => setIsSlow(true);
    window.addEventListener("offline", onOffline);
    return () => {
      clearTimeout(t);
      window.removeEventListener("offline", onOffline);
    };
  }, [slowAfter, forceClassic]);

  if (isSlow) {
    return (
      <Loader2
        className={`text-primary animate-spin ${className}`}
        style={{ width: size, height: size }}
      />
    );
  }

  return (
    <Zap
      className={`text-primary load-pop-rotate ${className}`}
      style={{ width: size, height: size }}
    />
  );
};

export default LoadIcon;
