# apps/inscricoes/views_rh.py
# Banco de Talentos — Polo de Inovação IFG
# Views de revisão de inscrições pelo time de RH.

from decimal import Decimal, InvalidOperation

from csp.decorators import csp_replace
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.clickjacking import xframe_options_sameorigin

from apps.auditoria.models import AuditAction, AuditLog
from apps.inscricoes.forms_rh import RevisaoForm
from apps.inscricoes.models import (
    Inscricao,
    OpcaoCriterio,
    StatusInscricao,
    TipoCriterio,
)


def _get_client_ip(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _validar_item(post_data, item):
    """Converte a revisão do RH de um item em (pontos, observação, resposta).

    `resposta` é o que o RH confirmou ({"quantidade": n} ou {"opcao": ...}),
    ou {} no legado, onde não há resposta a guardar.

    Duas formas, conforme a origem do critério:

    - Chamada Interna (fluxo atual): o RH corrige a RESPOSTA — a quantidade
      ("de 3 projetos declarados, 1 está comprovado") ou a opção escolhida — e
      os pontos são recalculados pelo mesmo `CriterioEdital.pontuar()` que o
      candidato usou. Ninguém digita pontuação, dos dois lados.

    - Credenciamento antigo (chamadas de legado): aqueles critérios não têm
      pontos por unidade nem opções — a pontuação era digitada. Para não zerar
      inscrição histórica ao reabri-la, o campo de pontos continua disponível
      nesse caso.
    """
    criterio = item.criterio
    obs = post_data.get(f"obs_{item.pk}", "").strip()

    if item.inscricao.e_legado:
        bruto = post_data.get(f"validado_{item.pk}", "").strip()
        if not bruto:
            return item.pontuacao, obs, {}
        try:
            valor = Decimal(bruto.replace(",", "."))
        except InvalidOperation:
            valor = Decimal("0")
        return max(Decimal("0"), min(valor, criterio.maximo)), obs, {}

    if criterio.tipo == TipoCriterio.ESCOLHA:
        bruto = post_data.get(f"validado_opcao_{item.pk}", "").strip()
        opcao = None
        if bruto.isdigit():
            opcao = OpcaoCriterio.objects.filter(pk=int(bruto), criterio=criterio).first()
        return criterio.pontuar(opcao=opcao), obs, {"opcao": opcao}

    bruto = post_data.get(f"validado_qtd_{item.pk}", "").strip()
    try:
        quantidade = max(0, int(Decimal(bruto))) if bruto else 0
    except (InvalidOperation, ValueError):
        quantidade = 0
    return criterio.pontuar(quantidade=quantidade), obs, {"quantidade": quantidade}


def _parse_validacoes(post_data, itens):
    """{item_pk: {"pontuacao_validada", "observacao", "resposta"}} + total."""
    validacoes = {}
    total = Decimal("0.00")
    for item in itens:
        pontos, obs, resposta = _validar_item(post_data, item)
        validacoes[item.pk] = {"pontuacao_validada": pontos, "observacao": obs, "resposta": resposta}
        total += pontos
    return validacoes, total


def _contexto_itens(itens, post_data=None):
    """Um dicionário por item, com o que o candidato respondeu e o que o RH vê.

    `post_data` só é passado quando o formulário volta com erro: aí os valores
    que o RH já tinha digitado são preservados, em vez de voltarem ao original.
    """
    contexto = []
    for numero, item in enumerate(itens, start=1):
        criterio = item.criterio
        legado = item.inscricao.e_legado

        if post_data is not None:
            qtd = post_data.get(f"validado_qtd_{item.pk}", "")
            opcao_id = post_data.get(f"validado_opcao_{item.pk}", "")
            pontos_legado = post_data.get(f"validado_{item.pk}", "")
        else:
            # Abertura da tela: o RH parte da resposta gravada — a do
            # candidato ou, com XML, a que o próprio RH já apurou — e só
            # mexe no que precisar corrigir.
            qtd = item.quantidade
            opcao_id = item.opcao_id or ""
            pontos_legado = (
                item.pontuacao_validada if item.pontuacao_validada is not None else ""
            )

        contexto.append(
            {
                "numero": numero,
                "item": item,
                "criterio": criterio,
                "legado": legado,
                "e_escolha": (not legado) and criterio.tipo == TipoCriterio.ESCOLHA,
                "validado_qtd": qtd,
                "validado_opcao_id": str(opcao_id),
                "validado_pontos": pontos_legado,
            }
        )
    return contexto


@staff_member_required
def revisao_view(request, pk):
    inscricao = get_object_or_404(Inscricao, pk=pk)

    if inscricao.status != StatusInscricao.EM_ANALISE:
        messages.warning(request, "Esta inscrição não está em análise e não pode ser revisada.")
        return redirect("admin:inscricoes_inscricao_changelist")

    itens = list(
        inscricao.itens.select_related("criterio", "opcao")
        .prefetch_related("criterio__opcoes")
        .order_by("criterio__ordem")
    )

    if request.method == "GET":
        itens_com_score = _contexto_itens(itens)
        return render(request, "rh/revisao.html", {
            "inscricao": inscricao,
            "itens_com_score": itens_com_score,
            "form": RevisaoForm(initial={"parecer_geral": inscricao.parecer_geral}),
        })

    acao = request.POST.get("acao", "")
    if acao not in ("aprovar", "indeferir"):
        messages.error(request, "Ação inválida.")
        itens_com_score = _contexto_itens(itens, request.POST)
        return render(request, "rh/revisao.html", {
            "inscricao": inscricao,
            "itens_com_score": itens_com_score,
            "form": RevisaoForm(request.POST, acao=acao),
        })

    form = RevisaoForm(request.POST, acao=acao)

    if not form.is_valid():
        itens_com_score = _contexto_itens(itens, request.POST)
        return render(request, "rh/revisao.html", {
            "inscricao": inscricao,
            "itens_com_score": itens_com_score,
            "form": form,
        })

    validacoes, total_validado = _parse_validacoes(request.POST, itens)

    # Com o XML do Lattes o candidato não responde o quadro: a quantidade (ou
    # opção) que o RH apurou vira a resposta do item. Fica registrada para
    # recurso e volta preenchida se a inscrição for reaberta. Sem XML, a
    # resposta é do candidato e não é sobrescrita.
    grava_resposta = bool(inscricao.lattes_xml)

    with transaction.atomic():
        for item in itens:
            v = validacoes[item.pk]
            item.pontuacao_validada = v["pontuacao_validada"]
            item.observacao_avaliacao = v["observacao"]
            campos = ["pontuacao_validada", "observacao_avaliacao"]
            if grava_resposta:
                for campo, valor in v["resposta"].items():
                    setattr(item, campo, valor)
                    campos.append(campo)
            item.save(update_fields=campos)

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
@xframe_options_sameorigin
@csp_replace(FRAME_ANCESTORS=("'self'",))
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
