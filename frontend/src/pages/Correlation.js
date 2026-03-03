import React, { useState, useEffect } from "react";
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Line, Legend
} from "recharts";
import { fetchCorrelationWeather, fetchCorrelationDaylight } from "../api/client";
import RegionSelector from "../components/filters/RegionSelector";
import MetricSelector from "../components/filters/MetricSelector";
import DateRangePicker from "../components/filters/DateRangePicker";

export default function Correlation() {
  const [region, setRegion] = useState("CISO");
  const [metric, setMetric] = useState("temperature");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [weatherData, setWeatherData] = useState(null);
  const [daylightData, setDaylightData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    const params = { region };
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;

    Promise.all([
      fetchCorrelationWeather({ ...params, metric }),
      fetchCorrelationDaylight(params),
    ]).then(([wd, dl]) => {
      setWeatherData(wd);
      setDaylightData(dl);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [region, metric, startDate, endDate]);

  if (loading) return <div className="loading">Loading correlation data...</div>;

  // Generate trendline data
  const weatherTrend = weatherData ? (() => {
    const vals = weatherData.data.map((d) => d.metric_value);
    const min = Math.min(...vals);
    const max = Math.max(...vals);
    return [
      { metric_value: min, solar_mwh: weatherData.slope * min + weatherData.intercept },
      { metric_value: max, solar_mwh: weatherData.slope * max + weatherData.intercept },
    ];
  })() : [];

  const daylightTrend = daylightData ? (() => {
    const vals = daylightData.data.map((d) => d.day_length_hours);
    const min = Math.min(...vals);
    const max = Math.max(...vals);
    return [
      { day_length_hours: min, solar_mwh: daylightData.slope * min + daylightData.intercept },
      { day_length_hours: max, solar_mwh: daylightData.slope * max + daylightData.intercept },
    ];
  })() : [];

  return (
    <div className="page">
      <h1>Weather Correlation</h1>
      <div className="filters">
        <RegionSelector value={region} onChange={setRegion} />
        <MetricSelector value={metric} onChange={setMetric} />
        <DateRangePicker
          startDate={startDate} endDate={endDate}
          onStartChange={setStartDate} onEndChange={setEndDate}
        />
      </div>

      {weatherData && (
        <>
          <h2>
            Solar vs {metric.replace("_", " ")}
            <span className="r-squared"> (R² = {weatherData.r_squared ?? "N/A"})</span>
          </h2>
          <ResponsiveContainer width="100%" height={400}>
            <ScatterChart>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="metric_value" name={metric} type="number" />
              <YAxis dataKey="solar_mwh" name="Solar (MWh)" type="number" />
              <Tooltip cursor={{ strokeDasharray: "3 3" }} />
              <Legend />
              <Scatter name="Daily Data" data={weatherData.data} fill="#f59e0b" opacity={0.5} />
              <Scatter name="Trend" data={weatherTrend} fill="none" line={{ stroke: "#ef4444", strokeWidth: 2 }} shape={() => null} />
            </ScatterChart>
          </ResponsiveContainer>
        </>
      )}

      {daylightData && (
        <>
          <h2>
            Solar vs Daylight Hours
            <span className="r-squared"> (R² = {daylightData.r_squared ?? "N/A"})</span>
          </h2>
          <ResponsiveContainer width="100%" height={400}>
            <ScatterChart>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="day_length_hours" name="Daylight (hrs)" type="number" />
              <YAxis dataKey="solar_mwh" name="Solar (MWh)" type="number" />
              <Tooltip cursor={{ strokeDasharray: "3 3" }} />
              <Legend />
              <Scatter name="Daily Data" data={daylightData.data} fill="#3b82f6" opacity={0.5} />
              <Scatter name="Trend" data={daylightTrend} fill="none" line={{ stroke: "#ef4444", strokeWidth: 2 }} shape={() => null} />
            </ScatterChart>
          </ResponsiveContainer>
        </>
      )}
    </div>
  );
}
