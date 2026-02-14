from datetime import date, datetime

from backend.models.biomarker import BiomarkerReference
from backend.models.lab_report import LabReportRecord, TestResultRecord
from backend.models.user import User
from backend.services.auth import hash_password


def _create_user_and_token(client, db_session):
    user = User(email="trend@example.com", password_hash=hash_password("secret123"), full_name="Trend User")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    login = client.post("/api/auth/login", json={"email": "trend@example.com", "password": "secret123"})
    assert login.status_code == 200
    return user, login.json()["token"]


def test_trends_overview_returns_delta(client, db_session):
    user, token = _create_user_and_token(client, db_session)

    biomarker = BiomarkerReference(
        standard_name="Glucose",
        category="Metabolic Panel",
        common_aliases='["GLUCOSE"]',
    )
    db_session.add(biomarker)
    db_session.commit()
    db_session.refresh(biomarker)

    r1 = LabReportRecord(
        user_id=user.id,
        patient_name="Trend User",
        report_date=date(2025, 1, 1),
        created_at=datetime.utcnow(),
    )
    r2 = LabReportRecord(
        user_id=user.id,
        patient_name="Trend User",
        report_date=date(2025, 2, 1),
        created_at=datetime.utcnow(),
    )
    db_session.add_all([r1, r2])
    db_session.flush()

    db_session.add_all(
        [
            TestResultRecord(doc_id=r1.doc_id, biomarker_id=biomarker.id, test_name="GLUCOSE", value="90"),
            TestResultRecord(doc_id=r2.doc_id, biomarker_id=biomarker.id, test_name="GLUCOSE", value="100"),
        ]
    )
    db_session.commit()

    response = client.get("/api/trends/overview", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) >= 1
    assert payload[0]["biomarker"] == "Glucose"
    assert payload[0]["direction"] in {"up", "down", "stable"}
    assert "category" in payload[0]
