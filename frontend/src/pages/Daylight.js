import React, { useState, useEffect } from "react";
import {
  ComposedChart, Area, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend
} from "recharts";
import { fetchDaylight } from "../api/client";
import RegionSelector from "../components/filters/RegionSelector";
import DateRangePicker from "../components/filters/DateRangePicker";

// Convert "HH:MM" to decimal hours for charting
function timeToDecimal(t) {
  if (!t) return null;
  const [h, m] = t.split(":").map(Number);
  return h + m / 60;
}

export default function Daylight() {
  const [region, setRegion] = useState("CISO");
  const [startDate, setStartDate] = useState("2024-01-01");
  const [endDate, setEndDate] = useState("2024-12-31");
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchDaylight({ region, start_date: startDate, end_date: endDate })
      .then((d) => {
        setData(
          d.map((r) => ({
            ...r,
            sunrise_hr: timeToDecimal(r.sunrise),
            sunset_hr: timeToDecimal(r.sunset),
          }))
        );
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [region, startDate, endDate]);

  if (loading) return <div className="loading">Loading daylight data...</div>;

  return (
    <div className="page">
      <h1>Daylight Analysis</h1>
      <div className="filters">
        <RegionSelector value={region} onChange={setRegion} />
        <DateRangePicker
          startDate={startDate} endDate={endDate}
          onStartChange={setStartDate} onEndChange={setEndDate}
        />
      </div>

      <h2>Daylight Hours & Solar Generation</h2>
      <ResponsiveContainer width="100%" height={400}>
        <ComposedChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" tickFormatter={(d) => d.slice(5)} />
          <YAxis yAxisId="hours" domain={[4, 22]} label={{ value: "Hour of Day (UTC)", angle: -90, position: "insideLeft" }} />
          <YAxis yAxisId="mwh" orientation="right" label={{ value: "MWh", angle: 90, position: "insideRight" }} />
          <Tooltip />
          <Legend />
          <Area
            yAxisId="hours" type="monotone" dataKey="sunset_hr"
            stroke="#6366f1" fill="#6366f1" fillOpacity={0.15}
            name="Sunset (UTC)"
          />
          <Area
            yAxisId="hours" type="monotone" dataKey="sunrise_hr"
            stroke="#f59e0b" fill="#ffffff" fillOpacity={1}
            name="Sunrise (UTC)"
          />
          <Line
            yAxisId="mwh" type="monotone" dataKey="total_mwh"
            stroke="#ef4444" strokeWidth={2} dot={false}
            name="Solar MWh"
          />
        </ComposedChart>
      </ResponsiveContainer>

      <h2>Day Length Over Time</h2>
      <ResponsiveContainer width="100%" height={300}>
        <ComposedChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" tickFormatter={(d) => d.slice(5)} />
          <YAxis label={{ value: "Hours", angle: -90, position: "insideLeft" }} />
          <Tooltip />
          <Area type="monotone" dataKey="day_length_hours" stroke="#10b981" fill="#10b981" fillOpacity={0.2} name="Day Length (hrs)" />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
