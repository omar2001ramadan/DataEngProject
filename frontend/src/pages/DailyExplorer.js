import React, { useState, useEffect } from "react";
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine, Legend
} from "recharts";
import { fetchSolarDaily, fetchSolarHourly } from "../api/client";
import RegionSelector from "../components/filters/RegionSelector";
import DateRangePicker from "../components/filters/DateRangePicker";

export default function DailyExplorer() {
  const [region, setRegion] = useState("CISO");
  const [startDate, setStartDate] = useState("2024-06-01");
  const [endDate, setEndDate] = useState("2024-08-31");
  const [daily, setDaily] = useState([]);
  const [selectedDay, setSelectedDay] = useState(null);
  const [hourly, setHourly] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchSolarDaily({ region, start_date: startDate, end_date: endDate })
      .then((data) => { setDaily(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, [region, startDate, endDate]);

  useEffect(() => {
    if (!selectedDay) return;
    fetchSolarHourly({ region, date: selectedDay })
      .then(setHourly)
      .catch(() => setHourly(null));
  }, [region, selectedDay]);

  const handleDayClick = (data) => {
    if (data && data.activePayload) {
      setSelectedDay(data.activePayload[0].payload.date);
    }
  };

  if (loading) return <div className="loading">Loading daily data...</div>;

  return (
    <div className="page">
      <h1>Daily Explorer</h1>
      <div className="filters">
        <RegionSelector value={region} onChange={setRegion} />
        <DateRangePicker
          startDate={startDate} endDate={endDate}
          onStartChange={setStartDate} onEndChange={setEndDate}
        />
      </div>

      <h2>Daily Solar Generation</h2>
      <p className="hint">Click on a day to see hourly breakdown</p>
      <ResponsiveContainer width="100%" height={350}>
        <AreaChart data={daily} onClick={handleDayClick}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" tickFormatter={(d) => d.slice(5)} />
          <YAxis />
          <Tooltip />
          <Area type="monotone" dataKey="total_mwh" stroke="#f59e0b" fill="#fbbf24" fillOpacity={0.3} name="Total MWh" />
        </AreaChart>
      </ResponsiveContainer>

      {selectedDay && hourly && (
        <>
          <h2>Hourly Breakdown — {selectedDay}</h2>
          <ResponsiveContainer width="100%" height={350}>
            <BarChart data={hourly.hours}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="hour" tickFormatter={(h) => `${h}:00`} />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="value_mwh" fill="#f59e0b" name="MWh" />
              {hourly.sunrise && (
                <ReferenceLine
                  x={parseInt(hourly.sunrise.split(":")[0])}
                  stroke="#ef4444" strokeDasharray="3 3"
                  label={{ value: `Sunrise ${hourly.sunrise}`, position: "top" }}
                />
              )}
              {hourly.sunset && (
                <ReferenceLine
                  x={parseInt(hourly.sunset.split(":")[0])}
                  stroke="#6366f1" strokeDasharray="3 3"
                  label={{ value: `Sunset ${hourly.sunset}`, position: "top" }}
                />
              )}
            </BarChart>
          </ResponsiveContainer>
        </>
      )}
    </div>
  );
}
