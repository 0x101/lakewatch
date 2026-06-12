"use client";

import { Map, Source, Layer, type LayerProps } from "react-map-gl/mapbox";
import { MAP_STYLE } from "@/lib/constants";
import "mapbox-gl/dist/mapbox-gl.css";

interface MiniMapProps {
  boundaryGeojson: GeoJSON.Geometry;
  center: [number, number]; // [longitude, latitude]
}

const fillLayer: LayerProps = {
  id: "lake-fill",
  type: "fill",
  paint: {
    "fill-color": "#3b82f6",
    "fill-opacity": 0.4,
  },
};

const outlineLayer: LayerProps = {
  id: "lake-outline",
  type: "line",
  paint: {
    "line-color": "#3b82f6",
    "line-width": 2,
  },
};

export default function MiniMap({ boundaryGeojson, center }: MiniMapProps) {
  const featureData: GeoJSON.Feature = {
    type: "Feature",
    geometry: boundaryGeojson,
    properties: {},
  };

  return (
    <div className="rounded-xl overflow-hidden h-[250px]">
      <Map
        mapboxAccessToken={process.env.NEXT_PUBLIC_MAPBOX_TOKEN}
        initialViewState={{
          longitude: center[0],
          latitude: center[1],
          zoom: 13,
        }}
        mapStyle={MAP_STYLE}
        style={{ width: "100%", height: "100%" }}
        interactive={false}
        attributionControl={false}
      >
        <Source id="lake-boundary" type="geojson" data={featureData}>
          <Layer {...fillLayer} />
          <Layer {...outlineLayer} />
        </Source>
      </Map>
    </div>
  );
}
