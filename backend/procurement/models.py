import uuid
from django.db import models


class DataImport(models.Model):
    """Информация о загруженных Excel-файлах."""

    DATA_TYPE_CHOICES = [
        ("planned", "Планируемые закупки"),
        ("stock", "Складские остатки"),
        ("purchased", "Приобретённые товары"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField("Название таблицы", max_length=255)
    filename = models.CharField("Название исходного Excel", max_length=255)
    data_type = models.CharField("Тип данных", max_length=20, choices=DATA_TYPE_CHOICES)
    year = models.IntegerField("Год закупки", null=True, blank=True)
    created_at = models.DateTimeField("Дата загрузки", auto_now_add=True)
    row_count = models.IntegerField("Количество записей", default=0)

    class Meta:
        db_table = "data_imports"
        ordering = ["-created_at"]
        verbose_name = "Импорт данных"
        verbose_name_plural = "Импорты данных"

    def __str__(self):
        return f"{self.name} ({self.get_data_type_display()}, {self.year})"


class ProcurementItem(models.Model):
    """Строки из Excel, преобразованные в единый формат."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    data_import = models.ForeignKey(
        DataImport,
        on_delete=models.CASCADE,
        related_name="items",
        db_column="import_id",
        verbose_name="Загруженная таблица",
    )
    nomenclature = models.TextField("Наименование номенклатуры")
    quantity = models.DecimalField("Количество", max_digits=15, decimal_places=4, null=True, blank=True)
    total_amount = models.DecimalField("Общая сумма", max_digits=15, decimal_places=2, null=True, blank=True)
    destination = models.TextField("Куда направляется товар", blank=True, default="")
    purpose = models.TextField("Для чего приобретается", blank=True, default="")
    unit = models.CharField("Единица измерения", max_length=50, blank=True, default="")
    unit_price = models.DecimalField("Цена за единицу", max_digits=15, decimal_places=2, null=True, blank=True)
    extra_fields = models.JSONField("Дополнительные данные", default=dict, blank=True)
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)
    updated_at = models.DateTimeField("Дата изменения", auto_now=True)

    class Meta:
        db_table = "procurement_items"
        ordering = ["created_at"]
        verbose_name = "Позиция закупки"
        verbose_name_plural = "Позиции закупок"

    def __str__(self):
        return self.nomenclature or f"Item {self.id}"