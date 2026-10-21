import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  type TooltipContentProps,
} from "recharts";
import type { NameType, ValueType } from "recharts/types/component/DefaultTooltipContent";
import { fmtDate, fmtShortDate } from "../format";
import type { ProductionPoint } from "../types";

export interface Series {
  key: keyof ProductionPoint;
  label: string;
  color: string;
}

interface Props {
  title: string;
  unit: string;
  data: ProductionPoint[];
  series: Series[];
  format: (n: number) => string;
  height?: number;
  /** Fixed y-axis range, e.g. [0, 1] for a fraction. Defaults to 0 to the data maximum. */
  domain?: [number, number];
  ticks?: number[];
}

/**
 * Daily rates over time. One unit per chart: oil and water share bbl/d,
 * gas (Mcf/d) gets its own chart rather than a second y-axis.
 */
export function RateChart({
  title,
  unit,
  data,
  series,
  format,
  height = 260,
  domain,
  ticks,
}: Props) {
  const renderTooltip = ({ active, payload, label }: TooltipContentProps<ValueType, NameType>) => {
    if (!active || !payload?.length) return null;
    return (
      <div className="chart-tooltip">
        <div className="chart-tooltip-date">{fmtDate(String(label))}</div>
        {payload.map((p) => (
          <div key={String(p.dataKey)} className="chart-tooltip-row">
            <span className="swatch" style={{ background: p.color }} />
            <span>{p.name}</span>
            <strong>
              {p.value == null ? "–" : format(Number(p.value))} {unit}
            </strong>
          </div>
        ))}
      </div>
    );
  };

  return (
    <figure className="chart">
      <figcaption className="chart-head">
        <h3>
          {title} <span className="unit">{unit}</span>
        </h3>
        {series.length > 1 && (
          <ul className="legend">
            {series.map((s) => (
              <li key={String(s.key)}>
                <span className="swatch" style={{ background: s.color }} />
                {s.label}
              </li>
            ))}
          </ul>
        )}
      </figcaption>

      {data.length === 0 ? (
        <p className="empty">No production recorded for this period.</p>
      ) : (
        <ResponsiveContainer width="100%" height={height}>
          <LineChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
            <CartesianGrid vertical={false} stroke="var(--rule)" />
            <XAxis
              dataKey="date"
              tickFormatter={fmtShortDate}
              minTickGap={40}
              tick={{ fill: "var(--muted)", fontSize: 12 }}
              axisLine={{ stroke: "var(--rule)" }}
              tickLine={false}
            />
            <YAxis
              tickFormatter={format}
              domain={domain ?? [0, "auto"]}
              ticks={ticks}
              width={56}
              tick={{ fill: "var(--muted)", fontSize: 12 }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip content={renderTooltip} cursor={{ stroke: "var(--muted)", strokeWidth: 1 }} />
            {series.map((s) => (
              <Line
                key={String(s.key)}
                type="monotone"
                dataKey={s.key}
                name={s.label}
                stroke={s.color}
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, stroke: "var(--panel)", strokeWidth: 2 }}
                isAnimationActive={false}
                connectNulls
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      )}

      {data.length > 0 && (
        <details className="chart-table">
          <summary>View as table</summary>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Date</th>
                  {series.map((s) => (
                    <th key={String(s.key)} className="num">
                      {s.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {[...data].reverse().map((row) => (
                  <tr key={row.date}>
                    <td>{fmtDate(row.date)}</td>
                    {series.map((s) => {
                      const v = row[s.key];
                      return (
                        <td key={String(s.key)} className="num">
                          {typeof v === "number" ? format(v) : "–"}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      )}
    </figure>
  );
}

export const PHASE = {
  oil: { key: "oil_bbl", label: "Oil", color: "var(--oil)" },
  water: { key: "water_bbl", label: "Water", color: "var(--water)" },
  gas: { key: "gas_mcf", label: "Gas", color: "var(--gas)" },
} satisfies Record<string, Series>;
