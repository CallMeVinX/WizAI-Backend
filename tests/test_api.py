"""Integration tests for FastAPI endpoints using an in-memory SQLite database."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.models.lead import Lead

# Set up in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert "version" in response.json()


def test_lead_crud_flow():
    # 1. Ingest a lead
    payload = [
        {
            "form_id": "demo_form",
            "form_name": "Demo Request",
            "page_url": "/demo",
            "name": "Jane Doe",
            "email": "jane.doe@example.com",
            "phone": "+1 555-123-4567",
            "company": "Acme Innovations",
            "country": "United States",
            "message": "He scanned our QR code at the TechCrunch Disrupt booth",
        }
    ]
    ingest_res = client.post("/api/leads/ingest", json=payload)
    assert ingest_res.status_code == 200
    data = ingest_res.json()
    assert data["created"] == 1
    lead_id = data["details"][0]["lead_id"]

    # 2. Get lead by ID
    get_res = client.get(f"/api/leads/{lead_id}")
    assert get_res.status_code == 200
    lead_data = get_res.json()
    assert lead_data["full_name"] == "Jane Doe"
    assert lead_data["company_name"] == "Acme Innovations"
    assert lead_data["ai_source_channel"] == "Event"

    # 3. Patch lead
    patch_res = client.patch(
        f"/api/leads/{lead_id}",
        json={"lead_status": "qualified", "contact_owner": "Alice Smith"},
    )
    assert patch_res.status_code == 200
    updated_lead = patch_res.json()
    assert updated_lead["lead_status"] == "qualified"
    assert updated_lead["contact_owner"] == "Alice Smith"

    # 4. List leads with filters
    list_res = client.get("/api/leads?status=qualified")
    assert list_res.status_code == 200
    assert list_res.json()["total"] == 1

    # 5. Extract source via POST /api/leads/extract-source
    extract_res = client.post(
        "/api/leads/extract-source",
        json={"notes": "Saw our post about AI sales workflows and commented"},
    )
    assert extract_res.status_code == 200
    assert extract_res.json()["channel"] == "LinkedIn"

    # 6. Check Dashboard
    dash_res = client.get("/api/dashboard")
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    assert dash_data["total_leads"] == 1
    assert "qualified" in dash_data["by_status"]


def test_ingest_create_and_update_enrichment_flow():
    """Verify POST /api/leads/ingest performs create first, and then update/enrichment on duplicate."""
    # First submission -> creates new lead
    sub1 = [
        {
            "form_id": "form_demo",
            "form_name": "Demo Request",
            "page_url": "/demo",
            "name": "Sarah Connor",
            "email": "sarah.connor@cyberdyne.com",
            "phone": "+1 415-555-0199",
            "company": "Cyberdyne Systems",
            "country": "USA",
            "message": "Interested in enterprise tier demo.",
        }
    ]
    res1 = client.post("/api/leads/ingest", json=sub1)
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["created"] == 1
    assert data1["updated"] == 0
    lead_id = data1["details"][0]["lead_id"]

    # Second submission with same person/email -> updates & enriches existing lead
    sub2 = [
        {
            "form_id": "form_pricing",
            "form_name": "Pricing Inquiry",
            "page_url": "/pricing",
            "name": "Sarah Connor",
            "email": "sarah.connor@cyberdyne.com",
            "phone": "+1 415-555-0199",
            "company": "Cyberdyne Systems",
            "country": "USA",
            "message": "Following up on pricing structure for 500 seats.",
        }
    ]
    res2 = client.post("/api/leads/ingest", json=sub2)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["created"] == 0
    assert data2["updated"] == 1
    assert data2["details"][0]["lead_id"] == lead_id
    assert data2["details"][0]["action"] == "updated"

    # Verify lead profile in DB has enriched notes
    get_res = client.get(f"/api/leads/{lead_id}")
    assert get_res.status_code == 200
    notes = get_res.json()["notes"]
    assert "enterprise tier demo" in notes
    assert "pricing structure for 500 seats" in notes


def test_export_leads_csv_endpoint():
    """Verify GET /api/leads/export returns valid CSV with headers and data."""
    # Seed a lead
    sub = [
        {
            "form_id": "form_1",
            "form_name": "Contact",
            "page_url": "/contact",
            "name": "Bruce Wayne",
            "email": "bruce@wayneenterprises.com",
            "company": "Wayne Enterprises",
            "country": "USA",
            "message": "Met at booth during Tech Week.",
        }
    ]
    client.post("/api/leads/ingest", json=sub)

    res = client.get("/api/leads/export")
    assert res.status_code == 200
    assert "text/csv" in res.headers.get("content-type", "")
    assert "leads_export.csv" in res.headers.get("content-disposition", "")
    content = res.text
    lines = content.strip().split("\n")
    assert len(lines) >= 2  # header + at least 1 data row
    assert "Email" in lines[0] or "email" in lines[0]
    assert "bruce@wayneenterprises.com" in content


def test_dedupe_candidates_and_clusters_endpoints():
    """Verify dedupe pipeline triggers and surfaces candidates and clusters via API."""
    # Ingest near duplicates directly
    client.post("/api/leads/ingest", json=[
        {
            "form_id": "f1",
            "form_name": "F1",
            "page_url": "/demo",
            "name": "Tony Stark",
            "email": "tony@starkindustries.com",
            "phone": "+1 212-555-0144",
            "company": "Stark Industries Inc",
            "country": "USA",
            "message": "Demo request",
        }
    ])

    # Direct DB insertion or pipeline call
    dedup_run = client.post("/api/leads/dedupe-candidates")
    assert dedup_run.status_code == 200
    assert "data" in dedup_run.json()

    clusters_res = client.get("/api/leads/dedupe-clusters")
    assert clusters_res.status_code == 200
    assert "clusters" in clusters_res.json()


def test_api_negative_and_validation_cases():
    """Verify 404, query validation errors, and empty payload handling."""
    # 404 on nonexistent lead
    res_404 = client.get("/api/leads/999999")
    assert res_404.status_code == 404

    # 404 on patch nonexistent lead
    patch_404 = client.patch("/api/leads/999999", json={"lead_status": "qualified"})
    assert patch_404.status_code == 404

    # Validation error for page_size > 100
    res_422 = client.get("/api/leads?page_size=500")
    assert res_422.status_code == 422

    # Empty ingest payload
    res_empty = client.post("/api/leads/ingest", json=[])
    assert res_empty.status_code == 200
    assert res_empty.json()["created"] == 0

