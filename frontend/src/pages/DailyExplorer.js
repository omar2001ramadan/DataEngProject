import React, { useState, useEffect, useRef, useMemo } from "react";
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine, ReferenceArea, Legend, Brush
} from "recharts";
import { fetchSolarDaily, fetchSolarHourly } from "../api/client";
import RegionSelector from "../components/filters/RegionSelector";
import DateRangePicker from "../components/filters/DateRangePicker";

// Derive weather icon from available data
function getWeatherIcon(d) {
  if (!d) return { icon: "--", label: "No data" };

  const precip = d.total_precip ?? d.precipitation;
  const hum = d.avg_humidity ?? d.humidity;
  const vis = d.avg_visibility ?? d.visibility;
  const temp = d.avg_temperature ?? d.temperature;
  const isHourlyData = d.hour != null;

  // No weather data available
  if (hum == null && vis == null && temp == null && !d.sky_conditions) return { icon: "\u2014", label: "No weather data" };

  // Use sky_conditions as primary indicator (METAR codes)
  if (d.sky_conditions) {
    const code = d.sky_conditions.slice(0, 3).toUpperCase();
    // For hourly data, check precipitation for that specific hour
    if (isHourlyData && precip != null && precip > 0) {
      if (temp != null && temp <= 0) return { icon: "\uD83C\uDF28\uFE0F", label: "Snow" };
      if (precip > 5) return { icon: "\uD83C\uDF27\uFE0F", label: "Heavy rain" };
      return { icon: "\uD83C\uDF26\uFE0F", label: "Rain" };
    }
    if (code === "CLR") return { icon: "\u2600\uFE0F", label: "Clear" };
    if (code === "FEW") return { icon: "\uD83C\uDF24\uFE0F", label: "Few clouds" };
    if (code === "SCT") return { icon: "\u26C5", label: "Partly cloudy" };
    if (code === "BKN") return { icon: "\uD83C\uDF25\uFE0F", label: "Mostly cloudy" };
    if (code === "OVC") return { icon: "\u2601\uFE0F", label: "Overcast" };
  }

  // Fallback: derive from humidity + visibility
  if (vis != null && vis < 5) return { icon: "\uD83C\uDF2B\uFE0F", label: "Low visibility" };
  if (hum != null && hum > 85) return { icon: "\u2601\uFE0F", label: "Overcast" };
  if (hum != null && hum > 60) return { icon: "\u26C5", label: "Partly cloudy" };
  if (hum != null && hum > 35) return { icon: "\uD83C\uDF24\uFE0F", label: "Few clouds" };
  return { icon: "\u2600\uFE0F", label: "Clear" };
}

function WeatherPanel({ data, isHourly }) {
  if (!data) {
    return (
      <div className="weather-panel">
        <div className="weather-icon">--</div>
        <div className="weather-label">Hover over chart</div>
      </div>
    );
  }
  const w = getWeatherIcon(data);
  const temp = isHourly ? data.temperature : data.avg_temperature;
  const hum = isHourly ? data.humidity : data.avg_humidity;
  const wind = isHourly ? data.wind_speed : data.avg_wind_speed;
  const precip = isHourly ? data.precipitation : data.total_precip;

  return (
    <div className="weather-panel">
      <div className="weather-icon">{w.icon}</div>
      <div className="weather-label">{w.label}</div>
      {temp != null && <div className="weather-stat">{temp}&deg;C / {Math.round(temp * 9 / 5 + 32)}&deg;F</div>}
      {hum != null && <div className="weather-stat">{hum}% humidity</div>}
      {wind != null && <div className="weather-stat">{wind} km/h wind</div>}
      {precip != null && precip > 0 && <div className="weather-stat">{precip} mm precip</div>}
      {isHourly && <div className="weather-time">{data.hour}:00</div>}
      {!isHourly && data.date && <div className="weather-time">{data.date}</div>}
    </div>
  );
}

