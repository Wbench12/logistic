# # optimizer/core.py
# """
# Optimization core (CP-SAT) for shared multi-company vehicle scheduling.

# - Minimal dependencies: pydantic, ortools
# - Public API: SharedOptimizer.optimize(trips, vehicles, config) -> OptimizationResult

# Notes:
# - This is a prototype baseline. Replace travel_time_minutes with your predictive matrix lookup
#   and replace default_return_distance / r_i0 with real distances from routing.
# - The code converts Pydantic models to plain dicts for safe mutation of derived fields.
# """

# from typing import List, Dict, Tuple, Optional, Any
# from dataclasses import dataclass
# from pydantic import BaseModel
# from ortools.sat.python import cp_model
# from collections import defaultdict
# import math
# import uuid
# import time


# # ----------------------------
# # Data models (Pydantic for input validation)
# # ----------------------------
# class Trip(BaseModel):
#     id: str
#     company_id: str
#     orig: Any
#     dest: Any
#     earliest: int
#     latest: int
#     duration: int
#     service: int = 0
#     demand: int = 1
#     r_i0: float = 0.0


# class Vehicle(BaseModel):
#     id: str
#     type_id: Optional[str] = None
#     capacity: int
#     depot: Any = None
#     available_from: int = 0
#     available_to: int = 24 * 60


# class Config(BaseModel):
#     timeout_seconds: float = 300.0
#     num_workers: int = 4
#     default_travel_time: int = 15
#     default_return_distance: float = 20.0
#     conservative_percentile: float = 0.9


# @dataclass
# class AssignmentResult:
#     vehicle_id: str
#     trip_sequence: List[str]
#     start_times: List[int]
#     end_times: List[int]
#     is_last: List[bool]


# @dataclass
# class OptimizationResult:
#     job_id: str
#     status: str                       # "COMPLETED"|"INFEASIBLE"|"FAILED"
#     objective: Optional[float]
#     metrics: Dict[str, Any]
#     assignments: List[AssignmentResult]
#     diagnostics: List[str]


# # ----------------------------
# # Utility functions
# # ----------------------------
# def haversine_km(a, b) -> float:
#     lat1, lon1 = a
#     lat2, lon2 = b
#     R = 6371.0
#     phi1 = math.radians(lat1)
#     phi2 = math.radians(lat2)
#     dphi = math.radians(lat2 - lat1)
#     dlambda = math.radians(lon2 - lon1)
#     x = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
#     return 2 * R * math.asin(math.sqrt(x))


# def travel_time_minutes(a, b, default=15, avg_speed_kmph=40.0) -> int:
#     try:
#         if isinstance(a, (tuple, list)) and isinstance(b, (tuple, list)):
#             km = haversine_km(a, b)
#             minutes = int(math.ceil((km / avg_speed_kmph) * 60.0))
#             return max(1, minutes)
#         if isinstance(a, int) and isinstance(b, int):
#             return 0 if a == b else default
#     except Exception:
#         pass
#     return default


# # ----------------------------
# # Core optimizer
# # ----------------------------
# class SharedOptimizer:
#     def __init__(self, config: Optional[Config] = None):
#         self.config = config or Config()

#     def optimize(self, trips: List[Trip], vehicles: List[Vehicle], config: Optional[Config] = None) -> OptimizationResult:
#         cfg = config or self.config
#         job_id = str(uuid.uuid4())
#         start_time = time.time()

#         try:
#             # Convert Pydantic models to plain dicts so we can add derived fields
#             trips_dict: Dict[str, Dict] = {t.id: t.dict() for t in trips}
#             vehicles_dict: Dict[str, Dict] = {v.id: v.dict() for v in vehicles}
#             trip_ids = list(trips_dict.keys())
#             vehicle_ids = list(vehicles_dict.keys())

#             if not trip_ids:
#                 return OptimizationResult(job_id, "INFEASIBLE", None, {}, [], ["No trips provided"])
#             if not vehicle_ids:
#                 return OptimizationResult(job_id, "INFEASIBLE", None, {}, [], ["No vehicles provided"])

#             # Preprocess time windows (store as ints on the dicts)
#             for tid, td in trips_dict.items():
#                 td["earliest_int"] = int(td.get("earliest", 0))
#                 td["latest_start_int"] = int(max(td["earliest_int"], int(td.get("latest", td["earliest_int"])) - int(td.get("duration", 0))))

#             # Precompute travel times and feasible edges
#             travel_time_cache: Dict[Tuple[str, str], int] = {}

