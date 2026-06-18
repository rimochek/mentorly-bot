import logging
import random
from dataclasses import dataclass
from datetime import datetime, timezone

from app.database.models import TutorProfile
from app.database.repositories.tutors import MODERATION_APPROVED
from app.services.search_config import get_fallback_keywords, get_goal_match_score

logger = logging.getLogger(__name__)

EXAM_KEYWORDS: dict[str, list[str]] = {
    "IELTS": ["IELTS", "ielts", "айлтс", "айелтс"],
    "SAT": ["SAT", "sat", "сэт", "сат"],
    "TOEFL": ["TOEFL", "toefl", "тоефл", "тофл"],
    "NUET": ["NUET", "nuet", "нует"],
    "ЕНТ": ["ЕНТ", "ент", "UNT", "unt"],
    "AP": ["AP", "ap", "Advanced Placement"],
    "NIS": ["NIS", "nis", "НИШ", "ниш"],
    "РФМШ": ["РФМШ", "рфмш", "RFMSh", "rfmsh"],
    "Олимпиады": ["олимпиада", "olympiad", "olympiads"],
}

BUDGET_RANGES: dict[str, tuple[int | None, int | None]] = {
    "до 3000 ₸": (None, 3000),
    "3000–5000 ₸": (3000, 5000),
    "5000–8000 ₸": (5000, 8000),
    "8000+ ₸": (8000, None),
    "Не знаю": (None, None),
}

SCORE_SHUFFLE_THRESHOLD = 10
VERIFIED_BONUS = 8
FALLBACK_SUBJECT_SCORE = 25


@dataclass
class StudentFilters:
    exam: str
    goal: str
    budget_min: int | None
    budget_max: int | None


@dataclass
class SearchParams:
    exam_keyword: str
    goal: str
    current_level: str
    budget_min: int | None
    budget_max: int | None
    budget_text: str


@dataclass
class ScoredTutor:
    tutor: TutorProfile
    score: int


def parse_budget(budget_text: str) -> tuple[int | None, int | None]:
    if budget_text in BUDGET_RANGES:
        return BUDGET_RANGES[budget_text]
    return (None, None)


def get_search_keywords(exam: str) -> list[str]:
    if exam in EXAM_KEYWORDS:
        return EXAM_KEYWORDS[exam]
    return [exam]


def _get_primary_keywords(exam: str, keywords: list[str]) -> set[str]:
    primary = {exam.lower()}
    if keywords:
        primary.add(keywords[0].lower())
    return primary


def get_exam_match_score(description: str, keywords: list[str], exam: str) -> int | None:
    description_lower = description.lower()
    primary_keywords = _get_primary_keywords(exam, keywords)
    best_score: int | None = None

    for keyword in keywords:
        keyword_lower = keyword.lower()
        if keyword_lower not in description_lower:
            continue
        score = 50 if keyword_lower in primary_keywords else 25
        best_score = max(best_score or 0, score)

    return best_score


def description_matches(description: str, keywords: list[str], exam: str) -> bool:
    return get_exam_match_score(description, keywords, exam) is not None


def get_subject_match_score(description: str, subject_keywords: list[str]) -> int | None:
    description_lower = description.lower()
    for keyword in subject_keywords:
        if keyword.lower() in description_lower:
            return FALLBACK_SUBJECT_SCORE
    return None


def description_matches_subjects(description: str, subject_keywords: list[str]) -> bool:
    return get_subject_match_score(description, subject_keywords) is not None


def budget_overlaps(
    tutor_min: int,
    tutor_max: int,
    student_min: int | None,
    student_max: int | None,
) -> bool:
    if student_min is None and student_max is None:
        return False

    effective_student_min = student_min if student_min is not None else 0
    effective_student_max = student_max if student_max is not None else tutor_max + 1

    return tutor_min <= effective_student_max and tutor_max >= effective_student_min


def budget_fully_fits(
    tutor_min: int,
    tutor_max: int,
    student_min: int | None,
    student_max: int | None,
) -> bool:
    if student_min is None and student_max is None:
        return False

    effective_student_min = student_min if student_min is not None else 0
    effective_student_max = student_max if student_max is not None else float("inf")

    return tutor_min >= effective_student_min and tutor_max <= effective_student_max


def _budget_match_score(
    tutor: TutorProfile,
    budget_min: int | None,
    budget_max: int | None,
) -> int:
    if budget_min is None and budget_max is None:
        return 0

    if budget_fully_fits(tutor.price_min, tutor.price_max, budget_min, budget_max):
        return 30
    if budget_overlaps(tutor.price_min, tutor.price_max, budget_min, budget_max):
        return 15
    return -20


def _fairness_score(tutor: TutorProfile) -> int:
    views = tutor.views_count
    if views == 0:
        return 40
    if views <= 3:
        return 25
    if views <= 10:
        return 10
    return 0


