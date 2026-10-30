# apps/inscricoes/admin.py
# Banco de Talentos — Polo de Inovação IFG
# Área administrativa para o time de RH gerenciar inscrições e critérios.

import csv

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet
from django.http import HttpResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html

from apps.inscricoes.models import (
    ChamadaInterna,
    CriterioEdital,
    Inscricao,
    InscricaoItem,
    OpcaoCriterio,
    StatusInscricao,
    Vaga,
    erros_do_quadro,
)


class VagaInline(admin.TabularInline):
    """Quadro 1 do Aviso — as posições ofertadas."""

    model = Vaga
    extra = 1
    fields = ("ordem", "codigo", "funcao", "modalidade", "tipo_servidor",
              "quantidade", "carga_horaria", "bolsa", "perfil")


class QuadroCriteriosFormSet(BaseInlineFormSet):
    """Recusa o quadro que soma mais de 100 pontos, conforme o Anexo I (Edital 29: 7.1; 30: 6.1; 31: 8.1)."""

    def clean(self):
        super().clean()
        if self.instance.legado:
            return
        linhas = [
            (f.cleaned_data["modalidade"], f.cleaned_data.get("tipo_servidor"), f.cleaned_data.get("maximo"))
            for f in self.forms
            if f.cleaned_data.get("modalidade")
            and f.cleaned_data.get("ativo")
            and not f.cleaned_data.get("DELETE")
        ]
        erros = erros_do_quadro(linhas)
        if erros:
            raise ValidationError(erros)


class CriterioEditalForm(forms.ModelForm):
    """Mesma regra do quadro, para quem edita um critério fora da chamada."""

    class Meta:
        model = CriterioEdital
        fields = "__all__"

    def clean(self):
        dados = super().clean()
        chamada = dados.get("chamada")
        if chamada is None or chamada.legado or not dados.get("ativo"):
            return dados
        modalidade, tipo_servidor = dados.get("modalidade"), dados.get("tipo_servidor") or ""
        # Todos os tipos da modalidade: o quadro de um tipo inclui os critérios gerais.
        irmaos = CriterioEdital.objects.filter(
            chamada=chamada, modalidade=modalidade, ativo=True,
        ).exclude(pk=self.instance.pk)
        linhas = [(c.modalidade, c.tipo_servidor, c.maximo) for c in irmaos]
        linhas.append((modalidade, tipo_servidor, dados.get("maximo")))
        erros = erros_do_quadro(linhas)
        if erros:
            raise ValidationError(erros)
        return dados


class CriterioEditalInline(admin.TabularInline):
    """Quadro 2 do Aviso — o quadro de critérios DESTA chamada.

    É aqui que a Coordenação do Projeto monta a avaliação curricular, sem
    precisar de deploy (item 5.1, VI do Edital). Para critérios de escolha
    (titulação, por exemplo), cadastre as opções em "Opções do critério"
    depois de salvar a linha. A soma das pontuações máximas de cada quadro
    não passa de 100, conforme o Anexo I (Edital 29: 7.1; 30: 6.1; 31: 8.1).
    """

    model = CriterioEdital
    formset = QuadroCriteriosFormSet
    extra = 1
    fields = ("ordem", "modalidade", "tipo_servidor", "item_id", "criterio",
              "regra", "tipo", "pontos_por_unidade", "unidade_rotulo", "maximo", "ativo")
    show_change_link = True


@admin.register(ChamadaInterna)
class ChamadaInternaAdmin(admin.ModelAdmin):
    list_display = ("__str__", "abertura", "encerramento", "publicada", "legado", "total_inscricoes")
    list_filter = ("ano", "publicada", "legado")
    search_fields = ("titulo", "projeto", "edital")
    inlines = [VagaInline, CriterioEditalInline]
    actions = ["duplicar_chamada"]

    def total_inscricoes(self, obj):
        return obj.inscricoes.count()
    total_inscricoes.short_description = "Inscrições"

    @admin.action(description="Duplicar chamada (com vagas e quadro de critérios)")
    def duplicar_chamada(self, request, queryset):
        """O fluxo real é "igual à anterior, menos alguns itens".

        Sem isso, alguém redigita dez linhas de critério a cada chamada — e
        erra. A cópia nasce despublicada, com número provisório, para o RH
        ajustar antes de publicar.
        """
        criadas = 0
        for original in queryset:
            proximo = (
                ChamadaInterna.objects.filter(ano=original.ano)
                .order_by("-numero")
                .first()
            )
            nova = ChamadaInterna.objects.create(
                numero=(proximo.numero if proximo else 0) + 1,
                ano=original.ano,
                titulo=f"{original.titulo} (cópia)",
                projeto=original.projeto,
                edital=original.edital,
                texto=original.texto,
                abertura=original.abertura,
                encerramento=original.encerramento,
                publicada=False,
            )
            for vaga in original.vagas.all():
                vaga.pk = None
                vaga.chamada = nova
                vaga.save()
            for criterio in original.criterios.all():
                opcoes = list(criterio.opcoes.all())
                criterio.pk = None
                criterio.chamada = nova
                criterio.save()
                for opcao in opcoes:
                    opcao.pk = None
                    opcao.criterio = criterio
                    opcao.save()
            criadas += 1
        self.message_user(
            request,
            f"{criadas} chamada(s) duplicada(s), despublicadas e com numeração provisória.",
            messages.SUCCESS,
        )


