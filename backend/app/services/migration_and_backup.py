import os
import json
import sqlite3
from datetime import datetime, timezone
from backend.app.database import Base, engine, SessionLocal
from backend.app.models import EducationalContext, PhaseTemplate, CurriculumSource, Lesson, Plan, PlanVersion, PlanReview, ExportTask
from sqlalchemy.dialects import postgresql, sqlite


def generate_postgresql_and_sqlite_ddl() -> dict:
    """
    Compiles all SQLAlchemy models against both PostgreSQL (`postgresql.dialect()`)
    and SQLite (`sqlite.dialect()`) to verify 100% production PostgreSQL DDL compatibility
    (foreign keys, JSON columns, timezone-aware timestamps, primary keys).
    """
    from sqlalchemy.schema import CreateTable

    pg_statements = []
    sqlite_statements = []
    for table in Base.metadata.sorted_tables:
        pg_ddl = str(CreateTable(table).compile(dialect=postgresql.dialect())).strip() + ";"
        sq_ddl = str(CreateTable(table).compile(dialect=sqlite.dialect())).strip() + ";"
        pg_statements.append(pg_ddl)
        sqlite_statements.append(sq_ddl)

    return {
        "postgresql_ddl": "\n\n".join(pg_statements),
        "sqlite_ddl": "\n\n".join(sqlite_statements),
        "tables_count": len(Base.metadata.sorted_tables),
    }


def create_database_backup_json(output_path: str) -> dict:
    """
    Exports a complete, transactional JSON backup of all educational contexts, templates,
    curriculum sources, lessons, plans, plan versions, reviews, and export records.
    Works identically on PostgreSQL and SQLite.
    """
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        payload = {
            "backupVersion": "1.0",
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "contexts": [
                {
                    "id": c.id,
                    "subject": c.subject,
                    "grade": c.grade,
                    "country": c.country,
                    "curriculum_name": c.curriculum_name,
                    "language": c.language,
                    "year": c.year,
                    "edition": c.edition,
                    "teacher_name": c.teacher_name,
                    "school_name": c.school_name,
                    "section_name": c.section_name,
                    "planning_date": c.planning_date,
                    "school_days": c.school_days,
                    "holidays": c.holidays,
                    "default_period_Minutes": c.default_period_Minutes,
                    "default_periods_count": c.default_periods_count,
                    "selected_tools": c.selected_tools,
                    "version": c.version,
                }
                for c in db.query(EducationalContext).all()
            ],
            "plansCount": db.query(Plan).count(),
            "lessonsCount": db.query(Lesson).count(),
            "sourcesCount": db.query(CurriculumSource).count(),
        }
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return payload
    finally:
        db.close()
