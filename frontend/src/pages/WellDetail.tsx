import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { AlertList } from "../components/AlertList";
import { Figures } from "../components/Figures";
import { ProductionForm } from "../components/ProductionForm";
import { PHASE, RateChart } from "../components/RateChart";
import { daysBefore, fmtDate, fmtGor, fmtMbbl, fmtPct, fmtRate, LIFT_LABELS } from "../format";
import { useApi } from "../useApi";

const pctFormat = (n: number) => `${(n * 100).toFixed(0)}%`;

export function WellDetail() {
  const id = Number(useParams().id);
  const [days, setDays] = useState(180);
  const [saving, setSaving] = useState(false);

  const well = useApi(() => api.well(id), [id]);
  const last = well.data?.last_date;
  const production = useApi(
    () => api.production(id, last ? daysBefore(last, days) : undefined),
    [id, last, days],
  );
  const alerts = useApi(async () => (await api.alerts()).filter((a) => a.well_id === id), [id]);

  if (well.error) {
    return (
      <main className="page">
        <Link to="/" className="back">
          Back to dashboard
        </Link>
        <p className="banner-error" role="alert">
          {well.error}
        </p>
      </main>
    );
  }
  const w = well.data;
  if (!w) return <main className="page" aria-busy="true" />;

  const reload = () => {
    well.reload();
    production.reload();
    alerts.reload();
  };

  async function toggleStatus() {
    setSaving(true);
    try {
      await api.setStatus(id, w!.status === "active" ? "shut_in" : "active");
      reload();
    } finally {
      setSaving(false);
    }
  }

  const data = production.data ?? [];

  return (
    <main className="page">
      <Link to="/" className="back">
        Back to dashboard
      </Link>
      <header className="page-head">
        <div>
          <h1>{w.name}</h1>
          <p className="as-of">
            {w.field}, {LIFT_LABELS[w.lift_type]}, online since {fmtDate(w.start_date)}
          </p>
        </div>
        <div className="filters">
          <span className={`status ${w.status}`}>
            {w.status === "active" ? "Producing" : "Shut in"}
          </span>
          <button type="button" className="button secondary" onClick={toggleStatus} disabled={saving}>
            {w.status === "active" ? "Shut in well" : "Return to production"}
          </button>
        </div>
      </header>

      <Figures
        items={[
          { label: "Oil", value: fmtRate(w.oil_rate), unit: "bbl/d", phase: "oil" },
          { label: "Gas", value: fmtRate(w.gas_rate), unit: "Mcf/d", phase: "gas" },
          { label: "Water", value: fmtRate(w.water_rate), unit: "bbl/d", phase: "water" },
          { label: "Water cut", value: fmtPct(w.water_cut) },
          { label: "GOR", value: fmtGor(w.gor), unit: "scf/bbl" },
          { label: "Uptime", value: fmtPct(w.uptime) },
          { label: "Cumulative oil", value: fmtMbbl(w.cum_oil) },
        ]}
      />
      <p className="note">
        Rates are 7-day averages to {fmtDate(w.last_date)}.
        {w.status === "shut_in" && " Shut-in wells report zero rate."}
      </p>

      {alerts.data && alerts.data.length > 0 && (
        <section className="panel">
          <h2>Needs attention</h2>
          <AlertList alerts={alerts.data} />
        </section>
      )}

      <div className="segmented range-row" role="radiogroup" aria-label="Time range">
        {[30, 90, 180, 365].map((r) => (
          <button key={r} type="button" role="radio" aria-checked={days === r} onClick={() => setDays(r)}>
            {r === 365 ? "1y" : `${r}d`}
          </button>
        ))}
      </div>

      <section className="charts">
        <div className="panel wide">
          <RateChart title="Liquids" unit="bbl/d" data={data} series={[PHASE.oil, PHASE.water]} format={fmtRate} />
        </div>
        <div className="panel">
          <RateChart title="Gas" unit="Mcf/d" data={data} series={[PHASE.gas]} format={fmtRate} />
        </div>
        <div className="panel">
          <RateChart
            title="Water cut"
            unit="%"
            data={data}
            series={[{ key: "water_cut", label: "Water cut", color: "var(--water)" }]}
            format={pctFormat}
            domain={[0, 1]}
            ticks={[0, 0.25, 0.5, 0.75, 1]}
            height={200}
          />
        </div>
        <div className="panel">
          <RateChart
            title="Gas-oil ratio"
            unit="scf/bbl"
            data={data}
            series={[{ key: "gor", label: "GOR", color: "var(--gas)" }]}
            format={fmtRate}
            height={200}
          />
        </div>
      </section>

      <section className="panel narrow">
        <h2>Record a day</h2>
        <ProductionForm wellId={id} onSaved={reload} />
      </section>
    </main>
  );
}
