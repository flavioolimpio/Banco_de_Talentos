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
    # Servidor: Pesquisador e Apoio Técnico usam o MESMO quadro (tipo_servidor="").
    #   O subtipo continua sendo registrado na inscrição, mas a pontuação é idêntica.
    # Colaborador Externo: Apoio Técnico tem quadro próprio (Quadro II), por isso
    #   mantemos o desvio apenas para essa modalidade.
    if usuario.vinculo == Vinculo.SERVIDOR:
        ts = ""
    else:
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
    Retorna (dict {criterio_pk: Decimal}, api_falhou: bool).
    api_falhou=True indica que o Lattes está preenchido mas a API não respondeu.
    """
    api_criterios = [c for c in criterios if c.is_api]
    if not api_criterios:
        return {}, False

    valor_api = buscar_pontuacao_ifgproduz(usuario.lattes)
    api_falhou = usuario.lattes and valor_api is None

    scores = {}
    for criterio in api_criterios:
        if valor_api is not None:
            scores[criterio.pk] = min(Decimal(str(valor_api)), criterio.maximo)
        elif inscricao and inscricao.pk:
            # só acessa o banco se a inscrição já foi salva (tem pk)
            item = inscricao.itens.filter(criterio=criterio).first()
            scores[criterio.pk] = item.pontuacao if item else Decimal("0")
        else:
            scores[criterio.pk] = Decimal("0")
    return scores, bool(api_falhou)


def _render_form(request, form, criterios, inscricao, scores=None, lattes_ausente=False, api_falhou=False):
    itens = scores or {}
    num_manual = 0
    criterios_com_score = []
    for c in criterios:
        score = itens.get(c.pk, Decimal("0"))
        if c.is_api:
            criterios_com_score.append((c, score, None))
        else:
            num_manual += 1
            criterios_com_score.append((c, score, num_manual))
    vinculo = request.user.vinculo
    return render(request, "inscricoes/formulario.html", {
        "form": form,
        "criterios_com_score": criterios_com_score,
        "inscricao": inscricao,
        "is_servidor": vinculo == Vinculo.SERVIDOR,
        "needs_subtipo": vinculo in (Vinculo.SERVIDOR, Vinculo.COLABORADOR_EXTERNO),
        "lattes_ausente": lattes_ausente,
        "api_falhou": api_falhou,
    })


@login_required
@require_http_methods(["GET", "POST"])
def inscricao_view(request):
    usuario = request.user

    try:
        inscricao = Inscricao.objects.get(usuario=usuario)
        # Trava o formulário depois de enviado. Exceção: se o RH devolveu a
        # inscrição para "Pendente" no admin, o candidato pode reabrir e
        # reenviar (ex.: após uma mudança de regras do edital).
        if inscricao.enviada_em and inscricao.status != StatusInscricao.PENDENTE:
            return redirect("inscricao_confirmacao")
    except Inscricao.DoesNotExist:
        inscricao = None

    if request.method == "GET":
        # A categoria (tipo_servidor) define qual quadro de critérios mostrar.
        # Para Colaborador Externo, Pesquisador e Apoio Técnico têm quadros
        # diferentes, então o JS recarrega a página com ?tipo=... ao trocar o
        # seletor. Prioridade: parâmetro da URL > inscrição existente > vazio.
        tipos_validos = {c[0] for c in TipoServidor.choices}
        tipo_param = request.GET.get("tipo", "")
        if tipo_param in tipos_validos:
            tipo_servidor = tipo_param
        elif inscricao:
            tipo_servidor = inscricao.tipo_servidor
        else:
            tipo_servidor = ""
        criterios = list(_get_criterios(usuario, tipo_servidor))
        itens_existentes = {}
        if inscricao:
            for item in inscricao.itens.select_related("criterio"):
                itens_existentes[item.criterio_id] = item.pontuacao

        api_scores, api_falhou = _resolve_api_scores(usuario, criterios, inscricao)
        itens_existentes.update(api_scores)

        lattes_ausente = usuario.vinculo == Vinculo.SERVIDOR and not usuario.lattes
        return _render_form(
            request,
            InscricaoForm(usuario=usuario, initial={"tipo_servidor": tipo_servidor}),
            criterios, inscricao,
            itens_existentes, lattes_ausente=lattes_ausente, api_falhou=api_falhou,
        )

    # POST
    action = request.POST.get("action", "rascunho")
    needs_subtipo = usuario.vinculo in (Vinculo.SERVIDOR, Vinculo.COLABORADOR_EXTERNO)
    tipo_servidor = request.POST.get("tipo_servidor", "") if needs_subtipo else ""
    criterios = list(_get_criterios(usuario, tipo_servidor))
    form = InscricaoForm(request.POST, request.FILES, usuario=usuario, acao=action)

    if not form.is_valid():
        scores, _ = _parse_scores(request.POST, criterios)
        api_scores, api_falhou = _resolve_api_scores(usuario, criterios, inscricao)
        scores.update(api_scores)
        lattes_ausente = usuario.vinculo == Vinculo.SERVIDOR and not usuario.lattes
        return _render_form(request, form, criterios, inscricao, scores, lattes_ausente=lattes_ausente, api_falhou=api_falhou)

    with transaction.atomic():
        if inscricao is None:
            inscricao = Inscricao(usuario=usuario, modalidade=usuario.vinculo)

        if needs_subtipo:
            inscricao.tipo_servidor = form.cleaned_data["tipo_servidor"]

        pdf = form.cleaned_data.get("comprovantes_pdf")
        if pdf:
            inscricao.comprovantes_pdf = pdf
            inscricao.comprovantes_pdf_nome_original = pdf.name
            inscricao.comprovantes_pdf_tamanho = pdf.size
            inscricao.comprovantes_pdf_mime = getattr(pdf, "content_type", "application/pdf")

        scores, total_manual = _parse_scores(request.POST, criterios)
        api_scores, _ = _resolve_api_scores(usuario, criterios, inscricao)
        scores.update(api_scores)
        total_api = sum(api_scores.values())

        if usuario.vinculo == Vinculo.SERVIDOR:
            # Nota final = (IFGProduz + critérios manuais) / 2, cada um capped em 100
            total = (min(total_manual, Decimal("100")) + min(total_api, Decimal("100"))) / 2
        else:
            total = total_manual + total_api
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
                defaults={"pontuacao": scores.get(criterio.pk, Decimal("0"))},
            )

        # Remove itens que não fazem mais parte do quadro atual (ex.: critérios
        # de um quadro antigo após mudança de regras). Sem isso, ao reenviar a
        # inscrição os itens obsoletos ficariam órfãos e apareceriam na revisão.
        criterio_ids_atuais = [c.pk for c in criterios]
        inscricao.itens.exclude(criterio_id__in=criterio_ids_atuais).delete()

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

    itens = inscricao.itens.select_related("criterio").order_by("criterio__ordem")
    num_manual = 0
    itens_com_num = []
    total_api = Decimal("0")
    total_manual = Decimal("0")
    for item in itens:
        if item.criterio.is_api:
            itens_com_num.append((item, None))
            total_api += item.pontuacao
        else:
            num_manual += 1
            itens_com_num.append((item, num_manual))
            total_manual += item.pontuacao

    is_servidor = inscricao.modalidade == Vinculo.SERVIDOR
    ctx = {"inscricao": inscricao, "itens_com_num": itens_com_num, "is_servidor": is_servidor}
    if is_servidor:
        ctx["formula_ifgproduz"] = min(total_api, Decimal("100"))
        ctx["formula_criterios"] = min(total_manual, Decimal("100"))
    return render(request, "inscricoes/confirmacao.html", ctx)


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
