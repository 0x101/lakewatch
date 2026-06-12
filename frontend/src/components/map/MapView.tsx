"use client";

import { useState, useCallback, useEffect, useMemo } from "react";
import {
  Map,
  Source,
  Layer,
  NavigationControl,
  useMap,
  type MapMouseEvent,
  type LayerProps,
} from "react-map-gl/mapbox";
import { useTheme } from "next-themes";
import { useLakesGeoJSON } from "@/hooks/useLakes";
// Stream overlay is a Bangalore city extension (via useStreams -> api-ext).
// In the public build the api-ext stub returns no streams, so the guarded
// {streamsGeojson && (...)} layer below simply renders nothing — no overlay.
import { useStreamsGeoJSON } from "@/hooks/useStreams";
import {
  MAP_CENTER,
  DEFAULT_ZOOM,
  MAP_STYLE,
  MAP_STYLE_LIGHT,
  HEALTH_SCALE,
} from "@/lib/constants";
import { useUIStore } from "@/lib/store";
import { enrichGeoJSON, getDisplayName } from "@/lib/lake-enrichment";
import { LakePopup } from "./LakePopup";
import { MapLegend } from "./MapLegend";

interface PopupData {
  longitude: number;
  latitude: number;
  name: string;
  healthScore: number;
  areaChange5yr: number | null;
  lakeId: string;
  latestWaterArea: number | null;
}

const healthColorExpr = [
  "interpolate",
  ["linear"],
  ["coalesce", ["get", "health_score"], 0],
  ...HEALTH_SCALE.flatMap((s) => [s.stop, s.color]),
];

const streamsLayer: LayerProps = {
  id: "streams-line",
  type: "line",
  paint: {
    "line-color": "#60a5fa",
    "line-width": 1,
    "line-opacity": 0.35,
    "line-dasharray": [3, 2],
  },
};

const highlightLayer: LayerProps = {
  id: "lakes-highlight",
  type: "line",
  paint: {
    "line-color": "#ffffff",
    "line-width": 3,
    "line-opacity": 0.9,
  },
};

// ---------------------------------------------------------------------------
// FlyTo controller — child of Map, uses useMap() hook
// ---------------------------------------------------------------------------

function FlyToController() {
  const { "main-map": mapRef } = useMap();
  const mapFlyTo = useUIStore((s) => s.mapFlyTo);
  const setMapFlyTo = useUIStore((s) => s.setMapFlyTo);

  useEffect(() => {
    if (mapFlyTo && mapRef) {
      mapRef.flyTo({
        center: [mapFlyTo.lng, mapFlyTo.lat],
        zoom: mapFlyTo.zoom,
        duration: 1500,
      });
      setMapFlyTo(null);
    }
  }, [mapFlyTo, mapRef, setMapFlyTo]);

  return null;
}

// ---------------------------------------------------------------------------
// Main MapView
// ---------------------------------------------------------------------------

