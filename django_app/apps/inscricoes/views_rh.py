# apps/inscricoes/views_rh.py
# Banco de Talentos — Polo de Inovação IFG
# Views de revisão de inscrições pelo time de RH.

from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.auditoria.models import AuditAction, AuditLog
from apps.inscricoes.forms_rh import RevisaoForm
from apps.inscricoes.models import Inscricao, StatusInscricao


def _get_client_ip(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _parse_validacoes(post_data, itens):
    validacoes = {}
    total = Decimal("0.00")
    for item in itens:
        raw = post_data.get(f"validado_{item.pk}", "").strip()
        obs = post_data.get(f"obs_{item.pk}", "").strip()
        if raw:
            try:
                valor = Decimal(raw.replace(",", "."))
            except InvalidOperation:
                valor = Decimal("0")
            valor = max(Decimal("0"), min(valor, item.criterio.maximo))
        else:
            valor = item.pontuacao
        validacoes[item.pk] = {"pontuacao_validada": valor, "observacao": obs}
        total += valor
    return validacoes, total


@staff_member_required
def revisao_view(request, pk):
    inscricao = get_object_or_404(Inscricao, pk=pk)

    if inscricao.status != StatusInscricao.EM_ANALISE:
        messages.warning(request, "Esta inscrição não está em análise e não pode ser revisada.")
        return redirect("admin:inscricoes_inscricao_changelist")

    itens = list(inscricao.itens.select_related("criterio").order_by("criterio__ordem"))

    if request.method == "GET":
        itens_com_score = [
            (item, item.pontuacao_validada if item.pontuacao_validada is not None else "")
            for item in itens
        ]
        return render(request, "rh/revisao.html", {
            "inscricao": inscricao,
            "itens_com_score": itens_com_score,
            "form": RevisaoForm(initial={"parecer_geral": inscricao.parecer_geral}),
        })

    acao = request.POST.get("acao", "")
    if acao not in ("aprovar", "indeferir"):
        messages.error(request, "Ação inválida.")
        itens_com_score = [
            (item, request.POST.get(f"validado_{item.pk}", ""))
            for item in itens
        ]
        return render(request, "rh/revisao.html", {
            "inscricao": inscricao,
            "itens_com_score": itens_com_score,
            "form": RevisaoForm(request.POST, acao=acao),
        })

    form = RevisaoForm(request.POST, acao=acao)

    if not form.is_valid():
        itens_com_score = [
            (item, request.POST.get(f"validado_{item.pk}", ""))
            for item in itens
        ]
        return render(request, "rh/revisao.html", {
            "inscricao": inscricao,
            "itens_com_score": itens_com_score,
            "form": form,
        })

    validacoes, total_validado = _parse_validacoes(request.POST, itens)

    with transaction.atomic():
        for item in itens:
            v = validacoes[item.pk]
            item.pontuacao_validada = v["pontuacao_validada"]
            item.observacao_avaliacao = v["observacao"]
            item.save(update_fields=["pontuacao_validada", "observacao_avaliacao"])

        inscricao.total_validado = total_validado
        inscricao.parecer_geral = form.cleaned_data["parecer_geral"]
        inscricao.revisado_em = timezone.now()
        inscricao.revisado_por = request.user
        inscricao.status = (
            StatusInscricao.APROVADA if acao == "aprovar" else StatusInscricao.INDEFERIDA
        )
        inscricao.save(update_fields=[
            "total_validado", "parecer_geral", "revisado_em", "revisado_por", "status",
        ])

        AuditLog.objects.create(
            ator=request.user,
            alvo=inscricao.usuario,
            acao=AuditAction.INSCRICAO_REVISADA,
            ip=_get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            detalhes={
                "inscricao_id": pk,
                "decisao": inscricao.get_status_display(),
                "total_validado": str(total_validado),
            },
        )

    messages.success(
        request,
        f"Inscrição de {inscricao.usuario.nome_completo} {inscricao.get_status_display().lower()}.",
    )
    return redirect("admin:inscricoes_inscricao_changelist")


@staff_member_required
def view_comprovante(request, pk):
    inscricao = get_object_or_404(Inscricao, pk=pk)
    if not inscricao.comprovantes_pdf:
        raise Http404
    AuditLog.objects.create(
        ator=request.user,
        alvo=inscricao.usuario,
        acao=AuditAction.COMPROVANTE_DOWNLOAD,
        ip=_get_client_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
        detalhes={"inscricao_id": pk},
    )
    return FileResponse(inscricao.comprovantes_pdf.open("rb"), content_type="application/pdf")