def _freshness_score(tutor: TutorProfile, now: datetime) -> int:
    if tutor.last_shown_at is None:
        return 30

    days = (now - tutor.last_shown_at).days
    if days >= 7:
        return 25
    if days >= 3:
        return 15
    if days >= 1:
        return 5
    return 0


def _activity_penalty(tutor: TutorProfile) -> int:
    if tutor.shown_today_count >= 10:
        return -30
    if tutor.shown_today_count >= 5:
        return -15
    return 0


def _verified_bonus(tutor: TutorProfile) -> int:
    return VERIFIED_BONUS if tutor.is_verified else 0


def _compose_tutor_score(
    tutor: TutorProfile,
    student_filters: StudentFilters,
    base_match_score: int,
) -> int:
    now = datetime.now(timezone.utc)
    return (
        base_match_score
        + get_goal_match_score(tutor.description, student_filters.exam, student_filters.goal)
        + _budget_match_score(tutor, student_filters.budget_min, student_filters.budget_max)
        + _fairness_score(tutor)
        + _freshness_score(tutor, now)
        + _activity_penalty(tutor)
        + _verified_bonus(tutor)
    )


def calculate_tutor_score(tutor: TutorProfile, student_filters: StudentFilters) -> int | None:
    keywords = get_search_keywords(student_filters.exam)
    exam_match_score = get_exam_match_score(tutor.description, keywords, student_filters.exam)
    if exam_match_score is None:
        return None
    return _compose_tutor_score(tutor, student_filters, exam_match_score)


def calculate_fallback_tutor_score(
    tutor: TutorProfile,
    student_filters: StudentFilters,
    subject_keywords: list[str],
) -> int | None:
    subject_match_score = get_subject_match_score(tutor.description, subject_keywords)
    if subject_match_score is None:
        return None
    return _compose_tutor_score(tutor, student_filters, subject_match_score)


def _shuffle_close_scores(scored: list[ScoredTutor]) -> list[ScoredTutor]:
    if not scored:
        return []

    sorted_scored = sorted(scored, key=lambda item: item.score, reverse=True)
    result: list[ScoredTutor] = []
    index = 0

    while index < len(sorted_scored):
        group = [sorted_scored[index]]
        next_index = index + 1
        while (
            next_index < len(sorted_scored)
            and sorted_scored[index].score - sorted_scored[next_index].score < SCORE_SHUFFLE_THRESHOLD
        ):
            group.append(sorted_scored[next_index])
            next_index += 1

        if len(group) > 1:
            random.shuffle(group)

        result.extend(group)
        index = next_index

    return result


def _is_eligible_tutor(tutor: TutorProfile) -> bool:
    return tutor.is_active and tutor.moderation_status == MODERATION_APPROVED


def _rank_tutors(scored: list[ScoredTutor], label: str) -> list[TutorProfile]:
    logger.info("Tutors matched after %s filtering: %d", label, len(scored))
    for item in scored:
        logger.info(
            "%s candidate: id=%s name=%s score=%s verified=%s views=%s shown_today=%s",
            label,
            item.tutor.id,
            item.tutor.name,
            item.score,
            item.tutor.is_verified,
            item.tutor.views_count,
            item.tutor.shown_today_count,
        )
    ranked = _shuffle_close_scores(scored)
    return [item.tutor for item in ranked]


def search_tutors(
    tutors: list[TutorProfile],
    exam: str,
    budget_min: int | None,
    budget_max: int | None,
    goal: str = "",
) -> tuple[list[TutorProfile], int]:
    student_filters = StudentFilters(
        exam=exam,
        goal=goal,
        budget_min=budget_min,
        budget_max=budget_max,
    )
    keywords = get_search_keywords(exam)
    primary_scored: list[ScoredTutor] = []

    for tutor in tutors:
        if not _is_eligible_tutor(tutor):
            continue
        if not description_matches(tutor.description, keywords, exam):
            continue

        score = calculate_tutor_score(tutor, student_filters)
        if score is None:
            continue
        primary_scored.append(ScoredTutor(tutor=tutor, score=score))

    primary = _rank_tutors(primary_scored, "primary")
    primary_ids = {tutor.id for tutor in primary}

    fallback_keywords = get_fallback_keywords(exam, goal)
    fallback_scored: list[ScoredTutor] = []
    if fallback_keywords:
        for tutor in tutors:
            if not _is_eligible_tutor(tutor):
                continue
            if tutor.id in primary_ids:
                continue
            if not description_matches_subjects(tutor.description, fallback_keywords):
                continue

            score = calculate_fallback_tutor_score(tutor, student_filters, fallback_keywords)
            if score is None:
                continue
            fallback_scored.append(ScoredTutor(tutor=tutor, score=score))

    fallback = _rank_tutors(fallback_scored, "fallback")
    return primary + fallback, len(primary)


