from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.usuarios.models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    model = Usuario
    ordering = ("nome_completo",)
    list_display = ("cpf", "nome_completo", "email", "vinculo", "perfil", "is_active", "is_staff")
    list_filter = ("vinculo", "perfil", "is_active", "is_staff")
    search_fields = ("cpf", "nome_completo", "email")
    fieldsets = (
        (None, {"fields": ("cpf", "password")}),
        ("Dados principais", {"fields": ("nome_completo", "email", "telefone", "vinculo", "perfil")}),
        ("Permissões", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("LGPD", {"fields": ("aceite_lgpd", "aceite_lgpd_em", "aceite_lgpd_versao", "aceite_lgpd_ip")}),
        ("Datas", {"fields": ("last_login", "date_joined", "created_at", "updated_at")}),
    )
    readonly_fields = ("last_login", "date_joined", "created_at", "updated_at", "aceite_lgpd_em", "aceite_lgpd_ip")
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("cpf", "email", "nome_completo", "vinculo", "password1", "password2"),
            },
        ),
    )
