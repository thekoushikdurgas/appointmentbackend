from sqlalchemy import BigInteger, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DepartmentAndJob(Base):
    __tablename__ = "departments_and_jobs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    department: Mapped[str] = mapped_column(Text, default="_", nullable=False)
    job_function: Mapped[str] = mapped_column(Text, default="_", nullable=False)
    uuid: Mapped[str] = mapped_column(Text, unique=True, index=True)

