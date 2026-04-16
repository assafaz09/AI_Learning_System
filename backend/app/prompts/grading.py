QUIZ_GRADER_SYSTEM_PROMPT = (
    "אתה בודק פדגוגי אמפתי. המטרה היא הערכה סמנטית: גם אם התשובה מנוסחת אחרת מהחומר, "
    "אם היא עונה נכון על השאלה יש לתת ציון גבוה. אין לדרוש העתקה מילולית. "
    "החזר JSON בלבד עם: score_0_to_100, why, how_to_improve, accepted_semantically."
)


def build_semantic_grading_prompt(question_prompt: str, expected: str, user_answer: str) -> str:
    return (
        "הערך תשובת תלמיד באופן סמנטי.\n"
        f"שאלה: {question_prompt}\n"
        f"תשובה צפויה/נקודות עיקריות: {expected}\n"
        f"תשובת תלמיד: {user_answer or 'לא ניתנה תשובה'}\n\n"
        "החזר JSON בלבד עם:\n"
        "{"
        '"score_0_to_100": number, '
        '"why": string, '
        '"how_to_improve": string, '
        '"accepted_semantically": boolean'
        "}"
    )
