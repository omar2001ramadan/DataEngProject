import axios from "axios";

const API_BASE = process.env.REACT_APP_API_URL || "http://localhost:5000";

const client = axios.create({ baseURL: API_BASE });

export const fetchOverview = (params) =>
  client.get("/api/overview", { params }).then((r) => r.data);

export const fetchSolarDaily = (params) =>
  client.get("/api/solar/daily", { params }).then((r) => r.data);

export const fetchSolarHourly = (params) =>
  client.get("/api/solar/hourly", { params }).then((r) => r.data);

export const fetchSolarMonthly = (params) =>
  client.get("/api/solar/monthly", { params }).then((r) => r.data);

export const fetchSolarComparison = (params) =>
  client.get("/api/solar/comparison", { params }).then((r) => r.data);

export const fetchWeatherDaily = (params) =>
  client.get("/api/weather/daily", { params }).then((r) => r.data);

export const fetchCorrelationWeather = (params) =>
  client.get("/api/correlation/solar-weather", { params }).then((r) => r.data);

export const fetchCorrelationDaylight = (params) =>
  client.get("/api/correlation/solar-daylight", { params }).then((r) => r.data);

export const fetchDaylight = (params) =>
  client.get("/api/daylight", { params }).then((r) => r.data);
