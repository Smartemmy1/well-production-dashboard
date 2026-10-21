import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { fmtGor, fmtMbbl, fmtPct, fmtRate, LIFT_LABELS } from "../format";
import type { Alert, WellSummary } from "../types";

type SortKey = "name" | "oil_rate" | "gas_rate" | "water_cut" | "gor" | "cum_oil";

const COLUMNS: { key: SortKey; label: string; numeric: boolean }[] = [
  { key: "name", label: "Well", numeric: false },
  { key: "oil_rate", label: "Oil bbl/d", numeric: true },
  { key: "gas_rate", label: "Gas Mcf/d", numeric: true },
  { key: "water_cut", label: "Water cut", numeric: true },
  { key: "gor", label: "GOR scf/bbl", numeric: true },
  { key: "cum_oil", label: "Cum. oil", numeric: true },
];

export function WellTable({ wells, alerts }: { wells: WellSummary[]; alerts: Alert[] }) {
  const [sort, setSort] = useState<{ key: SortKey; desc: boolean }>({ key: "name", desc: false });

  const flagged = useMemo(() => {
    const map = new Map<number, Alert["severity"]>();
    for (const a of alerts) {
      if (map.get(a.well_id) !== "critical") map.set(a.well_id, a.severity);
    }
    return map;
  }, [alerts]);

  const rows = useMemo(() => {
    const sorted = [...wells].sort((a, b) => {
      const av = a[sort.key] ?? -1;
      const bv = b[sort.key] ?? -1;
      return av < bv ? -1 : av > bv ? 1 : 0;
    });
    return sort.desc ? sorted.reverse() : sorted;
  }, [wells, sort]);

  const toggle = (key: SortKey) =>
    setSort((s) => (s.key === key ? { key, desc: !s.desc } : { key, desc: key !== "name" }));

  return (
    <div className="table-scroll">
      <table className="wells">
        <thead>
          <tr>
            {COLUMNS.map((c) => (
              <th
                key={c.key}
                className={c.numeric ? "num" : undefined}
                aria-sort={
                  sort.key === c.key ? (sort.desc ? "descending" : "ascending") : undefined
                }
              >
                <button type="button" onClick={() => toggle(c.key)}>
                  {c.label}
                  {sort.key === c.key && <span aria-hidden="true">{sort.desc ? " ▾" : " ▴"}</span>}
                </button>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((w) => {
            const severity = flagged.get(w.id);
            return (
              <tr key={w.id} className={w.status === "shut_in" ? "shut-in" : undefined}>
                <td>
                  <Link to={`/wells/${w.id}`} className="well-link">
                    {w.name}
                  </Link>
                  {severity && (
                    <span className={`flag ${severity}`} title={`Has a ${severity} alert`}>
                      {severity === "critical" ? "Critical" : "Warning"}
                    </span>
                  )}
                  <div className="sub">
                    {w.field}, {LIFT_LABELS[w.lift_type]}
                    {w.status === "shut_in" && <span className="tag">Shut in</span>}
                  </div>
                </td>
                <td className="num">{fmtRate(w.oil_rate)}</td>
                <td className="num">{fmtRate(w.gas_rate)}</td>
                <td className="num">
                  <WaterCutBar value={w.water_cut} />
                </td>
                <td className="num">{fmtGor(w.gor)}</td>
                <td className="num">{fmtMbbl(w.cum_oil)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function WaterCutBar({ value }: { value: number | null }) {
  return (
    <span className="wc">
      {fmtPct(value)}
      <span className="wc-track" aria-hidden="true">
        <span className="wc-fill" style={{ width: `${(value ?? 0) * 100}%` }} />
      </span>
    </span>
  );
}
