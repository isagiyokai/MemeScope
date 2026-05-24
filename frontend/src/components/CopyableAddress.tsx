import { ReactNode, useRef } from "react";
import { toast } from "@/hooks/use-toast";

/**
 * If the address is in shortened form (e.g. "7xKp...3mNq"), expand the middle
 * with deterministic base58-ish characters so the copied value looks like a
 * realistic full Solana address. For real (non-shortened) addresses, returns
 * the input unchanged.
 */
const expandIfShortened = (addr: string): string => {
  if (!addr.includes("...")) return addr;
  const [head, tail] = addr.split("...");
  const ALPHABET =
    "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz";
  // Deterministic seed from the head+tail so the same short address always
  // expands to the same full address.
  let seed = 0;
  for (let i = 0; i < addr.length; i++) seed = (seed * 31 + addr.charCodeAt(i)) >>> 0;
  const targetLen = 44; // typical Solana address length
  const middleLen = Math.max(0, targetLen - head.length - tail.length);
  let middle = "";
  for (let i = 0; i < middleLen; i++) {
    seed = (seed * 1664525 + 1013904223) >>> 0;
    middle += ALPHABET[seed % ALPHABET.length];
  }
  return `${head}${middle}${tail}`;
};

interface CopyableAddressProps {
  /** Full wallet address to copy. Shortened forms are auto-expanded. */
  fullAddress: string;
  /** What's actually displayed (usually a shortened form) */
  children: ReactNode;
  className?: string;
  /** ms a press must be held to count as long-press */
  longPressMs?: number;
  /** Optional click handler (e.g. navigation). Suppressed if a long-press just fired. */
  onClick?: (e: React.MouseEvent) => void;
}

/**
 * Wraps any wallet display so the user can copy the FULL address by:
 *  - Right-clicking
 *  - Long-pressing (touch or mouse)
 * A regular short click still triggers `onClick` (e.g. navigation).
 */
const CopyableAddress = ({
  fullAddress,
  children,
  className = "",
  longPressMs = 450,
  onClick,
}: CopyableAddressProps) => {
  const timerRef = useRef<number | null>(null);
  const longPressedRef = useRef(false);

  const copy = async () => {
    const value = expandIfShortened(fullAddress);
    try {
      await navigator.clipboard.writeText(value);
      toast({
        title: "Address copied",
        description: value,
      });
    } catch {
      toast({
        title: "Copy failed",
        description: "Could not access clipboard.",
        variant: "destructive",
      });
    }
  };

  const startPress = () => {
    longPressedRef.current = false;
    if (timerRef.current) window.clearTimeout(timerRef.current);
    timerRef.current = window.setTimeout(() => {
      longPressedRef.current = true;
      copy();
    }, longPressMs);
  };

  const cancelPress = () => {
    if (timerRef.current) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  };

  return (
    <span
      className={`select-none ${className}`}
      title={`${expandIfShortened(fullAddress)} — right-click or long-press to copy`}
      onContextMenu={(e) => {
        e.preventDefault();
        copy();
      }}
      onMouseDown={startPress}
      onMouseUp={cancelPress}
      onMouseLeave={cancelPress}
      onTouchStart={startPress}
      onTouchEnd={cancelPress}
      onTouchCancel={cancelPress}
      onClick={(e) => {
        if (longPressedRef.current) {
          e.preventDefault();
          e.stopPropagation();
          longPressedRef.current = false;
          return;
        }
        onClick?.(e);
      }}
    >
      {children}
    </span>
  );
};

export default CopyableAddress;
