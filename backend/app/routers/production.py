"""Bulk CSV import of daily production, as field data is usually delivered."""

import csv
import io

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ProductionRecord, Well
from app.schemas import ProductionIn, UploadResult

router = APIRouter(prefix="/api/production", tags=["production"])

REQUIRED_COLUMNS = {"well", "date", "oil_bbl", "gas_mcf", "water_bbl"}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_REPORTED_ERRORS = 20


@router.post("/upload", response_model=UploadResult)
async def upload_csv(file: UploadFile, db: Session = Depends(get_db)):
    """Import a CSV with columns: well, date, oil_bbl, gas_mcf, water_bbl[, hours_on].

    Rows for unknown wells or with invalid values are reported back, not imported.
    Rows for a well/date that already exists are skipped, so re-uploading is safe.
    """
    raw = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File is larger than 5 MB")
    try:
        text = raw.decode("utf-8-sig")  # tolerate the BOM Excel adds
    except UnicodeDecodeError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "File must be UTF-8 encoded CSV") from None

    reader = csv.DictReader(io.StringIO(text))
    columns = {c.strip().lower() for c in (reader.fieldnames or [])}
    missing = REQUIRED_COLUMNS - columns
    if missing:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"Missing columns: {', '.join(sorted(missing))}"
        )

    wells = {w.name: w.id for w in db.scalars(select(Well))}
    pairs = db.execute(select(ProductionRecord.well_id, ProductionRecord.date))
    existing = {(well_id, day) for well_id, day in pairs}

    inserted, skipped, errors = 0, 0, []
    for line_no, row in enumerate(reader, start=2):  # line 1 is the header
        row = {k.strip().lower(): (v or "").strip() for k, v in row.items() if k}
        well_id = wells.get(row["well"])
        if well_id is None:
            errors.append(f"Line {line_no}: unknown well '{row['well']}'")
            continue
        try:
            data = ProductionIn(
                date=row["date"],
                oil_bbl=row["oil_bbl"] or 0,
                gas_mcf=row["gas_mcf"] or 0,
                water_bbl=row["water_bbl"] or 0,
                hours_on=row.get("hours_on") or 24,
            )
        except ValidationError as exc:
            first = exc.errors()[0]
            errors.append(f"Line {line_no}: {first['loc'][0]} - {first['msg']}")
            continue
        if (well_id, data.date) in existing:
            skipped += 1
            continue
        db.add(ProductionRecord(well_id=well_id, **data.model_dump()))
        existing.add((well_id, data.date))
        inserted += 1

    db.commit()
    if len(errors) > MAX_REPORTED_ERRORS:
        errors = errors[:MAX_REPORTED_ERRORS] + [f"...and {len(errors) - MAX_REPORTED_ERRORS} more"]
    return UploadResult(inserted=inserted, skipped_duplicates=skipped, errors=errors)