class OpcaoCriterioInline(admin.TabularInline):
    model = OpcaoCriterio
    extra = 2
    fields = ("ordem", "rotulo", "pontos")


@admin.register(CriterioEdital)
class CriterioEditalAdmin(admin.ModelAdmin):
    form = CriterioEditalForm
    list_display = ("chamada", "modalidade", "tipo_servidor", "ordem", "criterio", "tipo", "maximo", "ativo")
    list_filter = ("chamada", "modalidade", "tipo_servidor", "tipo", "ativo")
    search_fields = ("criterio", "regra", "item_id")
    ordering = ("chamada", "modalidade", "tipo_servidor", "ordem")
    inlines = [OpcaoCriterioInline]


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
        "Tipo Servidor", "Status", "Pontuação Validada", "Pontuação Declarada (legado)", "Criado em",
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
            ins.total_validado,
            ins.total,
            ins.criado_em.strftime("%d/%m/%Y %H:%M"),
        ])
    return response


@admin.register(Inscricao)
class InscricaoAdmin(admin.ModelAdmin):
    # `total` é a soma declarada do credenciamento antigo; no fluxo por Chamada
    # é sempre 0 (o candidato não responde o quadro), então a lista mostra só
    # a pontuação validada. O `total` continua no formulário e no CSV.
    list_display = ("usuario", "modalidade", "tipo_servidor", "total_validado", "status", "link_revisar", "atualizado_em")
    list_filter = ("modalidade", "tipo_servidor", "status")
    search_fields = ("usuario__cpf", "usuario__nome_completo", "usuario__email")
    readonly_fields = ("criado_em", "atualizado_em", "enviada_em", "pdf_download_link", "xml_download_link", "total_validado", "revisado_em", "revisado_por")
    # Os campos de arquivo ficam fora do formulário: o widget padrão mostra o
    # caminho em /media/, que contém o CPF, e deixaria trocar ou apagar o
    # arquivo sem validação nem AuditLog. O acesso é pelos links abaixo, que
    # passam pelas views autenticadas e auditadas.
    exclude = ("comprovantes_pdf", "comprovantes_pdf_nome_original", "comprovantes_pdf_tamanho", "comprovantes_pdf_mime",
               "lattes_xml", "lattes_xml_nome_original")
    inlines = [InscricaoItemInline]
    actions = ["aprovar_selecionadas", "reprovar_selecionadas", "marcar_em_analise", "exportar_csv"]

    def pdf_download_link(self, obj):
        if not obj.comprovantes_pdf:
            return "—"
        download_url = reverse("download_comprovante", args=[obj.pk])
        view_url = reverse("view_comprovante", args=[obj.pk])
        return format_html(
            '<a href="{}" target="_blank">&#11015; Baixar</a>'
            ' &nbsp;|&nbsp; '
            '<a href="{}" target="_blank">&#128065; Visualizar</a>',
            download_url, view_url,
        )
    pdf_download_link.short_description = "Comprovantes"

    def xml_download_link(self, obj):
        if not obj.lattes_xml:
            return "—"
        return format_html(
            '<a href="{}">&#11015; Baixar XML do Lattes</a>',
            reverse("download_lattes_xml", args=[obj.pk]),
        )
    xml_download_link.short_description = "Currículo Lattes (XML)"

    def link_revisar(self, obj):
        if obj.status == StatusInscricao.EM_ANALISE:
            url = reverse("revisao_rh", args=[obj.pk])
            return format_html('<a href="{}">Revisar &rarr;</a>', url)
        return "—"
    link_revisar.short_description = "Revisão"

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
        from apps.auditoria.models import AuditAction, AuditLog
        AuditLog.objects.create(
            ator=request.user,
            acao=AuditAction.CSV_EXPORTADO,
            detalhes={"total": queryset.count()},
            ip=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )
        return _exportar_inscricoes_csv(queryset)


@admin.register(InscricaoItem)
class InscricaoItemAdmin(admin.ModelAdmin):
    list_display = ("inscricao", "criterio", "pontuacao", "pontuacao_validada")
    search_fields = ("inscricao__usuario__cpf", "inscricao__usuario__nome_completo", "criterio__criterio")
    autocomplete_fields = ("inscricao", "criterio")
