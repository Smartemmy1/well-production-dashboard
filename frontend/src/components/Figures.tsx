export interface Figure {
  label: string;
  value: string;
  unit?: string;
  /** Phase color shown as a short bar under the number, matching the charts. */
  phase?: "oil" | "gas" | "water";
}

/** A row of headline figures. Phase figures carry the same color as their chart line. */
export function Figures({ items }: { items: Figure[] }) {
  return (
    <dl className="figures">
      {items.map((f) => (
        <div key={f.label} className={f.phase ? `figure phase-${f.phase}` : "figure"}>
          <dt>{f.label}</dt>
          <dd>
            {f.value}
            {f.unit && <span className="unit"> {f.unit}</span>}
          </dd>
        </div>
      ))}
    </dl>
  );
}
