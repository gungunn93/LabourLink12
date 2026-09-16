import React from "react";
import { MapContainer, TileLayer, Marker, Popup, Circle } from "react-leaflet";
import L from "leaflet";

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png",
  iconUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png",
  shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
});

export default function MapView({ lat, lng, items = [], worker, height = 280 }) {
  const center = worker?.latitude != null ? [worker.latitude, worker.longitude] : [lat, lng];
  return (
    <div className="map-wrap" style={{ height }}>
      <MapContainer center={center} zoom={13} style={{ height: "100%", width: "100%" }}>
        <TileLayer attribution="&copy; OpenStreetMap contributors" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
        {lat != null && lng != null && <Marker position={[lat, lng]}>
          <Popup>Job location</Popup>
        </Marker>}
        {worker?.latitude && (
          <>
            <Marker position={[worker.latitude, worker.longitude]}>
              <Popup>Worker last location</Popup>
            </Marker>
            {worker.accuracy ? <Circle center={[worker.latitude, worker.longitude]} radius={worker.accuracy} /> : null}
          </>
        )}
        {items.filter((x) => x.latitude && x.longitude).map((x) => (
          <Marker key={x.id} position={[x.latitude, x.longitude]}>
            <Popup>{x.title}</Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
}
