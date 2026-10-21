import { Link } from "react-router-dom";
import type { Alert } from "../types";

const KIND_LABELS: Record<Alert["kind"], string> = {
  production_drop: "Production drop",
  high_water_cut: "High water cut",
  no_production: "No production",
};

export function SeverityIcon({ severity }: { severity: Alert["severity"] }) {
  // Shape differs as well as color, so severity never relies on color alone.
  return severity === "critical" ? (
    <svg className="sev-icon critical" viewBox="0 0 16 16" aria-hidden="true">
      <path d="M8 1 15 14H1Z" />
      <rect x="7.2" y="5.5" width="1.6" height="4.5" rx=".8" fill="var(--panel)" />
      <circle cx="8" cy="11.8" r=".9" fill="var(--panel)" />
    </svg>
  ) : (
    <svg className="sev-icon warning" viewBox="0 0 16 16" aria-hidden="true">
      <circle cx="8" cy="8" r="7" />
      <rect x="7.2" y="4" width="1.6" height="5" rx=".8" fill="var(--panel)" />
      <circle cx="8" cy="11.4" r=".9" fill="var(--panel)" />
    </svg>
  );
}

export function AlertList({ alerts }: { alerts: Alert[] }) {
  if (alerts.length === 0) {
    return <p className="empty">All active wells are within normal limits.</p>;
  }
  return (
    <ul className="alerts">
      {alerts.map((a) => (
        <li key={`${a.well_id}-${a.kind}`} className={`alert ${a.severity}`}>
          <SeverityIcon severity={a.severity} />
          <div>
            <Link to={`/wells/${a.well_id}`} className="alert-well">
              {a.well_name}
            </Link>
            <span className="alert-kind">
              {a.severity === "critical" ? "Critical" : "Warning"}: {KIND_LABELS[a.kind]}
            </span>
            <p>{a.message}</p>
          </div>
        </li>
      ))}
    </ul>
  );
}
