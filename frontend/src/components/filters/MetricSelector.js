import React from "react";

const METRICS = [
  { value: "temperature", label: "Temperature" },
  { value: "humidity", label: "Humidity" },
  { value: "wind_speed", label: "Wind Speed" },
  { value: "visibility", label: "Visibility" },
  { value: "pressure", label: "Pressure" },
];

export default function MetricSelector({ value, onChange }) {
  return (
    <div className="metric-selector">
      <label>Metric: </label>
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        {METRICS.map((m) => (
          <option key={m.value} value={m.value}>{m.label}</option>
        ))}
      </select>
    </div>
  );
}
