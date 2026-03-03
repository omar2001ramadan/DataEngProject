import React, { useState, useEffect } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend
} from "recharts";
import { fetchSolarComparison } from "../api/client";
import DateRangePicker from "../components/filters/DateRangePicker";

export default function Compare() {
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    const params = {};
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;
    fetchSolarComparison(params)
      .then((d) => {
        setData(d.map((r) => ({ ...r, label: r.month.slice(0, 7) })));
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [startDate, endDate]);

  if (loading) return <div className="loading">Loading comparison data...</div>;

  // Summary stats
  const cisoTotal = data.reduce((s, r) => s + (r.ciso_total_mwh || 0), 0);
  const ercoTotal = data.reduce((s, r) => s + (r.erco_total_mwh || 0), 0);

  return (
    <div className="page">
      <h1>Region Comparison</h1>
      <div className="filters">
        <DateRangePicker
          startDate={startDate} endDate={endDate}
          onStartChange={setStartDate} onEndChange={setEndDate}
        />
      </div>

      <h2>Monthly Generation — CISO vs ERCO</h2>
      <ResponsiveContainer width="100%" height={400}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="label" />
          <YAxis />
          <Tooltip />
          <Legend />
          <Bar dataKey="ciso_total_mwh" fill="#f59e0b" name="California (CISO)" />
          <Bar dataKey="erco_total_mwh" fill="#3b82f6" name="Texas (ERCO)" />
        </BarChart>
      </ResponsiveContainer>

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
            <td>{data.length ? Math.round(cisoTotal / data.length).toLocaleString() : "—"} MWh</td>
            <td>{data.length ? Math.round(ercoTotal / data.length).toLocaleString() : "—"} MWh</td>
          </tr>
          <tr>
            <td>Peak Month</td>
            <td>
              {data.length
                ? data.reduce((best, r) => (r.ciso_total_mwh || 0) > (best.ciso_total_mwh || 0) ? r : best, data[0]).label
                : "—"}
            </td>
            <td>
              {data.length
                ? data.reduce((best, r) => (r.erco_total_mwh || 0) > (best.erco_total_mwh || 0) ? r : best, data[0]).label
                : "—"}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}
