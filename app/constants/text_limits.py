TUTOR_DESCRIPTION_MAX = 1500
NAME_MAX = 80
CITY_MAX = 100
PLACE_OF_STUDY_MAX = 100
EXAM_CUSTOM_MAX = 100
GOAL_CUSTOM_MAX = 200
SUPPORT_MESSAGE_MAX = 1000
BROADCAST_MESSAGE_MAX = 4000


def format_length_error(limit: int, current: int) -> str:
    return (
        f"Слишком длинный текст. Есть лимит — максимум {limit} символов, "
        f"сейчас {current}. Пожалуйста, сократите сообщение."
    )


def is_within_limit(text: str, limit: int) -> bool:
    return len(text.strip()) <= limit
