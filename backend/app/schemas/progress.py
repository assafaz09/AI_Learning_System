from pydantic import BaseModel


class ProgressSummary(BaseModel):
    documents_count: int
    conversations_count: int
    teacher_messages_count: int
    quizzes_created: int
    quizzes_graded: int
    average_quiz_score: float | None
    best_quiz_score: float | None
    group_sessions_count: int
    group_messages_count: int
    projects_total: int
    projects_done: int
    projects_in_progress: int
    projects_not_started: int
    projects_completion_percent: float
    podcasts_count: int
    overall_progress_percent: int


class QuizScorePoint(BaseModel):
    date: str
    score: float
    quiz_id: int
    quiz_title: str


class ActivityDay(BaseModel):
    date: str
    count: int


class ActivityBreakdown(BaseModel):
    teacher_messages: int
    quiz_submissions: int
    group_messages: int
    documents_uploaded: int
    projects_updated: int
    podcasts_created: int


class ProjectStatusSlice(BaseModel):
    label: str
    value: int
    percent: float


class ProgressDashboardResponse(BaseModel):
    summary: ProgressSummary
    quiz_scores_timeline: list[QuizScorePoint]
    activity_last_14_days: list[ActivityDay]
    activity_breakdown: ActivityBreakdown
    project_status_slices: list[ProjectStatusSlice]
    insights: list[str]
