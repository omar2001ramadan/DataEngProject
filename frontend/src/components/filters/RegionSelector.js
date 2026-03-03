import React from "react";

export default function RegionSelector({ value, onChange }) {
  return (
    <div className="region-selector">
      <label>Region: </label>
      <button
        className={value === "CISO" ? "active" : ""}
        onClick={() => onChange("CISO")}
      >
        California (CISO)
      </button>
      <button
        className={value === "ERCO" ? "active" : ""}
        onClick={() => onChange("ERCO")}
      >
        Texas (ERCO)
      </button>
    </div>
  );
}
