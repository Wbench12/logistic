"""Backfill missing Valhalla polylines for existing trips.

Why:
- The DB populator (`scripts/populatedb.py`) sets `route_calculated=True` and simulates
  distance/duration, but does NOT set `route_polyline`, so the map endpoint returns
  null polylines for those trips.

Usage examples:
- Dry-run for a date:
  ./.venv/bin/python scripts/backfill_polylines.py --date 2025-12-15 --dry-run

- Backfill for a date (all companies):
  ./.venv/bin/python scripts/backfill_polylines.py --date 2025-12-15

- Backfill for a date + specific company:
  ./.venv/bin/python scripts/backfill_polylines.py --date 2025-12-15 --company-id <uuid>

Notes:
- By default we only *fill missing* fields (don’t overwrite existing distance/duration).
- If Valhalla /route fails, `ValhallaService.get_route()` may return a straight-line fallback polyline.
  Use `--require-valhalla` to skip saving fallback results.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Any, cast

# Add project root to path (same pattern as other scripts)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select

from app.core.db import engine
from app.models.company_models import Company
from app.models.trip_models import Trip
from app.services.valhalla_service import ValhallaService


@dataclass(frozen=True)
class DateRange:
	start: datetime
	end: datetime


def _parse_date_range(date_str: Optional[str], start_date: Optional[str], end_date: Optional[str]) -> DateRange:
	if date_str:
		day = datetime.strptime(date_str, "%Y-%m-%d")
		start = day.replace(hour=0, minute=0, second=0, microsecond=0)
		end = day.replace(hour=23, minute=59, second=59, microsecond=999999)
		return DateRange(start=start, end=end)

	if not start_date or not end_date:
		raise SystemExit("Provide either --date or both --start-date and --end-date")

	start_day = datetime.strptime(start_date, "%Y-%m-%d")
	end_day = datetime.strptime(end_date, "%Y-%m-%d")
	start = start_day.replace(hour=0, minute=0, second=0, microsecond=0)
	end = end_day.replace(hour=23, minute=59, second=59, microsecond=999999)
	return DateRange(start=start, end=end)


async def _backfill(
	*,
	date_range: DateRange,
	company_id: Optional[uuid.UUID],
	limit: int,
	dry_run: bool,
	require_valhalla: bool,
	max_concurrency: int,
) -> int:
	with Session(engine) as session:
		stmt = select(Trip).where(
			Trip.departure_datetime >= date_range.start,
			Trip.departure_datetime <= date_range.end,
		)

		if company_id is not None:
			stmt = stmt.where(Trip.company_id == company_id)

		# Only trips where we can compute a route and where polyline is missing
		stmt = stmt.where(
			cast(Any, Trip.departure_lat).is_not(None),
			cast(Any, Trip.departure_lng).is_not(None),
			cast(Any, Trip.arrival_lat).is_not(None),
			cast(Any, Trip.arrival_lng).is_not(None),
			cast(Any, Trip.route_polyline).is_(None),
		).limit(limit)

		trips = list(session.exec(stmt).all())

		if dry_run:
			print(f"Found {len(trips)} trips missing route_polyline (limit={limit}).")
			if trips:
				sample = trips[: min(10, len(trips))]
				print("Sample trip IDs:")
				for t in sample:
					print(f"- {t.id} (company_id={t.company_id}, departure={t.departure_point} -> arrival={t.arrival_point})")
			return 0

		if not trips:
			print("No trips need backfill.")
			return 0

		# Cache depots by company
		company_cache: dict[uuid.UUID, Company] = {}

		valhalla = ValhallaService()
		semaphore = asyncio.Semaphore(max_concurrency)

		updated = 0

		async def compute_and_update(trip: Trip) -> None:
			nonlocal updated
			async with semaphore:
				assert trip.departure_lat is not None
				assert trip.departure_lng is not None
				assert trip.arrival_lat is not None
				assert trip.arrival_lng is not None
				route = await valhalla.get_route(
					start_lat=float(trip.departure_lat),
					start_lng=float(trip.departure_lng),
					end_lat=float(trip.arrival_lat),
					end_lng=float(trip.arrival_lng),
					departure_time=trip.departure_datetime,
				)

				if require_valhalla and not bool(route.get("success")):
					return

				poly = route.get("polyline")
				if not poly:
					return

				trip.route_polyline = str(poly)
				trip.route_calculated = True

				# Fill distance/duration only if missing (don’t overwrite simulated values)
				if trip.route_distance_km is None and route.get("distance_km") is not None:
					trip.route_distance_km = float(route["distance_km"])
				if trip.route_duration_min is None and route.get("duration_min") is not None:
					trip.route_duration_min = int(float(route["duration_min"]))

				# Return route if depot exists and return polyline missing
				if trip.return_route_polyline is None:
					company = company_cache.get(trip.company_id)
					if company is None:
						company = session.get(Company, trip.company_id)
						if company:
							company_cache[trip.company_id] = company

					if company and company.depot_lat and company.depot_lng:
						assert trip.arrival_lat is not None
						assert trip.arrival_lng is not None
						ret = await valhalla.get_route(
							start_lat=float(trip.arrival_lat),
							start_lng=float(trip.arrival_lng),
							end_lat=float(company.depot_lat),
							end_lng=float(company.depot_lng),
						)
						if not (require_valhalla and not bool(ret.get("success"))):
							ret_poly = ret.get("polyline")
							if ret_poly:
								trip.return_route_polyline = str(ret_poly)
								if trip.return_distance_km is None and ret.get("distance_km") is not None:
									trip.return_distance_km = float(ret["distance_km"])
								if trip.return_duration_min is None and ret.get("duration_min") is not None:
									trip.return_duration_min = int(float(ret["duration_min"]))

				session.add(trip)
				updated += 1

		await asyncio.gather(*(compute_and_update(t) for t in trips))
		await valhalla.close()

		session.commit()

		print(f"Backfilled polylines for {updated} trips (attempted={len(trips)}).")
		if require_valhalla:
			print("Skipped saving fallback polylines when Valhalla failed (--require-valhalla).")

		return updated


def main() -> None:
	parser = argparse.ArgumentParser(description="Backfill missing route polylines for trips")
	parser.add_argument("--date", help="Single date (YYYY-MM-DD)")
	parser.add_argument("--start-date", help="Start date (YYYY-MM-DD)")
	parser.add_argument("--end-date", help="End date (YYYY-MM-DD)")
	parser.add_argument("--company-id", help="Filter by company UUID")
	parser.add_argument("--limit", type=int, default=1000, help="Max trips to process")
	parser.add_argument("--dry-run", action="store_true", help="Only report how many trips would be updated")
	parser.add_argument(
		"--require-valhalla",
		action="store_true",
		help="Only save polylines if Valhalla returned success=true (skip straight-line fallback)",
	)
	parser.add_argument("--max-concurrency", type=int, default=10, help="Max concurrent Valhalla /route calls")

	args = parser.parse_args()

	company_id = uuid.UUID(args.company_id) if args.company_id else None
	date_range = _parse_date_range(args.date, args.start_date, args.end_date)

	asyncio.run(
		_backfill(
			date_range=date_range,
			company_id=company_id,
			limit=args.limit,
			dry_run=bool(args.dry_run),
			require_valhalla=bool(args.require_valhalla),
			max_concurrency=int(args.max_concurrency),
		)
	)


if __name__ == "__main__":
	main()

