"""
Извлечение текста и данных из документов через Docling / PaddleOCR / LayoutLM.

Важная деталь: модели тяжёлые (сотни МБ — единицы ГБ) и медленно грузятся в память.
Поэтому каждая модель — синглтон на процесс (кэшируется в глобальной переменной):
загружается один раз при первом реальном запросе, а не при каждом вызове.
Это значит, что первый запрос после старта контейнера будет заметно медленнее
последующих — это ожидаемо, не баг.
"""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

TEXT_BASED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".html", ".htm", ".md"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp"}

_docling_converter = None
_paddle_ocr = None
_layoutlm_pipeline = None


def extract_text(file_path: str) -> str:
    """
    Главная точка входа: выбирает стратегию извлечения текста по расширению файла.
    Вызывается из DocumentViewSet.process (см. views.py).
    """
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix in TEXT_BASED_EXTENSIONS:
        return _extract_with_docling(path)
    if suffix in IMAGE_EXTENSIONS:
        return _extract_with_paddleocr(path)
    raise ValueError(f"Неподдерживаемый формат файла: {suffix}")


def _extract_with_docling(path: Path) -> str:
    """
    Docling читает PDF/DOCX/PPTX/HTML и понимает СТРУКТУРУ документа —
    заголовки, таблицы, списки, а не просто "суп из текста", как обычный OCR.
    Для сканированных PDF Docling сам подключает OCR под капотом.
    """
    global _docling_converter
    if _docling_converter is None:
        logger.info("Загружаю Docling DocumentConverter (первый раз в этом процессе)...")
        from docling.document_converter import DocumentConverter

        _docling_converter = DocumentConverter()

    result = _docling_converter.convert(str(path))
    return result.document.export_to_markdown()


def _extract_with_paddleocr(path: Path) -> str:
    """
    Для отдельных изображений (сканы, фото документов, скриншоты) используем
    PaddleOCR напрямую — быстрее, чем прогонять их через полный конвейер Docling.
    """
    global _paddle_ocr
    if _paddle_ocr is None:
        logger.info("Загружаю PaddleOCR (первый раз в этом процессе)...")
        from paddleocr import PaddleOCR

        # lang='ru' — под русский текст. Для англоязычных документов поменяйте на 'en',
        # либо сделайте выбор языка параметром запроса, если нужны оба.
        _paddle_ocr = PaddleOCR(use_angle_cls=True, lang="ru")

    result = _paddle_ocr.ocr(str(path), cls=True)

    lines = []
    for page in result:
        if not page:
            continue
        for _box, (text, _confidence) in page:
            lines.append(text)
    return "\n".join(lines)


def ask_document(file_path: str, question: str) -> str:
    """
    Вопрос-ответ по документу с учётом расположения текста на странице
    (LayoutLM понимает не только слова, но и их позицию — важно для таблиц,
    форм, счетов). Пример вопроса: "Какая сумма к оплате?", "Дата документа?".

    Работает с изображениями и одностраничными PDF. Модель — готовая,
    предобученная (impira/layoutlm-document-qa), без дообучения на вашем домене;
    для специфичных форм точность стоит проверить и при необходимости дообучить.
    """
    global _layoutlm_pipeline
    if _layoutlm_pipeline is None:
        logger.info("Загружаю LayoutLM pipeline (первый раз в этом процессе)...")
        from transformers import pipeline

        _layoutlm_pipeline = pipeline(
            "document-question-answering",
            model="impira/layoutlm-document-qa",
        )

    result = _layoutlm_pipeline(str(file_path), question)
    return result[0]["answer"] if result else ""