#             def tt(a: Any, b: Any) -> int:
#                 key = (repr(a), repr(b))
#                 if key not in travel_time_cache:
#                     travel_time_cache[key] = travel_time_minutes(a, b, default=cfg.default_travel_time)
#                 return travel_time_cache[key]

#             feasible_edges: List[Tuple[str, str]] = []
#             for i, ti in trips_dict.items():
#                 for j, tj in trips_dict.items():
#                     if i == j:
#                         continue
#                     travel = tt(ti["dest"], tj["orig"])
#                     finish_i = int(ti["earliest_int"]) + int(ti.get("duration", 0)) + int(ti.get("service", 0))
#                     if finish_i + travel <= int(tj["latest_start_int"]):
#                         feasible_edges.append((i, j))

#             # Quick pre-check diagnostics: capacity and impossible windows
#             diagnostics: List[str] = []
#             total_demand = sum(int(td.get("demand", 1)) for td in trips_dict.values())
#             total_capacity = sum(int(vd.get("capacity", 0)) for vd in vehicles_dict.values())
#             if total_capacity < total_demand:
#                 diagnostics.append(f"Total vehicle capacity {total_capacity} < total demand {total_demand}")

#             impossible_windows = [tid for tid, td in trips_dict.items() if td["latest_start_int"] < td["earliest_int"]]
#             if impossible_windows:
#                 diagnostics.append(f"Trips with impossible windows: {impossible_windows}")

#             # Build CP-SAT model (first objective: minimize vehicles used)
#             model = cp_model.CpModel()

#             # Variables
#             X: Dict[Tuple[str, str], cp_model.IntVar] = {}
#             Y: Dict[Tuple[str, str, str], cp_model.IntVar] = {}
#             IsLast: Dict[Tuple[str, str], cp_model.IntVar] = {}
#             L: Dict[str, cp_model.IntVar] = {}
#             Start: Dict[str, cp_model.IntVar] = {}

#             # Create X, IsLast, L variables (for all vehicle-trip pairs)
#             for v in vehicle_ids:
#                 for i in trip_ids:
#                     X[(v, i)] = model.NewBoolVar(f"X_{v}_{i}")
#                     IsLast[(v, i)] = model.NewBoolVar(f"IsLast_{v}_{i}")
#                 L[v] = model.NewBoolVar(f"L_{v}")

#             # Create Y only for feasible edges
#             for (i, j) in feasible_edges:
#                 for v in vehicle_ids:
#                     Y[(v, i, j)] = model.NewBoolVar(f"Y_{v}_{i}_{j}")

#             # Start variables per trip (time windows)
#             for i in trip_ids:
#                 lb = int(trips_dict[i]["earliest_int"])
#                 ub = int(trips_dict[i]["latest_start_int"])
#                 if ub < lb:
#                     ub = lb
#                 Start[i] = model.NewIntVar(lb, ub, f"Start_{i}")

#             # C1: each trip assigned exactly once
#             for i in trip_ids:
#                 model.Add(sum(X[(v, i)] for v in vehicle_ids) == 1)

#             # C2/C3: sequencing and implications
#             for (i, j) in feasible_edges:
#                 for v in vehicle_ids:
#                     model.AddImplication(Y[(v, i, j)], X[(v, i)])
#                     model.AddImplication(Y[(v, i, j)], X[(v, j)])
#                     travel = tt(trips_dict[i]["dest"], trips_dict[j]["orig"])
#                     model.Add(Start[j] >= Start[i] + int(trips_dict[i].get("duration", 0)) + int(trips_dict[i].get("service", 0)) + travel).OnlyEnforceIf(Y[(v, i, j)])

#             # C4: IsLast relation
#             for v in vehicle_ids:
#                 for i in trip_ids:
#                     outs = [Y[(v, a, b)] for (a, b) in feasible_edges if a == i]
#                     if outs:
#                         model.Add(sum(outs) + IsLast[(v, i)] == X[(v, i)])
#                     else:
#                         model.Add(IsLast[(v, i)] == X[(v, i)])
#                 # Link L[v] to existence of any IsLast true
#                 islasts = [IsLast[(v, i)] for i in trip_ids]
#                 model.Add(sum(islasts) >= L[v])
#                 model.Add(sum(islasts) <= len(trip_ids) * L[v])

#             # C5: capacity per vehicle
#             for v in vehicle_ids:
#                 model.Add(sum(X[(v, i)] * int(trips_dict[i].get("demand", 1)) for i in trip_ids) <= int(vehicles_dict[v].get("capacity", 0)))

