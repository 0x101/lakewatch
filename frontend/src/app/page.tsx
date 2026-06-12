"use client";

import dynamic from "next/dynamic";

const MapView = dynamic(() => import("@/components/map/MapView"), {
  ssr: false,
  loading: () => (
    <div className="h-screen w-full bg-gray-900 animate-pulse" />
  ),
});

const MapSidebar = dynamic(
  () =>
    import("@/components/map/MapSidebar").then((mod) => mod.MapSidebar),
  {
    ssr: false,
    loading: () => null,
  }
);

const MapSearchBar = dynamic(
  () =>
    import("@/components/map/MapSearchBar").then((mod) => mod.MapSearchBar),
  {
    ssr: false,
    loading: () => null,
  }
);

export default function HomePage() {
  return (
    <div className="relative w-full h-screen">
      <MapView />
      <MapSearchBar />
      <MapSidebar />
    </div>
  );
}
