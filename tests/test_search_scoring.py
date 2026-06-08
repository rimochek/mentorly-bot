import random
from datetime import datetime, timedelta, timezone

from app.services.search import (
    ScoredTutor,
    StudentFilters,
    _activity_penalty,
    _budget_match_score,
    _fairness_score,
    _freshness_score,
    _shuffle_close_scores,
    budget_fully_fits,
    budget_overlaps,
    calculate_tutor_score,
    description_matches,
    get_exam_match_score,
    get_search_keywords,
    parse_budget,
    search_tutors,
)

from tests.conftest import make_tutor


class TestExamFiltering:
    def test_ielts_in_description_matches(self) -> None:
        tutor = make_tutor(description="Готовлю к IELTS 8.0")
        keywords = get_search_keywords("IELTS")
        assert description_matches(tutor.description, keywords, "IELTS") is True

    def test_no_keyword_does_not_match(self) -> None:
        tutor = make_tutor(description="Только математика и физика")
        keywords = get_search_keywords("IELTS")
        assert description_matches(tutor.description, keywords, "IELTS") is False

    def test_custom_exam_matches(self) -> None:
        tutor = make_tutor(description="Подготовка к GRE Quant")
        keywords = get_search_keywords("GRE")
        assert description_matches(tutor.description, keywords, "GRE") is True

    def test_primary_keyword_scores_50(self) -> None:
        keywords = get_search_keywords("IELTS")
        assert get_exam_match_score("IELTS 8.0", keywords, "IELTS") == 50

    def test_secondary_keyword_scores_25(self) -> None:
        keywords = get_search_keywords("IELTS")
        assert get_exam_match_score("готовлю к айлтс", keywords, "IELTS") == 25


class TestBudgetScoring:
    def test_parse_budget_ranges(self) -> None:
        assert parse_budget("3000–5000 ₸") == (3000, 5000)
        assert parse_budget("Не знаю") == (None, None)

    def test_budget_fully_fits(self) -> None:
        assert budget_fully_fits(4000, 5000, 3000, 6000) is True

    def test_budget_partial_overlap(self) -> None:
        assert budget_overlaps(4500, 7000, 3000, 5000) is True
        assert budget_fully_fits(4500, 7000, 3000, 5000) is False

    def test_budget_no_overlap(self) -> None:
        assert budget_overlaps(8000, 10000, 3000, 5000) is False

    def test_budget_match_scores(self) -> None:
        tutor = make_tutor(price_min=4000, price_max=5000)
        assert _budget_match_score(tutor, 3000, 6000) == 30
        assert _budget_match_score(tutor, 3000, 4500) == 15
        assert _budget_match_score(tutor, 8000, 10000) == -20
        assert _budget_match_score(tutor, None, None) == 0


class TestFairnessFreshnessPenalty:
    def test_fairness_by_views(self) -> None:
        assert _fairness_score(make_tutor(views_count=0)) == 40
        assert _fairness_score(make_tutor(views_count=3)) == 25
        assert _fairness_score(make_tutor(views_count=10)) == 10
        assert _fairness_score(make_tutor(views_count=15)) == 0

    def test_freshness_by_last_shown(self) -> None:
        now = datetime.now(timezone.utc)
        assert _freshness_score(make_tutor(last_shown_at=None), now) == 30
        assert _freshness_score(make_tutor(last_shown_at=now - timedelta(days=8)), now) == 25
        assert _freshness_score(make_tutor(last_shown_at=now - timedelta(days=4)), now) == 15
        assert _freshness_score(make_tutor(last_shown_at=now - timedelta(days=1)), now) == 5
        assert _freshness_score(make_tutor(last_shown_at=now), now) == 0

    def test_activity_penalty(self) -> None:
        assert _activity_penalty(make_tutor(shown_today_count=0)) == 0
        assert _activity_penalty(make_tutor(shown_today_count=6)) == -15
        assert _activity_penalty(make_tutor(shown_today_count=11)) == -30


class TestCalculateTutorScore:
    def test_returns_none_without_exam_match(self) -> None:
        tutor = make_tutor(description="Математика")
        filters = StudentFilters(exam="IELTS", budget_min=3000, budget_max=5000)
        assert calculate_tutor_score(tutor, filters) is None

    def test_higher_score_for_new_tutor_with_budget_fit(self) -> None:
        filters = StudentFilters(exam="IELTS", budget_min=3000, budget_max=5000)
        new_tutor = make_tutor(id=1, views_count=0, price_min=4000, price_max=5000)
        old_tutor = make_tutor(
            id=2,
            views_count=20,
            shown_today_count=10,
            price_min=4000,
            price_max=5000,
            last_shown_at=datetime.now(timezone.utc),
        )
        assert calculate_tutor_score(new_tutor, filters) > calculate_tutor_score(old_tutor, filters)


class TestSearchTutors:
    def test_excludes_inactive_tutors(self) -> None:
        active = make_tutor(id=1, is_active=True)
        inactive = make_tutor(id=2, is_active=False, description="IELTS tutor")
        result = search_tutors([active, inactive], "IELTS", 3000, 5000)
        assert len(result) == 1
        assert result[0].id == 1

    def test_sorts_by_score_desc(self) -> None:
        high = make_tutor(
            id=1,
            views_count=0,
            price_min=4000,
            price_max=5000,
            description="IELTS 8.0",
        )
        low = make_tutor(
            id=2,
            views_count=50,
            shown_today_count=15,
            price_min=9000,
            price_max=12000,
            description="IELTS prep",
            last_shown_at=datetime.now(timezone.utc),
        )
        random.seed(42)
        result = search_tutors([low, high], "IELTS", 3000, 5000)
        assert result[0].id == 1

    def test_shuffle_groups_close_scores(self) -> None:
        tutors = [
            ScoredTutor(tutor=make_tutor(id=1), score=100),
            ScoredTutor(tutor=make_tutor(id=2), score=95),
            ScoredTutor(tutor=make_tutor(id=3), score=94),
            ScoredTutor(tutor=make_tutor(id=4), score=50),
        ]
        random.seed(1)
        shuffled = _shuffle_close_scores(tutors)
        top_ids = {item.tutor.id for item in shuffled[:3]}
        assert top_ids == {1, 2, 3}
        assert shuffled[3].tutor.id == 4
