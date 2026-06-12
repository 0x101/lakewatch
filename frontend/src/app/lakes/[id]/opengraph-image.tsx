import { ImageResponse } from "next/og";

export const alt = "Lake health card";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";
export const revalidate = 3600;

interface LakeData {
  id: string;
  name: string;
  health_score: number | null;
  latest_water_area_m2: number | null;
  area_change_1yr_pct: number | null;
  area_change_5yr_pct: number | null;
  mean_algae_fraction: number | null;
  observation_count: number;
  ward: string | null;
}

function getHealthColor(score: number): string {
  if (score >= 80) return "#00897b";
  if (score >= 60) return "#f9a825";
  if (score >= 30) return "#ef6c00";
  return "#c62828";
}

function formatChange(pct: number | null): string {
  if (pct === null) return "N/A";
  const sign = pct >= 0 ? "+" : "";
  return `${sign}${pct.toFixed(1)}%`;
}

function changeColor(pct: number | null): string {
  if (pct === null) return "#999";
  return pct >= 0 ? "#22c55e" : "#ef4444";
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
        Namma Lakes
      </div>
      <div
        style={{
          fontSize: 24,
          color: "#999",
          marginTop: 16,
          display: "flex",
        }}
      >
        Satellite-powered lake health tracking
      </div>
    </div>
  );
}

export default async function Image({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  let lake: LakeData | null = null;

  try {
    const backendUrl =
      process.env.BACKEND_URL || "http://localhost:8000";
    const res = await fetch(
      `${backendUrl}/api/lakes/${encodeURIComponent(id)}`,
      { next: { revalidate: 3600 } }
    );
    if (res.ok) {
      lake = await res.json();
    }
  } catch {
    // Fall through to fallback card
  }

  if (!lake) {
    return new ImageResponse(<FallbackCard />, { ...size });
  }

  const healthScore =
    lake.health_score !== null ? Math.round(lake.health_score) : null;
  const waterAreaHa =
    lake.latest_water_area_m2 !== null
      ? (lake.latest_water_area_m2 / 10000).toFixed(1)
      : "N/A";
  const algaePct =
    lake.mean_algae_fraction !== null
      ? `${(lake.mean_algae_fraction * 100).toFixed(0)}%`
      : "N/A";

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
        {/* Top section */}
        <div
          style={{
            display: "flex",
            flexDirection: "row",
            justifyContent: "space-between",
            alignItems: "flex-start",
          }}
        >
          {/* Left: Lake name + ward */}
          <div style={{ display: "flex", flexDirection: "column", flex: 1 }}>
            <div
              style={{
                fontSize: 48,
                fontWeight: 700,
                display: "flex",
                lineClamp: 2,
              }}
            >
              {lake.name}
            </div>
            {lake.ward && (
              <div
                style={{ fontSize: 24, color: "#999", marginTop: 8, display: "flex" }}
              >
                {lake.ward}
              </div>
            )}
          </div>

          {/* Right: Health score */}
          {healthScore !== null && (
            <div style={{ display: "flex", alignItems: "baseline" }}>
              <div
                style={{
                  fontSize: 72,
                  fontWeight: 800,
                  color: getHealthColor(healthScore),
                  display: "flex",
                }}
              >
                {healthScore}
              </div>
              <div
                style={{
                  fontSize: 28,
                  color: "#999",
                  marginLeft: 4,
                  display: "flex",
                }}
              >
                /100
              </div>
            </div>
          )}
        </div>

        {/* Middle section: stat boxes */}
        <div
          style={{
            display: "flex",
            flexDirection: "row",
            gap: 40,
            marginTop: 40,
          }}
        >
          {/* Water Area */}
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <div style={{ fontSize: 16, color: "#999", display: "flex" }}>
              Water Area
            </div>
            <div style={{ display: "flex", alignItems: "baseline" }}>
              <div
                style={{ fontSize: 32, fontWeight: 600, display: "flex" }}
              >
                {waterAreaHa}
              </div>
              {waterAreaHa !== "N/A" && (
                <div
                  style={{
                    fontSize: 18,
                    color: "#999",
                    marginLeft: 6,
                    display: "flex",
                  }}
                >
                  ha
                </div>
              )}
            </div>
          </div>

          {/* 5yr Change */}
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <div style={{ fontSize: 16, color: "#999", display: "flex" }}>
              5yr Change
            </div>
            <div
              style={{
                fontSize: 32,
                fontWeight: 600,
                color: changeColor(lake.area_change_5yr_pct),
                display: "flex",
              }}
            >
              {formatChange(lake.area_change_5yr_pct)}
            </div>
          </div>

          {/* Algae Level */}
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <div style={{ fontSize: 16, color: "#999", display: "flex" }}>
              Algae Level
            </div>
            <div
              style={{ fontSize: 32, fontWeight: 600, display: "flex" }}
            >
              {algaePct}
            </div>
          </div>

          {/* Observations */}
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <div style={{ fontSize: 16, color: "#999", display: "flex" }}>
              Observations
            </div>
            <div
              style={{ fontSize: 32, fontWeight: 600, display: "flex" }}
            >
              {lake.observation_count}
            </div>
          </div>
        </div>

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
            Namma Lakes
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
