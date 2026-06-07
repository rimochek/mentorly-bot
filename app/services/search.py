from dataclasses import dataclass

from app.database.models import TutorProfile

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


@dataclass
class SearchParams:
    exam_keyword: str
    goal: str
    current_level: str
    budget_min: int | None
    budget_max: int | None
    budget_text: str


def parse_budget(budget_text: str) -> tuple[int | None, int | None]:
    if budget_text in BUDGET_RANGES:
        return BUDGET_RANGES[budget_text]
    return (None, None)


def get_search_keywords(exam: str) -> list[str]:
    if exam in EXAM_KEYWORDS:
        return EXAM_KEYWORDS[exam]
    return [exam]


def description_matches(description: str, keywords: list[str]) -> bool:
    description_lower = description.lower()
    for keyword in keywords:
        if keyword.lower() in description_lower:
            return True
    return False


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


def search_tutors(
    tutors: list[TutorProfile],
    exam: str,
    budget_min: int | None,
    budget_max: int | None,
) -> list[TutorProfile]:
    keywords = get_search_keywords(exam)
    matched: list[TutorProfile] = []

    for tutor in tutors:
        if not tutor.is_active:
            continue
        if description_matches(tutor.description, keywords):
            matched.append(tutor)

    def sort_key(tutor: TutorProfile) -> tuple[int, float]:
        has_budget_match = int(
            budget_overlaps(tutor.price_min, tutor.price_max, budget_min, budget_max)
        )
        created_ts = tutor.created_at.timestamp() if tutor.created_at else 0
        return (-has_budget_match, -created_ts)

    matched.sort(key=sort_key)
    return matched


def format_tutor_card(tutor: TutorProfile) -> str:
    return (
        f"👤 {tutor.name}, {tutor.age}\n"
        f"📍 {tutor.city}\n"
        f"🎓 {tutor.place_of_study}\n"
        f"💰 {tutor.price_min}–{tutor.price_max} ₸ / занятие\n\n"
        f"📝 О себе:\n{tutor.description}"
    )
