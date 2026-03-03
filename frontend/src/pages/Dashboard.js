import React, { useState, useEffect } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Brush, Legend
} from "recharts";
import { fetchOverview, fetchSolarMonthly } from "../api/client";
import RegionSelector from "../components/filters/RegionSelector";
import StatCard from "../components/charts/StatCard";

export default function Dashboard() {
  const [region, setRegion] = useState("CISO");
  const [overview, setOverview] = useState(null);
  const [monthly, setMonthly] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      fetchOverview({ region }),
      fetchSolarMonthly({ region }),
    ]).then(([ov, mo]) => {
      setOverview(ov);
      setMonthly(mo.map((m) => ({ ...m, label: m.month.slice(0, 7) })));
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [region]);

  if (loading) return <div className="loading">Loading dashboard...</div>;

  return (
    <div className="page">
      <h1>Solar Energy Dashboard</h1>
      <RegionSelector value={region} onChange={setRegion} />

      {overview && (
        <div className="stat-grid">
          <StatCard title="Total Generation" value={overview.total_mwh} unit="MWh" />
          <StatCard title="Avg Daily" value={overview.avg_daily_mwh} unit="MWh/day" />
          <StatCard title="Peak Hour" value={overview.peak_mwh} unit="MWh" />
          <StatCard title="Avg Temperature" value={overview.avg_temperature} unit="°C" />
          <StatCard title="Avg Daylight" value={overview.avg_day_length_hours} unit="hours" />
          <StatCard title="Days Tracked" value={overview.total_days} unit="days" />
        </div>
      )}

      <h2>Monthly Solar Generation Trend</h2>
      <ResponsiveContainer width="100%" height={400}>
        <LineChart data={monthly}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="label" />
          <YAxis />
          <Tooltip />
          <Legend />
          <Line type="monotone" dataKey="total_mwh" stroke="#f59e0b" name="Total MWh" strokeWidth={2} />
          <Line type="monotone" dataKey="avg_daily_mwh" stroke="#3b82f6" name="Avg Daily MWh" strokeWidth={2} />
          <Brush dataKey="label" height={30} stroke="#8884d8" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
