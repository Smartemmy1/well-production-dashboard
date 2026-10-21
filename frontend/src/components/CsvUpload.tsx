import { useRef, useState } from "react";
import { api } from "../api";
import type { UploadResult } from "../types";

/** Import daily production from a CSV export (one row per well per day). */
export function CsvUpload({ onImported }: { onImported: () => void }) {
  const input = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<UploadResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleFile(file: File | undefined) {
    if (!file) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const res = await api.upload(file);
      setResult(res);
      if (res.inserted > 0) onImported();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
      if (input.current) input.current.value = "";
    }
  }

  return (
    <div className="upload">
      <p>
        CSV columns: <code>well, date, oil_bbl, gas_mcf, water_bbl, hours_on</code>. Days already
        recorded are skipped.
      </p>
      <label className="button secondary">
        {busy ? "Importing…" : "Import CSV"}
        <input
          ref={input}
          type="file"
          accept=".csv,text/csv"
          disabled={busy}
          onChange={(e) => handleFile(e.target.files?.[0])}
          className="visually-hidden"
        />
      </label>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      {result && (
        <div className="upload-result" role="status">
          Imported {result.inserted} {result.inserted === 1 ? "day" : "days"}
          {result.skipped_duplicates > 0 && `, skipped ${result.skipped_duplicates} already recorded`}
          .
          {result.errors.length > 0 && (
            <ul>
              {result.errors.map((e) => (
                <li key={e}>{e}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
