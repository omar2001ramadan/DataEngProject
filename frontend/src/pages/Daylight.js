import React, { useState, useEffect, useRef, useMemo } from "react";
import {
  ComposedChart, Area, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend, Brush
} from "recharts";
import { fetchDaylight } from "../api/client";
import RegionSelector from "../components/filters/RegionSelector";
import DateRangePicker from "../components/filters/DateRangePicker";

const REGION_TZ = {
  CISO: { name: "Pacific", std: -8, dst: -7 },
  ERCO: { name: "Central", std: -6, dst: -5 },
};

function isDST(dateStr) {
  const d = new Date(dateStr + "T12:00:00Z");
  const year = d.getUTCFullYear();
  const mar = new Date(Date.UTC(year, 2, 1));
  const marSecondSun = new Date(Date.UTC(year, 2, 8 + (7 - mar.getUTCDay()) % 7));
  const nov = new Date(Date.UTC(year, 10, 1));
  const novFirstSun = new Date(Date.UTC(year, 10, 1 + (7 - nov.getUTCDay()) % 7));
  return d >= marSecondSun && d < novFirstSun;
}

function timeToDecimal(t) {
  if (!t) return null;
  const [h, m] = t.split(":").map(Number);
  return h + m / 60;
}

function applyOffset(decimalHour, offset) {
  if (decimalHour == null) return null;
  let adjusted = decimalHour + offset;
  if (adjusted < 0) adjusted += 24;
  if (adjusted >= 24) adjusted -= 24;
  return adjusted;
}

function decimalToTime(dec) {
  if (dec == null) return "";
  const h = Math.floor(dec);
  const m = Math.round((dec - h) * 60);
  return `${h}:${m.toString().padStart(2, "0")}`;
}

const nightColor = "#312e81";
const dayColor = "#fef3c7";

