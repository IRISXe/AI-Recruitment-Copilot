from unittest.mock import MagicMock
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.candidate_job_match import CandidateJobMatch
from app.repositories.candidate_job_match_query_repository import (
    list_candidate_job_matches,
)


def test_list_candidate_job_matches_returns_repository_results(
) -> None:
    session = MagicMock(spec=Session)

    matches = [
        MagicMock(spec=CandidateJobMatch),
        MagicMock(spec=CandidateJobMatch),
    ]

    scalar_result = MagicMock()
    scalar_result.all.return_value = matches
    session.scalars.return_value = scalar_result

    result = list_candidate_job_matches(
        session,
        offset=0,
        limit=20,
    )

    session.scalars.assert_called_once()
    scalar_result.all.assert_called_once_with()

    assert result == matches


def test_list_candidate_job_matches_applies_all_filters(
) -> None:
    session = MagicMock(spec=Session)

    scalar_result = MagicMock()
    scalar_result.all.return_value = []
    session.scalars.return_value = scalar_result

    candidate_id = uuid4()
    job_id = uuid4()

    list_candidate_job_matches(
        session,
        offset=10,
        limit=25,
        candidate_id=candidate_id,
        job_id=job_id,
        minimum_score=70.0,
        minimum_confidence=60.0,
        recommendation="good_match",
        sort_by="confidence_score",
        sort_order="asc",
    )

    statement = session.scalars.call_args.args[0]
    statement_text = str(statement)

    parameter_values = set(
        statement.compile().params.values()
    )

    assert (
        "candidate_job_matches.candidate_id"
        in statement_text
    )
    assert (
        "candidate_job_matches.job_id"
        in statement_text
    )
    assert (
        "candidate_job_matches.overall_score"
        in statement_text
    )
    assert (
        "candidate_job_matches.confidence_score"
        in statement_text
    )
    assert (
        "candidate_job_matches.recommendation"
        in statement_text
    )

    assert (
        "ORDER BY candidate_job_matches.confidence_score ASC"
        in statement_text
    )

    assert candidate_id in parameter_values
    assert job_id in parameter_values
    assert 70.0 in parameter_values
    assert 60.0 in parameter_values
    assert "good_match" in parameter_values
    assert 10 in parameter_values
    assert 25 in parameter_values


def test_list_candidate_job_matches_defaults_to_score_descending(
) -> None:
    session = MagicMock(spec=Session)

    scalar_result = MagicMock()
    scalar_result.all.return_value = []
    session.scalars.return_value = scalar_result

    list_candidate_job_matches(
        session,
        offset=0,
        limit=20,
    )

    statement = session.scalars.call_args.args[0]
    statement_text = str(statement)

    assert (
        "ORDER BY candidate_job_matches.overall_score DESC"
        in statement_text
    )


def test_list_candidate_job_matches_uses_stable_id_tiebreaker(
) -> None:
    session = MagicMock(spec=Session)

    scalar_result = MagicMock()
    scalar_result.all.return_value = []
    session.scalars.return_value = scalar_result

    list_candidate_job_matches(
        session,
        offset=0,
        limit=20,
    )

    statement = session.scalars.call_args.args[0]
    statement_text = str(statement)

    assert "candidate_job_matches.id ASC" in statement_text