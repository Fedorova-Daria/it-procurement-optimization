from rest_framework import serializers
from .models import DataImport, ProcurementItem


class DataImportListSerializer(serializers.ModelSerializer):
    """Сериализатор для списка загруженных таблиц."""

    class Meta:
        model = DataImport
        fields = ["id", "name", "filename", "data_type", "year", "row_count", "created_at"]


class ProcurementItemSerializer(serializers.ModelSerializer):
    """Сериализатор для позиций закупок."""

    class Meta:
        model = ProcurementItem
        fields = [
            "id",
            "nomenclature",
            "quantity",
            "total_amount",
            "destination",
            "purpose",
            "unit",
            "unit_price",
            "extra_fields",
            "created_at",
            "updated_at",
        ]


class ProcurementItemUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для частичного обновления позиции (PATCH)."""

    class Meta:
        model = ProcurementItem
        fields = [
            "nomenclature",
            "quantity",
            "total_amount",
            "destination",
            "purpose",
            "unit",
            "unit_price",
            "extra_fields",
        ]
        extra_kwargs = {field: {"required": False} for field in fields}


class UploadResponseSerializer(serializers.Serializer):
    """Сериализатор ответа на загрузку файла."""

    upload_id = serializers.UUIDField()
    filename = serializers.CharField()
    sheets = serializers.ListField(child=serializers.CharField())
    columns = serializers.ListField(child=serializers.CharField())
    preview = serializers.ListField(child=serializers.DictField())


class CommitRequestSerializer(serializers.Serializer):
    """Сериализатор запроса на подтверждение импорта."""

    name = serializers.CharField(max_length=255)
    data_type = serializers.ChoiceField(choices=["planned", "stock", "purchased"])
    year = serializers.IntegerField(required=False, allow_null=True)
    sheet_name = serializers.CharField(max_length=255, required=False, default=None)
    mapping = serializers.DictField(
        child=serializers.CharField(),
        help_text="Словарь: ключ — название столбца Excel, значение — поле модели",
    )

    def validate_mapping(self, value):
        allowed_fields = {
            "nomenclature", "quantity", "total_amount",
            "destination", "purpose", "unit", "unit_price",
        }
        for excel_col, model_field in value.items():
            if model_field not in allowed_fields:
                raise serializers.ValidationError(
                    f"Поле '{model_field}' недопустимо. "
                    f"Разрешённые поля: {', '.join(sorted(allowed_fields))}"
                )
        if "nomenclature" not in value.values():
            raise serializers.ValidationError(
                "Обязательное поле 'nomenclature' должно быть указано в mapping."
            )
        return value


class CommitResponseSerializer(serializers.Serializer):
    """Сериализатор ответа на подтверждение импорта."""

    import_id = serializers.UUIDField()
    status = serializers.CharField()
    total_rows = serializers.IntegerField()
    imported_rows = serializers.IntegerField()