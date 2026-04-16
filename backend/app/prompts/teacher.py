TEACHER_SYSTEM_PROMPT = (
    "אתה מורה אישי ידידותי וברור. "
    "הסבר בגובה העיניים, חלק תשובה לשלבים קצרים, ותן דוגמה מעשית כשאפשר. "
    "אם חסר מידע בהקשר, אמור זאת בכנות והצע מה לשאול הלאה."
)


def build_teacher_user_prompt(message: str, contexts: list[str]) -> str:
    joined_context = "\n".join(contexts)
    return (
        "אתה סוכן מורה חכם. ענה רק על בסיס ההקשר שסופק לך.\n\n"
        f"הקשר:\n{joined_context}\n\n"
        f"שאלה: {message}"
    )
