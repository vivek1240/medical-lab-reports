from collections import defaultdict

from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends

from backend.database import get_db
from backend.models.biomarker import BiomarkerReference
from backend.models.lab_report import LabReportRecord, TestResultRecord
from backend.models.user import User
from backend.routers.deps import get_current_user
from backend.schemas.biomarker import BiomarkerSummaryItem, BiomarkerTrendPoint
from backend.services.trend_analyzer import to_float

router = APIRouter(prefix="/api/biomarkers", tags=["biomarkers"])


@router.get("/summary", response_model=list[BiomarkerSummaryItem])
def summary(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    reports = db.query(LabReportRecord.doc_id, LabReportRecord.report_date).filter(LabReportRecord.user_id == current_user.id).all()
    report_dates = {r.doc_id: r.report_date for r in reports}

    latest_by_biomarker = {}
    tests = (
        db.query(TestResultRecord, BiomarkerReference)
        .outerjoin(BiomarkerReference, TestResultRecord.biomarker_id == BiomarkerReference.id)
        .join(LabReportRecord, LabReportRecord.doc_id == TestResultRecord.doc_id)
        .filter(LabReportRecord.user_id == current_user.id)
        .all()
    )

    for test, biomarker in tests:
        key = test.biomarker_id or f"other::{test.test_name}"
        report_date = report_dates.get(test.doc_id)
        prev = latest_by_biomarker.get(key)
        if prev is None or (report_date and (prev["report_date"] is None or report_date > prev["report_date"])):
            latest_by_biomarker[key] = {
                "test": test,
                "biomarker": biomarker,
                "report_date": report_date,
            }

    items = []
    for v in latest_by_biomarker.values():
        t = v["test"]
        b = v["biomarker"]
        items.append(
            BiomarkerSummaryItem(
                biomarker_id=t.biomarker_id,
                biomarker_name=b.standard_name if b else t.test_name,
                category=b.category if b else "Other",
                latest_value=t.value,
                unit=t.unit,
                reference_range=t.reference_range,
                flag=t.flag,
                report_date=v["report_date"].isoformat() if v["report_date"] else None,
            )
        )
    return sorted(items, key=lambda x: (x.category, x.biomarker_name))


@router.get("/{biomarker_id}/history", response_model=list[BiomarkerTrendPoint])
def history(biomarker_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = (
        db.query(TestResultRecord, LabReportRecord)
        .join(LabReportRecord, TestResultRecord.doc_id == LabReportRecord.doc_id)
        .filter(
            TestResultRecord.biomarker_id == biomarker_id,
            LabReportRecord.user_id == current_user.id,
        )
        .order_by(LabReportRecord.report_date.is_(None).desc(), LabReportRecord.report_date.asc(), LabReportRecord.created_at.asc())
        .all()
    )

    return [
        BiomarkerTrendPoint(
            report_date=report.report_date.isoformat() if report.report_date else None,
            value=to_float(test.value),
            raw_value=test.value,
            unit=test.unit,
            flag=test.flag,
            doc_id=test.doc_id,
        )
        for test, report in rows
    ]


@router.get("/categories")
def categories(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    summary_rows = summary(db=db, current_user=current_user)
    grouped: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "flagged": 0, "normal": 0})
    for item in summary_rows:
        grouped[item.category]["total"] += 1
        if item.flag:
            grouped[item.category]["flagged"] += 1
        else:
            grouped[item.category]["normal"] += 1

    return [
        {
            "category": category,
            "total": counts["total"],
            "flagged": counts["flagged"],
            "normal": counts["normal"],
        }
        for category, counts in sorted(grouped.items(), key=lambda kv: kv[0])
    ]


@router.get("/unmapped")
def unmapped(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = (
        db.query(TestResultRecord.test_name)
        .join(LabReportRecord, LabReportRecord.doc_id == TestResultRecord.doc_id)
        .filter(LabReportRecord.user_id == current_user.id, TestResultRecord.biomarker_id.is_(None))
        .all()
    )
    counts: dict[str, int] = defaultdict(int)
    for (test_name,) in rows:
        counts[test_name] += 1

    return [
        {"test_name": test_name, "count": count}
        for test_name, count in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    ]
