from datetime import date, datetime
from uuid import uuid4

from sqlalchemy import BIGINT, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class LabReportRecord(Base):
    __tablename__ = "lab_reports"

    doc_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    patient_name: Mapped[str] = mapped_column(String(255), nullable=False)
    patient_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)
    lab_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    report_date: Mapped[date | None] = mapped_column(Date, index=True, nullable=True)
    collection_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    sample_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    physician_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    raw_parsed_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="lab_reports")
    test_results = relationship("TestResultRecord", back_populates="report", cascade="all, delete-orphan")


class TestResultRecord(Base):
    __tablename__ = "test_results"

    id: Mapped[int] = mapped_column(BIGINT().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    doc_id: Mapped[str] = mapped_column(String(36), ForeignKey("lab_reports.doc_id", ondelete="CASCADE"), index=True)
    biomarker_id: Mapped[int | None] = mapped_column(ForeignKey("biomarker_reference.id"), index=True, nullable=True)
    test_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    value: Mapped[str | None] = mapped_column(String(50), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reference_range: Mapped[str | None] = mapped_column(String(100), nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    flag: Mapped[str | None] = mapped_column(String(20), nullable=True)

    report = relationship("LabReportRecord", back_populates="test_results")
    biomarker = relationship("BiomarkerReference", back_populates="test_results")
