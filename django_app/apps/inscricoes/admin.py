# apps/inscricoes/admin.py
# Banco de Talentos — Polo de Inovação IFG
# Área administrativa para o time de RH gerenciar inscrições e critérios.

import csv

from django.contrib import admin, messages
from django.http import HttpResponse
from django.utils import timezone

from apps.inscricoes.models import CriterioEdital, Inscricao, InscricaoItem, StatusInscricao


@admin.register(CriterioEdital)
class CriterioEditalAdmin(admin.ModelAdmin):
    list_display = ("modalidade", "tipo_servidor", "ordem", "criterio", "maximo", "ativo")
    list_filter = ("modalidade", "tipo_servidor", "ativo")
    search_fields = ("criterio", "regra", "item_id")
    ordering = ("modalidade", "tipo_servidor", "ordem")


class InscricaoItemInline(admin.TabularInline):
    model = InscricaoItem
    extra = 0
    fields = ("criterio", "pontuacao", "pontuacao_validada", "observacao_avaliacao")
    autocomplete_fields = ("criterio",)
    readonly_fields = ("criterio", "pontuacao")


def _exportar_inscricoes_csv(queryset) -> HttpResponse:
    """Gera um HttpResponse com CSV das inscrições do queryset."""
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    filename = f"inscricoes_{timezone.localdate()}.csv"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response.write("﻿")  # BOM para Excel reconhecer UTF-8

    writer = csv.writer(response, delimiter=";")
    writer.writerow([
        "Nome", "CPF", "E-mail", "Vínculo", "Modalidade",
        "Tipo Servidor", "Status", "Pontuação Total", "Criado em",
    ])
    for ins in queryset.select_related("usuario"):
        u = ins.usuario
        writer.writerow([
            u.nome_completo,
            u.cpf,
            u.email,
            u.get_vinculo_display(),
            ins.get_modalidade_display(),
            ins.get_tipo_servidor_display() if ins.tipo_servidor else "—",
            ins.get_status_display(),
            ins.total,
            ins.criado_em.strftime("%d/%m/%Y %H:%M"),
        ])
    return response


@admin.register(Inscricao)
class InscricaoAdmin(admin.ModelAdmin):
    list_display = ("usuario", "modalidade", "tipo_servidor", "total", "status", "atualizado_em")
    list_filter = ("modalidade", "tipo_servidor", "status")
    search_fields = ("usuario__cpf", "usuario__nome_completo", "usuario__email")
    readonly_fields = ("criado_em", "atualizado_em", "enviada_em")
    inlines = [InscricaoItemInline]
    actions = ["aprovar_selecionadas", "reprovar_selecionadas", "marcar_em_analise", "exportar_csv"]

    @admin.action(description="Aprovar inscrições selecionadas")
    def aprovar_selecionadas(self, request, queryset):
        atualizadas = queryset.update(status=StatusInscricao.APROVADA)
        self.message_user(request, f"{atualizadas} inscrição(ões) aprovada(s).", messages.SUCCESS)

    @admin.action(description="Reprovar inscrições selecionadas")
    def reprovar_selecionadas(self, request, queryset):
        atualizadas = queryset.update(status=StatusInscricao.INDEFERIDA)
        self.message_user(request, f"{atualizadas} inscrição(ões) indeferida(s).", messages.WARNING)

    @admin.action(description="Marcar como Em análise")
    def marcar_em_analise(self, request, queryset):
        atualizadas = queryset.update(status=StatusInscricao.EM_ANALISE)
        self.message_user(request, f"{atualizadas} inscrição(ões) marcada(s) como Em análise.", messages.INFO)

    @admin.action(description="Exportar selecionadas como CSV")
    def exportar_csv(self, request, queryset):
        return _exportar_inscricoes_csv(queryset)


@admin.register(InscricaoItem)
class InscricaoItemAdmin(admin.ModelAdmin):
    list_display = ("inscricao", "criterio", "pontuacao", "pontuacao_validada")
    search_fields = ("inscricao__usuario__cpf", "inscricao__usuario__nome_completo", "criterio__criterio")
    autocomplete_fields = ("inscricao", "criterio")