#             # C8: degree (at most one outgoing/incoming per vehicle)
#             for v in vehicle_ids:
#                 for i in trip_ids:
#                     outs = [Y[(v, a, b)] for (a, b) in feasible_edges if a == i]
#                     ins = [Y[(v, a, b)] for (a, b) in feasible_edges if b == i]
#                     if outs:
#                         model.Add(sum(outs) <= 1)
#                     if ins:
#                         model.Add(sum(ins) <= 1)

#             # C9: return distance constraint (conservative simple form)
#             for v in vehicle_ids:
#                 lhs_terms = []
#                 for i in trip_ids:
#                     lhs_terms.append(IsLast[(v, i)] * int(cfg.default_return_distance))
#                 rhs = sum(X[(v, i)] * int(trips_dict[i].get("r_i0", 0)) for i in trip_ids)
#                 if lhs_terms:
#                     model.Add(sum(lhs_terms) <= rhs)

#             # Objective 1: minimize number of vehicles used
#             model.Minimize(sum(L[v] for v in vehicle_ids))

#             solver = cp_model.CpSolver()
#             solver.parameters.max_time_in_seconds = float(cfg.timeout_seconds)
#             solver.parameters.num_search_workers = int(cfg.num_workers)

#             status = solver.Solve(model)
#             if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
#                 metrics = {"solve_time_s": time.time() - start_time}
#                 return OptimizationResult(job_id, "INFEASIBLE", None, metrics, [], diagnostics or ["No feasible solution"])

#             bestL = int(solver.ObjectiveValue())

#             # --- second phase: minimize return distance keeping bestL ---
#             model2 = cp_model.CpModel()
#             X2: Dict[Tuple[str, str], cp_model.IntVar] = {}
#             Y2: Dict[Tuple[str, str, str], cp_model.IntVar] = {}
#             IsLast2: Dict[Tuple[str, str], cp_model.IntVar] = {}
#             L2: Dict[str, cp_model.IntVar] = {}
#             Start2: Dict[str, cp_model.IntVar] = {}

#             for v in vehicle_ids:
#                 for i in trip_ids:
#                     X2[(v, i)] = model2.NewBoolVar(f"X2_{v}_{i}")
#                     IsLast2[(v, i)] = model2.NewBoolVar(f"IsLast2_{v}_{i}")
#                 L2[v] = model2.NewBoolVar(f"L2_{v}")

#             for (i, j) in feasible_edges:
#                 for v in vehicle_ids:
#                     Y2[(v, i, j)] = model2.NewBoolVar(f"Y2_{v}_{i}_{j}")

#             for i in trip_ids:
#                 lb = int(trips_dict[i]["earliest_int"])
#                 ub = int(trips_dict[i]["latest_start_int"])
#                 if ub < lb:
#                     ub = lb
#                 Start2[i] = model2.NewIntVar(lb, ub, f"Start2_{i}")

#             # Re-add constraints on model2
#             for i in trip_ids:
#                 model2.Add(sum(X2[(v, i)] for v in vehicle_ids) == 1)

#             for (i, j) in feasible_edges:
#                 for v in vehicle_ids:
#                     model2.AddImplication(Y2[(v, i, j)], X2[(v, i)])
#                     model2.AddImplication(Y2[(v, i, j)], X2[(v, j)])
#                     travel = tt(trips_dict[i]["dest"], trips_dict[j]["orig"])
#                     model2.Add(Start2[j] >= Start2[i] + int(trips_dict[i].get("duration", 0)) + int(trips_dict[i].get("service", 0)) + travel).OnlyEnforceIf(Y2[(v, i, j)])

#             for v in vehicle_ids:
#                 for i in trip_ids:
#                     outs = [Y2[(v, a, b)] for (a, b) in feasible_edges if a == i]
#                     if outs:
#                         model2.Add(sum(outs) + IsLast2[(v, i)] == X2[(v, i)])
#                     else:
#                         model2.Add(IsLast2[(v, i)] == X2[(v, i)])
#                 islasts = [IsLast2[(v, i)] for i in trip_ids]
#                 model2.Add(sum(islasts) >= L2[v])
#                 model2.Add(sum(islasts) <= len(trip_ids) * L2[v])

#             for v in vehicle_ids:
#                 model2.Add(sum(X2[(v, i)] * int(trips_dict[i].get("demand", 1)) for i in trip_ids) <= int(vehicles_dict[v].get("capacity", 0)))

