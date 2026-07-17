"use client";

import Link from "next/link";
import { usePulse } from "@/hooks/useInsights";
import { ThemeToggle } from "@/components/ui/ThemeToggle";
import CopyButton from "@/components/pulse/CopyButton";
import { formatSignedHa, formatRelatableArea } from "@/lib/relatable";
import { getDisplayName } from "@/lib/lake-enrichment";
import { ATTRIBUTION, CITY, DOMAIN } from "@/lib/city.config";
import type { PulseLakeEntry } from "@/lib/types";

const SITE = DOMAIN;

function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`bg-white/5 rounded-xl animate-pulse ${className}`} />;
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

/** "+4.2 ha — ≈ 6 ⚽ football fields" (relatable suffix only when available). */
function changeLine(areaM2: number | null): string {
  if (areaM2 === null) return "—";
  const signed = formatSignedHa(areaM2);
  const relatable = formatRelatableArea(areaM2);
  return relatable ? `${signed} — ${relatable}` : signed;
}

function trendArrow(trend: number | null): string {
  if (trend === null) return "–";
  if (trend > 0) return "▲";
  if (trend < 0) return "▼";
  return "–";
}

/* ── Mover card (gainers + shrinkers) ──────────────────── */

function moverSnippet(lake: PulseLakeEntry): string {
  const name = getDisplayName(lake.lake_id, lake.lake_name);
  const change = lake.area_change_m2 ?? 0;
  const verb = change >= 0 ? "gained" : "lost";
  const ha = Math.abs(change / 10000).toFixed(1);
  const relatable = formatRelatableArea(change);
  const tail = relatable ? ` — about ${relatable.replace(/^≈\s*/, "")}` : "";
  return `${name} ${verb} ${ha} ha of water recently${tail}. Tracked from space by ${SITE}/lakes/${lake.lake_id} 🛰️`;
}

function MoverCard({ lake }: { lake: PulseLakeEntry }) {
  const name = getDisplayName(lake.lake_id, lake.lake_name);
  const positive = (lake.area_change_m2 ?? 0) >= 0;
  return (
    <div className="bg-white/5 border border-white/10 rounded-xl p-4 flex flex-col gap-2">
      <div className="flex items-start justify-between gap-3">
        <Link
          href={`/lakes/${lake.lake_id}`}
          className="font-medium text-white hover:underline"
        >
          {name}
        </Link>
        <CopyButton text={moverSnippet(lake)} />
      </div>
      <p
        className={`text-sm font-mono ${positive ? "text-green-400" : "text-red-400"}`}
      >
        {changeLine(lake.area_change_m2)}
      </p>
      {lake.area_change_pct !== null && (
        <p className="text-xs text-foreground/40">
          {positive ? "+" : ""}
          {lake.area_change_pct.toFixed(1)}% vs the previous reading
        </p>
      )}
    </div>
  );
}

/* ── Algae watch card ──────────────────────────────────── */

function algaeSnippet(lake: PulseLakeEntry): string {
  const name = getDisplayName(lake.lake_id, lake.lake_name);
  const pct = ((lake.algae_fraction ?? 0) * 100).toFixed(0);
  const trend = lake.algae_trend;
  const dir =
    trend === null || trend === 0
      ? "holding steady"
      : trend > 0
        ? "rising"
        : "easing";
  return `${name}'s algae cover is now ${pct}% (${dir}). Tracked from space by ${SITE}/lakes/${lake.lake_id} 🛰️`;
}

function AlgaeCard({ lake }: { lake: PulseLakeEntry }) {
  const name = getDisplayName(lake.lake_id, lake.lake_name);
  const pct = ((lake.algae_fraction ?? 0) * 100).toFixed(0);
  const arrow = trendArrow(lake.algae_trend);
  const arrowColor =
    lake.algae_trend === null || lake.algae_trend === 0
      ? "text-foreground/40"
      : lake.algae_trend > 0
        ? "text-red-400"
        : "text-green-400";
  return (
    <div className="bg-white/5 border border-white/10 rounded-xl p-4 flex flex-col gap-2">
      <div className="flex items-start justify-between gap-3">
        <Link
          href={`/lakes/${lake.lake_id}`}
          className="font-medium text-white hover:underline"
        >
          {name}
        </Link>
        <CopyButton text={algaeSnippet(lake)} />
      </div>
      <p className="text-sm font-mono text-white">
        {pct}% algae cover{" "}
        <span className={arrowColor}>{arrow}</span>
      </p>
      <p className="text-xs text-foreground/40">
        Share of the water surface reading as algae in the latest pass.
      </p>
    </div>
  );
}

