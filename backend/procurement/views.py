from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from .models import DataImport, ProcurementItem
from .serializers import (
    DataImportListSerializer,
    ProcurementItemSerializer,
    ProcurementItemUpdateSerializer,
    CommitRequestSerializer,
)
from .services import save_temp_file, get_preview, commit_import
from .validators import validate_excel_file


# ─── 4.1. Загрузка Excel ────────────────────────────────────────────────────

@api_view(["POST"])
@parser_classes([MultiPartParser])
def upload_excel(request):
    """POST /api/v1/imports/upload/ — загрузить Excel-файл."""
    file = request.FILES.get("file")
    if not file:
        return Response(
            {"error": "Файл не передан. Используйте поле 'file'."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    errors = validate_excel_file(file)
    if errors:
        return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

    try:
        result = save_temp_file(file)
    except Exception as e:
        return Response(
            {"error": f"Не удалось обработать файл: {str(e)}"},
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    return Response(result, status=status.HTTP_201_CREATED)


# ─── 4.2. Предварительный просмотр ──────────────────────────────────────────

@api_view(["GET"])
def preview_upload(request, upload_id):
    """GET /api/v1/imports/{upload_id}/preview/ — предварительный просмотр."""
    sheet_name = request.query_params.get("sheet")
    try:
        result = get_preview(str(upload_id), sheet_name)
    except FileNotFoundError:
        return Response(
            {"error": "Загруженный файл не найден. Возможно, истёк срок хранения."},
            status=status.HTTP_404_NOT_FOUND,
        )
    return Response(result)


# ─── 4.3. Подтверждение импорта ──────────────────────────────────────────────

@api_view(["POST"])
def commit_upload(request, upload_id):
    """POST /api/v1/imports/{upload_id}/commit/ — подтвердить и сохранить."""
    serializer = CommitRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    try:
        result = commit_import(
            upload_id=str(upload_id),
            name=data["name"],
            data_type=data["data_type"],
            year=data.get("year"),
            sheet_name=data.get("sheet_name"),
            mapping=data["mapping"],
        )
    except FileNotFoundError:
        return Response(
            {"error": "Загруженный файл не найден."},
            status=status.HTTP_404_NOT_FOUND,
        )
    except ValueError as e:
        error_detail = e.args[0] if e.args else str(e)
        return Response(
            {"error": error_detail},
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    return Response(result, status=status.HTTP_201_CREATED)


# ─── 4.4. Список загруженных таблиц ─────────────────────────────────────────

@api_view(["GET"])
def list_imports(request):
    """GET /api/v1/imports/ — получить список загруженных таблиц."""
    data_type = request.query_params.get("data_type")
    year = request.query_params.get("year")

    queryset = DataImport.objects.all()
    if data_type:
        queryset = queryset.filter(data_type=data_type)
    if year:
        queryset = queryset.filter(year=year)

    serializer = DataImportListSerializer(queryset, many=True)
    return Response({"results": serializer.data})


# ─── 4.5. Содержимое таблицы ────────────────────────────────────────────────

class ItemsPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 500


@api_view(["GET"])
def list_import_items(request, import_id):
    """GET /api/v1/imports/{id}/items/ — получить содержимое таблицы."""
    try:
        data_import = DataImport.objects.get(id=import_id)
    except DataImport.DoesNotExist:
        return Response(
            {"error": "Таблица не найдена."},
            status=status.HTTP_404_NOT_FOUND,
        )

    paginator = ItemsPagination()
    items = data_import.items.all()
    page = paginator.paginate_queryset(items, request)

    serializer = ProcurementItemSerializer(page, many=True)
    response_data = paginator.get_paginated_response(serializer.data).data
    response_data["import_id"] = str(data_import.id)
    return Response(response_data)


# ─── 4.6. Редактирование записи ─────────────────────────────────────────────

@api_view(["PATCH"])
def update_item(request, item_id):
    """PATCH /api/v1/items/{id}/ — изменить запись."""
    try:
        item = ProcurementItem.objects.get(id=item_id)
    except ProcurementItem.DoesNotExist:
        return Response(
            {"error": "Запись не найдена."},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = ProcurementItemUpdateSerializer(item, data=request.data, partial=True)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    serializer.save()
    return Response(ProcurementItemSerializer(item).data)


# ─── 4.7. Удаление записи ───────────────────────────────────────────────────

@api_view(["DELETE"])
def delete_item(request, item_id):
    """DELETE /api/v1/items/{id}/ — удалить запись."""
    try:
        item = ProcurementItem.objects.select_related("data_import").get(id=item_id)
    except ProcurementItem.DoesNotExist:
        return Response(
            {"error": "Запись не найдена."},
            status=status.HTTP_404_NOT_FOUND,
        )

    data_import = item.data_import
    item.delete()

    # Обновляем row_count
    data_import.row_count = data_import.items.count()
    data_import.save(update_fields=["row_count"])

    return Response(status=status.HTTP_204_NO_CONTENT)


# ─── 4.8. Удаление всей таблицы ─────────────────────────────────────────────

@api_view(["DELETE"])
def delete_import(request, import_id):
    """DELETE /api/v1/imports/{id}/ — удалить всю таблицу."""
    try:
        data_import = DataImport.objects.get(id=import_id)
    except DataImport.DoesNotExist:
        return Response(
            {"error": "Таблица не найдена."},
            status=status.HTTP_404_NOT_FOUND,
        )

    data_import.delete()  # CASCADE удалит все связанные items
    return Response(status=status.HTTP_204_NO_CONTENT)