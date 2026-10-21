import { Link, Route, Routes } from "react-router-dom";
import { Dashboard } from "./pages/Dashboard";
import { WellDetail } from "./pages/WellDetail";

export function App() {
  return (
    <>
      <nav className="topbar">
        <Link to="/" className="brand">
          <svg viewBox="0 0 32 32" aria-hidden="true">
            <rect x="7" y="18" width="4" height="8" rx="1" fill="var(--oil)" />
            <rect x="14" y="12" width="4" height="14" rx="1" fill="var(--water)" />
            <rect x="21" y="7" width="4" height="19" rx="1" fill="var(--gas)" />
          </svg>
          Production Dashboard
        </Link>
        <a href="/docs" className="topbar-link">
          API docs
        </a>
      </nav>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/wells/:id" element={<WellDetail />} />
        <Route
          path="*"
          element={
            <main className="page">
              <h1>Page not found</h1>
              <Link to="/">Go to the dashboard</Link>
            </main>
          }
        />
      </Routes>
    </>
  );
}
