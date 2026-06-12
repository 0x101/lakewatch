"use client";

import { useRef, useState } from "react";
import { useTimelapse } from "@/hooks/useTimelapse";
import type { FrameItem } from "@/lib/types";

interface ThenVsNowProps {
  lakeId: string;
}

function formatMonthYear(dateStr: string): string {
  const d = new Date(dateStr);
  if (Number.isNaN(d.getTime())) return dateStr;
  return d.toLocaleDateString("en-US", { month: "short", year: "numeric" });
}

/**
 * Draggable then-vs-now comparison of the oldest and newest timelapse frames.
 * Renders nothing when fewer than two frames exist.
 */
export default function ThenVsNow({ lakeId }: ThenVsNowProps) {
  const { data: timelapse } = useTimelapse(lakeId);
  const containerRef = useRef<HTMLDivElement>(null);
  const [pct, setPct] = useState(50);

  const frames: FrameItem[] = (timelapse?.frames ?? [])
    .slice()
    .sort((a, b) => a.frame_order - b.frame_order);

  if (frames.length < 2) return null;

  const first = frames[0];
  const last = frames[frames.length - 1];

  const updateFromClientX = (clientX: number) => {
    const el = containerRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const raw = ((clientX - rect.left) / rect.width) * 100;
    setPct(Math.max(0, Math.min(100, raw)));
  };

  return (
    <div className="bg-white/5 border border-white/10 rounded-xl p-4">
      <h3 className="text-lg font-semibold text-white mb-1">Then vs Now</h3>
      <p className="text-xs text-foreground/40 mb-4">
        Drag to compare the oldest and newest satellite frames.
      </p>

      <div
        ref={containerRef}
        className="relative rounded-xl overflow-hidden aspect-video bg-black select-none cursor-ew-resize"
        onPointerDown={(e) => {
          e.currentTarget.setPointerCapture(e.pointerId);
          updateFromClientX(e.clientX);
        }}
        onPointerMove={(e) => {
          if (e.buttons === 0) return;
          updateFromClientX(e.clientX);
        }}
        onPointerUp={(e) => {
          e.currentTarget.releasePointerCapture(e.pointerId);
        }}
      >
        {/* Base: newest frame */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={last.frame_url}
          alt={`Satellite frame from ${last.observation_date}`}
          className="absolute inset-0 w-full h-full object-cover"
          draggable={false}
        />

        {/* Overlay: oldest frame, clipped to pct width */}
        <div
          className="absolute inset-y-0 left-0 overflow-hidden"
          style={{ width: `${pct}%` }}
        >
          <div className="absolute inset-y-0 left-0" style={{ width: `${10000 / pct}%` }}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={first.frame_url}
              alt={`Satellite frame from ${first.observation_date}`}
              className="w-full h-full object-cover"
              draggable={false}
            />
          </div>
        </div>

        {/* Divider handle */}
        <div
          className="absolute inset-y-0 w-0.5 bg-white/80 pointer-events-none"
          style={{ left: `${pct}%` }}
        >
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-6 h-6 rounded-full bg-white/90 border border-black/20 shadow" />
        </div>

        {/* Date labels */}
        <span className="absolute top-2 left-2 bg-black/60 px-2 py-0.5 rounded text-xs text-white font-mono">
          {formatMonthYear(first.observation_date)}
        </span>
        <span className="absolute top-2 right-2 bg-black/60 px-2 py-0.5 rounded text-xs text-white font-mono">
          {formatMonthYear(last.observation_date)}
        </span>
      </div>
    </div>
  );
}
