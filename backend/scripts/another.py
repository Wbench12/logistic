# scripts/realistic_compare.py
"""
Build realistic test instance, run:
 - per-company-only optimization (each company runs optimizer on its own trips + own vehicles)
 - shared optimization (all trips, all vehicles)
Produce a JSON file for visualization and print a summary.

Usage:
  python scripts/realistic_compare.py
Produces:
  - prints summary to stdout
  - writes scripts/optimizer_comparison.json
"""

import json
import time
from app.services.solver import SharedOptimizer, Trip, Vehicle, Config
from collections import defaultdict

def minutes(h, m=0):
    return h * 60 + m

def build_instance():
    C1 = "Company_Hydra"
    C2 = "Company_Kouba"
    C3 = "ThirdParty"

    trips = [
        Trip(id="C1-T1", company_id=C1, orig=(36.7531, 2.9958), dest=(36.7606, 3.0586),
             earliest=minutes(8,0), latest=minutes(10,0), duration=30, service=5, demand=2, r_i0=8.0),
        Trip(id="C1-T2", company_id=C1, orig=(36.7606, 3.0586), dest=(36.7890, 3.0412),
             earliest=minutes(10,30), latest=minutes(12,30), duration=30, service=5, demand=1, r_i0=12.0),
        Trip(id="C1-T3", company_id=C1, orig=(36.7890, 3.0412), dest=(36.7606, 3.0586),
             earliest=minutes(14,0), latest=minutes(17,0), duration=35, service=7, demand=1, r_i0=10.0),
        Trip(id="C2-T1", company_id=C2, orig=(36.7308, 3.0839), dest=(36.7120, 3.1042),
             earliest=minutes(9,0), latest=minutes(11,0), duration=45, service=10, demand=3, r_i0=15.0),
        Trip(id="C2-T2", company_id=C2, orig=(36.7120, 3.1042), dest=(36.7531, 2.9958),
             earliest=minutes(13,0), latest=minutes(16,0), duration=40, service=8, demand=2, r_i0=20.0),
        Trip(id="C3-T1", company_id=C3, orig=(36.7400, 3.0200), dest=(36.7308, 3.0839),
             earliest=minutes(8,30), latest=minutes(11,30), duration=30, service=5, demand=1, r_i0=9.0),
    ]

    vehicles = [
        Vehicle(id="V1", type_id="truck_small", capacity=6, depot=(36.7531, 2.9958)),  # C1
        Vehicle(id="V2", type_id="van", capacity=4, depot=(36.7308, 3.0839)),          # C2
        Vehicle(id="V3", type_id="truck_medium", capacity=8, depot=(36.7400, 3.0200)), # C3 provider
        Vehicle(id="V4", type_id="van", capacity=4, depot=(36.7531, 2.9958)),          # C1 extra
    ]

    vehicle_owner = {
        "V1": C1,
        "V2": C2,
        "V3": C3,
        "V4": C1,
    }

    return trips, vehicles, vehicle_owner

def summarize_result(res):
    # res is OptimizationResult
    return {
        "status": res.status,
        "objective": res.objective,
        "metrics": res.metrics,
        "diag": res.diagnostics
    }

def convert_assignments_to_map(assignments):
    # assignments: list of AssignmentResult dataclasses
    out = {}
    for a in assignments:
        out[a.vehicle_id] = a.trip_sequence
    return out

def run_per_company(trips, vehicles, vehicle_owner, cfg):
    # group trips by company and run optimizer per company with only company vehicles
    trips_by_company = defaultdict(list)
    vehicles_by_company = defaultdict(list)
    for t in trips:
        trips_by_company[t.company_id].append(t)
    for v in vehicles:
        owner = vehicle_owner.get(v.id)
        vehicles_by_company[owner].append(v)

    per_company_output = {"assignments": {}, "metrics": {}, "diagnostics": []}
    for comp, comp_trips in trips_by_company.items():
        comp_vehicles = vehicles_by_company.get(comp, [])
        if not comp_vehicles:
            # mark as infeasible: no vehicle for this company
            per_company_output["diagnostics"].append(f"No vehicles for company {comp}")
            continue
        opt = SharedOptimizer(cfg)
        t0 = time.time()
        res = opt.optimize(comp_trips, comp_vehicles, cfg)
        elapsed = time.time() - t0
        # convert assignments
        if res.status == "COMPLETED":
            per_company_output["assignments"].update(convert_assignments_to_map(res.assignments))
            per_company_output["metrics"][comp] = {
                "solve_time_s": elapsed,
                "objective": res.objective,
                "metrics": res.metrics
            }
        else:
            per_company_output["diagnostics"].append(f"Company {comp} run status: {res.status} diag: {res.diagnostics}")
    return per_company_output

def run_shared(trips, vehicles, cfg):
    opt = SharedOptimizer(cfg)
    t0 = time.time()
    res = opt.optimize(trips, vehicles, cfg)
    elapsed = time.time() - t0
    shared_out = {
        "assignments": convert_assignments_to_map(res.assignments) if res.status == "COMPLETED" else {},
        "metrics": {"solve_time_s": elapsed, "objective": res.objective, "metrics": res.metrics},
        "diagnostics": res.diagnostics
    }
    return shared_out

def main():
    trips, vehicles, vehicle_owner = build_instance()
    cfg = Config(timeout_seconds=30, num_workers=4, default_travel_time=12, default_return_distance=18)

    # BEFORE structure (trip and vehicle info) for the HTML
    before = {"trips": {}, "vehicles": {}}
    for t in trips:
        before["trips"][t.id] = {
            "company": t.company_id,
            "orig": t.orig,
            "dest": t.dest,
            "time": f"{t.earliest}-{t.latest}",
            "duration": t.duration
        }
    for v in vehicles:
        before["vehicles"][v.id] = {"owner": vehicle_owner.get(v.id), "depot": v.depot, "capacity": v.capacity}

    # Run per-company-only
    per_company = run_per_company(trips, vehicles, vehicle_owner, cfg)

    # Run shared
    shared = run_shared(trips, vehicles, cfg)

    # Summary printed to console
    print("=== COMPARISON SUMMARY ===")
    print("Per-company-only assignments (vehicle->trips):")
    print(json.dumps(per_company["assignments"], indent=2))
    print("Per-company diagnostics:", per_company.get("diagnostics", []))
    print()
    print("Shared assignments (vehicle->trips):")
    print(json.dumps(shared["assignments"], indent=2))
    print("Shared diagnostics:", shared.get("diagnostics", []))
    print()
    print("Per-company metrics:", json.dumps(per_company.get("metrics", {}), indent=2))
    print("Shared metrics:", json.dumps(shared.get("metrics", {}), indent=2))

    # Persist comparison file for HTML visualization
    out = {
        "before": before,
        "per_company": per_company,
        "shared": shared
    }
    out_path = "./optimizer_comparison.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\nWrote comparison JSON to {out_path}")

if __name__ == "__main__":
    main()