export default function DailyExplorer() {
  const [region, setRegion] = useState("CISO");
  const [allData, setAllData] = useState([]);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [brushKey, setBrushKey] = useState(0);
  const [selectedDay, setSelectedDay] = useState(null);
  const [hourly, setHourly] = useState(null);
  const [hoveredDaily, setHoveredDaily] = useState(null);
  const [hoveredHourly, setHoveredHourly] = useState(null);
  const [useLocal, setUseLocal] = useState(true);
  const [loading, setLoading] = useState(true);
  const brushRef = useRef({ startIndex: 0, endIndex: 0 });

  useEffect(() => {
    setLoading(true);
    fetchSolarDaily({ region })
      .then((data) => {
        setAllData(data);
        if (data.length > 0) {
          setStartDate(data[0].date);
          setEndDate(data[data.length - 1].date);
          brushRef.current = { startIndex: 0, endIndex: data.length - 1 };
        }
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [region]);

  const handleBrushChange = (range) => {
    if (range && allData.length > 0) {
      brushRef.current = range;
      setStartDate(allData[range.startIndex].date);
      setEndDate(allData[range.endIndex].date);
    }
  };

  const handleStartDateChange = (val) => {
    setStartDate(val);
    const idx = allData.findIndex((d) => d.date >= val);
    if (idx >= 0) {
      brushRef.current = { ...brushRef.current, startIndex: idx };
      setBrushKey((k) => k + 1);
    }
  };

  const handleEndDateChange = (val) => {
    setEndDate(val);
    let idx = allData.length - 1;
    for (let i = allData.length - 1; i >= 0; i--) {
      if (allData[i].date <= val) { idx = i; break; }
    }
    brushRef.current = { ...brushRef.current, endIndex: idx };
    setBrushKey((k) => k + 1);
  };

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

  const handleDailyHover = (state) => {
    if (state && state.activePayload) {
      setHoveredDaily(state.activePayload[0].payload);
    }
  };

  const handleHourlyHover = (state) => {
    if (state && state.activePayload) {
      setHoveredHourly(state.activePayload[0].payload);
    }
  };

  const REGION_TZ = { CISO: { name: "Pacific", std: -8, dst: -7 }, ERCO: { name: "Central", std: -6, dst: -5 } };
  const tz = REGION_TZ[region] || REGION_TZ.CISO;
  const tzLabel = useLocal ? `${tz.name}` : "UTC";

  // Compute timezone offset for the selected day
  const tzOffset = useMemo(() => {
    if (!selectedDay) return 0;
    const d = new Date(selectedDay + "T12:00:00Z");
    const year = d.getUTCFullYear();
    const mar = new Date(Date.UTC(year, 2, 1));
    const marSun = new Date(Date.UTC(year, 2, 8 + (7 - mar.getUTCDay()) % 7));
    const nov = new Date(Date.UTC(year, 10, 1));
    const novSun = new Date(Date.UTC(year, 10, 1 + (7 - nov.getUTCDay()) % 7));
    const dst = d >= marSun && d < novSun;
    return dst ? tz.dst : tz.std;
  }, [selectedDay, tz]);

  // Shift hourly data to local time
  const hourlyData = useMemo(() => {
    if (!hourly) return [];
    const offset = useLocal ? tzOffset : 0;
    return hourly.hours.map((h) => {
      let localHour = h.hour + offset;
      if (localHour < 0) localHour += 24;
      if (localHour >= 24) localHour -= 24;
      return { ...h, displayHour: localHour };
    }).sort((a, b) => a.displayHour - b.displayHour);
  }, [hourly, useLocal, tzOffset]);

  // Compute sunrise/sunset in display timezone
  const sunTimes = useMemo(() => {
    if (!hourly || !hourly.sunrise || !hourly.sunset) return null;
    const riseUtc = parseInt(hourly.sunrise.split(":")[0]) + parseInt(hourly.sunrise.split(":")[1]) / 60;
    const setUtc = parseInt(hourly.sunset.split(":")[0]) + parseInt(hourly.sunset.split(":")[1]) / 60;
    const offset = useLocal ? tzOffset : 0;
    let rise = riseUtc + offset;
    let set = setUtc + offset;
    if (rise < 0) rise += 24;
    if (rise >= 24) rise -= 24;
    if (set < 0) set += 24;
    if (set >= 24) set -= 24;
    const fmt = (dec) => `${Math.floor(dec)}:${String(Math.round((dec % 1) * 60)).padStart(2, "0")}`;
    return { riseHr: Math.floor(rise), setHr: Math.floor(set), riseLabel: fmt(rise) + " " + tzLabel, setLabel: fmt(set) + " " + tzLabel };
  }, [hourly, useLocal, tzOffset, tzLabel]);

  if (loading) return <div className="loading">Loading daily data...</div>;

  return (
    <div className="page">
      <h1>Daily Explorer</h1>
      <div className="filters">
        <RegionSelector value={region} onChange={setRegion} />
        <DateRangePicker
          startDate={startDate} endDate={endDate}
          onStartChange={handleStartDateChange} onEndChange={handleEndDateChange}
        />
      </div>

      <h2>Daily Solar Generation</h2>
      <p className="hint">Click on a day to see hourly breakdown</p>
      <div className="chart-with-panel">
        <ResponsiveContainer width="100%" height={400}>
          <AreaChart data={allData} onClick={handleDayClick} onMouseMove={handleDailyHover}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" tickFormatter={(d) => d.slice(5)} />
            <YAxis />
            <Tooltip />
            <Area type="monotone" dataKey="total_mwh" stroke="#f59e0b" fill="#fbbf24" fillOpacity={0.3} name="Total MWh" />
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
        <WeatherPanel data={hoveredDaily} isHourly={false} />
      </div>

      {selectedDay && hourly && (
        <>
          <div style={{ display: "flex", alignItems: "center", gap: "1rem", marginTop: "1.5rem" }}>
            <h2 style={{ margin: 0 }}>Hourly Breakdown - {selectedDay}</h2>
            <div className="tz-toggle">
              <button className={useLocal ? "active" : ""} onClick={() => setUseLocal(true)}>
                Local ({tz.name})
              </button>
              <button className={!useLocal ? "active" : ""} onClick={() => setUseLocal(false)}>
                UTC
              </button>
            </div>
          </div>
          <div className="chart-with-panel">
            <ResponsiveContainer width="100%" height={350}>
              <BarChart data={hourlyData} onMouseMove={handleHourlyHover}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="displayHour" tickFormatter={(h) => `${h}:00`} label={{ value: `Hour (${tzLabel})`, position: "insideBottom", offset: -5, fill: "#94a3b8" }} />
                <YAxis />
                <Tooltip labelFormatter={(h) => `${h}:00 ${tzLabel}`} />
                {sunTimes && (() => {
                  const minHr = Math.min(...hourlyData.map(h => h.displayHour));
                  const maxHr = Math.max(...hourlyData.map(h => h.displayHour));
                  if (sunTimes.riseHr < sunTimes.setHr) {
                    return (
                      <>
                        <ReferenceArea x1={minHr} x2={sunTimes.riseHr} fill="#312e81" fillOpacity={0.25} />
                        <ReferenceArea x1={sunTimes.setHr} x2={maxHr} fill="#312e81" fillOpacity={0.25} />
                      </>
                    );
                  } else {
                    return (
                      <ReferenceArea x1={sunTimes.setHr} x2={sunTimes.riseHr} fill="#312e81" fillOpacity={0.25} />
                    );
                  }
                })()}
                <Bar dataKey="value_mwh" fill="#f59e0b" name="MWh" />
                {sunTimes && (
                  <ReferenceLine
                    x={sunTimes.riseHr}
                    stroke="#f59e0b" strokeWidth={2} strokeDasharray="3 3"
                    label={{ value: `Sunrise ${sunTimes.riseLabel}`, position: "top", fill: "#f59e0b" }}
                  />
                )}
                {sunTimes && (
                  <ReferenceLine
                    x={sunTimes.setHr}
                    stroke="#6366f1" strokeWidth={2} strokeDasharray="3 3"
                    label={{ value: `Sunset ${sunTimes.setLabel}`, position: "top", fill: "#6366f1" }}
                  />
                )}
              </BarChart>
            </ResponsiveContainer>
            <WeatherPanel data={hoveredHourly} isHourly={true} />
          </div>
          <div className="chart-legend">
            <span><span className="legend-swatch" style={{ background: "#f59e0b" }}></span> Solar Generation (MWh)</span>
            <span><span className="legend-line" style={{ borderColor: "#f59e0b" }}></span> Sunrise</span>
            <span><span className="legend-line" style={{ borderColor: "#6366f1" }}></span> Sunset</span>
            <span><span className="legend-swatch" style={{ background: "#312e81", opacity: 0.5 }}></span> Night</span>
          </div>
        </>
      )}
    </div>
  );
}
