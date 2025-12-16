"""
Test Optimization Module for Collaborative Logistics Platform
Tests the empty-return minimization algorithm with real data
"""

import sys
import os
import json
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, cast
import uuid
import webbrowser

# Add project to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from sqlmodel import Session, create_engine, select
from app.core.config import settings
from app.models.trip_models import Trip, TripStatus, OptimizationBatch
from app.models.company_models import Company, Vehicle
from app.services.optimization import optimize_trips_for_date
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OptimizationTester:
    def __init__(self):
        """Initialize with database connection"""
        self.db_url = str(settings.SQLALCHEMY_DATABASE_URI)
        self.engine = create_engine(self.db_url)
        logger.info(f"✅ Connected to database: {settings.POSTGRES_DB}")

    def find_best_planned_trip_date(
        self,
        *,
        min_companies: int = 2,
        min_trips: int = 4,
        lookahead_days: int = 60,
    ) -> Optional[datetime]:
        """Pick a date that makes cross-company optimization meaningful.

        Preference order:
        1) Dates with >= min_companies and >= min_trips planned trips
        2) Otherwise, the earliest date with any planned trips
        """
        with Session(self.engine) as session:
            rows = session.exec(
                select(Trip.departure_datetime, Trip.company_id)
                .where(Trip.status == TripStatus.PLANNED)
                .where(Trip.assigned_vehicle_id == None)
                .order_by(cast(Any, Trip.departure_datetime))
                .limit(5000)
            ).all()

            if not rows:
                return None

            by_date: dict[datetime, dict[str, Any]] = {}
            for dt, company_id in rows:
                if not dt:
                    continue
                day = dt.replace(hour=0, minute=0, second=0, microsecond=0)
                info = by_date.setdefault(day, {"trips": 0, "companies": set()})
                info["trips"] += 1
                info["companies"].add(str(company_id))

            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            candidates: list[tuple[int, int, datetime]] = []
            fallback: Optional[datetime] = None
            for day, info in by_date.items():
                if day < today - timedelta(days=1):
                    continue
                if day > today + timedelta(days=lookahead_days):
                    continue
                if fallback is None:
                    fallback = day
                trips = int(info["trips"])
                companies = len(info["companies"])
                if companies >= min_companies and trips >= min_trips:
                    candidates.append((companies, trips, day))

            if candidates:
                candidates.sort(key=lambda x: (x[0], x[1], -x[2].timestamp()), reverse=True)
                return candidates[0][2]

            return fallback
    
    def analyze_global_day(self, target_date: datetime) -> dict[str, Any]:
        """Basic stats for planned trips + available vehicles across all companies."""
        with Session(self.engine) as session:
            start_date = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=1)

            trips = session.exec(
                select(Trip)
                .where(Trip.status == TripStatus.PLANNED)
                .where(Trip.assigned_vehicle_id == None)
                .where(Trip.departure_datetime >= start_date)
                .where(Trip.departure_datetime < end_date)
            ).all()

            vehicles = session.exec(
                select(Vehicle)
                .where(Vehicle.is_active == True)
            ).all()

            trips_by_company: dict[str, int] = {}
            for t in trips:
                key = str(t.company_id)
                trips_by_company[key] = trips_by_company.get(key, 0) + 1

            vehicles_by_company: dict[str, int] = {}
            for v in vehicles:
                key = str(v.company_id)
                vehicles_by_company[key] = vehicles_by_company.get(key, 0) + 1

            return {
                "planned_trips": len(trips),
                "companies_with_trips": len(trips_by_company),
                "active_vehicles": len(vehicles),
                "trips_by_company": trips_by_company,
                "vehicles_by_company": vehicles_by_company,
            }
    
    def run_cross_company_optimization(self, target_date: datetime) -> Dict[str, Any]:
        """Run the global cross-company optimizer."""
        logger.info(f"🚀 Starting cross-company optimization for {target_date.date()}")

        with Session(self.engine) as session:
            result = optimize_trips_for_date(
                session=session,
                target_date=target_date,
                company_id=None,
                optimization_type="cross_company",
            )

            if result.get("success"):
                logger.info("✅ Optimization completed successfully!")
                logger.info(f"   Trips optimized: {result.get('trips_optimized', 0)}")
                logger.info(f"   Vehicles used: {result.get('vehicles_used', 0)}")

                if result.get("company_results"):
                    self._print_company_results(cast(Dict[str, Any], result["company_results"]))

                if result.get("assignments"):
                    self._print_assignments(result["assignments"], session)
                return result

            logger.error(f"❌ Optimization failed: {result.get('error', result.get('message', 'Unknown error'))}")
            return result
    
    def _print_company_results(self, company_results: Dict[str, Any]) -> None:
        logger.info("📊 PER-COMPANY SUMMARY (assigned trips):")
        for company_id, stats in sorted(company_results.items(), key=lambda x: x[0]):
            logger.info(
                f"   - {company_id[:8]}: {stats.get('trips_assigned', 0)} assigned "
                f"(own={stats.get('trips_assigned_to_own_vehicles', 0)}, other={stats.get('trips_assigned_to_other_vehicles', 0)})"
            )
    
    def _print_assignments(self, assignments: List[Dict], session: Session):
        """Print detailed vehicle assignments"""
        logger.info(f"🔄 VEHICLE ASSIGNMENTS:")
        
        # Group assignments by vehicle
        vehicle_assignments: dict[str, list[Dict]] = {}
        for assignment in assignments:
            vehicle_id = assignment["assigned_vehicle_id"]
            if vehicle_id not in vehicle_assignments:
                vehicle_assignments[vehicle_id] = []
            vehicle_assignments[vehicle_id].append(assignment)
        
        for vehicle_id, vehicle_trips in vehicle_assignments.items():
            # Get vehicle info
            vehicle_uuid = uuid.UUID(vehicle_id) if isinstance(vehicle_id, str) else vehicle_id
            vehicle_stmt = select(Vehicle).where(Vehicle.id == vehicle_uuid)
            vehicle = session.exec(vehicle_stmt).first()
            
            vehicle_name = vehicle.license_plate if vehicle else f"Vehicle {vehicle_id[:8]}"
            
            # Sort trips by sequence
            vehicle_trips.sort(key=lambda x: x["sequence_order"])
            
            logger.info(f"\n   🚛 {vehicle_name} ({len(vehicle_trips)} trips):")
            
            total_distance: float = 0.0
            for trip_assignment in vehicle_trips:
                trip_id_val = trip_assignment.get("trip_id")
                trip_uuid = uuid.UUID(trip_id_val) if isinstance(trip_id_val, str) else trip_id_val
                trip_stmt = select(Trip).where(Trip.id == trip_uuid)
                trip = session.exec(trip_stmt).first()
                
                if trip:
                    distance = trip.route_distance_km or 0
                    total_distance += distance

                    orig_company = trip_assignment.get("original_company_id", "")
                    assigned_company = trip_assignment.get("assigned_company_id", "")
                    
                    logger.info(f"      {trip_assignment['sequence_order']}. {trip.departure_point[:20]} → {trip.arrival_point[:20]}")
                    logger.info(
                        f"           📦 {trip.cargo_category.value}, {trip.cargo_weight_kg}kg, {distance}km | "
                        f"🏢 {str(orig_company)[:8]} → {str(assigned_company)[:8]}"
                    )
            
            logger.info(f"      📏 Total distance for chain: {round(total_distance, 2)} km")
    
    def visualize_optimization(self, target_date: datetime, result: Dict):
        """Create a simple visualization of the cross-company optimization"""
        with Session(self.engine) as session:
            html_content = self._generate_visualization_html(target_date, result, session)
            
            # Save HTML file
            filename = f"optimization_visualization_{target_date.date()}.html"
            with open(filename, "w") as f:
                f.write(html_content)
            
            logger.info(f"📊 Visualization saved to: {filename}")
            
            # Open in browser
            try:
                webbrowser.open(f"file://{os.path.abspath(filename)}")
            except:
                pass
    
    def _generate_visualization_html(self, target_date: datetime, result: Dict, session: Session) -> str:
        """Generate HTML visualization"""
        
        # Get assignments grouped by vehicle
        vehicle_assignments: dict[str, list[dict[str, Any]]] = {}
        for assignment in result.get("assignments", []):
            vehicle_id = assignment["assigned_vehicle_id"]
            if vehicle_id not in vehicle_assignments:
                vehicle_assignments[vehicle_id] = []
            vehicle_assignments[vehicle_id].append(assignment)
        
        # Build HTML
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Optimization Results - All Companies - {target_date.date()}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 5px; }}
                .summary {{ background: #ecf0f1; padding: 15px; margin: 20px 0; border-radius: 5px; }}
                .vehicle-chain {{ border: 1px solid #ddd; margin: 20px 0; padding: 15px; border-radius: 5px; }}
                .trip {{ padding: 10px; margin: 5px 0; background: #f8f9fa; border-left: 4px solid #3498db; }}
                .stats {{ display: flex; justify-content: space-around; margin: 20px 0; }}
                .stat-box {{ background: white; padding: 15px; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); text-align: center; }}
                .savings {{ color: #27ae60; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🚛 Logistics Optimization Results</h1>
                <h2>All Companies - {target_date.date()}</h2>
            </div>
            
            <div class="summary">
                <h3>📊 Optimization Summary</h3>
                <p><strong>Status:</strong> {"✅ Success" if result.get("success") else "❌ Failed"}</p>
                <p><strong>Trips Optimized:</strong> {result.get("trips_optimized", 0)}</p>
                <p><strong>Vehicles Used:</strong> {result.get("vehicles_used", 0)}</p>
                <p><strong>Batch ID:</strong> {result.get("batch_id", "N/A")}</p>
            </div>
        """
        
        # Add vehicle chains
        for vehicle_id, assignments in vehicle_assignments.items():
            # Get vehicle info
            vehicle_uuid = uuid.UUID(vehicle_id) if isinstance(vehicle_id, str) else vehicle_id
            vehicle_stmt = select(Vehicle).where(Vehicle.id == vehicle_uuid)
            vehicle = session.exec(vehicle_stmt).first()
            
            vehicle_name = vehicle.license_plate if vehicle else f"Vehicle {vehicle_id[:8]}"
            assignments.sort(key=lambda x: x["sequence_order"])
            
            total_distance: float = 0.0
            trip_html = ""
            
            for assignment in assignments:
                trip_id_val = assignment.get("trip_id")
                trip_uuid = uuid.UUID(trip_id_val) if isinstance(trip_id_val, str) else trip_id_val
                trip_stmt = select(Trip).where(Trip.id == trip_uuid)
                trip = session.exec(trip_stmt).first()
                
                if trip:
                    distance = trip.route_distance_km or 0
                    total_distance += distance
                    
                    trip_html += f"""
                    <div class="trip">
                        <strong>#{assignment['sequence_order']}:</strong> {trip.departure_point} → {trip.arrival_point}<br>
                        <small>📦 {trip.cargo_category.value} | ⚖️ {trip.cargo_weight_kg}kg | 📏 {distance}km</small>
                    </div>
                    """
            
            html += f"""
            <div class="vehicle-chain">
                <h3>🚛 {vehicle_name}</h3>
                <p><strong>Chain Length:</strong> {len(assignments)} trips</p>
                <p><strong>Total Distance:</strong> {round(total_distance, 2)} km</p>
                {trip_html}
            </div>
            """
        
        # Add unassigned trips
        unassigned = result.get("unassigned", [])
        if unassigned:
            html += f"""
            <div class="vehicle-chain" style="border-color: #e74c3c;">
                <h3>⚠️ Unassigned Trips ({len(unassigned)})</h3>
                <ul>
            """
            
            for unassigned_trip in unassigned[:10]:  # Show first 10
                html += f"<li>Trip {unassigned_trip.get('trip_id', 'N/A')[:8]}: {unassigned_trip.get('reason', 'Unknown')}</li>"
            
            if len(unassigned) > 10:
                html += f"<li>... and {len(unassigned) - 10} more</li>"
            
            html += """
                </ul>
            </div>
            """
        
        # Add statistics
        html += """
            <div class="stats">
                <div class="stat-box">
                    <h3>📦 Total Trips</h3>
                    <p style="font-size: 24px;">""" + str(result.get("trips_optimized", 0)) + """</p>
                </div>
                <div class="stat-box">
                    <h3>🚛 Vehicles Used</h3>
                    <p style="font-size: 24px;">""" + str(result.get("vehicles_used", 0)) + """</p>
                </div>
                <div class="stat-box">
                    <h3>🎯 Efficiency</h3>
                    <p style="font-size: 24px;">""" + ("{:.1f}".format(result.get("trips_optimized", 0) / max(result.get("vehicles_used", 1), 1)) if result.get("vehicles_used", 0) > 0 else "0") + """ trips/vehicle</p>
                </div>
            </div>
            
            <div style="margin-top: 40px; padding: 20px; background: #f8f9fa; border-radius: 5px;">
                <h3>💡 What was optimized?</h3>
                <ul>
                    <li><strong>Empty Return Minimization:</strong> Trips were chained to reduce vehicles returning empty to depot</li>
                    <li><strong>Vehicle Utilization:</strong> Multiple trips assigned to each vehicle when possible</li>
                    <li><strong>Compatibility Matching:</strong> Cargo types matched to appropriate vehicle categories</li>
                    <li><strong>Distance Optimization:</strong> Trips sequenced to minimize total travel distance</li>
                </ul>
                <p><em>Generated by Logistics Platform Optimization Test</em></p>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def run_full_test_suite(self, target_date: Optional[datetime] = None):
        """Run comprehensive optimization tests"""
        if target_date is None:
            target_date = self.find_best_planned_trip_date() or (datetime.utcnow() + timedelta(days=1))
        
        logger.info("="*60)
        logger.info("🧪 RUNNING OPTIMIZATION TEST SUITE")
        logger.info("="*60)
        
        analysis = self.analyze_global_day(target_date)
        logger.info("\n🎯 Testing cross-company optimization (global pool)")

        logger.info("\n📈 PRE-OPTIMIZATION SNAPSHOT:")
        logger.info(f"   Planned trips (all companies): {analysis.get('planned_trips', 0)}")
        logger.info(f"   Companies with trips: {analysis.get('companies_with_trips', 0)}")
        logger.info(f"   Active vehicles (all companies): {analysis.get('active_vehicles', 0)}")
        
        # Run optimization
        logger.info(f"\n⚙️ RUNNING OPTIMIZATION...")
        result = self.run_cross_company_optimization(target_date)
        
        if result.get("success"):
            # Generate visualization
            logger.info(f"\n🎨 GENERATING VISUALIZATION...")
            self.visualize_optimization(target_date, result)
            
            # Save results to JSON
            self._save_results_to_json(target_date, result)
            
            logger.info(f"\n✅ TEST COMPLETED SUCCESSFULLY!")
        else:
            logger.error(f"\n❌ TEST FAILED")
    
    def _save_results_to_json(self, target_date: datetime, result: Dict):
        """Save optimization results to JSON file"""
        filename = f"optimization_results_{target_date.date()}_all_companies.json"
        
        with open(filename, "w") as f:
            json.dump({
                "scope": "all_companies",
                "date": target_date.isoformat(),
                "optimization_result": result,
                "generated_at": datetime.utcnow().isoformat()
            }, f, indent=2, default=str)
        
        logger.info(f"💾 Results saved to: {filename}")

def main():
    """Command-line interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test the logistics optimization module")
    parser.add_argument(
        "--date",
        type=str,
        help="Target date for optimization (YYYY-MM-DD). Default: tomorrow"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick test without visualization"
    )
    
    args = parser.parse_args()
    
    # Run test
    tester = OptimizationTester()

    # Parse/choose date
    if args.date:
        try:
            target_date = datetime.strptime(args.date, "%Y-%m-%d")
        except ValueError:
            print("❌ Invalid date format. Use YYYY-MM-DD")
            return
    else:
        # Prefer a date that actually has planned trips.
        target_date = tester.find_best_planned_trip_date() or (datetime.utcnow() + timedelta(days=1))

    print(f"\n🚛 Logistics Platform - Optimization Test")
    print(f"📅 Target Date: {target_date.date()}")
    print("="*50)
    
    if args.quick:
        result = tester.run_cross_company_optimization(target_date)
        print(f"\n📊 Quick test result: {'Success' if result.get('success') else 'Failed'}")
    else:
        # Full test suite
        tester.run_full_test_suite(target_date)

if __name__ == "__main__":
    main()