// Shapes returned by the FastAPI backend (see backend/app/schemas.py).

export type WellStatus = "active" | "shut_in";
export type LiftType = "natural_flow" | "esp" | "gas_lift" | "rod_pump";

export interface WellSummary {
  id: number;
  name: string;
  field: string;
  lift_type: LiftType;
  status: WellStatus;
  start_date: string;
  last_date: string | null;
  oil_rate: number;
  gas_rate: number;
  water_rate: number;
  water_cut: number | null;
  gor: number | null;
  uptime: number | null;
  cum_oil: number;
}

export interface ProductionPoint {
  date: string;
  oil_bbl: number;
  gas_mcf: number;
  water_bbl: number;
  hours_on?: number | null;
  water_cut: number | null;
  gor: number | null;
}

export interface Alert {
  well_id: number;
  well_name: string;
  field: string;
  kind: "production_drop" | "high_water_cut" | "no_production";
  severity: "warning" | "critical";
  message: string;
}

export interface DashboardSummary {
  as_of: string | null;
  active_wells: number;
  total_wells: number;
  oil_rate: number;
  gas_rate: number;
  water_rate: number;
  water_cut: number | null;
  alert_count: number;
  series: ProductionPoint[];
}

export interface ProductionInput {
  date: string;
  oil_bbl: number;
  gas_mcf: number;
  water_bbl: number;
  hours_on: number;
}

export interface UploadResult {
  inserted: number;
  skipped_duplicates: number;
  errors: string[];
}
