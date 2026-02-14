from pydantic import BaseModel, Field


class TestResult(BaseModel):
    """Individual lab test result with value, unit, and reference range."""
    test_name: str = Field(description="Name of the lab test")
    value: str | None = Field(default=None, description="Test result value")
    unit: str | None = Field(default=None, description="Unit of measurement")
    reference_range: str | None = Field(default=None, description="Normal/reference range for the test")
    category: str | None = Field(default=None, description="Category or panel the test belongs to")
    flag: str | None = Field(default=None, description="Flag indicating abnormal result")


class PatientInfo(BaseModel):
    """Patient demographic information."""
    name: str = Field(description="Patient full name")
    date_of_birth: str | None = Field(default=None, description="Patient date of birth")
    gender: str | None = Field(default=None, description="Patient gender")
    patient_id: str | None = Field(default=None, description="Patient ID or MRN")


class LabReport(BaseModel):
    """Complete laboratory report with patient info and all test results."""
    patient_info: PatientInfo
    lab_name: str | None = None
    report_date: str | None = None
    collection_date: str | None = None
    sample_type: str | None = None
    physician_name: str | None = None
    test_results: list[TestResult]


class ReportListItem(BaseModel):
    doc_id: str
    lab_name: str | None
    report_date: str | None
    patient_name: str
    created_at: str


class ReportDetailResponse(BaseModel):
    doc_id: str
    patient_info: PatientInfo
    lab_name: str | None
    report_date: str | None
    collection_date: str | None
    sample_type: str | None
    physician_name: str | None
    test_results: list[TestResult]
