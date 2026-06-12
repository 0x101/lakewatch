import type { Metadata } from "next";
import LakeDetailClient from "./LakeDetailClient";

type Props = {
  params: Promise<{ id: string }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;

  try {
    const backendUrl =
      process.env.BACKEND_URL || "http://localhost:8000";
    const res = await fetch(
      `${backendUrl}/api/lakes/${encodeURIComponent(id)}`,
      { next: { revalidate: 300 } }
    );

    if (!res.ok) {
      return { title: `Lake - Namma Lakes` };
    }

    const lake = await res.json();
    const healthLabel =
      lake.health_score !== null
        ? `Health: ${Math.round(lake.health_score)}/100`
        : "";
    const areaLabel =
      lake.area_change_5yr_pct !== null
        ? `5yr change: ${lake.area_change_5yr_pct >= 0 ? "+" : ""}${lake.area_change_5yr_pct.toFixed(1)}%`
        : "";

    const description = [
      `Satellite-tracked health data for ${lake.name}.`,
      healthLabel,
      areaLabel,
      `${lake.observation_count} observations from Sentinel-2.`,
    ]
      .filter(Boolean)
      .join(" ");

    return {
      title: `${lake.name} - Namma Lakes`,
      description,
      openGraph: {
        title: `${lake.name} - Namma Lakes`,
        description,
      },
    };
  } catch {
    return { title: `Lake - Namma Lakes` };
  }
}

export default async function LakeDetailPage({ params }: Props) {
  const { id } = await params;

  return <LakeDetailClient lakeId={id} />;
}
