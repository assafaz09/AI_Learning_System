from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse, UserOut
from app.schemas.document import DocumentOut, SelectedDocumentsRequest, SelectedDocumentsResponse
from app.schemas.quiz import GradeOut, QuestionOut, QuizGenerateRequest, QuizOut, QuizSubmitRequest
from app.schemas.teacher import TeacherChatRequest, TeacherChatResponse

__all__ = [
    "DocumentOut",
    "GradeOut",
    "LoginRequest",
    "QuestionOut",
    "QuizGenerateRequest",
    "QuizOut",
    "QuizSubmitRequest",
    "RefreshRequest",
    "RegisterRequest",
    "SelectedDocumentsRequest",
    "SelectedDocumentsResponse",
    "TeacherChatRequest",
    "TeacherChatResponse",
    "TokenResponse",
    "UserOut",
]
