"""Gates impedem uso científico com parâmetros e serviço pendentes."""
REQUIRED = (
    "fleet_service_schedule_verified", "individual_charging_mapping_verified",
    "pv_roof_limit_reconciled", "chp_fuel_contract_verified",
    "gas_fleet_and_fueling_verified", "economic_cost_components_verified",
    "discounted_pkm_verified", "grid_reinforcement_cost_verified",
    "scenario_policy_approved", "time_series_provenance_verified",
)

def readiness(evidence: dict):
    pending = [k for k in REQUIRED if evidence.get(k) is not True]
    return {"status":"READY" if not pending else "BLOCKED_PENDING_EVIDENCE",
            "pending":pending,"ready":not pending}
