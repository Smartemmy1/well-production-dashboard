"""API tests through FastAPI's TestClient."""

from datetime import date

from app.seed import seed


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_create_and_fetch_well(client):
    payload = {"name": "NW-01", "field": "North", "start_date": "2026-01-01"}
    created = client.post("/api/wells", json=payload)
    assert created.status_code == 201
    well_id = created.json()["id"]

    fetched = client.get(f"/api/wells/{well_id}").json()
    assert fetched["name"] == "NW-01"
    assert fetched["status"] == "active"
    assert fetched["oil_rate"] == 0


def test_duplicate_well_name_conflicts(client):
    payload = {"name": "NW-01", "field": "North", "start_date": "2026-01-01"}
    client.post("/api/wells", json=payload)
    assert client.post("/api/wells", json=payload).status_code == 409


def test_unknown_well_is_404(client):
    assert client.get("/api/wells/999").status_code == 404


def test_well_summary_rates(client, make_well):
    well = make_well(oil=1000, water=250, gas=900)
    body = client.get(f"/api/wells/{well.id}").json()
    assert body["oil_rate"] == 1000
    assert body["water_cut"] == 0.2
    assert body["gor"] == 900
    assert body["uptime"] == 1.0
    assert body["cum_oil"] == 40 * 1000


def test_filter_wells_by_field(client, make_well):
    make_well(name="A-1", field="Alpha")
    make_well(name="B-1", field="Beta")
    names = [w["name"] for w in client.get("/api/wells", params={"field": "Beta"}).json()]
    assert names == ["B-1"]
    assert client.get("/api/wells/fields").json() == ["Alpha", "Beta"]


def test_patch_status(client, make_well):
    well = make_well()
    res = client.patch(f"/api/wells/{well.id}", json={"status": "shut_in"})
    assert res.json()["status"] == "shut_in"


def test_add_production_and_reject_duplicate_day(client, make_well):
    well = make_well(days=1)
    day = {"date": "2020-01-01", "oil_bbl": 500, "gas_mcf": 400, "water_bbl": 50}
    assert client.post(f"/api/wells/{well.id}/production", json=day).status_code == 201
    assert client.post(f"/api/wells/{well.id}/production", json=day).status_code == 409


def test_negative_volumes_rejected(client, make_well):
    well = make_well(days=1)
    bad = {"date": "2020-01-01", "oil_bbl": -5, "gas_mcf": 0, "water_bbl": 0}
    assert client.post(f"/api/wells/{well.id}/production", json=bad).status_code == 422


def test_production_date_filter(client, make_well):
    well = make_well(days=10)
    points = client.get(f"/api/wells/{well.id}/production").json()
    assert len(points) == 10
    since = points[5]["date"]
    filtered = client.get(f"/api/wells/{well.id}/production", params={"start": since}).json()
    assert len(filtered) == 5


def test_delete_well_removes_production(client, make_well):
    well = make_well()
    assert client.delete(f"/api/wells/{well.id}").status_code == 204
    assert client.get(f"/api/wells/{well.id}/production").status_code == 404


def test_csv_upload(client, make_well):
    make_well(name="AR-01", days=1)
    csv = (
        "well,date,oil_bbl,gas_mcf,water_bbl,hours_on\n"
        "AR-01,2020-01-01,100,80,10,24\n"
        "AR-01,2020-01-02,110,85,12,\n"
        "AR-01,2020-01-02,110,85,12,24\n"  # duplicate within file
        "ZZ-99,2020-01-01,1,1,1,24\n"  # unknown well
        "AR-01,not-a-date,1,1,1,24\n"  # bad value
    )
    res = client.post("/api/production/upload", files={"file": ("p.csv", csv, "text/csv")})
    body = res.json()
    assert body["inserted"] == 2
    assert body["skipped_duplicates"] == 1
    assert len(body["errors"]) == 2


def test_csv_missing_columns(client):
    res = client.post(
        "/api/production/upload", files={"file": ("p.csv", "well,date\n", "text/csv")}
    )
    assert res.status_code == 400


def test_dashboard_and_alerts_on_demo_data(client, db):
    seed(db, end=date(2026, 6, 30))
    summary = client.get("/api/dashboard", params={"days": 30}).json()
    assert summary["total_wells"] == 12
    assert summary["active_wells"] == 11
    assert summary["as_of"] == "2026-06-30"
    assert len(summary["series"]) == 30
    assert summary["oil_rate"] > 0

    alerts = client.get("/api/alerts").json()
    by_well = {a["well_name"]: (a["kind"], a["severity"]) for a in alerts}
    assert by_well["GB-03"] == ("production_drop", "critical")
    assert by_well["AR-02"] == ("production_drop", "warning")
    assert by_well["PS-02"] == ("high_water_cut", "warning")
    assert by_well["PS-04"] == ("no_production", "critical")
    assert "AR-04" not in by_well  # shut in
    assert summary["alert_count"] == len(alerts)
    assert alerts[0]["severity"] == "critical"


def test_dashboard_field_filter(client, db):
    seed(db, end=date(2026, 6, 30))
    summary = client.get("/api/dashboard", params={"field": "Placentia Shelf"}).json()
    assert summary["total_wells"] == 4


def test_shut_in_well_reports_zero_rate(client, make_well):
    well = make_well()
    client.patch(f"/api/wells/{well.id}", json={"status": "shut_in"})
    body = client.get(f"/api/wells/{well.id}").json()
    assert body["oil_rate"] == 0
    assert body["last_date"] is not None


def test_future_production_date_rejected(client, make_well):
    well = make_well(days=1)
    future = {"date": "2999-01-01", "oil_bbl": 1, "gas_mcf": 1, "water_bbl": 1}
    assert client.post(f"/api/wells/{well.id}/production", json=future).status_code == 422
