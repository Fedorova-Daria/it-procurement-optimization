from django.db import models


class Document(models.Model):
    """Минимальная модель загруженного документа — точка роста для OCR/LayoutLM-обработки."""

    STATUS_CHOICES = [
        ("uploaded", "Загружен"),
        ("processing", "Обрабатывается"),
        ("done", "Обработан"),
        ("error", "Ошибка"),
    ]

    file = models.FileField(upload_to="documents/%Y/%m/%d/")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="uploaded")
    extracted_text = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Document #{self.pk} ({self.status})"
