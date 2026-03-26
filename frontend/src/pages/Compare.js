import React, { useState, useEffect, useRef, useMemo } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend, Brush
} from "recharts";
import { fetchSolarComparison } from "../api/client";

export default function Compare() {
  const [allData, setAllData] = useState([]);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [brushKey, setBrushKey] = useState(0);
  const [loading, setLoading] = useState(true);
  const [normalize, setNormalize] = useState(false);
  const brushRef = useRef({ startIndex: 0, endIndex: 0 });

  useEffect(() => {
    setLoading(true);
    fetchSolarComparison({})
      .then((d) => {
        const mapped = d.map((r) => ({ ...r, label: r.month.slice(0, 7) }));
        setAllData(mapped);
        if (mapped.length > 0) {
          setStartDate(mapped[0].label);
          setEndDate(mapped[mapped.length - 1].label);
          brushRef.current = { startIndex: 0, endIndex: mapped.length - 1 };
        }
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const handleBrushChange = (range) => {
    if (range && allData.length > 0) {
      brushRef.current = range;
      setStartDate(allData[range.startIndex].label);
      setEndDate(allData[range.endIndex].label);
    }
  };

  const handleStartDateChange = (val) => {
    setStartDate(val);
    const idx = allData.findIndex((d) => d.label >= val);
    if (idx >= 0) {
      brushRef.current = { ...brushRef.current, startIndex: idx };
      setBrushKey((k) => k + 1);
    }
  };

  const handleEndDateChange = (val) => {
    setEndDate(val);
    let idx = allData.length - 1;
    for (let i = allData.length - 1; i >= 0; i--) {
      if (allData[i].label <= val) { idx = i; break; }
    }
    brushRef.current = { ...brushRef.current, endIndex: idx };
    setBrushKey((k) => k + 1);
  };

  const visibleData = useMemo(() => {
    return allData.slice(brushRef.current.startIndex, brushRef.current.endIndex + 1);
  }, [allData, startDate, endDate]);

  // Check if capacity data is available for the normalize toggle
  const hasCapacity = allData.some(
    (r) => r.ciso_capacity_factor_pct != null || r.erco_capacity_factor_pct != null
  );

  // Pick which data keys to chart based on normalize toggle
  const cisoKey = normalize ? "ciso_capacity_factor_pct" : "ciso_total_mwh";
  const ercoKey = normalize ? "erco_capacity_factor_pct" : "erco_total_mwh";
  const yLabel = normalize ? "Capacity Factor (%)" : "MWh";

  if (loading) return <div className="loading">Loading comparison data...</div>;

  const cisoTotal = visibleData.reduce((s, r) => s + (r.ciso_total_mwh || 0), 0);
  const ercoTotal = visibleData.reduce((s, r) => s + (r.erco_total_mwh || 0), 0);
  const cisoAvgCF = visibleData.filter((r) => r.ciso_capacity_factor_pct != null);
  const ercoAvgCF = visibleData.filter((r) => r.erco_capacity_factor_pct != null);

  return (
    <div className="page">
      <h1>Region Comparison</h1>
      <div className="filters">
        <div className="date-range-picker">
          <label>From</label>
          <input type="text" value={startDate} placeholder="YYYY-MM" size="8" onChange={(e) => handleStartDateChange(e.target.value)} />
          <label>To</label>
          <input type="text" value={endDate} placeholder="YYYY-MM" size="8" onChange={(e) => handleEndDateChange(e.target.value)} />
        </div>
        {hasCapacity && (
          <div className="region-selector">
            <label>View</label>
            <button className={!normalize ? "active" : ""} onClick={() => setNormalize(false)}>Raw MWh</button>
            <button className={normalize ? "active" : ""} onClick={() => setNormalize(true)}>Normalize by Capacity</button>
          </div>
        )}
      </div>

      <h2>
        {normalize
          ? "Monthly Capacity Factor - CISO vs ERCO"
          : "Monthly Generation - CISO vs ERCO"}
      </h2>
      <ResponsiveContainer width="100%" height={400}>
        <BarChart data={allData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="label" />
          <YAxis label={{ value: yLabel, angle: -90, position: "insideLeft", style: { fill: "#94a3b8" } }} />
          <Tooltip
            formatter={(value, name) =>
              normalize
                ? [`${value != null ? value.toFixed(2) : "N/A"}%`, name]
                : [`${value != null ? value.toLocaleString() : "N/A"} MWh`, name]
            }
          />
          <Legend />
          <Bar dataKey={cisoKey} fill="#f59e0b" name="California (CISO)" />
          <Bar dataKey={ercoKey} fill="#3b82f6" name="Texas (ERCO)" />
          <Brush
            key={brushKey}
            dataKey="label" height={30} stroke="#8884d8"
            startIndex={brushRef.current.startIndex}
            endIndex={brushRef.current.endIndex}
            onChange={handleBrushChange}
          />
        </BarChart>
      </ResponsiveContainer>

      {normalize && (
        <p className="hint">Capacity values are sourced from EIA Form 860M (monthly estimates) and may not reflect actual installed capacity, particularly during periods of rapid solar expansion.</p>
      )}

      <h2>Summary</h2>
      <table className="summary-table">
        <thead>
          <tr>
            <th>Metric</th>
            <th>California (CISO)</th>
            <th>Texas (ERCO)</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Total Generation</td>
            <td>{cisoTotal.toLocaleString()} MWh</td>
            <td>{ercoTotal.toLocaleString()} MWh</td>
          </tr>
          <tr>
            <td>Avg Monthly</td>
            <td>{visibleData.length ? Math.round(cisoTotal / visibleData.length).toLocaleString() : "-"} MWh</td>
            <td>{visibleData.length ? Math.round(ercoTotal / visibleData.length).toLocaleString() : "-"} MWh</td>
          </tr>
          <tr>
            <td>Peak Month</td>
            <td>
              {visibleData.length
                ? visibleData.reduce((best, r) => (r.ciso_total_mwh || 0) > (best.ciso_total_mwh || 0) ? r : best, visibleData[0]).label
                : "-"}
            </td>
            <td>
              {visibleData.length
                ? visibleData.reduce((best, r) => (r.erco_total_mwh || 0) > (best.erco_total_mwh || 0) ? r : best, visibleData[0]).label
                : "-"}
            </td>
          </tr>
          {hasCapacity && (
            <tr>
              <td>Avg Capacity Factor</td>
              <td>
                {cisoAvgCF.length
                  ? (cisoAvgCF.reduce((s, r) => s + r.ciso_capacity_factor_pct, 0) / cisoAvgCF.length).toFixed(2) + "%"
                  : "N/A"}
              </td>
              <td>
                {ercoAvgCF.length
                  ? (ercoAvgCF.reduce((s, r) => s + r.erco_capacity_factor_pct, 0) / ercoAvgCF.length).toFixed(2) + "%"
                  : "N/A"}
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
