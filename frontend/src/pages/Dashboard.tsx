import { useSearchParams } from "react-router-dom";
import { api } from "../api";
import { AlertList } from "../components/AlertList";
import { CsvUpload } from "../components/CsvUpload";
import { Figures } from "../components/Figures";
import { PHASE, RateChart } from "../components/RateChart";
import { WellTable } from "../components/WellTable";
import { fmtDate, fmtPct, fmtRate } from "../format";
import { useApi } from "../useApi";

const RANGES = [30, 90, 180, 365];

export function Dashboard() {
  // Filters live in the URL so a filtered view can be bookmarked or shared.
  const [params, setParams] = useSearchParams();
  const field = params.get("field") || undefined;
  const days = Number(params.get("days")) || 90;

  const fields = useApi(() => api.fields(), []);
  const summary = useApi(() => api.dashboard(field, days), [field, days]);
  const wells = useApi(() => api.wells(field), [field]);
  const alerts = useApi(() => api.alerts(field), [field]);

  const update = (key: string, value: string | undefined) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next, { replace: true });
  };

  const reloadAll = () => {
    summary.reload();
    wells.reload();
    alerts.reload();
  };

  const s = summary.data;
  const error = summary.error || wells.error || alerts.error;

  return (
    <main className="page">
      <header className="page-head">
        <div>
          <h1>{field ?? "All fields"}</h1>
          <p className="as-of">
            {s?.as_of ? `Latest report ${fmtDate(s.as_of)}` : "Waiting for production data"}
          </p>
        </div>
        <div className="filters" role="group" aria-label="Filters">
          <label>
            <span className="visually-hidden">Field</span>
            <select value={field ?? ""} onChange={(e) => update("field", e.target.value)}>
              <option value="">All fields</option>
              {fields.data?.map((f) => (
                <option key={f} value={f}>
                  {f}
                </option>
              ))}
            </select>
          </label>
          <div className="segmented" role="radiogroup" aria-label="Time range">
            {RANGES.map((r) => (
              <button
                key={r}
                type="button"
                role="radio"
                aria-checked={days === r}
                onClick={() => update("days", String(r))}
              >
                {r === 365 ? "1y" : `${r}d`}
              </button>
            ))}
          </div>
        </div>
      </header>

      {error && (
        <p className="banner-error" role="alert">
          Could not load data: {error}. Check that the API is running on port 8000.
        </p>
      )}

      {s && (
        <Figures
          items={[
            { label: "Oil", value: fmtRate(s.oil_rate), unit: "bbl/d", phase: "oil" },
            { label: "Gas", value: fmtRate(s.gas_rate), unit: "Mcf/d", phase: "gas" },
            { label: "Water", value: fmtRate(s.water_rate), unit: "bbl/d", phase: "water" },
            { label: "Water cut", value: fmtPct(s.water_cut) },
            { label: "Wells producing", value: `${s.active_wells} of ${s.total_wells}` },
          ]}
        />
      )}
      <p className="note">Rates are 7-day averages.</p>

      <section className="charts">
        <div className="panel wide">
          <RateChart
            title="Liquids"
            unit="bbl/d"
            data={s?.series ?? []}
            series={[PHASE.oil, PHASE.water]}
            format={fmtRate}
          />
        </div>
        <div className="panel">
          <RateChart
            title="Gas"
            unit="Mcf/d"
            data={s?.series ?? []}
            series={[PHASE.gas]}
            format={fmtRate}
          />
        </div>
      </section>

      <section className="split">
        <div className="panel">
          <h2>Wells</h2>
          {wells.data && <WellTable wells={wells.data} alerts={alerts.data ?? []} />}
        </div>
        <aside className="side">
          <div className="panel">
            <h2>
              Needs attention
              {alerts.data && alerts.data.length > 0 && (
                <span className="count">{alerts.data.length}</span>
              )}
            </h2>
            {alerts.data && <AlertList alerts={alerts.data} />}
          </div>
          <div className="panel">
            <h2>Import production</h2>
            <CsvUpload onImported={reloadAll} />
          </div>
        </aside>
      </section>
    </main>
  );
}
