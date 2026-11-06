import uuid
import logging
from pathlib import Path
from decimal import Decimal, InvalidOperation

import pandas as pd
from django.conf import settings
from django.db import transaction

from .models import DataImport, ProcurementItem

logger = logging.getLogger(__name__)

TEMP_UPLOAD_DIR = Path(settings.MEDIA_ROOT) / "temp_uploads"


def get_temp_filepath(upload_id: str) -> Path:
    """Возвращает путь к временному файлу по upload_id."""
    return TEMP_UPLOAD_DIR / f"{upload_id}.xlsx"


def save_temp_file(uploaded_file) -> dict:
    """
    Сохраняет загруженный Excel во временную папку,
    считывает столбцы и формирует предварительный просмотр.
    """
    TEMP_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    upload_id = uuid.uuid4()
    filepath = get_temp_filepath(str(upload_id))

    with open(filepath, "wb") as f:
        for chunk in uploaded_file.chunks():
            f.write(chunk)

    # Считываем структуру файла
    excel_file = pd.ExcelFile(filepath, engine="openpyxl")
    sheet_names = excel_file.sheet_names

    # Берём первый лист для превью
    df = pd.read_excel(excel_file, sheet_name=sheet_names[0], engine="openpyxl")
    columns = df.columns.tolist()

    # Первые 20 строк для предпросмотра
    preview_df = df.head(20).where(df.notna(), None)
    preview = preview_df.to_dict(orient="records")

    return {
        "upload_id": str(upload_id),
        "filename": uploaded_file.name,
        "sheets": sheet_names,
        "columns": columns,
        "preview": preview,
    }


def get_preview(upload_id: str, sheet_name: str | None = None) -> dict:
    """
    Возвращает предварительный просмотр временно загруженного файла.
    """
    filepath = get_temp_filepath(upload_id)
    if not filepath.exists():
        raise FileNotFoundError(f"Временный файл {upload_id} не найден.")

    excel_file = pd.ExcelFile(filepath, engine="openpyxl")
    sheet_names = excel_file.sheet_names
    target_sheet = sheet_name if sheet_name in sheet_names else sheet_names[0]

    df = pd.read_excel(excel_file, sheet_name=target_sheet, engine="openpyxl")
    columns = df.columns.tolist()
    total_rows = len(df)

    preview_df = df.head(20).where(df.notna(), None)
    preview = preview_df.to_dict(orient="records")

    return {
        "upload_id": upload_id,
        "sheets": sheet_names,
        "current_sheet": target_sheet,
        "columns": columns,
        "total_rows": total_rows,
        "preview": preview,
    }


def commit_import(upload_id: str, name: str, data_type: str,
                  year: int | None, sheet_name: str | None,
                  mapping: dict) -> dict:
    """
    Читает Excel, применяет маппинг столбцов,
    валидирует и сохраняет данные в БД.
    """
    filepath = get_temp_filepath(upload_id)
    if not filepath.exists():
        raise FileNotFoundError(f"Временный файл {upload_id} не найден.")

    excel_file = pd.ExcelFile(filepath, engine="openpyxl")
    sheet_names = excel_file.sheet_names
    target_sheet = sheet_name if sheet_name in sheet_names else sheet_names[0]

    df = pd.read_excel(excel_file, sheet_name=target_sheet, engine="openpyxl")
    df = df.where(df.notna(), None)

    total_rows = len(df)
    if total_rows == 0:
        raise ValueError("Файл не содержит данных.")

    # Проверяем, что все столбцы из mapping существуют в файле
    missing_cols = set(mapping.keys()) - set(df.columns.tolist())
    if missing_cols:
        raise ValueError(f"Столбцы не найдены в файле: {', '.join(missing_cols)}")

    # Поля, которые попадают в основную модель
    model_fields = {
        "nomenclature", "quantity", "total_amount",
        "destination", "purpose", "unit", "unit_price",
    }
    decimal_fields = {"quantity", "total_amount", "unit_price"}

    # Собираем инвертированный маппинг: model_field -> excel_column
    inverted_mapping = {v: k for k, v in mapping.items()}

    # Определяем столбцы, которые пойдут в extra_fields
    mapped_excel_cols = set(mapping.keys())
    extra_cols = [col for col in df.columns if col not in mapped_excel_cols]

    errors = []
    items_to_create = []

    with transaction.atomic():
        data_import = DataImport.objects.create(
            name=name,
            filename=filepath.name,
            data_type=data_type,
            year=year,
            row_count=0,
        )

        for row_idx, row in df.iterrows():
            row_num = row_idx + 2  # +2: заголовок + 0-based index
            item_data = {}

            for model_field in model_fields:
                if model_field in inverted_mapping:
                    excel_col = inverted_mapping[model_field]
                    value = row.get(excel_col)

                    if model_field == "nomenclature" and (value is None or str(value).strip() == ""):
                        errors.append({"row": row_num, "error": "Наименование не может быть пустым."})
                        break

                    if model_field in decimal_fields and value is not None:
                        try:
                            value = Decimal(str(value))
                        except (InvalidOperation, ValueError):
                            errors.append({
                                "row": row_num,
                                "error": f"Некорректное числовое значение в поле '{model_field}': {value}",
                            })
                            break

                    item_data[model_field] = value if value is not None else ("" if model_field not in decimal_fields else None)
                else:
                    item_data[model_field] = "" if model_field not in decimal_fields else None

            else:
                # Собираем extra_fields
                extra = {}
                for col in extra_cols:
                    val = row.get(col)
                    if val is not None:
                        extra[col] = val if not isinstance(val, Decimal) else float(val)
                item_data["extra_fields"] = extra

                items_to_create.append(
                    ProcurementItem(data_import=data_import, **item_data)
                )

        if errors:
            # Откатываем транзакцию — не сохраняем частичные данные
            raise ValueError({"message": "Ошибки валидации", "errors": errors})

        ProcurementItem.objects.bulk_create(items_to_create, batch_size=500)
        data_import.row_count = len(items_to_create)
        data_import.save(update_fields=["row_count"])

    # Удаляем временный файл после успешного импорта
    filepath.unlink(missing_ok=True)

    return {
        "import_id": str(data_import.id),
        "status": "completed",
        "total_rows": total_rows,
        "imported_rows": len(items_to_create),
    }