from datetime import date, datetime

from backend.models.biomarker import BiomarkerReference
from backend.models.lab_report import LabReportRecord, TestResultRecord


def _user_id() -> str:
    return "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


def test_trends_overview_returns_delta(client, db_session):
    user_id = _user_id()

    biomarker = BiomarkerReference(
        standard_name="Glucose",
        category="Metabolic Panel",
        common_aliases='["GLUCOSE"]',
    )
    db_session.add(biomarker)
    db_session.commit()
    db_session.refresh(biomarker)

    r1 = LabReportRecord(
        user_id=user_id,
        patient_name="Trend User",
        report_date=date(2025, 1, 1),
        created_at=datetime.utcnow(),
    )
    r2 = LabReportRecord(
        user_id=user_id,
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

    response = client.get("/api/trends/overview", headers={"X-MHC-User-Id": user_id})
    assert response.status_code == 200
    payload = response.json()["data"]
    assert len(payload) >= 1
    assert payload[0]["biomarker"] == "Glucose"
    assert payload[0]["direction"] in {"up", "down", "stable"}
    assert "category" in payload[0]
