from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.usuarios.models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    model = Usuario
    ordering = ("nome_completo",)
    list_display = (
        "cpf", "nome_completo", "email", "vinculo", "categoria_pretendida",
        "cnpq_area", "aceite_comunicacoes", "is_active", "is_staff",
    )
    # cnpq_area filtra por área; para filtrar pela grande área inteira, use a
    # busca do admin com o prefixo (ex.: "3.") — a grande área é derivada do
    # código, não tem coluna própria.
    list_filter = (
        "vinculo", "perfil", "categoria_pretendida", "maior_titulacao",
        "cnpq_area", "aceite_comunicacoes", "is_active", "is_staff",
    )
    search_fields = ("cpf", "nome_completo", "email", "cnpq_area")
    fieldsets = (
        (None, {"fields": ("cpf", "password")}),
        ("Dados principais", {"fields": ("nome_completo", "email", "telefone", "vinculo", "perfil")}),
        ("Perfil profissional", {"fields": (
            "categoria_pretendida", "servidor_ativo", "maior_titulacao",
            "area_atuacao", "cnpq_area", "disponibilidade_semanal",
            "nao_afastado_licenciado", "lattes", "resumo",
        )}),
        ("Permissões", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("LGPD", {"fields": (
            "aceite_lgpd", "aceite_lgpd_em", "aceite_lgpd_versao", "aceite_lgpd_ip",
            "aceite_comunicacoes", "aceite_comunicacoes_em",
        )}),
        ("Datas", {"fields": ("last_login", "date_joined", "created_at", "updated_at")}),
    )
    readonly_fields = (
        "last_login", "date_joined", "created_at", "updated_at",
        "aceite_lgpd_em", "aceite_lgpd_ip", "aceite_comunicacoes_em",
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("cpf", "email", "nome_completo", "vinculo", "password1", "password2"),
            },
        ),
    )
