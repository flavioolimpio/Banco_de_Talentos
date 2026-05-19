# apps/inscricoes/views.py
# Banco de Talentos — Polo de Inovação IFG
# Views da área de inscrição do candidato (formulário + confirmação).

from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.auditoria.models import AuditAction, AuditLog
from apps.inscricoes.forms import InscricaoForm
from apps.inscricoes.models import CriterioEdital, Inscricao, InscricaoItem, StatusInscricao
from apps.usuarios.models import Vinculo


def _get_criterios(usuario):
    return CriterioEdital.objects.filter(
        modalidade=usuario.vinculo,
        tipo_servidor="",
        ativo=True,
    ).order_by("ordem")


def _parse_scores(post_data, criterios):
    scores = {}
    total = Decimal("0.00")
    for criterio in criterios:
        raw = post_data.get(f"score_{criterio.pk}") or "0"
        try:
            valor = Decimal(raw.replace(",", "."))
        except InvalidOperation:
            valor = Decimal("0")
        valor = max(Decimal("0"), min(valor, criterio.maximo))
        scores[criterio.pk] = valor
        total += valor
    return scores, total


def _render_form(request, form, criterios, inscricao, scores=None):
    itens = scores or {}
    criterios_com_score = [
        (c, itens.get(c.pk, Decimal("0")))
        for c in criterios
    ]
    return render(request, "inscricoes/formulario.html", {
        "form": form,
        "criterios_com_score": criterios_com_score,
        "inscricao": inscricao,
        "is_servidor": request.user.vinculo == Vinculo.SERVIDOR,
    })


@login_required
@require_http_methods(["GET", "POST"])
def inscricao_view(request):
    usuario = request.user

    try:
        inscricao = Inscricao.objects.get(usuario=usuario)
        if inscricao.enviada_em:
            return redirect("inscricao_confirmacao")
    except Inscricao.DoesNotExist:
        inscricao = None

    criterios = list(_get_criterios(usuario))

    if request.method == "GET":
        itens_existentes = {}
        if inscricao:
            for item in inscricao.itens.select_related("criterio"):
                itens_existentes[item.criterio_id] = item.pontuacao
        return _render_form(request, InscricaoForm(usuario=usuario), criterios, inscricao, itens_existentes)

    # POST — implemented in Task 5
    return redirect("inscricao")


@login_required
def confirmacao_view(request):
    try:
        inscricao = Inscricao.objects.get(usuario=request.user)
    except Inscricao.DoesNotExist:
        return redirect("inscricao")
    return render(request, "inscricoes/confirmacao.html", {"inscricao": inscricao})
