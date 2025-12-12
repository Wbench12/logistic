# scripts/realistic_test.py
"""
Realistic multi-company test for the SharedOptimizer.

What each company should upload (simulated here):
- company_id (string)
- a "trip journal": list of trips with fields:
    id, company_id, orig (lat,lon), dest (lat,lon), earliest (minutes), latest (minutes),
    duration (minutes), service (minutes), demand (int), r_i0 (return distance estimate)
- a list of vehicles they provide (we simulate vehicles + owners separately)

This script:
- builds trip lists for two companies + one third-party provider
- builds vehicle list (with a vehicle_owner map)
- runs SharedOptimizer.optimize and prints results grouped by company and vehicle owner
"""

# from app.services.solver import SharedOptimizer, Trip, Vehicle, Config
import pprint
import uuid

def minutes(h, m=0):
    return h * 60 + m

def make_sample():
    # Companies
    C1 = "Company_Hydra"  # production company with local deliveries
    C2 = "Company_Kouba"  # retail company
    C3 = "ThirdParty"     # logistics provider's vehicle available to share

    # Realistic coordinates in Algiers (approx)
    # Hydra: 36.7531, 2.9958
    # Didouche Mourad: 36.7606, 3.0586
    # Bab El Oued: 36.7890, 3.0412
    # Kouba: 36.7308, 3.0839
    # El Harrach: 36.7120, 3.1042

    # Company uploads - trip journals
    trips = [
        # Company 1 trips (Hydra area)
        Trip(
            id="C1-T1",
            company_id=C1,
            orig=(36.7531, 2.9958),
            dest=(36.7606, 3.0586),
            earliest=minutes(8, 0),
            latest=minutes(10, 0),
            duration=30,
            service=5,
            demand=2,
            r_i0=8.0,
        ),
        Trip(
            id="C1-T2",
            company_id=C1,
            orig=(36.7606, 3.0586),
            dest=(36.7890, 3.0412),
            earliest=minutes(10, 30),
            latest=minutes(12, 30),
            duration=30,
            service=5,
            demand=1,
            r_i0=12.0,
        ),

        # Company 2 trips (Kouba area)
        Trip(
            id="C2-T1",
            company_id=C2,
            orig=(36.7308, 3.0839),
            dest=(36.7120, 3.1042),
            earliest=minutes(9, 0),
            latest=minutes(11, 0),
            duration=45,
            service=10,
            demand=3,
            r_i0=15.0,
        ),
        Trip(
            id="C2-T2",
            company_id=C2,
            orig=(36.7120, 3.1042),
            dest=(36.7531, 2.9958),
            earliest=minutes(13, 0),
            latest=minutes(16, 0),
            duration=40,
            service=8,
            demand=2,
            r_i0=20.0,
        ),

        # Company 1 another late trip
        Trip(
            id="C1-T3",
            company_id=C1,
            orig=(36.7890, 3.0412),
            dest=(36.7606, 3.0586),
            earliest=minutes(14, 0),
            latest=minutes(17, 0),
            duration=35,
            service=7,
            demand=1,
            r_i0=10.0,
        ),

        # Company 3 trip (third-party client of their own, but included to model variety)
        Trip(
            id="C3-T1",
            company_id=C3,
            orig=(36.7400, 3.0200),
            dest=(36.7308, 3.0839),
            earliest=minutes(8, 30),
            latest=minutes(11, 30),
            duration=30,
            service=5,
            demand=1,
            r_i0=9.0,
        ),
    ]

    # Vehicles (each company supplies vehicles — but they are all available for shared optimization)
    vehicles = [
        Vehicle(id="V1", type_id="truck_small", capacity=6, depot=(36.7531, 2.9958)),  # owned by C1
        Vehicle(id="V2", type_id="van", capacity=4, depot=(36.7308, 3.0839)),          # owned by C2
        Vehicle(id="V3", type_id="truck_medium", capacity=8, depot=(36.7400, 3.0200)), # owned by C3 (provider)
        Vehicle(id="V4", type_id="van", capacity=4, depot=(36.7531, 2.9958)),          # owned by C1 (extra)
    ]

    # Map vehicle -> owner company (optimizer core doesn't carry owner, so keep mapping externally)
    vehicle_owner = {
        "V1": C1,
        "V2": C2,
        "V3": C3,
        "V4": C1,
    }

    return trips, vehicles, vehicle_owner

def pretty_print_result(res, vehicle_owner_map):
    print("STATUS:", res.status)
    print("OBJECTIVE (vehicles used):", res.objective)
    print("METRICS:", res.metrics)
    if res.diagnostics:
        print("DIAGNOSTICS:", res.diagnostics)
    print()
    # Display assignments grouped by vehicle and show owner
    if res.assignments:
        for a in res.assignments:
            owner = vehicle_owner_map.get(a.vehicle_id, "UNKNOWN")
            print(f"--- Vehicle: {a.vehicle_id} (owner={owner})")
            for tid, st, et, last in zip(a.trip_sequence, a.start_times, a.end_times, a.is_last):
                # convert minutes to hh:mm
                def fmt(t):
                    h = int(t // 60)
                    m = int(t % 60)
                    return f"{h:02d}:{m:02d}"
                print(f"  {tid} start={fmt(st)} end={fmt(et)} is_last={last}")
    else:
        print("No assignments returned.")

def main():
    trips, vehicles, vehicle_owner = make_sample()

    # (Optional) print what each company needs to upload in production
    print("=== Upload requirements per company (example) ===")
    print("- company submits a trip journal (list of rows). Each row:")
    print("  id, orig(lat,lon) , dest(lat,lon) , earliest(minutes) , latest(minutes) , duration(min), service(min), demand(int), r_i0(km)")
    print()
    print("Simulated trip journals:")
    for t in trips:
        print(f"  company={t.company_id} trip={t.id} orig={t.orig} dest={t.dest} earliest={t.earliest} latest={t.latest} duration={t.duration}")

    print("\nStarting optimizer...\n")

    cfg = Config(timeout_seconds=30, num_workers=4, default_travel_time=12, default_return_distance=18)
    opt = SharedOptimizer(cfg)

    # Run optimization
    result = opt.optimize(trips, vehicles, cfg)

    # Print nicely grouped by vehicle owner
    pretty_print_result(result, vehicle_owner)

if __name__ == "__main__":
    main()
