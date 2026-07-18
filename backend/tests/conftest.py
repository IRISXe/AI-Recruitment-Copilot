from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from app.db.session import engine, get_db
from app.main import app
from app.models.application import Application
from app.models.candidate import Candidate
from app.models.job import Job
from app.models.resume import Resume
from app.models.resume_content import ResumeContent


@pytest.fixture
def db_connection() -> Generator[Connection, None, None]:
    connection = engine.connect()
    transaction = connection.begin()

    # Tests begin with empty Resume content, resumes, applications,
    # candidates, and jobs tables. Existing development rows are
    # restored when the outer transaction is rolled back.
    connection.execute(delete(ResumeContent))
    connection.execute(delete(Resume))
    connection.execute(delete(Application))
    connection.execute(delete(Candidate))
    connection.execute(delete(Job))

    try:
        yield connection
    finally:
        if transaction.is_active:
            transaction.rollback()

        connection.close()


@pytest.fixture
def db_session(
    db_connection: Connection,
) -> Generator[Session, None, None]:
    session = Session(
        bind=db_connection,
        autoflush=False,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )

    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(
    db_connection: Connection,
) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        with Session(
            bind=db_connection,
            autoflush=False,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        ) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)