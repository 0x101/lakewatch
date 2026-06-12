import { ImageResponse } from "next/og";

export const alt = "Namma Lakes Pulse — what changed at Bangalore's lakes";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";
export const revalidate = 3600;

interface PulseLakeEntry {
  lake_id: string;
  lake_name: string;
  area_change_m2: number | null;
}

interface PulseData {
  gainers: PulseLakeEntry[];
  shrinkers: PulseLakeEntry[];
  city: {
    net_change_m2: number | null;
  };
}

function signedHa(areaM2: number | null): string {
  if (areaM2 === null) return "N/A";
  const ha = areaM2 / 10000;
  const sign = ha >= 0 ? "+" : "";
  return `${sign}${ha.toFixed(1)} ha`;
}

function changeColor(areaM2: number | null): string {
  if (areaM2 === null) return "#999";
  return areaM2 >= 0 ? "#22c55e" : "#ef4444";
}

function topMover(data: PulseData): PulseLakeEntry | null {
  const all = [...data.gainers, ...data.shrinkers].filter(
    (e) => e.area_change_m2 !== null
  );
  if (all.length === 0) return null;
  return all.reduce((best, e) =>
    Math.abs(e.area_change_m2 ?? 0) > Math.abs(best.area_change_m2 ?? 0)
      ? e
      : best
  );
}

function FallbackCard() {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        width: "100%",
        height: "100%",
        background: "#0a0a0a",
        color: "white",
        padding: 60,
        fontFamily: "Inter, sans-serif",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <div style={{ fontSize: 56, fontWeight: 700, display: "flex" }}>
        Namma Lakes Pulse
      </div>
      <div
        style={{
          fontSize: 24,
          color: "#999",
          marginTop: 16,
          display: "flex",
        }}
      >
        What changed at Bangalore&apos;s lakes
      </div>
    </div>
  );
}

export default async function Image() {
  let pulse: PulseData | null = null;

  try {
    const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";
    const res = await fetch(`${backendUrl}/api/insights/pulse`, {
      next: { revalidate: 3600 },
    });
    if (res.ok) {
      pulse = await res.json();
    }
  } catch {
    // Fall through to fallback card
  }

  if (!pulse) {
    return new ImageResponse(<FallbackCard />, { ...size });
  }

  const net = pulse.city.net_change_m2;
  const mover = topMover(pulse);

  return new ImageResponse(
    (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          width: "100%",
          height: "100%",
          background: "#0a0a0a",
          color: "white",
          padding: 60,
          fontFamily: "Inter, sans-serif",
        }}
      >
        {/* Title */}
        <div style={{ display: "flex", flexDirection: "column" }}>
          <div style={{ fontSize: 56, fontWeight: 800, display: "flex" }}>
            Namma Lakes Pulse
          </div>
          <div
            style={{
              fontSize: 24,
              color: "#999",
              marginTop: 8,
              display: "flex",
            }}
          >
            What changed at Bangalore&apos;s lakes
          </div>
        </div>

        {/* City net change */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 6,
            marginTop: 56,
          }}
        >
          <div style={{ fontSize: 18, color: "#999", display: "flex" }}>
            City-wide water change vs ~1 year ago
          </div>
          <div
            style={{
              fontSize: 72,
              fontWeight: 800,
              color: changeColor(net),
              display: "flex",
            }}
          >
            {signedHa(net)}
          </div>
        </div>

        {/* Top mover */}
        {mover && (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: 4,
              marginTop: 40,
            }}
          >
            <div style={{ fontSize: 18, color: "#999", display: "flex" }}>
              Biggest mover
            </div>
            <div style={{ display: "flex", alignItems: "baseline", gap: 12 }}>
              <div
                style={{ fontSize: 36, fontWeight: 700, display: "flex" }}
              >
                {mover.lake_name}
              </div>
              <div
                style={{
                  fontSize: 30,
                  fontWeight: 700,
                  color: changeColor(mover.area_change_m2),
                  display: "flex",
                }}
              >
                {signedHa(mover.area_change_m2)}
              </div>
            </div>
          </div>
        )}

        {/* Bottom bar */}
        <div
          style={{
            display: "flex",
            flexDirection: "row",
            justifyContent: "space-between",
            marginTop: "auto",
          }}
        >
          <div style={{ fontSize: 20, color: "#666", display: "flex" }}>
            nammalakes.com/pulse
          </div>
          <div style={{ fontSize: 16, color: "#666", display: "flex" }}>
            Satellite-powered lake health tracking
          </div>
        </div>
      </div>
    ),
    { ...size }
  );
}
