import { useMemo } from "react";

export interface InkStampProps {
  text: string;
  variant?: "red" | "sage" | "ochre" | "navy";
  rotation?: number;
  className?: string;
  doubleRing?: boolean;
}

function hashString(str: string): number {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = (hash << 5) - hash + str.charCodeAt(i);
    hash |= 0;
  }
  return hash;
}

export function InkStamp({
  text,
  variant,
  rotation,
  className = "",
  doubleRing = false,
}: InkStampProps) {
  // Deterministic slight rotation (-2deg to +2deg) based on text hash
  const computedRotation = useMemo(() => {
    if (rotation !== undefined) return rotation;
    const hash = hashString(text);
    const angles = [-2, -1.2, 0.8, 1.5, 2.2, -1.8, 1.1, -0.6];
    return angles[Math.abs(hash) % angles.length];
  }, [text, rotation]);

  const computedVariant = useMemo(() => {
    if (variant) return variant;
    const upper = text.toUpperCase();
    if (upper.includes("OVERDUE") || upper.includes("HIGH") || upper.includes("MISSING") || upper.includes("URGENT")) {
      return "red";
    }
    if (upper.includes("ELIGIBLE") || upper.includes("VERIFIED") || upper.includes("FILED") || upper.includes("DONE") || upper.includes("APPROVED")) {
      return "sage";
    }
    return "ochre";
  }, [text, variant]);

  const variantStyles = {
    red: "text-[#A85043] border-[#A85043]/80 bg-[#A85043]/10 shadow-[0_0_10px_rgba(168,80,67,0.1)]",
    sage: "text-[#8CA189] border-[#8CA189]/80 bg-[#8CA189]/10 shadow-[0_0_10px_rgba(140,161,137,0.1)]",
    ochre: "text-[#BB8A34] border-[#BB8A34]/80 bg-[#BB8A34]/10 shadow-[0_0_10px_rgba(187,138,52,0.1)]",
    navy: "text-[#3B82F6] border-[#3B82F6]/80 bg-[#3B82F6]/10 shadow-[0_0_10px_rgba(59,130,246,0.1)]",
  };

  return (
    <span
      style={{ transform: `rotate(${computedRotation}deg)` }}
      className={`inline-flex items-center justify-center px-2.5 py-0.5 rounded-[3px] text-[10.5px] font-mono font-bold uppercase tracking-wider ink-stamp border-1.5 transition-transform duration-100 ${variantStyles[computedVariant]} ${
        doubleRing ? "outline-1 outline-dashed outline-current outline-offset-[-3px]" : ""
      } ${className}`}
    >
      {text}
    </span>
  );
}
