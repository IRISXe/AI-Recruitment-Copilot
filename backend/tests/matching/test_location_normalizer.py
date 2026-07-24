import pytest

from app.matching.location_normalizer import (
    locations_match,
    normalize_location_text,
    primary_location_key,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Hyderabad", "hyderabad"),
        ("Hyderabad, Telangana", "hyderabad telangana"),
        ("Bangalore", "bengaluru"),
        ("Bangalore, Karnataka", "bengaluru karnataka"),
        ("Bengaluru", "bengaluru"),
        ("Bombay", "mumbai"),
        ("Calcutta", "kolkata"),
        ("Madras", "chennai"),
        ("New Delhi", "delhi"),
        ("Delhi NCR", "delhi"),
        (
            "National Capital Region",
            "delhi",
        ),
    ],
)
def test_normalize_location_text_normalizes_known_values(
    value: str,
    expected: str,
) -> None:
    assert normalize_location_text(value) == expected


def test_normalize_location_text_normalizes_case_and_spacing() -> None:
    assert normalize_location_text(
        "  HYDERABAD,   TELANGANA  "
    ) == "hyderabad telangana"


@pytest.mark.parametrize(
    "value",
    [
        "",
        " ",
        "\n\t",
    ],
)
def test_normalize_location_text_returns_empty_for_blank_values(
    value: str,
) -> None:
    assert normalize_location_text(value) == ""


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Hyderabad, Telangana", "hyderabad"),
        ("Bangalore | Karnataka", "bengaluru"),
        ("Chennai / Tamil Nadu", "chennai"),
        ("Mumbai", "mumbai"),
    ],
)
def test_primary_location_key_returns_first_location_segment(
    value: str,
    expected: str,
) -> None:
    assert primary_location_key(value) == expected


@pytest.mark.parametrize(
    ("candidate_location", "job_location"),
    [
        ("Hyderabad", "Hyderabad"),
        ("Hyderabad, Telangana", "Hyderabad"),
        ("Hyderabad", "Hyderabad, Telangana"),
        ("Bangalore", "Bengaluru"),
        ("Bangalore", "Bengaluru, Karnataka"),
        ("Bombay", "Mumbai"),
        ("New Delhi", "Delhi NCR"),
        ("Chennai, Tamil Nadu", "Madras"),
    ],
)
def test_locations_match_equivalent_locations(
    candidate_location: str,
    job_location: str,
) -> None:
    assert locations_match(
        candidate_location,
        job_location,
    ) is True


@pytest.mark.parametrize(
    ("candidate_location", "job_location"),
    [
        ("Hyderabad", "Bengaluru"),
        ("Mumbai", "Chennai"),
        ("Delhi", "Kolkata"),
        ("Pune", "Hyderabad"),
    ],
)
def test_locations_match_rejects_different_locations(
    candidate_location: str,
    job_location: str,
) -> None:
    assert locations_match(
        candidate_location,
        job_location,
    ) is False


@pytest.mark.parametrize(
    ("candidate_location", "job_location"),
    [
        ("", "Hyderabad"),
        ("Hyderabad", ""),
        (" ", " "),
    ],
)
def test_locations_match_returns_false_for_missing_locations(
    candidate_location: str,
    job_location: str,
) -> None:
    assert locations_match(
        candidate_location,
        job_location,
    ) is False


def test_location_normalization_preserves_unknown_location() -> None:
    assert normalize_location_text(
        "Visakhapatnam, Andhra Pradesh"
    ) == "visakhapatnam andhra pradesh"


def test_locations_match_is_symmetric() -> None:
    assert locations_match(
        "Hyderabad, Telangana",
        "Hyderabad",
    ) is True

    assert locations_match(
        "Hyderabad",
        "Hyderabad, Telangana",
    ) is True


def test_locations_match_is_deterministic() -> None:
    first_result = locations_match(
        "Bangalore",
        "Bengaluru, Karnataka",
    )
    second_result = locations_match(
        "Bangalore",
        "Bengaluru, Karnataka",
    )

    assert first_result == second_result