#             for v in vehicle_ids:
#                 for i in trip_ids:
#                     outs = [Y2[(v, a, b)] for (a, b) in feasible_edges if a == i]
#                     ins = [Y2[(v, a, b)] for (a, b) in feasible_edges if b == i]
#                     if outs:
#                         model2.Add(sum(outs) <= 1)
#                     if ins:
#                         model2.Add(sum(ins) <= 1)

#             for v in vehicle_ids:
#                 lhs_terms2 = []
#                 for i in trip_ids:
#                     lhs_terms2.append(IsLast2[(v, i)] * int(cfg.default_return_distance))
#                 rhs2 = sum(X2[(v, i)] * int(trips_dict[i].get("r_i0", 0)) for i in trip_ids)
#                 if lhs_terms2:
#                     model2.Add(sum(lhs_terms2) <= rhs2)

#             model2.Add(sum(L2[v] for v in vehicle_ids) <= bestL)

#             total_return_terms = []
#             for v in vehicle_ids:
#                 for i in trip_ids:
#                     total_return_terms.append(IsLast2[(v, i)] * int(cfg.default_return_distance))
#             model2.Minimize(sum(total_return_terms))

#             solver2 = cp_model.CpSolver()
#             remaining_time = max(0.1, float(cfg.timeout_seconds) - (time.time() - start_time))
#             solver2.parameters.max_time_in_seconds = remaining_time
#             solver2.parameters.num_search_workers = int(cfg.num_workers)

#             status2 = solver2.Solve(model2)
#             final_solver = solver2 if status2 in (cp_model.OPTIMAL, cp_model.FEASIBLE) else solver

#             # choose which variable sets to extract from
#             if status2 in (cp_model.OPTIMAL, cp_model.FEASIBLE):
#                 X_use, Y_use, IsLast_use, Start_use = X2, Y2, IsLast2, Start2
#                 solver_for_extract = solver2
#             else:
#                 X_use, Y_use, IsLast_use, Start_use = X, Y, IsLast, Start
#                 solver_for_extract = solver

#             # Collect assignments
#             assignments: List[AssignmentResult] = []
#             for v in vehicle_ids:
#                 assigned = [i for i in trip_ids if solver_for_extract.Value(X_use[(v, i)]) == 1]
#                 if not assigned:
#                     continue

#                 next_map: Dict[str, str] = {}
#                 for (i, j) in feasible_edges:
#                     try:
#                         if solver_for_extract.Value(Y_use[(v, i, j)]) == 1:
#                             next_map[i] = j
#                     except KeyError:
#                         # variable may not exist in this variables set
#                         pass

#                 starts = [i for i in assigned if i not in next_map.values()]
#                 for s in starts:
#                     chain = [s]
#                     cur = s
#                     while cur in next_map:
#                         cur = next_map[cur]
#                         chain.append(cur)

#                     seq = chain
#                     s_times = [int(solver_for_extract.Value(Start_use[i])) for i in seq]
#                     e_times = [s_times[k] + int(trips_dict[seq[k]].get("duration", 0)) for k in range(len(seq))]
#                     is_last_flags = [bool(solver_for_extract.Value(IsLast_use[(v, seq[k])]) == 1) for k in range(len(seq))]
#                     assignments.append(AssignmentResult(vehicle_id=v, trip_sequence=seq, start_times=s_times, end_times=e_times, is_last=is_last_flags))

#             # Compute metrics
#             total_return_distance = 0.0
#             vehicles_used_count = 0
#             for v in vehicle_ids:
#                 used = False
#                 for i in trip_ids:
#                     try:
#                         if solver_for_extract.Value(IsLast_use[(v, i)]) == 1:
#                             total_return_distance += float(cfg.default_return_distance)
#                             used = True
#                     except Exception:
#                         pass
#                 if used:
#                     vehicles_used_count += 1

#             metrics = {
#                 "solve_time_s": time.time() - start_time,
#                 "num_assignments": len(assignments),
#                 "num_vehicles_used": vehicles_used_count,
#                 "total_return_distance": total_return_distance,
#                 "solver_status": solver_for_extract.StatusName(),
#             }

#             return OptimizationResult(job_id, "COMPLETED", float(bestL), metrics, assignments, diagnostics)

#         except Exception as exc:
#             return OptimizationResult(job_id=str(uuid.uuid4()), status="FAILED", objective=None, metrics={}, assignments=[], diagnostics=[str(exc)])

# # # optimizer/core.py
# # """
# # Optimization core (CP-SAT) for shared multi-company vehicle scheduling.

