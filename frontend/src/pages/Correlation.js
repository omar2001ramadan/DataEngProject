import React, { useState, useEffect, useRef, useMemo } from "react";
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend,
  AreaChart, Area, Brush
} from "recharts";
import { fetchCorrelationWeather, fetchCorrelationDaylight } from "../api/client";
import RegionSelector from "../components/filters/RegionSelector";
import MetricSelector from "../components/filters/MetricSelector";
import DateRangePicker from "../components/filters/DateRangePicker";

export default function Correlation() {
  const [region, setRegion] = useState("CISO");
  const [metric, setMetric] = useState("temperature");
  const [weatherData, setWeatherData] = useState(null);
  const [daylightData, setDaylightData] = useState(null);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [brushKey, setBrushKey] = useState(0);
  const [loading, setLoading] = useState(true);
  const brushRef = useRef({ startIndex: 0, endIndex: 0 });

  useEffect(() => {
    setLoading(true);
    Promise.all([
      fetchCorrelationWeather({ region, metric }),
      fetchCorrelationDaylight({ region }),
    ]).then(([wd, dl]) => {
      setWeatherData(wd);
      setDaylightData(dl);
      if (wd && wd.data.length > 0) {
        setStartDate(wd.data[0].date);
        setEndDate(wd.data[wd.data.length - 1].date);
        brushRef.current = { startIndex: 0, endIndex: wd.data.length - 1 };
      }
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [region, metric]);

  const timelineData = useMemo(() => {
    if (!weatherData) return [];
    return weatherData.data.map((d) => ({ date: d.date, solar_mwh: d.solar_mwh }));
  }, [weatherData]);

  const handleBrushChange = (range) => {
    if (range && timelineData.length > 0) {
      brushRef.current = range;
      setStartDate(timelineData[range.startIndex].date);
      setEndDate(timelineData[range.endIndex].date);
    }
  };

  const handleStartDateChange = (val) => {
    setStartDate(val);
    const idx = timelineData.findIndex((d) => d.date >= val);
    if (idx >= 0) {
      brushRef.current = { ...brushRef.current, startIndex: idx };
      setBrushKey((k) => k + 1);
    }
  };

  const handleEndDateChange = (val) => {
    setEndDate(val);
    let idx = timelineData.length - 1;
    for (let i = timelineData.length - 1; i >= 0; i--) {
      if (timelineData[i].date <= val) { idx = i; break; }
    }
    brushRef.current = { ...brushRef.current, endIndex: idx };
    setBrushKey((k) => k + 1);
  };

  // Filter data to brush range
  const filteredWeather = useMemo(() => {
    if (!weatherData) return [];
    return weatherData.data.filter((d) => d.date >= startDate && d.date <= endDate);
  }, [weatherData, startDate, endDate]);

  const filteredDaylight = useMemo(() => {
    if (!daylightData) return [];
    return daylightData.data.filter((d) => d.date >= startDate && d.date <= endDate);
  }, [daylightData, startDate, endDate]);

  // Compute trendlines for filtered data
  const computeTrend = (data, xKey, yKey) => {
    if (data.length < 3) return { slope: 0, intercept: 0, r_squared: null, trend: [] };
    const x = data.map((d) => d[xKey]);
    const y = data.map((d) => d[yKey]);
    const n = x.length;
    const sumX = x.reduce((a, b) => a + b, 0);
    const sumY = y.reduce((a, b) => a + b, 0);
    const sumXY = x.reduce((a, b, i) => a + b * y[i], 0);
    const sumX2 = x.reduce((a, b) => a + b * b, 0);
    const sumY2 = y.reduce((a, b) => a + b * b, 0);
    const denom = (n * sumX2 - sumX ** 2) * (n * sumY2 - sumY ** 2);
    let slope = 0, intercept = 0, r_squared = null;
    if (denom > 0) {
      const r = (n * sumXY - sumX * sumY) / Math.sqrt(denom);
      r_squared = Math.round(r * r * 10000) / 10000;
      slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX ** 2);
      intercept = (sumY - slope * sumX) / n;
    }
    const min = Math.min(...x);
    const max = Math.max(...x);
    return {
      slope, intercept, r_squared,
      trend: [
        { [xKey]: min, [yKey]: slope * min + intercept },
        { [xKey]: max, [yKey]: slope * max + intercept },
      ],
    };
  };

  const weatherTrend = useMemo(() => computeTrend(filteredWeather, "metric_value", "solar_mwh"), [filteredWeather]);
  const daylightTrend = useMemo(() => computeTrend(filteredDaylight, "day_length_hours", "solar_mwh"), [filteredDaylight]);

  if (loading) return <div className="loading">Loading correlation data...</div>;

  return (
    <div className="page">
      <h1>Weather Correlation</h1>
      <div className="filters">
        <RegionSelector value={region} onChange={setRegion} />
        <MetricSelector value={metric} onChange={setMetric} />
        <DateRangePicker
          startDate={startDate} endDate={endDate}
          onStartChange={handleStartDateChange} onEndChange={handleEndDateChange}
        />
      </div>

      {timelineData.length > 0 && (
        <ResponsiveContainer width="100%" height={80}>
          <AreaChart data={timelineData}>
            <YAxis hide domain={["dataMin", "dataMax"]} />
            <Area type="monotone" dataKey="solar_mwh" stroke="#f59e0b" fill="#fbbf24" fillOpacity={0.3} />
            <Brush
              key={brushKey}
              dataKey="date" height={30} stroke="#8884d8"
              tickFormatter={(d) => d.slice(5)}
              startIndex={brushRef.current.startIndex}
              endIndex={brushRef.current.endIndex}
              onChange={handleBrushChange}
            />
          </AreaChart>
        </ResponsiveContainer>
      )}

      {filteredWeather.length > 0 && (
        <>
          <h2>
            Solar vs {metric.replace("_", " ")}
            <span className="r-squared"> (R² = {weatherTrend.r_squared ?? "N/A"})</span>
          </h2>
          <ResponsiveContainer width="100%" height={400}>
            <ScatterChart>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="metric_value" name={metric} type="number" />
              <YAxis dataKey="solar_mwh" name="Solar (MWh)" type="number" />
              <Tooltip cursor={{ strokeDasharray: "3 3" }} />
              <Legend />
              <Scatter name="Daily Data" data={filteredWeather} fill="#f59e0b" opacity={0.5} />
              <Scatter name="Trend" data={weatherTrend.trend} fill="none" line={{ stroke: "#ef4444", strokeWidth: 2 }} shape={() => null} />
            </ScatterChart>
          </ResponsiveContainer>
        </>
      )}

      {filteredDaylight.length > 0 && (
        <>
          <h2>
            Solar vs Daylight Hours
            <span className="r-squared"> (R² = {daylightTrend.r_squared ?? "N/A"})</span>
          </h2>
          <ResponsiveContainer width="100%" height={400}>
            <ScatterChart>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="day_length_hours" name="Daylight (hrs)" type="number" />
              <YAxis dataKey="solar_mwh" name="Solar (MWh)" type="number" />
              <Tooltip cursor={{ strokeDasharray: "3 3" }} />
              <Legend />
              <Scatter name="Daily Data" data={filteredDaylight} fill="#3b82f6" opacity={0.5} />
              <Scatter name="Trend" data={daylightTrend.trend} fill="none" line={{ stroke: "#ef4444", strokeWidth: 2 }} shape={() => null} />
            </ScatterChart>
          </ResponsiveContainer>
        </>
      )}
    </div>
  );
}
