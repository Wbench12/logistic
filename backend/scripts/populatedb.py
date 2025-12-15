"""
scripts/populate_db.py
Database Population Script - Uses existing app configuration
"""

import uuid
import random
import sys
import os
from datetime import datetime, timedelta
from typing import List, TypedDict

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Now import your app modules
from sqlmodel import Session
from sqlalchemy import delete
from app.core.config import settings  # ← Use your existing settings
from app.core.db import engine
from app.models.user_models import User
from app.models.company_models import (
    Company, CompanyType, PartnerType, ActivitySector, 
    Vehicle, VehicleCategory, VehicleStatus
)
from app.models.trip_models import (
    Trip, CargoCategory, MaterialType, TripStatus,
    MapMarker, OptimizationBatch, OptimizationBatchStatus, CompanyOptimizationResult
)
from app.core.security import get_password_hash  # ← Use your existing password hashing

class City(TypedDict):
    name: str
    lat: float
    lng: float


# Algerian cities data (same as before)
ALGERIAN_CITIES: list[City] = [
    {"name": "Algiers", "lat": 36.7538, "lng": 3.0588},
    {"name": "Oran", "lat": 35.6970, "lng": -0.6337},
    {"name": "Constantine", "lat": 36.3650, "lng": 6.6147},
    # ... (rest of cities from previous script)
]

