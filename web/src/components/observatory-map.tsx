"use client";

import { MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import type { Observatory } from "@/lib/api";

function colorForScore(score: number): string {
  if (score >= 80) return "#10b981"; // emerald
  if (score >= 60) return "#38bdf8"; // sky
  if (score >= 40) return "#f59e0b"; // amber
  return "#f43f5e"; // rose
}

export default function ObservatoryMap({ data }: { data: Observatory[] }) {
  const points = data.filter(
    (o) => o.latitude != null && o.longitude != null
  );
  return (
    <MapContainer
      center={[20, 0]}
      zoom={2}
      minZoom={2}
      className="h-[70vh] w-full rounded-xl"
      worldCopyJump
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {points.map((o) => (
        <CircleMarker
          key={o.id}
          center={[o.latitude, o.longitude]}
          radius={5}
          pathOptions={{
            color: colorForScore(o.observation_score),
            fillColor: colorForScore(o.observation_score),
            fillOpacity: 0.7,
            weight: 1,
          }}
        >
          <Popup>
            <div className="text-sm">
              <div className="font-semibold">
                {o.observatory.replace(/^\d+\s+/, "")}
              </div>
              <div>{o.country ?? "—"}</div>
              <div>
                Score:{" "}
                <span className="font-medium">
                  {o.observation_score.toFixed(0)}
                </span>
              </div>
              {o.cloud_cover_pct != null && (
                <div>Cloud: {o.cloud_cover_pct}%</div>
              )}
            </div>
          </Popup>
        </CircleMarker>
      ))}
    </MapContainer>
  );
}
