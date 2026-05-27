# apps/inscricoes/views.py
# Banco de Talentos — Polo de Inovação IFG
# Views da área de inscrição do candidato (formulário + confirmação).

from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.auditoria.models import AuditAction, AuditLog
from apps.inscricoes.forms import InscricaoForm
from apps.inscricoes.models import CriterioEdital, Inscricao, InscricaoItem, StatusInscricao, TipoServidor
from apps.inscricoes.services import buscar_pontuacao_ifgproduz
from apps.usuarios.models import Vinculo


def _get_client_ip(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _get_criterios(usuario, tipo_servidor=""):
    # Critérios de pesquisador ficam com tipo_servidor="" (quadro compartilhado de servidor).
    # Apenas apoio_tecnico tem quadro próprio.
    ts = tipo_servidor if tipo_servidor == TipoServidor.APOIO_TECNICO else ""
    return CriterioEdital.objects.filter(
        modalidade=usuario.vinculo,
        tipo_servidor=ts,
        ativo=True,
    ).order_by("ordem")


def _parse_scores(post_data, criterios):
    """Processa apenas critérios manuais (is_api=False) a partir do POST."""
    scores = {}
    total = Decimal("0.00")
    for criterio in criterios:
        if criterio.is_api:
            continue
        raw = post_data.get(f"score_{criterio.pk}") or "0"
        try:
            valor = Decimal(raw.replace(",", "."))
        except InvalidOperation:
            valor = Decimal("0")
        valor = max(Decimal("0"), min(valor, criterio.maximo))
        scores[criterio.pk] = valor
        total += valor
    return scores, total


def _resolve_api_scores(usuario, criterios, inscricao):
    """
    Busca pontuação dos critérios API (IFGProduz) para o usuário.
    Retorna dict {criterio_pk: Decimal} com os valores resolvidos.
    """
    api_criterios = [c for c in criterios if c.is_api]
    if not api_criterios:
        return {}

    valor_api = buscar_pontuacao_ifgproduz(usuario.lattes)

    scores = {}
    for criterio in api_criterios:
        if valor_api is not None:
            scores[criterio.pk] = min(Decimal(str(valor_api)), criterio.maximo)
        elif inscricao:
            item = inscricao.itens.filter(criterio=criterio).first()
            scores[criterio.pk] = item.pontuacao if item else Decimal("0")
        else:
            scores[criterio.pk] = Decimal("0")
    return scores


def _render_form(request, form, criterios, inscricao, scores=None, lattes_ausente=False):
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
        "lattes_ausente": lattes_ausente,
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

    if request.method == "GET":
        tipo_servidor = inscricao.tipo_servidor if inscricao else ""
        criterios = list(_get_criterios(usuario, tipo_servidor))
        itens_existentes = {}
        if inscricao:
            for item in inscricao.itens.select_related("criterio"):
                itens_existentes[item.criterio_id] = item.pontuacao

        api_scores = _resolve_api_scores(usuario, criterios, inscricao)
        itens_existentes.update(api_scores)

        lattes_ausente = usuario.vinculo == Vinculo.SERVIDOR and not usuario.lattes
        return _render_form(
            request, InscricaoForm(usuario=usuario), criterios, inscricao,
            itens_existentes, lattes_ausente=lattes_ausente,
        )

    # POST
    action = request.POST.get("action", "rascunho")
    tipo_servidor = request.POST.get("tipo_servidor", "") if usuario.vinculo == Vinculo.SERVIDOR else ""
    criterios = list(_get_criterios(usuario, tipo_servidor))
    form = InscricaoForm(request.POST, request.FILES, usuario=usuario, acao=action)

    if not form.is_valid():
        scores, _ = _parse_scores(request.POST, criterios)
        api_scores = _resolve_api_scores(usuario, criterios, inscricao)
        scores.update(api_scores)
        lattes_ausente = usuario.vinculo == Vinculo.SERVIDOR and not usuario.lattes
        return _render_form(request, form, criterios, inscricao, scores, lattes_ausente=lattes_ausente)

    with transaction.atomic():
        if inscricao is None:
            inscricao = Inscricao(usuario=usuario, modalidade=usuario.vinculo)

        if usuario.vinculo == Vinculo.SERVIDOR:
            inscricao.tipo_servidor = form.cleaned_data["tipo_servidor"]

        pdf = form.cleaned_data.get("comprovantes_pdf")
        if pdf:
            inscricao.comprovantes_pdf = pdf
            inscricao.comprovantes_pdf_nome_original = pdf.name
            inscricao.comprovantes_pdf_tamanho = pdf.size
            inscricao.comprovantes_pdf_mime = getattr(pdf, "content_type", "application/pdf")

        scores, total = _parse_scores(request.POST, criterios)
        api_scores = _resolve_api_scores(usuario, criterios, inscricao)
        scores.update(api_scores)
        total += sum(api_scores.values())
        inscricao.total = total

        if action == "enviar":
            inscricao.status = StatusInscricao.EM_ANALISE
            inscricao.enviada_em = timezone.now()
        else:
            inscricao.status = StatusInscricao.PENDENTE

        inscricao.save()

        for criterio in criterios:
            InscricaoItem.objects.update_or_create(
                inscricao=inscricao,
                criterio=criterio,
                defaults={"pontuacao": scores[criterio.pk]},
            )

        AuditLog.objects.create(
            ator=usuario,
            acao=AuditAction.INSCRICAO_SALVA,
            ip=_get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            detalhes={"action": action, "total": str(total)},
        )

    if action == "enviar":
        messages.success(request, "Inscrição enviada com sucesso!")
        return redirect("inscricao_confirmacao")

    messages.success(request, "Rascunho salvo com sucesso.")
    return redirect("inscricao")


@login_required
def confirmacao_view(request):
    try:
        inscricao = Inscricao.objects.get(usuario=request.user)
    except Inscricao.DoesNotExist:
        return redirect("inscricao")
    return render(request, "inscricoes/confirmacao.html", {"inscricao": inscricao})


@login_required
def download_comprovante(request, pk):
    if not request.user.is_staff:
        raise PermissionDenied
    inscricao = get_object_or_404(Inscricao, pk=pk)
    if not inscricao.comprovantes_pdf:
        raise Http404("Esta inscrição não possui comprovante em PDF.")
    file_handle = inscricao.comprovantes_pdf.open("rb")
    AuditLog.objects.create(
        ator=request.user,
        acao=AuditAction.COMPROVANTE_DOWNLOAD,
        ip=_get_client_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
        detalhes={
            "inscricao_id": pk,
            "arquivo": inscricao.comprovantes_pdf_nome_original,
        },
    )
    return FileResponse(
        file_handle,
        as_attachment=True,
        filename=inscricao.comprovantes_pdf_nome_original or "comprovantes.pdf",
    )
