from django.urls import path
from . import views

app_name = "procurement"

urlpatterns = [
    # Импорты
    path("imports/upload/", views.upload_excel, name="upload-excel"),
    path("imports/", views.list_imports, name="list-imports"),
    path("imports/<uuid:upload_id>/preview/", views.preview_upload, name="preview-upload"),
    path("imports/<uuid:upload_id>/commit/", views.commit_upload, name="commit-upload"),
    path("imports/<uuid:import_id>/items/", views.list_import_items, name="list-import-items"),
    path("imports/<uuid:import_id>/", views.delete_import, name="delete-import"),

    # Позиции
    path("items/<uuid:item_id>/", views.update_item, name="update-item"),  # PATCH + DELETE
]