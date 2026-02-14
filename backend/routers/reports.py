from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.lab_report import LabReportRecord, TestResultRecord
from backend.models.user import User
from backend.routers.deps import get_current_user
from backend.schemas.lab_report import PatientInfo, ReportDetailResponse, ReportListItem, TestResult
from backend.services.classifier import classify_test_name
from backend.services.parser import extract_lab_data, parse_pdf_bytes

router = APIRouter(prefix="/api/reports", tags=["reports"])


def _safe_date(value: str | None):
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


@router.post("/upload")
async def upload_report(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF file")

    file_bytes = await file.read()
    parsed_text = parse_pdf_bytes(file_bytes=file_bytes, file_name=file.filename)
    parsed_report = extract_lab_data(parsed_text)

    report = LabReportRecord(
        user_id=current_user.id,
        patient_name=parsed_report.patient_info.name,
        patient_id=parsed_report.patient_info.patient_id,
        date_of_birth=_safe_date(parsed_report.patient_info.date_of_birth),
        gender=parsed_report.patient_info.gender,
        lab_name=parsed_report.lab_name,
        report_date=_safe_date(parsed_report.report_date),
        collection_date=_safe_date(parsed_report.collection_date),
        sample_type=parsed_report.sample_type,
        physician_name=parsed_report.physician_name,
        original_filename=file.filename,
        raw_parsed_text=parsed_text,
    )
    db.add(report)
    db.flush()

    mapped_count = 0
    unmapped_tests: list[str] = []
    for item in parsed_report.test_results:
        biomarker_id = classify_test_name(db, item.test_name)
        if biomarker_id is not None:
            mapped_count += 1
        else:
            unmapped_tests.append(item.test_name)
        db.add(
            TestResultRecord(
                doc_id=report.doc_id,
                biomarker_id=biomarker_id,
                test_name=item.test_name,
                value=item.value,
                unit=item.unit,
                reference_range=item.reference_range,
                category=item.category,
                flag=item.flag,
            )
        )

    db.commit()
    return {
        "doc_id": report.doc_id,
        "tests": len(parsed_report.test_results),
        "mapped_tests": mapped_count,
        "unmapped_tests_count": len(unmapped_tests),
        "unmapped_tests_preview": unmapped_tests[:10],
    }


@router.get("", response_model=list[ReportListItem])
def list_reports(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = (
        db.query(LabReportRecord)
        .filter(LabReportRecord.user_id == current_user.id)
        .order_by(LabReportRecord.report_date.desc().nullslast(), LabReportRecord.created_at.desc())
        .all()
    )
    return [
        ReportListItem(
            doc_id=r.doc_id,
            lab_name=r.lab_name,
            report_date=r.report_date.isoformat() if r.report_date else None,
            patient_name=r.patient_name,
            created_at=r.created_at.isoformat(),
        )
        for r in rows
    ]


@router.get("/{doc_id}", response_model=ReportDetailResponse)
def get_report(doc_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    report = (
        db.query(LabReportRecord)
        .filter(LabReportRecord.doc_id == doc_id, LabReportRecord.user_id == current_user.id)
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    tests = db.query(TestResultRecord).filter(TestResultRecord.doc_id == doc_id).all()
    return ReportDetailResponse(
        doc_id=report.doc_id,
        patient_info=PatientInfo(
            name=report.patient_name,
            date_of_birth=report.date_of_birth.isoformat() if report.date_of_birth else None,
            gender=report.gender,
            patient_id=report.patient_id,
        ),
        lab_name=report.lab_name,
        report_date=report.report_date.isoformat() if report.report_date else None,
        collection_date=report.collection_date.isoformat() if report.collection_date else None,
        sample_type=report.sample_type,
        physician_name=report.physician_name,
        test_results=[
            TestResult(
                test_name=t.test_name,
                value=t.value,
                unit=t.unit,
                reference_range=t.reference_range,
                category=t.category,
                flag=t.flag,
            )
            for t in tests
        ],
    )