export default function MapView() {
  const { data: geojson, isLoading } = useLakesGeoJSON();
  const { data: streamsGeojson } = useStreamsGeoJSON();
  const { resolvedTheme } = useTheme();
  const [popupInfo, setPopupInfo] = useState<PopupData | null>(null);
  const [cursor, setCursor] = useState<string>("grab");

  const setMobileSidebarOpen = useUIStore((s) => s.setMobileSidebarOpen);
  const highlightedLakeId = useUIStore((s) => s.highlightedLakeId);
  const setHighlightedLakeId = useUIStore((s) => s.setHighlightedLakeId);
  const mapFlyTo = useUIStore((s) => s.mapFlyTo);
  const activeZones = useUIStore((s) => s.activeZones);
  const activeTiers = useUIStore((s) => s.activeTiers);

  const mapStyle = resolvedTheme === "light" ? MAP_STYLE_LIGHT : MAP_STYLE;

  // Enrich GeoJSON with zone/tier/display_name
  const enrichedGeojson = useMemo(() => {
    if (!geojson) return null;
    return enrichGeoJSON(geojson);
  }, [geojson]);

  // Derive popup from highlighted lake (no effect needed — computed inline)
  const pendingPopup = useMemo<PopupData | null>(() => {
    if (!highlightedLakeId || !mapFlyTo || !enrichedGeojson) return null;
    const feature = enrichedGeojson.features.find(
      (f) => (f.properties?.id ?? f.id) === highlightedLakeId
    );
    if (!feature?.properties) return null;
    const props = feature.properties;
    return {
      longitude: mapFlyTo.lng,
      latitude: mapFlyTo.lat,
      name: props.display_name ?? props.name ?? "Unknown Lake",
      healthScore: props.health_score ?? 0,
      areaChange5yr: props.area_change_5yr_pct ?? null,
      lakeId: props.id ?? "",
      latestWaterArea: props.latest_water_area_m2 ?? null,
    };
  }, [highlightedLakeId, mapFlyTo, enrichedGeojson]);

  // Dynamic opacity for zone/tier filtering
  const hasFilters = activeZones.length > 0 || activeTiers.length > 0;

  const filterMatchExpr = useMemo(() => {
    if (!hasFilters) return null;
    if (activeZones.length > 0 && activeTiers.length > 0) {
      return [
        "all",
        ["in", ["get", "zone"], ["literal", activeZones]],
        ["in", ["get", "tier"], ["literal", activeTiers]],
      ];
    }
    if (activeZones.length > 0) {
      return ["in", ["get", "zone"], ["literal", activeZones]];
    }
    return ["in", ["get", "tier"], ["literal", activeTiers]];
  }, [hasFilters, activeZones, activeTiers]);

  const fillOpacity = useMemo(() => {
    if (!filterMatchExpr) return 0.7;
    return ["case", filterMatchExpr, 0.7, 0.1];
  }, [filterMatchExpr]);

  const outlineOpacity = useMemo(() => {
    if (!filterMatchExpr) return 0.8;
    return ["case", filterMatchExpr, 0.8, 0.1];
  }, [filterMatchExpr]);

  const lakesFillLayer: LayerProps = useMemo(
    () => ({
      id: "lakes-fill",
      type: "fill",
      paint: {
        "fill-color": healthColorExpr as unknown as string,
        "fill-opacity": fillOpacity as unknown as number,
      },
    }),
    [fillOpacity]
  );

  const lakesOutlineLayer: LayerProps = useMemo(
    () => ({
      id: "lakes-outline",
      type: "line",
      paint: {
        "line-color": healthColorExpr as unknown as string,
        "line-width": 1.5,
        "line-opacity": outlineOpacity as unknown as number,
      },
    }),
    [outlineOpacity]
  );

  const highlightFilter = useMemo(
    () =>
      highlightedLakeId
        ? (["==", ["get", "id"], highlightedLakeId] as unknown as undefined)
        : (["==", ["get", "id"], ""] as unknown as undefined),
    [highlightedLakeId]
  );

  const onClick = useCallback(
    (event: MapMouseEvent) => {
      setMobileSidebarOpen(false);

      const feature = event.features?.[0];
      if (feature && feature.layer?.id === "lakes-fill") {
        const props = feature.properties;
        const displayName = getDisplayName(
          props?.id ?? "",
          props?.name ?? "Unknown Lake"
        );
        setPopupInfo({
          longitude: event.lngLat.lng,
          latitude: event.lngLat.lat,
          name: displayName,
          healthScore: props?.health_score ?? 0,
          areaChange5yr: props?.area_change_5yr_pct ?? null,
          lakeId: props?.id ?? "",
          latestWaterArea: props?.latest_water_area_m2 ?? null,
        });
        setHighlightedLakeId(null);
      } else {
        setPopupInfo(null);
        setHighlightedLakeId(null);
      }
    },
    [setMobileSidebarOpen, setHighlightedLakeId]
  );

  const onMouseEnter = useCallback(() => setCursor("pointer"), []);
  const onMouseLeave = useCallback(() => setCursor("grab"), []);

  return (
    <div className="relative w-full h-screen">
      <Map
        id="main-map"
        mapboxAccessToken={process.env.NEXT_PUBLIC_MAPBOX_TOKEN}
        initialViewState={{
          longitude: MAP_CENTER.longitude,
          latitude: MAP_CENTER.latitude,
          zoom: DEFAULT_ZOOM,
        }}
        mapStyle={mapStyle}
        style={{ width: "100%", height: "100%" }}
        interactiveLayerIds={["lakes-fill"]}
        onClick={onClick}
        onMouseEnter={onMouseEnter}
        onMouseLeave={onMouseLeave}
        cursor={cursor}
      >
        <NavigationControl position="top-right" />
        <FlyToController />

        {streamsGeojson && (
          <Source id="streams" type="geojson" data={streamsGeojson}>
            <Layer {...streamsLayer} />
          </Source>
        )}

        {enrichedGeojson && (
          <Source id="lakes" type="geojson" data={enrichedGeojson}>
            <Layer {...lakesFillLayer} />
            <Layer {...lakesOutlineLayer} />
            <Layer {...highlightLayer} filter={highlightFilter} />
          </Source>
        )}

        {(() => {
          const popup = popupInfo ?? pendingPopup;
          if (!popup) return null;
          return (
            <LakePopup
              longitude={popup.longitude}
              latitude={popup.latitude}
              name={popup.name}
              healthScore={popup.healthScore}
              areaChange5yr={popup.areaChange5yr}
              latestWaterArea={popup.latestWaterArea}
              lakeId={popup.lakeId}
              onClose={() => {
                setPopupInfo(null);
                setHighlightedLakeId(null);
              }}
            />
          );
        })()}
      </Map>

      <MapLegend />

      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="bg-gray-900/80 backdrop-blur-sm rounded-lg px-4 py-2 text-sm text-white/70">
            Loading lake data...
          </div>
        </div>
      )}
    </div>
  );
}
