from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.static import serve
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.documents.urls")),
    # Swagger / OpenAPI
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("swagger/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    # Раздача загруженных файлов. Nginx проксирует сюда /media/ (см. frontend/nginx.conf).
    # Для проекта с высокой нагрузкой на медиа в реальном проде лучше отдавать файлы
    # напрямую через Nginx с общего volume, минуя Django — но для старта этого достаточно.
    path("media/<path:path>", serve, {"document_root": settings.MEDIA_ROOT}),
]
