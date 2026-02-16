from backend.schemas.lab_report import LabReport, PatientInfo, TestResult


def _user_id() -> str:
    return "11111111-2222-3333-4444-555555555555"


def test_upload_report_with_mocked_parser(client, db_session, monkeypatch):
    user_id = _user_id()

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
    response = client.post("/api/reports/upload", files=files, headers={"X-MHC-User-Id": user_id})
    assert response.status_code == 200
    payload = response.json()
    assert payload["statusCode"] == 200
    assert payload["data"]["total_tests"] == 1
    assert payload["data"]["mapped_tests"] >= 0
    assert "doc_id" in payload["data"]
