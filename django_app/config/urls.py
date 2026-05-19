from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("", include("apps.usuarios.urls")),
    path("", include("apps.inscricoes.urls")),
    path("admin/", admin.site.urls),
]
