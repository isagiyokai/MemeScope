import { ReactNode, useRef } from "react";
import { toast } from "@/hooks/use-toast";

interface CopyableAddressProps {
  /** Full wallet address to copy. */
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
    try {
      await navigator.clipboard.writeText(fullAddress);
      toast({
        title: "Address copied",
        description: fullAddress,
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
      title={`${fullAddress} — right-click or long-press to copy`}
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