export default function Daylight() {
  const [region, setRegion] = useState("CISO");
  const [allData, setAllData] = useState([]);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [useLocal, setUseLocal] = useState(true);
  const [brushKey, setBrushKey] = useState(0);
  const [loading, setLoading] = useState(true);
  const brushRef = useRef({ startIndex: 0, endIndex: 0 });

  useEffect(() => {
    setLoading(true);
    fetchDaylight({ region })
      .then((d) => {
        const mapped = d.map((r) => ({
          ...r,
          sunrise_utc: timeToDecimal(r.sunrise),
          sunset_utc: timeToDecimal(r.sunset),
        }));
        setAllData(mapped);
        if (mapped.length > 0) {
          setStartDate(mapped[0].date);
          setEndDate(mapped[mapped.length - 1].date);
          brushRef.current = { startIndex: 0, endIndex: mapped.length - 1 };
        }
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [region]);

  const chartData = useMemo(() => {
    const tz = REGION_TZ[region] || REGION_TZ.CISO;
    let prevRise = null, prevSet = null;

    return allData.map((r) => {
      let rise, set;
      if (useLocal) {
        const offset = isDST(r.date) ? tz.dst : tz.std;
        rise = applyOffset(r.sunrise_utc, offset);
        set = applyOffset(r.sunset_utc, offset);
      } else {
        rise = r.sunrise_utc;
        set = r.sunset_utc;
      }

      const lower = (rise != null && set != null) ? Math.min(rise, set) : 0;
      const upper = (rise != null && set != null) ? Math.max(rise, set) : 24;
      const gap = upper - lower;

      // Use day_length to decide if the gap between lines is day or night
      const dayHrs = r.day_length_hours || 12;
      const middleIsDay = Math.abs(gap - dayHrs) < Math.abs((24 - gap) - dayHrs);

      // Two sets of stacked bands - only one set is non-zero per point
      // Normal: night(0->lower) + day(lower->upper) + night(upper->24)
      // Wrapped: day(0->lower) + night(lower->upper) + day(upper->24)
      let n_night_low = 0, n_day = 0, n_night_high = 0;
      let w_day_low = 0, w_night = 0, w_day_high = 0;

      if (middleIsDay) {
        n_night_low = lower;
        n_day = gap;
        n_night_high = 24 - upper;
      } else {
        w_day_low = lower;
        w_night = gap;
        w_day_high = 24 - upper;
      }

      // Break lines on large jumps
      let sunrise_line = rise;
      let sunset_line = set;
      if (prevRise != null && rise != null && Math.abs(rise - prevRise) > 6) sunrise_line = null;
      if (prevSet != null && set != null && Math.abs(set - prevSet) > 6) sunset_line = null;
      prevRise = rise;
      prevSet = set;

      return {
        ...r,
        sunrise_hr: rise,
        sunset_hr: set,
        sunrise_line,
        sunset_line,
        n_night_low, n_day, n_night_high,
        w_day_low, w_night, w_day_high,
      };
    });
  }, [allData, region, useLocal]);

  const tz = REGION_TZ[region] || REGION_TZ.CISO;
  const tzLabel = useLocal ? `${tz.name} Time` : "UTC";

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

  if (loading) return <div className="loading">Loading daylight data...</div>;

  const customTooltip = ({ active, payload }) => {
    if (!active || !payload || !payload.length) return null;
    const d = payload[0]?.payload;
    if (!d) return null;
    return (
      <div style={{ background: "#1e293b", border: "1px solid #475569", borderRadius: 8, padding: "8px 12px" }}>
        <p style={{ color: "#e2e8f0", margin: 0, fontWeight: 600 }}>{d.date}</p>
        <p style={{ color: "#f59e0b", margin: "4px 0 0" }}>Sunrise: {decimalToTime(d.sunrise_hr)} {tzLabel}</p>
        <p style={{ color: "#6366f1", margin: "2px 0 0" }}>Sunset: {decimalToTime(d.sunset_hr)} {tzLabel}</p>
        {d.day_length_hours != null && (
          <p style={{ color: "#10b981", margin: "2px 0 0" }}>Day length: {d.day_length_hours} hrs</p>
        )}
        {d.total_mwh != null && (
          <p style={{ color: "#ef4444", margin: "2px 0 0" }}>Solar: {d.total_mwh} MWh</p>
        )}
      </div>
    );
  };

  return (
    <div className="page">
      <h1>Daylight Analysis</h1>
      <div className="filters">
        <RegionSelector value={region} onChange={setRegion} />
        <DateRangePicker
          startDate={startDate} endDate={endDate}
          onStartChange={handleStartDateChange} onEndChange={handleEndDateChange}
        />
        <div className="tz-toggle">
          <button className={useLocal ? "active" : ""} onClick={() => setUseLocal(true)}>
            Local ({tz.name})
          </button>
          <button className={!useLocal ? "active" : ""} onClick={() => setUseLocal(false)}>
            UTC
          </button>
        </div>
      </div>

      <h2>Daylight Hours & Solar Generation</h2>
      <ResponsiveContainer width="100%" height={400}>
        <ComposedChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" tickFormatter={(d) => d.slice(5)} />
          <YAxis
            yAxisId="hours" domain={[0, 24]}
            label={{ value: `Hour of Day (${tzLabel})`, angle: -90, position: "insideLeft" }}
            tickFormatter={(v) => `${v}:00`}
          />
          <YAxis yAxisId="mwh" orientation="right" label={{ value: "MWh", angle: 90, position: "insideRight" }} />
          <Tooltip content={customTooltip} />
          <Legend />

          {/* Normal bands: night-day-night (active when rise < set) */}
          <Area yAxisId="hours" type="monotone" dataKey="n_night_low" stackId="bands"
            stroke="none" fill={nightColor} fillOpacity={0.4} legendType="none" name="n1" />
          <Area yAxisId="hours" type="monotone" dataKey="n_day" stackId="bands"
            stroke="none" fill={dayColor} fillOpacity={0.15} legendType="none" name="n2" />
          <Area yAxisId="hours" type="monotone" dataKey="n_night_high" stackId="bands"
            stroke="none" fill={nightColor} fillOpacity={0.4} legendType="none" name="n3" />

          {/* Wrapped bands: day-night-day (active when rise > set) */}
          <Area yAxisId="hours" type="monotone" dataKey="w_day_low" stackId="bands"
            stroke="none" fill={dayColor} fillOpacity={0.15} legendType="none" name="w1" />
          <Area yAxisId="hours" type="monotone" dataKey="w_night" stackId="bands"
            stroke="none" fill={nightColor} fillOpacity={0.4} legendType="none" name="w2" />
          <Area yAxisId="hours" type="monotone" dataKey="w_day_high" stackId="bands"
            stroke="none" fill={dayColor} fillOpacity={0.15} legendType="none" name="w3" />

          {/* Legend entries */}
          <Line yAxisId="hours" dataKey={() => null} stroke={dayColor} strokeWidth={8}
            legendType="rect" name="Daylight" dot={false} />
          <Line yAxisId="hours" dataKey={() => null} stroke={nightColor} strokeWidth={8}
            legendType="rect" name="Night" dot={false} />

          {/* Sunrise and sunset lines */}
          <Line yAxisId="hours" type="monotone" dataKey="sunrise_line"
            stroke="#f59e0b" strokeWidth={2} dot={false}
            connectNulls={false}
            name={`Sunrise (${tzLabel})`} />
          <Line yAxisId="hours" type="monotone" dataKey="sunset_line"
            stroke="#6366f1" strokeWidth={2} dot={false}
            connectNulls={false}
            name={`Sunset (${tzLabel})`} />

          <Line yAxisId="mwh" type="monotone" dataKey="total_mwh"
            stroke="#ef4444" strokeWidth={2} dot={false}
            name="Solar MWh" />

          <Brush
            key={brushKey}
            dataKey="date" height={30} stroke="#8884d8"
            tickFormatter={(d) => d.slice(5)}
            startIndex={brushRef.current.startIndex}
            endIndex={brushRef.current.endIndex}
            onChange={handleBrushChange}
          />
        </ComposedChart>
      </ResponsiveContainer>

    </div>
  );
}
