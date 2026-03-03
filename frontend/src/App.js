import React from "react";
import { BrowserRouter as Router, Routes, Route, NavLink } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import DailyExplorer from "./pages/DailyExplorer";
import Correlation from "./pages/Correlation";
import Daylight from "./pages/Daylight";
import Compare from "./pages/Compare";
import "./App.css";

function Nav() {
  return (
    <nav className="main-nav">
      <div className="nav-brand">Solar Energy Platform</div>
      <div className="nav-links">
        <NavLink to="/" end>Dashboard</NavLink>
        <NavLink to="/daily">Daily Explorer</NavLink>
        <NavLink to="/correlation">Correlation</NavLink>
        <NavLink to="/daylight">Daylight</NavLink>
        <NavLink to="/compare">Compare</NavLink>
      </div>
    </nav>
  );
}

export default function App() {
  return (
    <Router>
      <Nav />
      <main className="main-content">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/daily" element={<DailyExplorer />} />
          <Route path="/correlation" element={<Correlation />} />
          <Route path="/daylight" element={<Daylight />} />
          <Route path="/compare" element={<Compare />} />
        </Routes>
      </main>
    </Router>
  );
}
