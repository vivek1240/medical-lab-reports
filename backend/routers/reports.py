from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db
from backend.models.biomarker import BiomarkerReference
from backend.models.lab_report import LabReportRecord, TestResultRecord
from backend.routers.deps import get_user_id
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
    user_id: str = Depends(get_user_id),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF file")

    file_bytes = await file.read()
    max_size_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(file_bytes) > max_size_bytes:
        raise HTTPException(status_code=400, detail=f"File too large. Max size is {settings.max_upload_size_mb}MB")

    parsed_text = parse_pdf_bytes(file_bytes=file_bytes, file_name=file.filename)
    parsed_report = extract_lab_data(parsed_text)

    report = LabReportRecord(
        user_id=user_id,
        patient_name=parsed_report.patient_info.name or "Unknown",
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
    response_tests: list[dict[str, str | None]] = []
    for item in parsed_report.test_results:
        if not item.test_name:
            continue  # skip entries the LLM returned without a test name
        biomarker_id = classify_test_name(db, item.test_name)
        matched_biomarker = None
        if biomarker_id is not None:
            mapped_count += 1
            biomarker = db.query(BiomarkerReference).filter(BiomarkerReference.id == biomarker_id).first()
            matched_biomarker = biomarker.standard_name if biomarker else None
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
        response_tests.append(
            {
                "test_name": item.test_name,
                "value": item.value,
                "unit": item.unit,
                "reference_range": item.reference_range,
                "category": item.category,
                "flag": item.flag,
                "matched_biomarker": matched_biomarker,
            }
        )

    db.commit()
    return {
        "statusCode": 200,
        "message": "Report processed successfully",
        "data": {
            "doc_id": report.doc_id,
            "patient_name": report.patient_name,
            "lab_name": report.lab_name,
            "report_date": report.report_date.isoformat() if report.report_date else None,
            "total_tests": len(response_tests),
            "mapped_tests": mapped_count,
            "unmapped_tests_count": len(unmapped_tests),
            "unmapped_tests": unmapped_tests,
            "test_results": response_tests,
        },
    }


@router.get("")
def list_reports(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id),
):
    offset = (page - 1) * limit
    total = db.query(func.count(LabReportRecord.doc_id)).filter(LabReportRecord.user_id == user_id).scalar() or 0
    rows = (
        db.query(LabReportRecord)
        .filter(LabReportRecord.user_id == user_id)
        .order_by(LabReportRecord.report_date.is_(None), LabReportRecord.report_date.desc(), LabReportRecord.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    reports = []
    for report in rows:
        total_tests = (
            db.query(func.count(TestResultRecord.id))
            .filter(TestResultRecord.doc_id == report.doc_id)
            .scalar()
            or 0
        )
        mapped_tests = (
            db.query(func.count(TestResultRecord.id))
            .filter(TestResultRecord.doc_id == report.doc_id, TestResultRecord.biomarker_id.is_not(None))
            .scalar()
            or 0
        )
        reports.append(
            {
                "doc_id": report.doc_id,
                "patient_name": report.patient_name,
                "lab_name": report.lab_name,
                "report_date": report.report_date.isoformat() if report.report_date else None,
                "original_filename": report.original_filename,
                "total_tests": total_tests,
                "mapped_tests": mapped_tests,
                "created_at": report.created_at.isoformat(),
            }
        )

    return {
        "statusCode": 200,
        "message": "Success",
        "data": {
            "reports": reports,
            "total": total,
            "page": page,
            "limit": limit,
        },
    }


@router.get("/{doc_id}")
def get_report(doc_id: str, db: Session = Depends(get_db), user_id: str = Depends(get_user_id)):
    report = (
        db.query(LabReportRecord)
        .filter(LabReportRecord.doc_id == doc_id, LabReportRecord.user_id == user_id)
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    tests = (
        db.query(TestResultRecord, BiomarkerReference)
        .outerjoin(BiomarkerReference, TestResultRecord.biomarker_id == BiomarkerReference.id)
        .filter(TestResultRecord.doc_id == doc_id)
        .all()
    )
    return {
        "statusCode": 200,
        "message": "Success",
        "data": {
            "doc_id": report.doc_id,
            "user_id": report.user_id,
            "patient_name": report.patient_name,
            "patient_id": report.patient_id,
            "date_of_birth": report.date_of_birth.isoformat() if report.date_of_birth else None,
            "gender": report.gender,
            "lab_name": report.lab_name,
            "report_date": report.report_date.isoformat() if report.report_date else None,
            "collection_date": report.collection_date.isoformat() if report.collection_date else None,
            "sample_type": report.sample_type,
            "physician_name": report.physician_name,
            "original_filename": report.original_filename,
            "total_tests": len(tests),
            "mapped_tests": sum(1 for t, _ in tests if t.biomarker_id is not None),
            "created_at": report.created_at.isoformat(),
            "test_results": [
                {
                    "id": test.id,
                    "test_name": test.test_name,
                    "value": test.value,
                    "unit": test.unit,
                    "reference_range": test.reference_range,
                    "category": test.category,
                    "flag": test.flag,
                    "matched_biomarker": biomarker.standard_name if biomarker else None,
                    "biomarker_id": test.biomarker_id,
                }
                for test, biomarker in tests
            ],
        },
    }


@router.delete("/{doc_id}")
def delete_report(doc_id: str, db: Session = Depends(get_db), user_id: str = Depends(get_user_id)):
    report = (
        db.query(LabReportRecord)
        .filter(LabReportRecord.doc_id == doc_id, LabReportRecord.user_id == user_id)
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    db.delete(report)
    db.commit()
    return {
        "statusCode": 200,
        "message": "Report deleted",
        "data": None,
    }
