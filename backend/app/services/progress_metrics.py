from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.models import (
    Conversation,
    Document,
    Grade,
    GroupLearningMessage,
    GroupLearningSession,
    LearningProject,
    Message,
    Podcast,
    Quiz,
)


def _day_key(value: datetime) -> str:
    return value.date().isoformat()


def _last_n_days(n: int) -> list[str]:
    today = date.today()
    return [(today - timedelta(days=offset)).isoformat() for offset in range(n - 1, -1, -1)]


def _compute_overall_progress(
    *,
    documents_count: int,
    teacher_messages_count: int,
    grades_count: int,
    group_sessions_count: int,
    projects_done: int,
    projects_in_progress: int,
    podcasts_count: int,
    average_quiz_score: float | None,
) -> int:
    score = 0
    if documents_count > 0:
        score += 15
    if teacher_messages_count >= 5:
        score += 20
    elif teacher_messages_count > 0:
        score += 10
    if grades_count > 0:
        score += 20
        if average_quiz_score is not None and average_quiz_score >= 80:
            score += 10
        elif average_quiz_score is not None and average_quiz_score >= 60:
            score += 5
    if group_sessions_count > 0:
        score += 15
    if projects_done > 0:
        score += 10
    if projects_in_progress > 0:
        score += 5
    if podcasts_count > 0:
        score += 5
    return min(100, score)


def _build_insights(
    *,
    documents_count: int,
    teacher_messages_count: int,
    grades_count: int,
    average_quiz_score: float | None,
    group_sessions_count: int,
    projects_total: int,
    projects_done: int,
    activity_last_14_days: list[dict],
) -> list[str]:
    insights: list[str] = []
    if documents_count == 0:
        insights.append("העלו מסמך לימוד ראשון — כך תוכלו לראות התקדמות אמיתית בדשבורד.")
    if teacher_messages_count == 0 and documents_count > 0:
        insights.append("יש לכם חומר למידה — נסו לשאול את המורה שאלה אחת היום.")
    if grades_count == 0 and documents_count > 0:
        insights.append("צרו שאלון קצר כדי למדוד את רמת הידע שלכם.")
    if average_quiz_score is not None and average_quiz_score < 70:
        insights.append("ממוצע הציונים מתחת ל-70% — מומלץ לחזור על החומר ולשאול את המורה על נקודות חלשות.")
    elif average_quiz_score is not None and average_quiz_score >= 85:
        insights.append("ממוצע ציונים מצוין! נסו אתגר קשה יותר או פרויקט למידה חדש.")
    if group_sessions_count == 0 and teacher_messages_count >= 3:
        insights.append("נסו למידה בקבוצה — הסברה לעמיתים מחזקת את ההבנה.")
    if projects_total > 0 and projects_done == 0:
        insights.append("יש פרויקטים שמורים — סמנו אחד כ״בתהליך״ והתחילו צעד קטן.")
    recent_total = sum(day["count"] for day in activity_last_14_days[-7:])
    if recent_total == 0 and (documents_count > 0 or grades_count > 0):
        insights.append("לא הייתה פעילות בשבוע האחרון — חזרה קצרה של 10 דקות תשמור על המומנטום.")
    if not insights:
        insights.append("ממשיכים בקצב טוב — שמרו על שגרת למידה קבועה.")
    return insights[:4]