class DatabasePopulator:
    def __init__(self):
        """Initialize with database engine from app settings."""
        # Keep a local reference for Session(...)
        self.engine = engine
        
        # Clear previous data
        self.users: List[User] = []
        self.companies: List[Company] = []
        self.vehicles: List[Vehicle] = []
        self.trips: List[Trip] = []
        
    def clear_existing_data(self):
        """Clear existing data (optional - for fresh start)"""
        print("Clearing existing data...")
        with Session(self.engine) as session:
            # Delete in FK-safe order
            session.execute(delete(CompanyOptimizationResult))
            session.execute(delete(OptimizationBatch))
            session.execute(delete(Trip))
            session.execute(delete(MapMarker))
            session.execute(delete(Vehicle))
            session.execute(delete(Company))
            session.execute(delete(User))
            session.commit()
        print("Existing data cleared")
    
    def create_users(self, session: Session, count: int = 50):
        """Create users - uses your existing password hashing"""
        print(f"👤 Creating {count} users...")

        for i in range(count):
            # First user is superuser
            is_superuser = (i == 0)

            user = User(
                email=f"user{i}@example.dz",
                hashed_password=get_password_hash("password123"),  # ← Your security module
                full_name=f"Test User {i}",
                is_active=True,
                is_superuser=is_superuser,
            )
            session.add(user)
            self.users.append(user)

        session.commit()
        print(f"✅ Created {len(self.users)} users")
        if self.users:
            print(f"   Admin: {self.users[0].email} / password123")
    
    def create_companies(self, session: Session):
        """Create companies linked to users"""
        print("🏢 Creating companies...")

        for i, user in enumerate(self.users[:30]):  # First 30 users get companies
            city = random.choice(ALGERIAN_CITIES)

            company = Company(
                company_name=f"Test Company {i}",
                nis=f"{random.randint(100000000, 999999999)}",
                nif=f"{random.randint(100000000000000, 999999999999999)}",
                headquarters_address=f"Test Address, {city['name']}",
                company_type=random.choice(list(CompanyType)),
                activity_sector=random.choice(list(ActivitySector)),
                partner_type=random.choice(list(PartnerType)),
                legal_representative_name=user.full_name or "Test Manager",
                legal_representative_contact=f"+213{random.randint(500000000, 799999999)}",
                is_active=True,
                is_verified=True,
                depot_lat=float(city["lat"]) + random.uniform(-0.1, 0.1),
                depot_lng=float(city["lng"]) + random.uniform(-0.1, 0.1),
                depot_address=f"Test Depot, {city['name']}",
                user_id=user.id,
            )
            session.add(company)
            self.companies.append(company)

        session.commit()
        print(f"✅ Created {len(self.companies)} companies")
    
    def create_vehicles(self, session: Session):
        """Create vehicles for companies"""
        print("🚚 Creating vehicles...")
        
        vehicle_brands = ["Mercedes", "Volvo", "MAN", "Scania", "Iveco", "Renault"]
        
        for company in self.companies:
            num_vehicles = random.randint(2, 6)

            for _ in range(num_vehicles):
                category = random.choice(list(VehicleCategory))

                vehicle = Vehicle(
                    license_plate=f"{random.randint(100, 999)}-{random.randint(10, 99)}",
                    category=category,
                    capacity_tons=round(random.uniform(5.0, 25.0), 1),
                    capacity_m3=round(random.uniform(15.0, 40.0), 1),
                    status=VehicleStatus.AVAILABLE,
                    current_km=random.uniform(10000, 200000),
                    last_technical_control=datetime.utcnow() - timedelta(days=random.randint(0, 180)),
                    insurance_expiry=datetime.utcnow() + timedelta(days=random.randint(30, 365)),
                    is_active=True,
                    year=random.randint(2015, 2023),
                    brand=random.choice(vehicle_brands),
                    model="Test Model",
                    fuel_type="Diesel",
                    cost_per_km=round(random.uniform(0.3, 0.7), 2),
                    fuel_consumption_l_per_100km=round(random.uniform(25.0, 35.0), 1),
                    company_id=company.id,
                )
                session.add(vehicle)
                self.vehicles.append(vehicle)

        session.commit()
        print(f"✅ Created {len(self.vehicles)} vehicles")
    
    def create_trips(self, session: Session, count: int = 300):
        """Create realistic trips"""
        print(f"📦 Creating {count} trips...")
        
        # Cargo to vehicle mapping (simplified)
        cargo_mapping = {
            CargoCategory.A01: VehicleCategory.AG1,
            CargoCategory.A02: VehicleCategory.AG2,
            CargoCategory.B01: VehicleCategory.BT1,
            CargoCategory.B02: VehicleCategory.BT4,
            CargoCategory.I01: VehicleCategory.IN2,
            CargoCategory.C01: VehicleCategory.CH2,
        }
        
        for _ in range(count):
            company = random.choice(self.companies)
            city1, city2 = random.sample(ALGERIAN_CITIES, 2)

            # Random dates (past 30 days to next 30 days)
            days_offset = random.randint(-30, 30)
            departure_time = datetime.utcnow() + timedelta(
                days=days_offset,
                hours=random.randint(6, 18),
            )

            # Select cargo
            cargo_category = random.choice(list(CargoCategory))
            required_vehicle = cargo_mapping.get(cargo_category, VehicleCategory.AG1)

            # Find compatible vehicle
            compatible_vehicles = [
                v for v in self.vehicles
                if v.company_id == company.id and v.category == required_vehicle
            ]
            vehicle = random.choice(compatible_vehicles) if compatible_vehicles else None

            # Create trip
            trip = Trip(
                company_id=company.id,
                vehicle_id=vehicle.id if vehicle else None,

                # Location
                departure_point=f"{city1['name']} Depot",
                departure_lat=float(city1["lat"]) + random.uniform(-0.05, 0.05),
                departure_lng=float(city1["lng"]) + random.uniform(-0.05, 0.05),
                arrival_point=f"{city2['name']} Warehouse",
                arrival_lat=float(city2["lat"]) + random.uniform(-0.05, 0.05),
                arrival_lng=float(city2["lng"]) + random.uniform(-0.05, 0.05),

                # Timing
                departure_datetime=departure_time,
                arrival_datetime_planned=departure_time + timedelta(hours=random.uniform(2, 6)),

                # Cargo details
                cargo_category=cargo_category,
                material_type=MaterialType.SOLID,
                cargo_weight_kg=round(random.uniform(1000, 20000), 2),
                cargo_volume_m3=round(random.uniform(5.0, 30.0), 2),

                # Status
                status=(
                    TripStatus.COMPLETED if days_offset < -1 else
                    TripStatus.IN_PROGRESS if days_offset == 0 else
                    TripStatus.PLANNED
                ),

                # Calculated fields (simulated)
                route_distance_km=round(random.uniform(50, 500), 1),
                route_duration_min=random.randint(120, 360),
                route_calculated=True,

                # Required vehicle for optimization
                required_vehicle_category=required_vehicle,

                # Dates
                trip_date=departure_time.replace(hour=0, minute=0, second=0, microsecond=0),
                uploaded_at=departure_time - timedelta(days=random.randint(1, 7)),
                created_at=datetime.utcnow(),
            )

            session.add(trip)
            self.trips.append(trip)

        session.commit()
        print(f"✅ Created {len(self.trips)} trips")

        # Print statistics
        print("\n📊 Trip Statistics:")
        status_counts: dict[TripStatus, int] = {}
        for trip in self.trips:
            status_counts[trip.status] = status_counts.get(trip.status, 0) + 1

        for status, count in status_counts.items():
            print(f"   {status.value}: {count}")
    
    def run(self, clear_existing: bool = False):
        """Main entry point"""
        print("="*50)
        print("🚀 Collaborative Logistics Platform - Database Populator")
        print("="*50)
        
        if clear_existing:
            self.clear_existing_data()

        # Create all data in a single session to avoid detached/expired instances
        with Session(self.engine, expire_on_commit=False) as session:
            self.create_users(session, 30)  # 30 users
            self.create_companies(session)
            self.create_vehicles(session)
            self.create_trips(session, 350)  # 350+ trips as requested
        
        print("\n" + "="*50)
        print("✅ DATABASE POPULATION COMPLETE!")
        print("="*50)
        print(f"Total created:")
        print(f"  👤 Users: {len(self.users)}")
        print(f"  🏢 Companies: {len(self.companies)}")
        print(f"  🚚 Vehicles: {len(self.vehicles)}")
        print(f"  📦 Trips: {len(self.trips)}")
        print("\n🔑 Login with:")
        print(f"   Email: user0@example.dz")
        print(f"   Password: password123")

def main():
    """Command-line entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Populate database with test data")
    parser.add_argument(
        "--clear", 
        action="store_true",
        help="Clear existing data before populating"
    )
    
    args = parser.parse_args()
    
    # Run the populator
    populator = DatabasePopulator()
    populator.run(clear_existing=args.clear)

if __name__ == "__main__":
    main()