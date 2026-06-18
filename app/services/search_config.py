from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

# button label -> stored goal value
ENT_PROFILES: list[tuple[str, str]] = [
    ("Физмат", "Физмат"),
    ("Инфомат", "Инфомат"),
    ("Биохим", "Биохим"),
    ("История + География", "Всемирная история + География"),
    ("Язык + Всемирка", "Иностранный язык + Всемирка"),
    ("Матгео", "Матгео"),
    ("Био + География", "Биология + География"),
    ("Не знаю", "Не знаю"),
]

IELTS_TARGETS = ["6.0", "6.5", "7.0", "7.5", "8.0", "8.5+", "Не знаю"]
TOEFL_TARGETS = ["80+", "90+", "100+", "110+", "Не знаю"]
SAT_TARGETS = ["1200+", "1300+", "1400+", "1500+", "1550+", "Не знаю"]
NUET_TARGETS = ["150+", "200+", "Не знаю"]
NIS_TARGETS = ["Математика", "Физика", "Общий профиль", "Не знаю"]

AP_SUBJECTS: list[tuple[str, str]] = [
    ("Calculus AB", "AP Calculus AB"),
    ("Calculus BC", "AP Calculus BC"),
    ("Computer Science A", "AP Computer Science A"),
    ("Physics 1", "AP Physics 1"),
    ("Chemistry", "AP Chemistry"),
    ("Statistics", "AP Statistics"),
    ("Biology", "AP Biology"),
    ("Другое AP", "Другое AP"),
]

OLYMPIAD_SUBJECTS = [
    "Математика",
    "Физика",
    "Информатика",
    "Химия",
    "Биология",
    "География",
    "История",
    "Не знаю",
]

OLYMPIAD_GRADES = ["7 класс", "8 класс", "9 класс", "10 класс", "11 класс", "Не знаю"]

EXAMS_SKIP_GOAL = {"РФМШ"}

EXAM_DETAIL_PROMPTS: dict[str, str] = {
    "IELTS": "Какой band IELTS вы хотите получить?",
    "TOEFL": "Какой балл TOEFL вы хотите получить?",
    "SAT": "Какой score SAT вы хотите получить?",
    "NUET": "Какой балл NUET вы хотите получить?",
    "ЕНТ": "Выберите профиль ЕНТ:",
    "AP": "Выберите предмет AP:",
    "NIS": "Выберите профиль подготовки к NIS:",
    "Олимпиады": "Выберите предмет олимпиады:",
}

# goal value -> search keywords (soft match bonus)
GOAL_KEYWORDS: dict[str, list[str]] = {
    # IELTS
    "6.0": ["6.0", "6.5", "band 6"],
    "6.5": ["6.5", "7.0", "band 6", "band 7"],
    "7.0": ["7.0", "7.5", "band 7"],
    "7.5": ["7.5", "8.0", "band 7", "band 8"],
    "8.0": ["8.0", "8.5", "band 8"],
    "8.5+": ["8.5", "9.0", "band 8", "band 9"],
    # TOEFL
    "80+": ["80", "90", "toefl 80"],
    "90+": ["90", "100", "toefl 90"],
    "100+": ["100", "110", "toefl 100"],
    "110+": ["110", "120", "toefl 110"],
    # SAT
    "1200+": ["1200", "1300", "sat 1200"],
    "1300+": ["1300", "1400", "sat 1300"],
    "1400+": ["1400", "1500", "sat 1400"],
    "1500+": ["1500", "1550", "sat 1500"],
    "1550+": ["1550", "1600", "sat 1550"],
    # NUET
    "150+": ["150", "200", "nuet 150"],
    "200+": ["200", "250", "nuet 200"],
    # AP
    "AP Calculus AB": ["calculus ab", "calculus", "ap calc"],
    "AP Calculus BC": ["calculus bc", "calculus", "ap calc"],
    "AP Computer Science A": ["computer science", "cs a", "ap cs", "информатика"],
    "AP Physics 1": ["physics 1", "ap physics", "физика"],
    "AP Chemistry": ["chemistry", "ap chem", "химия"],
    "AP Statistics": ["statistics", "ap stat"],
    "AP Biology": ["biology", "ap bio", "биология"],
    # ENT profiles
    "Физмат": ["физмат", "математика", "физика"],
    "Инфомат": ["инфомат", "информатика", "математика", "it"],
    "Биохим": ["биохим", "биология", "химия"],
    "Всемирная история + География": ["всемирная история", "география", "история"],
    "Иностранный язык + Всемирка": ["иностранный", "английский", "всемирная", "история"],
    "Матгео": ["матгео", "математика", "география"],
    "Биология + География": ["биология", "география"],
    # NIS
    "Математика": ["математика", "math"],
    "Физика": ["физика", "physics"],
    "Общий профиль": ["nis", "ниш", "общий"],
    # RFMSh
    "РФМШ": ["рфмш", "rfmsh"],
}

