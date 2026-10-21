import { useState, type ChangeEvent, type FormEvent } from "react";
import { api } from "../api";

const today = () => new Date().toISOString().slice(0, 10);

const EMPTY = { date: today(), oil_bbl: "", gas_mcf: "", water_bbl: "", hours_on: "24" };

/** Enter one day of measured production for a well. */
export function ProductionForm({ wellId, onSaved }: { wellId: number; onSaved: () => void }) {
  const [values, setValues] = useState(EMPTY);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const set = (key: keyof typeof EMPTY) => (e: ChangeEvent<HTMLInputElement>) =>
    setValues((v) => ({ ...v, [key]: e.target.value }));

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setSaved(null);
    try {
      await api.addProduction(wellId, {
        date: values.date,
        oil_bbl: Number(values.oil_bbl),
        gas_mcf: Number(values.gas_mcf),
        water_bbl: Number(values.water_bbl),
        hours_on: Number(values.hours_on),
      });
      setSaved(values.date);
      setValues({ ...EMPTY, date: values.date });
      onSaved();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="form" onSubmit={submit}>
      <label>
        Date
        <input type="date" required value={values.date} onChange={set("date")} />
      </label>
      <label>
        Oil (bbl)
        <input type="number" min="0" step="any" required value={values.oil_bbl} onChange={set("oil_bbl")} />
      </label>
      <label>
        Gas (Mcf)
        <input type="number" min="0" step="any" required value={values.gas_mcf} onChange={set("gas_mcf")} />
      </label>
      <label>
        Water (bbl)
        <input type="number" min="0" step="any" required value={values.water_bbl} onChange={set("water_bbl")} />
      </label>
      <label>
        Hours on
        <input type="number" min="0" max="24" step="0.1" required value={values.hours_on} onChange={set("hours_on")} />
      </label>
      <div className="form-actions">
        <button type="submit" className="button" disabled={busy}>
          {busy ? "Saving…" : "Save day"}
        </button>
        {saved && <span role="status">Saved {saved}.</span>}
        {error && (
          <span className="form-error" role="alert">
            {error}
          </span>
        )}
      </div>
    </form>
  );
}
