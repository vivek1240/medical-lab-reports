from pydantic import BaseModel


class BiomarkerSummaryItem(BaseModel):
    biomarker_id: int | None
    biomarker_name: str
    category: str
    latest_value: str | None
    unit: str | None
    reference_range: str | None
    flag: str | None
    report_date: str | None


class BiomarkerTrendPoint(BaseModel):
    report_date: str | None
    value: float | None
    raw_value: str | None
    unit: str | None
    flag: str | None
    doc_id: str