OLYMPIAD_SUBJECT_KEYWORDS: dict[str, list[str]] = {
    "Математика": ["математика", "math"],
    "Физика": ["физика", "physics"],
    "Информатика": ["информатика", "informatics", "cs"],
    "Химия": ["химия", "chemistry"],
    "Биология": ["биология", "biology"],
    "География": ["география", "geography"],
    "История": ["история", "history"],
}

OLYMPIAD_GRADE_KEYWORDS: dict[str, list[str]] = {
    "7 класс": ["7 класс", "7-класс"],
    "8 класс": ["8 класс", "8-класс"],
    "9 класс": ["9 класс", "9-класс"],
    "10 класс": ["10 класс", "10-класс"],
    "11 класс": ["11 класс", "11-класс"],
}

EXAM_FALLBACK_SUBJECTS: dict[str, list[str]] = {
    "РФМШ": ["логика", "математика"],
    "NIS": ["логика", "математика", "языки", "английский", "биология", "естествознание"],
    "IELTS": ["английский", "english", "writing", "speaking", "reading", "grammar"],
    "TOEFL": ["английский", "english", "writing", "speaking", "reading", "grammar"],
    "SAT": ["math", "mathematics", "математика", "english", "reading", "writing"],
    "NUET": ["математика", "math", "english", "английский"],
}


def _buttons_keyboard(buttons: list[str], columns: int = 2) -> ReplyKeyboardMarkup:
    rows: list[list[KeyboardButton]] = []
    row: list[KeyboardButton] = []
    for btn in buttons:
        row.append(KeyboardButton(text=btn))
        if len(row) == columns:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def _labeled_keyboard(options: list[tuple[str, str]], columns: int = 2) -> ReplyKeyboardMarkup:
    return _buttons_keyboard([label for label, _ in options], columns)


def exam_detail_keyboard(exam: str) -> ReplyKeyboardMarkup | None:
    if exam == "IELTS":
        return _buttons_keyboard(IELTS_TARGETS, columns=3)
    if exam == "TOEFL":
        return _buttons_keyboard(TOEFL_TARGETS, columns=2)
    if exam == "SAT":
        return _buttons_keyboard(SAT_TARGETS, columns=2)
    if exam == "NUET":
        return _buttons_keyboard(NUET_TARGETS, columns=2)
    if exam == "ЕНТ":
        return _labeled_keyboard(ENT_PROFILES, columns=2)
    if exam == "AP":
        return _labeled_keyboard(AP_SUBJECTS, columns=2)
    if exam == "NIS":
        return _buttons_keyboard(NIS_TARGETS, columns=2)
    return None


def olympiad_subject_keyboard() -> ReplyKeyboardMarkup:
    return _buttons_keyboard(OLYMPIAD_SUBJECTS, columns=2)


def olympiad_grade_keyboard() -> ReplyKeyboardMarkup:
    return _buttons_keyboard(OLYMPIAD_GRADES, columns=2)


def skips_goal_step(exam: str) -> bool:
    return exam in EXAMS_SKIP_GOAL


def get_exam_detail_prompt(exam: str) -> str:
    return EXAM_DETAIL_PROMPTS.get(exam, "Уточните цель подготовки:")


