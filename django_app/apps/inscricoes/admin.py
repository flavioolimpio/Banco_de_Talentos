from django.contrib import admin

from apps.inscricoes.models import CriterioEdital, Inscricao, InscricaoItem


@admin.register(CriterioEdital)
class CriterioEditalAdmin(admin.ModelAdmin):
    list_display = ("modalidade", "tipo_servidor", "ordem", "criterio", "maximo", "ativo")
    list_filter = ("modalidade", "tipo_servidor", "ativo")
    search_fields = ("criterio", "regra", "item_id")
    ordering = ("modalidade", "tipo_servidor", "ordem")


class InscricaoItemInline(admin.TabularInline):
    model = InscricaoItem
    extra = 0
    autocomplete_fields = ("criterio",)


@admin.register(Inscricao)
class InscricaoAdmin(admin.ModelAdmin):
    list_display = ("usuario", "modalidade", "tipo_servidor", "total", "status", "atualizado_em")
    list_filter = ("modalidade", "tipo_servidor", "status")
    search_fields = ("usuario__cpf", "usuario__nome_completo", "usuario__email")
    inlines = [InscricaoItemInline]


@admin.register(InscricaoItem)
class InscricaoItemAdmin(admin.ModelAdmin):
    list_display = ("inscricao", "criterio", "pontuacao", "pontuacao_validada")
    search_fields = ("inscricao__usuario__cpf", "inscricao__usuario__nome_completo", "criterio__criterio")
    autocomplete_fields = ("inscricao", "criterio")