# # - Minimal dependencies: pydantic, ortools
# # - Public API: optimize(trips, vehicles, config) -> OptimizationResult

# # Data model:
# # - Trip: id, company_id, orig, dest, earliest, latest, duration, service, demand, r_i0
# # - Vehicle: id, type_id, capacity, depot, available_from, available_to
# # - Config: timeouts, num_workers, use_conservative_travel_time, penalty_external_assign

# # Notes:
# # - Travel times currently computed by _travel_time_minutes() which uses Haversine if coords
# #   or defaults to constant travel time between different nodes. Replace with your matrix lookup.
# # - Uses lexicographic 2-step solve:
# #     1) minimize number of vehicles used (sum L[v])
# #     2) minimize total return distance while keeping step1 value
# # - Returns assignments per vehicle and grouped by company.
# # """

# # from typing import List, Dict, Tuple, Optional, Any
# # from dataclasses import dataclass
# # from pydantic import BaseModel
# # from ortools.sat.python import cp_model
# # from collections import defaultdict
# # import math
# # import uuid
# # import time


# # # ----------------------------
# # # Data models (Pydantic for easy validation)
# # # ----------------------------
# # class Trip(BaseModel):
# #     id: str
# #     company_id: str
# #     # origin/destination: either tuple(lat, lon) or an integer node id
# #     orig: Any
# #     dest: Any
# #     earliest: int         # minutes from midnight
# #     latest: int           # minutes from midnight (latest start or finish convention)
# #     duration: int         # minutes on-site/trip time
# #     service: int = 0      # service time in minutes
# #     demand: int = 1
# #     r_i0: float = 0.0     # estimated return distance/time (used for C9)


# # class Vehicle(BaseModel):
# #     id: str
# #     type_id: Optional[str] = None
# #     capacity: int
# #     depot: Any = None
# #     available_from: int = 0
# #     available_to: int = 24 * 60


# # class Config(BaseModel):
# #     timeout_seconds: float = 300.0
# #     num_workers: int = 4
# #     default_travel_time: int = 15           # minutes fallback
# #     default_return_distance: float = 20.0   # km fallback
# #     conservative_percentile: float = 0.9    # not used in demo; for predictive times
# #     # penalty_external_assignment: int = 100000  # if you want to penalize cross-company use (optional)


# # @dataclass
# # class AssignmentResult:
# #     vehicle_id: str
# #     trip_sequence: List[str]
# #     start_times: List[int]
# #     end_times: List[int]
# #     is_last: List[bool]


# # @dataclass
# # class OptimizationResult:
# #     job_id: str
# #     status: str                       # "COMPLETED"|"INFEASIBLE"|"FAILED"
# #     objective: Optional[float]
# #     metrics: Dict[str, Any]
# #     assignments: List[AssignmentResult]
# #     diagnostics: List[str]


# # # ----------------------------
# # # Utility: simple haversine distance and travel time
# # # ----------------------------
# # def haversine_km(a, b) -> float:
# #     # a,b are (lat,lon)
# #     lat1, lon1 = a
# #     lat2, lon2 = b
# #     R = 6371.0
# #     phi1 = math.radians(lat1)
# #     phi2 = math.radians(lat2)
# #     dphi = math.radians(lat2 - lat1)
# #     dlambda = math.radians(lon2 - lon1)
# #     x = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
# #     return 2 * R * math.asin(math.sqrt(x))


# # def travel_time_minutes(a, b, default=15, avg_speed_kmph=40.0) -> int:
# #     """
# #     Return minutes travel time between a and b:
# #     - If both are coordinate pairs (lat,lon) use haversine and avg speed.
# #     - If they are integers and identical -> 0, else default fallback.
# #     """
# #     try:
# #         if isinstance(a, (tuple, list)) and isinstance(b, (tuple, list)):
# #             km = haversine_km(a, b)
# #             minutes = int(math.ceil((km / avg_speed_kmph) * 60.0))
# #             return max(1, minutes)
# #         if isinstance(a, int) and isinstance(b, int):
# #             return 0 if a == b else default
# #     except Exception:
# #         pass
# #     return default


# # # ----------------------------
# # # Core optimizer
# # # ----------------------------
# # class SharedOptimizer:
# #     def __init__(self, config: Optional[Config] = None):
# #         self.config = config or Config()

# #     def optimize(self, trips: List[Trip], vehicles: List[Vehicle], config: Optional[Config] = None) -> OptimizationResult:
# #         cfg = config or self.config
# #         job_id = str(uuid.uuid4())
# #         start_time = time.time()

