import React from "react";

export default function StatCard({ title, value, unit }) {
  return (
    <div className="stat-card">
      <div className="stat-title">{title}</div>
      <div className="stat-value">
        {value != null ? value.toLocaleString() : "—"}
      </div>
      {unit && <div className="stat-unit">{unit}</div>}
    </div>
  );
}
