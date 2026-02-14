from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.biomarker import BiomarkerReference
from backend.models.lab_report import LabReportRecord, TestResultRecord
from backend.models.user import User
from backend.routers.deps import get_current_user
from backend.services.trend_analyzer import compute_delta, to_float

router = APIRouter(prefix="/api/trends", tags=["trends"])


@router.get("/overview")
def overview(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = (
        db.query(TestResultRecord, LabReportRecord, BiomarkerReference)
        .join(LabReportRecord, TestResultRecord.doc_id == LabReportRecord.doc_id)
        .outerjoin(BiomarkerReference, TestResultRecord.biomarker_id == BiomarkerReference.id)
        .filter(LabReportRecord.user_id == current_user.id)
        .order_by(LabReportRecord.report_date.is_(None).desc(), LabReportRecord.report_date.asc(), LabReportRecord.created_at.asc())
        .all()
    )

    grouped = defaultdict(list)
    for test, report, biomarker in rows:
        key = biomarker.standard_name if biomarker else test.test_name
        grouped[key].append(
            {
                "report_date": report.report_date,
                "value": to_float(test.value),
                "flag": test.flag,
                "biomarker_id": test.biomarker_id,
                "category": biomarker.category if biomarker else "Other",
            }
        )

    output = []
    for name, values in grouped.items():
        if len(values) < 2:
            continue
        prev = values[-2]["value"]
        curr = values[-1]["value"]
        delta = compute_delta(prev, curr)
        if delta is None:
            continue
        direction = "stable"
        if delta > 5:
            direction = "up"
        elif delta < -5:
            direction = "down"
        output.append({
            "biomarker_id": values[-1]["biomarker_id"],
            "biomarker": name,
            "category": values[-1]["category"],
            "previous": prev,
            "current": curr,
            "delta_percent": round(delta, 2),
            "direction": direction,
            "latest_flag": values[-1]["flag"],
            "previous_report_date": values[-2]["report_date"].isoformat() if values[-2]["report_date"] else None,
            "latest_report_date": values[-1]["report_date"].isoformat() if values[-1]["report_date"] else None,
        })

    output.sort(key=lambda x: abs(x["delta_percent"]), reverse=True)
    return output
