import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app import crud
from app.core.config import settings
from app.models import User, UserCreate
from app.models.company_models import Company
from tests.utils.user import authentication_token_from_email
from tests.utils.utils import random_email, random_lower_string


class TestCompanyRegistration:
    """Integration tests for company registration workflow: signup -> login -> create company"""

    def test_company_registration_complete_flow(
        self, client: TestClient, db: Session
    ) -> None:
        """
        Complete workflow:
        1. Sign up new user
        2. Login with credentials
        3. Create company profile
        4. Verify company is linked to user
        """
        # Step 1: Register user
        email = random_email()
        password = random_lower_string()
        full_name = "Test User"
        
        signup_data = {
            "email": email,
            "password": password,
            "full_name": full_name,
        }
        signup_response = client.post(
            f"{settings.API_V1_STR}/users/signup",
            json=signup_data,
        )
        assert signup_response.status_code == 200
        user_response = signup_response.json()
        assert user_response["email"] == email
        assert user_response["full_name"] == full_name

        # Step 2: Login with new credentials
        login_response = client.post(
            f"{settings.API_V1_STR}/login/access-token",
            data={"username": email, "password": password},
        )
        assert login_response.status_code == 200
        tokens = login_response.json()
        access_token = tokens["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # Step 3: Create company profile
        company_payload = {
            "company_name": "Test Company SARL",
            "nis": "123456789012345",
            "nif": "123456789012345",
            "headquarters_address": "123 Rue de la République, Oran, Algeria",
            "company_type": "production",
            "activity_sector": "agroalimentaire",
            "partner_type": "entreprise",
            "legal_representative_name": "Ahmed Benali",
            "legal_representative_contact": "+213555123456",
        }
        company_response = client.post(
            f"{settings.API_V1_STR}/companies/",
            headers=headers,
            json=company_payload,
        )
        assert company_response.status_code == 200
        created_company = company_response.json()
        assert created_company["company_name"] == company_payload["company_name"]
        assert created_company["nis"] == company_payload["nis"]

        # Step 4: Verify company is in database and linked to user
        company_query = select(Company).where(Company.nis == company_payload["nis"])
        db_company = db.exec(company_query).first()
        assert db_company is not None
        assert db_company.company_name == company_payload["company_name"]

        # Get user from database to verify relationship
        user_query = select(User).where(User.email == email)
        db_user = db.exec(user_query).first()
        assert db_user is not None
        assert db_user.id == db_company.user_id

    def test_company_creation_requires_authentication(self, client: TestClient) -> None:
        """Company creation endpoint should require authentication"""
        company_payload = {
            "company_name": "Test Company",
            "nis": "123456789012345",
            "nif": "123456789012345",
            "headquarters_address": "123 Rue Test",
            "company_type": "production",
            "activity_sector": "agroalimentaire",
            "partner_type": "entreprise",
            "legal_representative_name": "Test Rep",
            "legal_representative_contact": "+213123456",
        }
        response = client.post(
            f"{settings.API_V1_STR}/companies/",
            json=company_payload,
        )
        assert response.status_code == 401  # Unauthorized without auth

    def test_company_creation_duplicate_nis(
        self, client: TestClient, db: Session, normal_user_token_headers: dict[str, str]
    ) -> None:
        """Cannot create company with duplicate NIS"""
        # Create first company
        email = random_email()
        password = random_lower_string()
        user_in = UserCreate(email=email, password=password)
        user = crud.create_user(session=db, user_create=user_in)

        shared_nis = random_lower_string()[:15]  # NIS max 15 chars
        company_payload = {
            "company_name": "First Company",
            "nis": shared_nis,
            "nif": random_lower_string()[:20],  # NIF 15-20 chars
            "headquarters_address": "Address 1",
            "company_type": "production",
            "activity_sector": "agroalimentaire",
            "partner_type": "entreprise",
            "legal_representative_name": "Rep 1",
            "legal_representative_contact": "+213111111",
        }
        
        auth_headers = authentication_token_from_email(
            client=client, email=email, db=db
        )
        
        # Create first company successfully
        response1 = client.post(
            f"{settings.API_V1_STR}/companies/",
            headers=auth_headers,
            json=company_payload,
        )
        assert response1.status_code == 200

        # Try to create second company with same NIS - should fail
        email2 = random_email()
        password2 = random_lower_string()
        user_in2 = UserCreate(email=email2, password=password2)
        user2 = crud.create_user(session=db, user_create=user_in2)
        
        auth_headers2 = authentication_token_from_email(
            client=client, email=email2, db=db
        )
        
        company_payload2 = {
            "company_name": "Second Company",
            "nis": shared_nis,  # Same NIS as first company
            "nif": random_lower_string()[:20],  # NIF 15-20 chars
            "headquarters_address": "Address 1",
            "company_type": "production",
            "activity_sector": "agroalimentaire",
            "partner_type": "entreprise",
            "legal_representative_name": "Rep 1",
            "legal_representative_contact": "+213111111",
        }
        
        response2 = client.post(
            f"{settings.API_V1_STR}/companies/",
            headers=auth_headers2,
            json=company_payload2,
        )
        assert response2.status_code == 400
        assert "NIS" in response2.json()["detail"]

    def test_user_can_only_have_one_company(
        self, client: TestClient, db: Session
    ) -> None:
        """User can only have one company profile"""
        email = random_email()
        password = random_lower_string()
        user_in = UserCreate(email=email, password=password)
        crud.create_user(session=db, user_create=user_in)
        
        auth_headers = authentication_token_from_email(
            client=client, email=email, db=db
        )

        # Create first company
        nis1 = random_lower_string()[:15]  # NIS max 15 chars
        nif1 = random_lower_string()[:20]  # NIF 15-20 chars
        company_payload = {
            "company_name": "Company One",
            "nis": nis1,
            "nif": nif1,
            "headquarters_address": "Address 1",
            "company_type": "production",
            "activity_sector": "agroalimentaire",
            "partner_type": "entreprise",
            "legal_representative_name": "Rep 1",
            "legal_representative_contact": "+213111111",
        }
        response1 = client.post(
            f"{settings.API_V1_STR}/companies/",
            headers=auth_headers,
            json=company_payload,
        )
        assert response1.status_code == 200

        # Try to create second company - should fail
        nis2 = random_lower_string()[:15]  # NIS max 15 chars
        nif2 = random_lower_string()[:20]  # NIF 15-20 chars
        company_payload2 = {
            "company_name": "Company Two",
            "nis": nis2,
            "nif": nif2,
            "headquarters_address": "Address 1",
            "company_type": "production",
            "activity_sector": "agroalimentaire",
            "partner_type": "entreprise",
            "legal_representative_name": "Rep 1",
            "legal_representative_contact": "+213111111",
        }
        response2 = client.post(
            f"{settings.API_V1_STR}/companies/",
            headers=auth_headers,
            json=company_payload2,
        )
        assert response2.status_code == 400
        assert "already has a company" in response2.json()["detail"]

    def test_read_company_me(
        self, client: TestClient, db: Session
    ) -> None:
        """Can retrieve current user's company profile"""
        email = random_email()
        password = random_lower_string()
        user_in = UserCreate(email=email, password=password)
        crud.create_user(session=db, user_create=user_in)
        
        auth_headers = authentication_token_from_email(
            client=client, email=email, db=db
        )

        company_payload = {
            "company_name": "My Company",
            "nis": "333333333333333",
            "nif": "333333333333333",
            "headquarters_address": "My Address",
            "company_type": "service",
            "activity_sector": "logistique_messagerie",
            "partner_type": "prestataire_logistique",
            "legal_representative_name": "My Rep",
            "legal_representative_contact": "+213333333",
        }
        
        # Create company
        create_response = client.post(
            f"{settings.API_V1_STR}/companies/",
            headers=auth_headers,
            json=company_payload,
        )
        assert create_response.status_code == 200

        # Read company
        read_response = client.get(
            f"{settings.API_V1_STR}/companies/me",
            headers=auth_headers,
        )
        assert read_response.status_code == 200
        company = read_response.json()
        assert company["company_name"] == company_payload["company_name"]
        assert company["nis"] == company_payload["nis"]

    def test_read_company_me_not_found(
        self, client: TestClient, db: Session
    ) -> None:
        """Reading company/me before creating company returns 404"""
        email = random_email()
        password = random_lower_string()
        user_in = UserCreate(email=email, password=password)
        crud.create_user(session=db, user_create=user_in)
        
        auth_headers = authentication_token_from_email(
            client=client, email=email, db=db
        )

        response = client.get(
            f"{settings.API_V1_STR}/companies/me",
            headers=auth_headers,
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_update_company_me(
        self, client: TestClient, db: Session
    ) -> None:
        """Can update company profile"""
        email = random_email()
        password = random_lower_string()
        user_in = UserCreate(email=email, password=password)
        crud.create_user(session=db, user_create=user_in)
        
        auth_headers = authentication_token_from_email(
            client=client, email=email, db=db
        )

        # Create company
        company_payload = {
            "company_name": "Original Company",
            "nis": "444444444444444",
            "nif": "444444444444444",
            "headquarters_address": "Original Address",
            "company_type": "production",
            "activity_sector": "construction_btp",
            "partner_type": "entreprise",
            "legal_representative_name": "Original Rep",
            "legal_representative_contact": "+213444444",
        }
        
        create_response = client.post(
            f"{settings.API_V1_STR}/companies/",
            headers=auth_headers,
            json=company_payload,
        )
        assert create_response.status_code == 200

        # Update company
        update_payload = {
            "company_name": "Updated Company",
            "headquarters_address": "Updated Address",
        }
        update_response = client.patch(
            f"{settings.API_V1_STR}/companies/me",
            headers=auth_headers,
            json=update_payload,
        )
        assert update_response.status_code == 200
        updated_company = update_response.json()
        assert updated_company["company_name"] == "Updated Company"
        assert updated_company["headquarters_address"] == "Updated Address"
        # Other fields should remain unchanged
        assert updated_company["nis"] == company_payload["nis"]
        assert updated_company["legal_representative_name"] == company_payload["legal_representative_name"]