/* ── Section wrapper ───────────────────────────────────── */

function Section({
  title,
  emoji,
  blurb,
  children,
  empty,
}: {
  title: string;
  emoji: string;
  blurb: string;
  children: React.ReactNode;
  empty: boolean;
}) {
  return (
    <section className="space-y-3">
      <div>
        <h2 className="text-lg font-semibold text-white">
          {emoji} {title}
        </h2>
        <p className="text-xs text-foreground/40">{blurb}</p>
      </div>
      {empty ? (
        <p className="text-sm text-foreground/30 bg-white/5 border border-white/10 rounded-xl p-4">
          No lakes to show here right now.
        </p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {children}
        </div>
      )}
    </section>
  );
}

/* ── Main ──────────────────────────────────────────────── */

export default function PulseClient() {
  const { data, isLoading } = usePulse();

  return (
    <div className="max-w-7xl mx-auto p-4 md:p-8 space-y-8">
      {/* Header */}
      <div>
        <Link
          href="/"
          className="text-sm text-foreground/50 hover:text-foreground/80 mb-2 inline-block"
        >
          &larr; Back to map
        </Link>
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold text-white">
            What changed at {CITY}&apos;s lakes
          </h1>
          <ThemeToggle />
        </div>
      </div>

      {/* Hero */}
      {isLoading || !data ? (
        <Skeleton className="h-40" />
      ) : (
        <div className="bg-white/5 border border-white/10 rounded-xl p-6 space-y-3">
          <p className="text-xs uppercase tracking-wider text-foreground/40">
            Latest reading: {formatDate(data.as_of)}
          </p>
          {data.city.net_change_m2 !== null ? (
            <>
              <p
                className={`text-4xl font-bold ${data.city.net_change_m2 >= 0 ? "text-green-400" : "text-red-400"}`}
              >
                {formatSignedHa(data.city.net_change_m2)}
              </p>
              <p className="text-sm text-foreground/60">
                City-wide water change vs about a year ago
                {formatRelatableArea(data.city.net_change_m2) && (
                  <> — {formatRelatableArea(data.city.net_change_m2)}</>
                )}
                .
              </p>
              <div className="pt-1">
                <CopyButton
                  label="Share this"
                  text={`${CITY}'s lakes are ${data.city.net_change_m2 >= 0 ? "up" : "down"} ${formatSignedHa(data.city.net_change_m2)} of water vs a year ago${
                    formatRelatableArea(data.city.net_change_m2)
                      ? ` — about ${formatRelatableArea(data.city.net_change_m2)!.replace(/^≈\s*/, "")}`
                      : ""
                  }. Tracked from space by ${SITE}/pulse 🛰️`}
                />
              </div>
            </>
          ) : (
            <p className="text-sm text-foreground/50">
              Not enough matched history yet for a city-wide year-over-year
              number. The movers below still show what shifted recently.
            </p>
          )}
        </div>
      )}

      {/* Sections */}
      {isLoading || !data ? (
        <div className="space-y-6">
          <Skeleton className="h-48" />
          <Skeleton className="h-48" />
        </div>
      ) : (
        <>
          <Section
            title="Gainers"
            emoji="📈"
            blurb="Lakes that grew the most since their previous reading."
            empty={data.gainers.length === 0}
          >
            {data.gainers.map((l) => (
              <MoverCard key={l.lake_id} lake={l} />
            ))}
          </Section>

          <Section
            title="Shrinkers"
            emoji="📉"
            blurb="Lakes that lost the most water since their previous reading."
            empty={data.shrinkers.length === 0}
          >
            {data.shrinkers.map((l) => (
              <MoverCard key={l.lake_id} lake={l} />
            ))}
          </Section>

          <Section
            title="Algae watch"
            emoji="🟢"
            blurb="Lakes with the highest algae cover in the latest pass."
            empty={data.algae_watch.length === 0}
          >
            {data.algae_watch.map((l) => (
              <AlgaeCard key={l.lake_id} lake={l} />
            ))}
          </Section>
        </>
      )}

      {/* Footer */}
      <div className="border-t border-white/10 pt-4 text-xs text-foreground/30 space-y-1">
        {ATTRIBUTION.map((line) => (
          <p key={line}>{line}</p>
        ))}
        <p>Satellite-derived estimates, not ground truth.</p>
      </div>
    </div>
  );
}