# #         try:
# #             # Convert to dicts for easy access
# #             trips_dict = {t.id: t.dict() for t in trips}
# #             vehicles_dict = {v.id: v.dict() for v in vehicles}
# #             trip_ids = list(trips_dict.keys())
# #             vehicle_ids = list(vehicles_dict.keys())

# #             if not trip_ids:
# #                 return OptimizationResult(job_id, "INFEASIBLE", None, {}, [], ["No trips provided"])
# #             if not vehicle_ids:
# #                 return OptimizationResult(job_id, "INFEASIBLE", None, {}, [], ["No vehicles provided"])

# #             # Preprocess time windows   
# #             for tid, td in trips_dict.items():
# #                 td.earliest_int = int(getattr(td, "earliest", 0))
# #                 # interpret latest as latest start; ensure feasible ub
# #                 td.latest_start_int = int(max(td.earliest_int, int(getattr(td, "latest", td.earliest_int)) - int(getattr(td, "duration", 0))))

# #             # Precompute travel times and feasible edges
# #             travel_time_cache: Dict[Tuple[Any, Any], int] = {}
# #             def tt(a, b):
# #                 key = (repr(a), repr(b))
# #                 if key not in travel_time_cache:
# #                     travel_time_cache[key] = travel_time_minutes(a, b, default=cfg.default_travel_time)
# #                 return travel_time_cache[key]

# #             feasible_edges = []
# #             for i, ti in trips_dict.items():
# #                 for j, tj in trips_dict.items():
# #                     if i == j:
# #                         continue
# #                     # quick location check: allow if same node or if travel_time allows within time windows
# #                     travel = tt(ti.dest, tj.orig)
# #                     finish_i = ti.earliest_int + ti.duration + ti.service
# #                     if finish_i + travel <= tj.latest_start_int:
# #                         feasible_edges.append((i, j))

# #             # Build CP-SAT model (first objective: minimize vehicles used)
# #             model = cp_model.CpModel()
# #             # Variables
# #             X = {}   # X[v,i]
# #             Y = {}   # Y[v,i,j]
# #             IsLast = {}
# #             L = {}
# #             Start = {}

# #             for v in vehicle_ids:
# #                 for i in trip_ids:
# #                     X[(v, i)] = model.NewBoolVar(f"X_{v}_{i}")
# #                     IsLast[(v, i)] = model.NewBoolVar(f"IsLast_{v}_{i}")
# #                 L[v] = model.NewBoolVar(f"L_{v}")

# #             for (i, j) in feasible_edges:
# #                 for v in vehicle_ids:
# #                     Y[(v, i, j)] = model.NewBoolVar(f"Y_{v}_{i}_{j}")

# #             for i in trip_ids:
# #                 lb = trips_dict[i].earliest_int
# #                 ub = trips_dict[i].latest_start_int
# #                 if ub < lb:
# #                     ub = lb
# #                 Start[i] = model.NewIntVar(lb, ub, f"Start_{i}")

# #             # C1: each trip assigned exactly once
# #             for i in trip_ids:
# #                 model.Add(sum(X[(v, i)] for v in vehicle_ids) == 1)

# #             # C2/C3: sequencing and implications
# #             for (i, j) in feasible_edges:
# #                 for v in vehicle_ids:
# #                     model.AddImplication(Y[(v, i, j)], X[(v, i)])
# #                     model.AddImplication(Y[(v, i, j)], X[(v, j)])
# #                     travel = tt(trips_dict[i].dest, trips_dict[j].orig)
# #                     model.Add(Start[j] >= Start[i] + trips_dict[i].duration + trips_dict[i].service + travel).OnlyEnforceIf(Y[(v, i, j)])

# #             # C4: IsLast relation
# #             for v in vehicle_ids:
# #                 for i in trip_ids:
# #                     outs = [Y[(v, a, b)] for (a, b) in feasible_edges if a == i]
# #                     if outs:
# #                         model.Add(sum(outs) + IsLast[(v, i)] == X[(v, i)])
# #                     else:
# #                         model.Add(IsLast[(v, i)] == X[(v, i)])
# #                 islasts = [IsLast[(v, i)] for i in trip_ids]
# #                 model.Add(sum(islasts) >= L[v])
# #                 model.Add(sum(islasts) <= len(trip_ids) * L[v])

# #             # C5: capacity per vehicle
# #             for v in vehicle_ids:
# #                 model.Add(sum(X[(v, i)] * int(trips_dict[i].demand) for i in trip_ids) <= vehicles_dict[v].capacity)

