from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class BiomarkerReference(Base):
    __tablename__ = "biomarker_reference"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    standard_name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    common_aliases: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    typical_unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    typical_range_male: Mapped[str | None] = mapped_column(String(100), nullable=True)
    typical_range_female: Mapped[str | None] = mapped_column(String(100), nullable=True)

    test_results = relationship("TestResultRecord", back_populates="biomarker")
