# scripts/run_optimizer.py
# from app.services.solver import SharedOptimizer, Trip, Vehicle, Config
import uuid

def sample_data():
    # Two companies upload trips
    trips = [
        Trip(id="T1", company_id="C1", orig=(36.752887,3.042048), dest=(36.753500,3.050000), earliest=8*60+0, latest=10*60, duration=30, service=5, demand=2, r_i0=10),
        Trip(id="T2", company_id="C1", orig=(36.753500,3.050000), dest=(36.760000,3.060000), earliest=10*60, latest=12*60, duration=30, service=5, demand=2, r_i0=12),
        Trip(id="T3", company_id="C2", orig=(36.760000,3.060000), dest=(36.770000,3.070000), earliest=9*60, latest=12*60, duration=40, service=10, demand=3, r_i0=15),
        Trip(id="T4", company_id="C2", orig=(36.770000,3.070000), dest=(36.780000,3.080000), earliest=13*60, latest=16*60, duration=45, service=10, demand=1, r_i0=8),
    ]
    vehicles = [
        Vehicle(id="V1", type_id="truck_small", capacity=6, depot=(36.750000,3.040000)),
        Vehicle(id="V2", type_id="truck_medium", capacity=4, depot=(36.740000,3.030000)),
    ]
    return trips, vehicles

if __name__ == "__main__":
    trips, vehicles = sample_data()
    cfg = Config(timeout_seconds=30, num_workers=4)
    opt = SharedOptimizer(cfg)
    result = opt.optimize(trips, vehicles, cfg)
    print("STATUS:", result.status)
    print("OBJECTIVE (vehicles used):", result.objective)
    print("METRICS:", result.metrics)
    if result.assignments:
        for a in result.assignments:
            print("--- Vehicle:", a.vehicle_id)
            for tid, st, et, last in zip(a.trip_sequence, a.start_times, a.end_times, a.is_last):
                print(f"  {tid} start={st} end={et} is_last={last}")
    if result.diagnostics:
        print("DIAGNOSTICS:", result.diagnostics)
