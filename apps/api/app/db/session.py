import json
import sqlite3
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.models.schemas import CaseRecord, ObservationRecord, now_utc


def _sqlite_path_from_url(database_url: str) -> str:
    if database_url == "sqlite:///:memory:":
        return ":memory:"
    if database_url.startswith("sqlite:///"):
        return database_url.removeprefix("sqlite:///")
    raise ValueError("Only sqlite:/// database URLs are supported")


def _json_dump(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False)


def _json_load(value: str | None) -> Any:
    if value is None:
        return None
    return json.loads(value)


class SQLiteStore:
    def __init__(self, database_url: str | None = None) -> None:
        self.configure(database_url or get_settings().database_url)

    def configure(self, database_url: str) -> None:
        self.database_url = database_url
        self.db_path = _sqlite_path_from_url(database_url)
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.init_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def init_schema(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS cases (
                    id TEXT PRIMARY KEY,
                    anonymous_code TEXT NOT NULL UNIQUE,
                    age_group TEXT,
                    gender TEXT,
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS observations (
                    id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL,
                    image_path TEXT,
                    collection_context TEXT NOT NULL,
                    symptom_context TEXT,
                    symptom_text TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    quality_result TEXT,
                    visual_features TEXT,
                    symptom_profile TEXT,
                    assisted_interpretation TEXT,
                    report TEXT,
                    FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE
                );
                """
            )
            self._ensure_column(connection, "observations", "symptom_context", "TEXT")

    def _ensure_column(
        self,
        connection: sqlite3.Connection,
        table_name: str,
        column_name: str,
        column_type: str,
    ) -> None:
        columns = {
            str(row["name"])
            for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        }
        if column_name not in columns:
            connection.execute(
                f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
            )

    def clear_all(self) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM observations")
            connection.execute("DELETE FROM cases")

    def next_case_serial(self, date_prefix: str) -> int:
        pattern = f"TM-{date_prefix}-%"
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS total FROM cases WHERE anonymous_code LIKE ?",
                (pattern,),
            ).fetchone()
        return int(row["total"]) + 1

    def create_case(self, case: CaseRecord) -> CaseRecord:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO cases (
                    id, anonymous_code, age_group, gender, notes, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    case.id,
                    case.anonymous_code,
                    case.age_group,
                    case.gender,
                    case.notes,
                    case.created_at.isoformat(),
                    case.updated_at.isoformat(),
                ),
            )
        return case

    def list_cases(self) -> list[CaseRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM cases ORDER BY created_at DESC"
            ).fetchall()
        return [self._case_from_row(row) for row in rows]

    def get_case(self, case_id: str) -> CaseRecord | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
        if row is None:
            return None
        return self._case_from_row(row)

    def create_observation(self, observation: ObservationRecord) -> ObservationRecord:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO observations (
                    id, case_id, image_path, collection_context, symptom_context,
                    symptom_text, created_at, updated_at, quality_result,
                    visual_features, symptom_profile, assisted_interpretation, report
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                self._observation_values(observation),
            )
        return observation

    def save_observation(self, observation: ObservationRecord) -> ObservationRecord:
        observation.updated_at = now_utc()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE observations
                SET case_id = ?, image_path = ?, collection_context = ?, symptom_context = ?,
                    symptom_text = ?, created_at = ?, updated_at = ?, quality_result = ?,
                    visual_features = ?, symptom_profile = ?, assisted_interpretation = ?, report = ?
                WHERE id = ?
                """,
                (
                    observation.case_id,
                    observation.image_path,
                    _json_dump(observation.collection_context.model_dump(mode="json")),
                    _json_dump(observation.symptom_context.model_dump(mode="json")),
                    observation.symptom_text,
                    observation.created_at.isoformat(),
                    observation.updated_at.isoformat(),
                    _json_dump(observation.quality_result),
                    _json_dump(observation.visual_features),
                    _json_dump(observation.symptom_profile),
                    _json_dump(observation.assisted_interpretation),
                    _json_dump(observation.report),
                    observation.id,
                ),
            )
        return observation

    def get_observation(self, observation_id: str) -> ObservationRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM observations WHERE id = ?",
                (observation_id,),
            ).fetchone()
        if row is None:
            return None
        return self._observation_from_row(row)

    def list_observations(self) -> list[ObservationRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM observations ORDER BY created_at DESC"
            ).fetchall()
        return [self._observation_from_row(row) for row in rows]

    def list_case_observations(self, case_id: str) -> list[ObservationRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM observations
                WHERE case_id = ?
                ORDER BY created_at DESC
                """,
                (case_id,),
            ).fetchall()
        return [self._observation_from_row(row) for row in rows]

    def _case_from_row(self, row: sqlite3.Row) -> CaseRecord:
        return CaseRecord(**dict(row))

    def _observation_from_row(self, row: sqlite3.Row) -> ObservationRecord:
        data = dict(row)
        data["collection_context"] = _json_load(data["collection_context"]) or {}
        data["symptom_context"] = _json_load(data.get("symptom_context")) or {}
        data["quality_result"] = _json_load(data["quality_result"])
        data["visual_features"] = _json_load(data["visual_features"])
        data["symptom_profile"] = _json_load(data["symptom_profile"])
        data["assisted_interpretation"] = _json_load(data["assisted_interpretation"])
        data["report"] = _json_load(data["report"])
        return ObservationRecord(**data)

    def _observation_values(self, observation: ObservationRecord) -> tuple[Any, ...]:
        return (
            observation.id,
            observation.case_id,
            observation.image_path,
            _json_dump(observation.collection_context.model_dump(mode="json")),
            _json_dump(observation.symptom_context.model_dump(mode="json")),
            observation.symptom_text,
            observation.created_at.isoformat(),
            observation.updated_at.isoformat(),
            _json_dump(observation.quality_result),
            _json_dump(observation.visual_features),
            _json_dump(observation.symptom_profile),
            _json_dump(observation.assisted_interpretation),
            _json_dump(observation.report),
        )


store = SQLiteStore()
