import logging

from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from . import processing
from .models import Document
from .serializers import DocumentSerializer

logger = logging.getLogger(__name__)


@api_view(["GET"])
def health_check(request):
    """Простой эндпоинт, чтобы проверить, что backend вообще жив и достучался до БД."""
    return Response({"status": "ok"})


class DocumentViewSet(viewsets.ModelViewSet):
    """
    CRUD для документов + два действия для запуска обработки:
    - POST /api/documents/{id}/process/  — извлечь текст (Docling/PaddleOCR)
    - POST /api/documents/{id}/ask/      — задать вопрос по документу (LayoutLM)

    Обработка синхронная (запрос ждёт результата) — это осознанное упрощение
    на старте проекта. Как только обработка документов станет частым/долгим
    действием, этот же код почти без изменений переезжает в Celery-таску:
    вместо extract_text(...) внутри view будет process_document.delay(document.id),
    а сам view сразу вернёт 202 Accepted.
    """

    queryset = Document.objects.all().order_by("-created_at")
    serializer_class = DocumentSerializer

    @action(detail=True, methods=["post"])
    def process(self, request, pk=None):
        document = self.get_object()
        document.status = "processing"
        document.save(update_fields=["status"])

        try:
            text = processing.extract_text(document.file.path)
        except Exception:
            logger.exception("Не удалось обработать документ #%s", document.pk)
            document.status = "error"
            document.save(update_fields=["status"])
            return Response(
                {"detail": "Не удалось обработать документ, подробности в логах backend"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        document.extracted_text = text
        document.status = "done"
        document.save(update_fields=["extracted_text", "status"])
        return Response(self.get_serializer(document).data)

    @action(detail=True, methods=["post"])
    def ask(self, request, pk=None):
        document = self.get_object()
        question = request.data.get("question")
        if not question:
            return Response(
                {"detail": "Передайте поле 'question' в теле запроса"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            answer = processing.ask_document(document.file.path, question)
        except Exception:
            logger.exception("Не удалось ответить на вопрос по документу #%s", document.pk)
            return Response(
                {"detail": "Не удалось обработать вопрос, подробности в логах backend"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({"question": question, "answer": answer})