def build_progress_dashboard(db: Session, user_id: int) -> dict:
    documents = db.query(Document).filter(Document.user_id == user_id).all()
    documents_count = len(documents)

    conversations_count = db.query(Conversation).filter(Conversation.user_id == user_id).count()
    teacher_messages_count = (
        db.query(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .filter(Conversation.user_id == user_id, Message.role == "user")
        .count()
    )

    quizzes_created = db.query(Quiz).filter(Quiz.user_id == user_id).count()
    grades = db.query(Grade).filter(Grade.user_id == user_id).order_by(Grade.created_at.asc()).all()
    grades_count = len(grades)
    average_quiz_score = round(sum(g.score for g in grades) / grades_count, 1) if grades else None
    best_quiz_score = round(max(g.score for g in grades), 1) if grades else None

    quiz_title_by_id = {
        row.id: row.title
        for row in db.query(Quiz).filter(Quiz.user_id == user_id).all()
    }
    quiz_scores_timeline = [
        {
            "date": _day_key(g.created_at),
            "score": float(g.score),
            "quiz_id": g.quiz_id,
            "quiz_title": quiz_title_by_id.get(g.quiz_id, f"שאלון #{g.quiz_id}"),
        }
        for g in grades
    ]

    group_sessions_count = (
        db.query(GroupLearningSession).filter(GroupLearningSession.user_id == user_id).count()
    )
    group_messages_count = (
        db.query(GroupLearningMessage)
        .join(GroupLearningSession, GroupLearningMessage.session_id == GroupLearningSession.id)
        .filter(GroupLearningSession.user_id == user_id, GroupLearningMessage.role == "user")
        .count()
    )

    projects = db.query(LearningProject).filter(LearningProject.user_id == user_id).all()
    projects_total = len(projects)
    projects_done = sum(1 for p in projects if p.status == "done")
    projects_in_progress = sum(1 for p in projects if p.status == "in_progress")
    projects_not_started = sum(1 for p in projects if p.status == "not_started")
    projects_completion_percent = (
        round(projects_done / projects_total * 100, 1) if projects_total else 0.0
    )

    podcasts = db.query(Podcast).filter(Podcast.user_id == user_id).all()
    podcasts_count = len(podcasts)

    overall_progress_percent = _compute_overall_progress(
        documents_count=documents_count,
        teacher_messages_count=teacher_messages_count,
        grades_count=grades_count,
        group_sessions_count=group_sessions_count,
        projects_done=projects_done,
        projects_in_progress=projects_in_progress,
        podcasts_count=podcasts_count,
        average_quiz_score=average_quiz_score,
    )

    activity_breakdown = {
        "teacher_messages": teacher_messages_count,
        "quiz_submissions": grades_count,
        "group_messages": group_messages_count,
        "documents_uploaded": documents_count,
        "projects_updated": projects_total,
        "podcasts_created": podcasts_count,
    }

    day_counts: dict[str, int] = defaultdict(int)
    for doc in documents:
        day_counts[_day_key(doc.created_at)] += 1
    for conv in db.query(Conversation).filter(Conversation.user_id == user_id).all():
        day_counts[_day_key(conv.created_at)] += 1
    for msg in (
        db.query(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .filter(Conversation.user_id == user_id, Message.role == "user")
        .all()
    ):
        day_counts[_day_key(msg.created_at)] += 1
    for grade in grades:
        day_counts[_day_key(grade.created_at)] += 1
    for session in db.query(GroupLearningSession).filter(GroupLearningSession.user_id == user_id).all():
        day_counts[_day_key(session.created_at)] += 1
    for gmsg in (
        db.query(GroupLearningMessage)
        .join(GroupLearningSession, GroupLearningMessage.session_id == GroupLearningSession.id)
        .filter(GroupLearningSession.user_id == user_id, GroupLearningMessage.role == "user")
        .all()
    ):
        day_counts[_day_key(gmsg.created_at)] += 1
    for project in projects:
        day_counts[_day_key(project.updated_at)] += 1
    for podcast in podcasts:
        day_counts[_day_key(podcast.created_at)] += 1

    activity_last_14_days = [
        {"date": day, "count": day_counts.get(day, 0)} for day in _last_n_days(14)
    ]

    project_slices_raw = [
        ("הושלמו", projects_done),
        ("בתהליך", projects_in_progress),
        ("לא התחילו", projects_not_started),
    ]
    project_status_slices = []
    for label, value in project_slices_raw:
        percent = round(value / projects_total * 100, 1) if projects_total else 0.0
        project_status_slices.append({"label": label, "value": value, "percent": percent})

    insights = _build_insights(
        documents_count=documents_count,
        teacher_messages_count=teacher_messages_count,
        grades_count=grades_count,
        average_quiz_score=average_quiz_score,
        group_sessions_count=group_sessions_count,
        projects_total=projects_total,
        projects_done=projects_done,
        activity_last_14_days=activity_last_14_days,
    )

    return {
        "summary": {
            "documents_count": documents_count,
            "conversations_count": conversations_count,
            "teacher_messages_count": teacher_messages_count,
            "quizzes_created": quizzes_created,
            "quizzes_graded": grades_count,
            "average_quiz_score": average_quiz_score,
            "best_quiz_score": best_quiz_score,
            "group_sessions_count": group_sessions_count,
            "group_messages_count": group_messages_count,
            "projects_total": projects_total,
            "projects_done": projects_done,
            "projects_in_progress": projects_in_progress,
            "projects_not_started": projects_not_started,
            "projects_completion_percent": projects_completion_percent,
            "podcasts_count": podcasts_count,
            "overall_progress_percent": overall_progress_percent,
        },
        "quiz_scores_timeline": quiz_scores_timeline,
        "activity_last_14_days": activity_last_14_days,
        "activity_breakdown": activity_breakdown,
        "project_status_slices": project_status_slices,
        "insights": insights,
    }