# #             # C8: degree (at most one outgoing/incoming per vehicle)
# #             for v in vehicle_ids:
# #                 for i in trip_ids:
# #                     outs = [Y[(v, a, b)] for (a, b) in feasible_edges if a == i]
# #                     ins = [Y[(v, a, b)] for (a, b) in feasible_edges if b == i]
# #                     if outs:
# #                         model.Add(sum(outs) <= 1)
# #                     if ins:
# #                         model.Add(sum(ins) <= 1)

# #             # C9: return distance constraint (conservative simple form)
# #             for v in vehicle_ids:
# #                 # LHS = sum(IsLast[v,i] * return_distance_estimate)
# #                 lhs_terms = []
# #                 for i in trip_ids:
# #                     lhs_terms.append(IsLast[(v, i)] * int(cfg.default_return_distance))
# #                 # RHS = sum(X[v,i] * r_i0)
# #                 rhs = sum(X[(v, i)] * int(trips_dict[i].r_i0) for i in trip_ids)
# #                 if lhs_terms:
# #                     model.Add(sum(lhs_terms) <= rhs)

# #             # Objective 1: minimize number of vehicles used
# #             model.Minimize(sum(L[v] for v in vehicle_ids))

# #             solver = cp_model.CpSolver()
# #             solver.parameters.max_time_in_seconds = cfg.timeout_seconds
# #             solver.parameters.num_search_workers = cfg.num_workers

# #             status = solver.Solve(model)
# #             if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
# #                 return OptimizationResult(job_id, "INFEASIBLE", None, {"solve_time_s": time.time() - start_time}, [], ["No feasible solution"])

# #             bestL = int(solver.ObjectiveValue())

# #             # --- second phase: minimize return distance keeping bestL ---
# #             model2 = cp_model.CpModel()
# #             # recreate variables for model2
# #             X2 = {}
# #             Y2 = {}
# #             IsLast2 = {}
# #             L2 = {}
# #             Start2 = {}

# #             for v in vehicle_ids:
# #                 for i in trip_ids:
# #                     X2[(v, i)] = model2.NewBoolVar(f"X2_{v}_{i}")
# #                     IsLast2[(v, i)] = model2.NewBoolVar(f"IsLast2_{v}_{i}")
# #                 L2[v] = model2.NewBoolVar(f"L2_{v}")

# #             for (i, j) in feasible_edges:
# #                 for v in vehicle_ids:
# #                     Y2[(v, i, j)] = model2.NewBoolVar(f"Y2_{v}_{i}_{j}")

# #             for i in trip_ids:
# #                 lb = trips_dict[i].earliest_int
# #                 ub = trips_dict[i].latest_start_int
# #                 if ub < lb:
# #                     ub = lb
# #                 Start2[i] = model2.NewIntVar(lb, ub, f"Start2_{i}")

# #             # re-add constraints identical to above but on model2 variables
# #             # C1
# #             for i in trip_ids:
# #                 model2.Add(sum(X2[(v, i)] for v in vehicle_ids) == 1)
# #             # C2/C3
# #             for (i, j) in feasible_edges:
# #                 for v in vehicle_ids:
# #                     model2.AddImplication(Y2[(v, i, j)], X2[(v, i)])
# #                     model2.AddImplication(Y2[(v, i, j)], X2[(v, j)])
# #                     travel = tt(trips_dict[i].dest, trips_dict[j].orig)
# #                     model2.Add(Start2[j] >= Start2[i] + trips_dict[i].duration + trips_dict[i].service + travel).OnlyEnforceIf(Y2[(v, i, j)])
# #             # C4
# #             for v in vehicle_ids:
# #                 for i in trip_ids:
# #                     outs = [Y2[(v, a, b)] for (a, b) in feasible_edges if a == i]
# #                     if outs:
# #                         model2.Add(sum(outs) + IsLast2[(v, i)] == X2[(v, i)])
# #                     else:
# #                         model2.Add(IsLast2[(v, i)] == X2[(v, i)])
# #                 islasts = [IsLast2[(v, i)] for i in trip_ids]
# #                 model2.Add(sum(islasts) >= L2[v])
# #                 model2.Add(sum(islasts) <= len(trip_ids) * L2[v])
# #             # C5
# #             for v in vehicle_ids:
# #                 model2.Add(sum(X2[(v, i)] * int(trips_dict[i].demand) for i in trip_ids) <= vehicles_dict[v].capacity)
# #             # C8
# #             for v in vehicle_ids:
# #                 for i in trip_ids:
# #                     outs = [Y2[(v, a, b)] for (a, b) in feasible_edges if a == i]
# #                     ins = [Y2[(v, a, b)] for (a, b) in feasible_edges if b == i]
# #                     if outs:
# #                         model2.Add(sum(outs) <= 1)
# #                     if ins:
# #                         model2.Add(sum(ins) <= 1)
# #             # C9
# #             for v in vehicle_ids:
# #                 lhs_terms = []
# #                 for i in trip_ids:
# #                     lhs_terms.append(IsLast2[(v, i)] * int(cfg.default_return_distance))
# #                 rhs = sum(X2[(v, i)] * int(trips_dict[i].r_i0) for i in trip_ids)
# #                 if lhs_terms:
# #                     model2.Add(sum(lhs_terms) <= rhs)

