import React from "react";

export default function DateRangePicker({ startDate, endDate, onStartChange, onEndChange }) {
  return (
    <div className="date-range-picker">
      <label>From: </label>
      <input type="date" value={startDate} onChange={(e) => onStartChange(e.target.value)} />
      <label> To: </label>
      <input type="date" value={endDate} onChange={(e) => onEndChange(e.target.value)} />
    </div>
  );
}
