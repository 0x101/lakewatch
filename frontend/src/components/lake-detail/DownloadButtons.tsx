"use client";

import type { AssetItem } from "@/lib/types";

interface DownloadButtonsProps {
  assets: AssetItem[];
}

function formatFileSize(bytes: number | null): string {
  if (bytes === null) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function findAsset(
  assets: AssetItem[],
  preferred: string,
  fallback: string
): AssetItem | undefined {
  return (
    assets.find((a) => a.asset_type === preferred) ??
    assets.find((a) => a.asset_type === fallback)
  );
}

function DownloadIcon() {
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
      <path d="M8 2v9M4 8l4 4 4-4M2 14h12" />
    </svg>
  );
}

export default function DownloadButtons({ assets }: DownloadButtonsProps) {
  const gif = findAsset(assets, "gif_share", "gif_full");
  const video = findAsset(assets, "video_share", "video_full");

  if (!gif && !video) return null;

  return (
    <div className="flex flex-wrap gap-3">
      {gif && (
        <a
          href={gif.url}
          download
          className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-medium px-4 py-2 rounded-lg transition-colors"
        >
          <DownloadIcon />
          Download GIF
          {gif.file_size_bytes !== null && (
            <span className="text-white/70 text-sm">
              ({formatFileSize(gif.file_size_bytes)})
            </span>
          )}
        </a>
      )}
      {video && (
        <a
          href={video.url}
          download
          className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-medium px-4 py-2 rounded-lg transition-colors"
        >
          <DownloadIcon />
          Download Video
          {video.file_size_bytes !== null && (
            <span className="text-white/70 text-sm">
              ({formatFileSize(video.file_size_bytes)})
            </span>
          )}
        </a>
      )}
    </div>
  );
}
