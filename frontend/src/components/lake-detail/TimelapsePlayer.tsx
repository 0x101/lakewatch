"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useTimelapse } from "@/hooks/useTimelapse";
import type { FrameItem } from "@/lib/types";

/**
 * Custom hook that pre-loads all timelapse frame images for smooth playback.
 * Reports loading progress and completion state.
 */
function usePreloadFrames(frameUrls: string[]) {
  const [loaded, setLoaded] = useState(false);
  const [progress, setProgress] = useState(0);

  /* eslint-disable react-hooks/set-state-in-effect --
     preload state must reset synchronously when the frame list changes */
  useEffect(() => {
    if (frameUrls.length === 0) {
      setLoaded(true);
      setProgress(1);
      return;
    }

    let cancelled = false;
    let loadedCount = 0;

    setLoaded(false);
    setProgress(0);

    frameUrls.forEach((url) => {
      const img = new window.Image();
      const onDone = () => {
        if (cancelled) return;
        loadedCount++;
        setProgress(loadedCount / frameUrls.length);
        if (loadedCount >= frameUrls.length) {
          setLoaded(true);
        }
      };
      img.onload = onDone;
      img.onerror = onDone;
      img.src = url;
    });

    return () => {
      cancelled = true;
    };
  }, [frameUrls]);
  /* eslint-enable react-hooks/set-state-in-effect */

  return { loaded, progress };
}

const SPEED_OPTIONS = [0.5, 1, 2] as const;
const BASE_INTERVAL_MS = 500;

interface TimelapsePlayerProps {
  lakeId: string;
}

export default function TimelapsePlayer({ lakeId }: TimelapsePlayerProps) {
  const { data: timelapse, isLoading, error } = useTimelapse(lakeId);

  const frames: FrameItem[] = (timelapse?.frames ?? [])
    .slice()
    .sort((a, b) => a.frame_order - b.frame_order);

  const frameUrls = frames.map((f) => f.frame_url);
  const { loaded, progress } = usePreloadFrames(frameUrls);

  const [currentFrame, setCurrentFrame] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState<number>(1);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const frameCount = frames.length;

  const clearPlayback = useCallback(() => {
    if (intervalRef.current !== null) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  // Playback loop
  useEffect(() => {
    if (!isPlaying || !loaded || frameCount === 0) {
      clearPlayback();
      return;
    }

    intervalRef.current = setInterval(() => {
      setCurrentFrame((prev) => (prev + 1) % frameCount);
    }, BASE_INTERVAL_MS / speed);

    return clearPlayback;
  }, [isPlaying, speed, loaded, frameCount, clearPlayback]);

  const togglePlay = () => {
    if (!loaded || frameCount === 0) return;
    setIsPlaying((prev) => !prev);
  };

  const handleScrub = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = Number(e.target.value);
    setCurrentFrame(val);
    setIsPlaying(false);
  };

  const handleSpeedChange = (s: number) => {
    setSpeed(s);
  };

  // --- Render ---

  if (isLoading) {
    return (
      <div className="bg-white/5 border border-white/10 rounded-xl p-4">
        <h3 className="text-lg font-semibold text-white mb-4">Timelapse</h3>
        <div className="aspect-video bg-black rounded-xl animate-pulse" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white/5 border border-white/10 rounded-xl p-4">
        <h3 className="text-lg font-semibold text-white mb-4">Timelapse</h3>
        <div className="aspect-video bg-black rounded-xl flex items-center justify-center text-foreground/40">
          Failed to load timelapse data.
        </div>
      </div>
    );
  }

  if (frameCount === 0) {
    return (
      <div className="bg-white/5 border border-white/10 rounded-xl p-4">
        <h3 className="text-lg font-semibold text-white mb-4">Timelapse</h3>
        <div className="aspect-video bg-black rounded-xl flex items-center justify-center text-foreground/40">
          No timelapse available for this lake yet
        </div>
      </div>
    );
  }

  const currentFrameData = frames[currentFrame];

  return (
    <div className="bg-white/5 border border-white/10 rounded-xl p-4">
      <h3 className="text-lg font-semibold text-white mb-4">Timelapse</h3>

      {/* Frame display */}
      <div className="relative rounded-xl overflow-hidden aspect-video bg-black">
        {!loaded ? (
          /* Loading progress */
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3">
            <div className="w-48 h-2 bg-white/10 rounded overflow-hidden">
              <div
                className="h-full bg-blue-500 transition-all duration-200"
                style={{ width: `${Math.round(progress * 100)}%` }}
              />
            </div>
            <span className="text-sm text-foreground/60">
              Loading timelapse... {Math.round(progress * 100)}%
            </span>
          </div>
        ) : (
          <>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={currentFrameData.frame_url}
              alt={`Timelapse frame from ${currentFrameData.observation_date}`}
              className="w-full h-full object-contain"
            />
            {/* Date overlay */}
            <div className="absolute bottom-2 left-2 bg-black/60 px-2 py-1 rounded text-sm text-white font-mono">
              {currentFrameData.observation_date}
            </div>
          </>
        )}
      </div>

      {/* Controls bar */}
      {loaded && (
        <div className="flex items-center gap-3 py-3">
          {/* Play/Pause */}
          <button
            onClick={togglePlay}
            className="rounded-full bg-white/10 hover:bg-white/20 p-2 transition-colors flex-shrink-0"
            aria-label={isPlaying ? "Pause" : "Play"}
          >
            {isPlaying ? (
              <svg
                width="16"
                height="16"
                viewBox="0 0 16 16"
                fill="currentColor"
                className="text-white"
              >
                <rect x="3" y="2" width="4" height="12" rx="1" />
                <rect x="9" y="2" width="4" height="12" rx="1" />
              </svg>
            ) : (
              <svg
                width="16"
                height="16"
                viewBox="0 0 16 16"
                fill="currentColor"
                className="text-white"
              >
                <path d="M4 2l10 6-10 6V2z" />
              </svg>
            )}
          </button>

          {/* Scrub bar */}
          <input
            type="range"
            min={0}
            max={frameCount - 1}
            value={currentFrame}
            onChange={handleScrub}
            className="w-full h-2 bg-white/20 rounded appearance-none accent-blue-500"
          />

          {/* Speed selector */}
          <div className="flex gap-1 flex-shrink-0">
            {SPEED_OPTIONS.map((s) => (
              <button
                key={s}
                onClick={() => handleSpeedChange(s)}
                className={`px-2 py-1 text-xs rounded transition-colors ${
                  speed === s
                    ? "bg-blue-500 text-white"
                    : "bg-white/10 text-white/60 hover:text-white/80"
                }`}
              >
                {s}x
              </button>
            ))}
          </div>

          {/* Frame counter */}
          <span className="text-sm text-foreground/60 flex-shrink-0 tabular-nums">
            {currentFrame + 1} / {frameCount}
          </span>
        </div>
      )}
    </div>
  );
}
