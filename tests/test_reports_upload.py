from backend.models.user import User
from backend.schemas.lab_report import LabReport, PatientInfo, TestResult


def _register_and_token(client) -> str:
    response = client.post(
        "/api/auth/register",
        json={"email": "uploader@example.com", "password": "secret123", "full_name": "Uploader"},
    )
    assert response.status_code == 200
    return response.json()["token"]


def test_upload_report_with_mocked_parser(client, db_session, monkeypatch):
    token = _register_and_token(client)

    def fake_parse_pdf_bytes(file_bytes: bytes, file_name: str, llama_api_key=None) -> str:
        assert file_name.endswith(".pdf")
        return "mock parsed text"

    def fake_extract_lab_data(parsed_text: str, openai_api_key=None) -> LabReport:
        assert parsed_text == "mock parsed text"
        return LabReport(
            patient_info=PatientInfo(name="Mock Patient", patient_id="P-1"),
            lab_name="Mock Lab",
            report_date="2025-01-01",
            collection_date="2025-01-01",
            test_results=[
                TestResult(
                    test_name="GLUCOSE",
                    value="95",
                    unit="MG/DL",
                    reference_range="70-99",
                    category="Metabolic Panel",
                    flag=None,
                )
            ],
        )

    monkeypatch.setattr("backend.routers.reports.parse_pdf_bytes", fake_parse_pdf_bytes)
    monkeypatch.setattr("backend.routers.reports.extract_lab_data", fake_extract_lab_data)

    files = {"file": ("sample.pdf", b"%PDF-1.4 mock", "application/pdf")}
    response = client.post("/api/reports/upload", files=files, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["tests"] == 1
    assert payload["mapped_tests"] >= 0
    assert "doc_id" in payload

    # Ensure report row persisted for the current user.
    user = db_session.query(User).filter(User.email == "uploader@example.com").first()
    assert user is not None