# #             # maintain vehicle usage count
# #             model2.Add(sum(L2[v] for v in vehicle_ids) <= bestL)

# #             # objective2: minimize total return distance (simple sum using default_return_distance)
# #             total_return_terms = []
# #             for v in vehicle_ids:
# #                 for i in trip_ids:
# #                     total_return_terms.append(IsLast2[(v, i)] * int(cfg.default_return_distance))
# #             model2.Minimize(sum(total_return_terms))

# #             solver2 = cp_model.CpSolver()
# #             solver2.parameters.max_time_in_seconds = max(1.0, cfg.timeout_seconds - (time.time() - start_time))
# #             solver2.parameters.num_search_workers = cfg.num_workers

# #             status2 = solver2.Solve(model2)
# #             final_solver = solver2 if status2 in (cp_model.OPTIMAL, cp_model.FEASIBLE) else solver

# #             # extract solution from the solver used
# #             use_vars = (X2, Y2, IsLast2, Start2) if status2 in (cp_model.OPTIMAL, cp_model.FEASIBLE) else (X, Y, IsLast, Start)
# #             solver_for_extract = final_solver

# #             X_use, Y_use, IsLast_use, Start_use = use_vars

# #             # Collect assignments
# #             assignments: List[AssignmentResult] = []
# #             for v in vehicle_ids:
# #                 # assigned trips
# #                 assigned = [i for i in trip_ids if solver_for_extract.Value(X_use[(v, i)]) == 1]
# #                 if not assigned:
# #                     continue
# #                 # build next map
# #                 next_map = {}
# #                 for (i, j) in feasible_edges:
# #                     try:
# #                         if solver_for_extract.Value(Y_use[(v, i, j)]) == 1:
# #                             next_map[i] = j
# #                     except KeyError:
# #                         pass
# #                 # starts of chains
# #                 starts = [i for i in assigned if i not in next_map.values()]
# #                 for s in starts:
# #                     chain = [s]
# #                     cur = s
# #                     while cur in next_map:
# #                         cur = next_map[cur]
# #                         chain.append(cur)
# #                     # sequence -> start times + end times + is_last
# #                     seq = chain
# #                     s_times = [solver_for_extract.Value(Start_use[i]) for i in seq]
# #                     e_times = [s_times[k] + trips_dict[seq[k]].duration for k in range(len(seq))]
# #                     is_last_flags = [bool(solver_for_extract.Value(IsLast_use[(v, seq[k])]) == 1) for k in range(len(seq))]
# #                     assignments.append(AssignmentResult(vehicle_id=v, trip_sequence=seq, start_times=s_times, end_times=e_times, is_last=is_last_flags))

# #             total_return_distance = 0
# #             for v in vehicle_ids:
# #                 for i in trip_ids:
# #                     try:
# #                         if solver_for_extract.Value(IsLast_use[(v, i)]) == 1:
# #                             total_return_distance += cfg.default_return_distance
# #                     except Exception:
# #                         pass

# #             metrics = {
# #                 "solve_time_s": time.time() - start_time,
# #                 "num_assignments": len(assignments),
# #                 "num_vehicles": len([1 for v in vehicle_ids if any(solver_for_extract.Value(IsLast_use.get((v, i), 0)) for i in trip_ids)]),
# #                 "total_return_distance": total_return_distance,
# #                 "solver_status": solver_for_extract.StatusName(),
# #             }

# #             return OptimizationResult(job_id, "COMPLETED", float(bestL), metrics, assignments, [])

# #         except Exception as exc:
# #             return OptimizationResult(job_id=str(uuid.uuid4()), status="FAILED", objective=None, metrics={}, assignments=[], diagnostics=[str(exc)])