def resolve_exam_detail(exam: str, button_text: str) -> str | None:
    text = button_text.strip()
    if exam == "ЕНТ":
        for label, goal in ENT_PROFILES:
            if text == label:
                return goal
        return None
    if exam == "AP":
        for label, goal in AP_SUBJECTS:
            if text == label:
                return goal
        return None
    if exam == "IELTS" and text in IELTS_TARGETS:
        return text
    if exam == "TOEFL" and text in TOEFL_TARGETS:
        return text
    if exam == "SAT" and text in SAT_TARGETS:
        return text
    if exam == "NUET" and text in NUET_TARGETS:
        return text
    if exam == "NIS" and text in NIS_TARGETS:
        return text
    return None


def is_ap_custom_goal(goal: str) -> bool:
    return goal == "Другое AP"


def build_olympiad_goal(subject: str, grade: str) -> str:
    if subject == "Не знаю" and grade == "Не знаю":
        return "Не знаю"
    if grade == "Не знаю":
        return subject
    if subject == "Не знаю":
        return grade
    return f"{subject}, {grade}"


def _dedupe_keywords(keywords: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for keyword in keywords:
        kw = keyword.lower()
        if kw in seen:
            continue
        seen.add(kw)
        result.append(kw)
    return result


def get_fallback_keywords(exam: str, goal: str) -> list[str]:
    keywords: list[str] = list(EXAM_FALLBACK_SUBJECTS.get(exam, []))

    if exam == "ЕНТ" and goal and goal != "Не знаю":
        keywords.extend(GOAL_KEYWORDS.get(goal, []))
    elif exam == "AP" and goal and goal not in ("Не знаю", "Другое AP"):
        keywords.extend(GOAL_KEYWORDS.get(goal, []))
    elif exam == "NIS" and goal and goal not in ("Не знаю", "Общий профиль"):
        keywords.extend(GOAL_KEYWORDS.get(goal, []))
    elif exam == "Олимпиады":
        if goal and "," in goal:
            subject, _grade = [part.strip() for part in goal.split(",", 1)]
            keywords.extend(OLYMPIAD_SUBJECT_KEYWORDS.get(subject, [subject.lower()]))
        elif goal and goal != "Не знаю":
            keywords.extend(OLYMPIAD_SUBJECT_KEYWORDS.get(goal, [goal.lower()]))
    elif exam not in EXAM_FALLBACK_SUBJECTS:
        if goal and goal != "Не знаю":
            keywords.append(goal)
        keywords.append(exam)

    return _dedupe_keywords(keywords)


def get_goal_match_score(description: str, exam: str, goal: str) -> int:
    if not goal or goal == "Не знаю":
        return 0

    description_lower = description.lower()
    best = 0

    keywords = list(GOAL_KEYWORDS.get(goal, []))
    if goal not in GOAL_KEYWORDS and goal:
        keywords.append(goal.lower())

    if exam == "Олимпиады" and "," in goal:
        subject, grade = [part.strip() for part in goal.split(",", 1)]
        keywords.extend(OLYMPIAD_SUBJECT_KEYWORDS.get(subject, [subject.lower()]))
        keywords.extend(OLYMPIAD_GRADE_KEYWORDS.get(grade, [grade.lower()]))
    elif exam == "Олимпиады":
        keywords.extend(OLYMPIAD_SUBJECT_KEYWORDS.get(goal, [goal.lower()]))

    seen: set[str] = set()
    for keyword in keywords:
        kw = keyword.lower()
        if kw in seen:
            continue
        seen.add(kw)
        if kw in description_lower:
            best = max(best, 20 if kw == goal.lower() else 15)

    return min(best, 25)


def all_search_flow_buttons() -> frozenset[str]:
    labels: set[str] = set()
    labels.update(IELTS_TARGETS)
    labels.update(TOEFL_TARGETS)
    labels.update(SAT_TARGETS)
    labels.update(NUET_TARGETS)
    labels.update(NIS_TARGETS)
    labels.update(OLYMPIAD_SUBJECTS)
    labels.update(OLYMPIAD_GRADES)
    for label, _ in ENT_PROFILES:
        labels.add(label)
    for label, _ in AP_SUBJECTS:
        labels.add(label)
    return frozenset(labels)
