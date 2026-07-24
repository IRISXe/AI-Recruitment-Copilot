from typing import Literal


CandidateJobMatchSortBy = Literal[
    "overall_score",
    "confidence_score",
    "matched_at",
    "created_at",
]

CandidateJobMatchSortOrder = Literal[
    "asc",
    "desc",
]