"use client";

import { useState, useCallback } from "react";
import { BRAND } from "@/lib/city.config";

interface ShareButtonProps {
  lakeName: string;
}

function ShareIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="12" cy="3" r="2" />
      <circle cx="4" cy="8" r="2" />
      <circle cx="12" cy="13" r="2" />
      <line x1="5.7" y1="7" x2="10.3" y2="4" />
      <line x1="5.7" y1="9" x2="10.3" y2="12" />
    </svg>
  );
}

export default function ShareButton({ lakeName }: ShareButtonProps) {
  const [copied, setCopied] = useState(false);

  const handleShare = useCallback(async () => {
    const shareData = {
      title: lakeName,
      text: `Check out ${lakeName} on ${BRAND}`,
      url: window.location.href,
    };

    if (typeof navigator.share === "function") {
      try {
        await navigator.share(shareData);
        return;
      } catch {
        // User cancelled or share failed -- fall through to clipboard
      }
    }

    // Clipboard fallback
    try {
      await navigator.clipboard.writeText(window.location.href);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard not available
    }
  }, [lakeName]);

  return (
    <button
      onClick={handleShare}
      className="inline-flex items-center gap-2 bg-white/10 hover:bg-white/20 text-white font-medium px-4 py-2 rounded-lg transition-colors"
    >
      <ShareIcon />
      {copied ? "Copied!" : "Share"}
    </button>
  );
}
