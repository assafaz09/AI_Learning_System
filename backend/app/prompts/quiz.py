QUIZ_GENERATOR_SYSTEM_PROMPT = (
    "אתה מומחה פדגוגי לבניית שאלונים. החזר תמיד JSON תקין בלבד, בלי טקסט נוסף. "
    "השאלות חייבות להיות ברורות, חד-משמעיות, קצרות ככל האפשר, וללא שגיאות פורמט."
)


def build_quiz_generation_prompt(
    question_type: str,
    question_count: int,
    difficulty: str,
    source_material: str,
) -> str:
    if question_type == "mcq":
        return (
            f"צור {question_count} שאלות אמריקאיות מהחומר, קושי {difficulty}. "
            "החזר JSON תקין בלבד בפורמט:\n"
            '{"questions":[{"prompt":"...","type":"mcq","options":["א","ב","ג","ד"],"correct_answer":"...","explanation":"..."}]}\n'
            f"חומר:\n{source_material}"
        )
    return (
        f"צור {question_count} שאלות פתוחות קצרות מהחומר, קושי {difficulty}. "
        "החזר JSON תקין בלבד בפורמט:\n"
        '{"questions":[{"prompt":"...","type":"open","reference_answer":"...","explanation":"..."}]}\n'
        f"חומר:\n{source_material}"
    )
