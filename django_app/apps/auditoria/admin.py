from django.contrib import admin

from apps.auditoria.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("acao", "ator", "alvo", "ip", "criado_em")
    list_filter = ("acao", "criado_em")
    search_fields = ("ator__cpf", "ator__nome_completo", "alvo__cpf", "alvo__nome_completo", "ip")
    readonly_fields = ("ator", "alvo", "acao", "objeto_tipo", "objeto_id", "ip", "user_agent", "detalhes", "criado_em")
    ordering = ("-criado_em",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
