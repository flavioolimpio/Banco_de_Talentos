# apps/inscricoes/views_chamadas.py
# Banco de Talentos — Polo de Inovação IFG
#
# Fluxo de inscrição por Chamada Interna (Edital 29/2026, itens 5.1 a 5.16 na
# redação da proposta de Retificação nº 4/2026).
#
# Diferença para o fluxo antigo (views.py), que virou histórico:
#   - o quadro de critérios é o DA CHAMADA, montado pela Coordenação do
#     Projeto no admin, e não um quadro fixo por modalidade;
#   - o candidato NÃO digita pontos. Ele responde uma quantidade ("quantos
#     projetos?") ou escolhe uma opção (titulação), e o servidor calcula —
#     ver CriterioEdital.pontuar();
#   - existe uma inscrição por candidato POR chamada;
#   - o prazo é o da chamada, não uma flag global.

from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.auditoria.models import AuditAction, AuditLog
from apps.inscricoes.forms import InscricaoChamadaForm
from apps.inscricoes.models import (
    ChamadaInterna,
    Inscricao,
    InscricaoItem,
    OpcaoCriterio,
    StatusInscricao,
    TipoCriterio,
)


def _get_client_ip(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def chamadas_abertas_para(usuario):
    """Chamadas publicadas, dentro do prazo, com vaga para o vínculo da pessoa.

    A elegibilidade sai das vagas: não existe campo "modalidades elegíveis" na
    chamada, justamente para não haver como ele divergir do que foi publicado.
    """
    agora = timezone.now()
    return (
        ChamadaInterna.objects.filter(
            publicada=True,
            legado=False,
            abertura__lte=agora,
            encerramento__gte=agora,
            vagas__modalidade=usuario.vinculo,
        )
        .distinct()
        .order_by("encerramento")
    )


def _criterios_da(chamada, usuario, tipo_servidor=""):
    """Quadro de critérios da chamada para o vínculo/categoria do candidato."""
    return (
        chamada.criterios.filter(ativo=True, modalidade=usuario.vinculo)
        .filter(tipo_servidor__in=["", tipo_servidor])
        .prefetch_related("opcoes")
        .order_by("ordem")
    )


def _parse_respostas(post_data, criterios):
    """Lê as respostas do POST e devolve {criterio_pk: (quantidade, opcao)}.

    As perguntas não são campos de um Form porque variam por chamada: são
    lidas direto do POST, como já era feito no fluxo antigo. Toda a conversão
    para pontos acontece no servidor.
    """
    respostas = {}
    for criterio in criterios:
        if criterio.tipo == TipoCriterio.ESCOLHA:
            bruto = post_data.get(f"opcao_{criterio.pk}", "").strip()
            opcao = None
            if bruto.isdigit():
                # filter() em vez de get(): id de outro critério (ou inexistente)
                # simplesmente não pontua, em vez de derrubar a página.
                opcao = OpcaoCriterio.objects.filter(
                    pk=int(bruto), criterio=criterio
                ).first()
            respostas[criterio.pk] = (0, opcao)
        else:
            bruto = post_data.get(f"qtd_{criterio.pk}", "").strip().replace(",", ".")
            try:
                quantidade = int(Decimal(bruto)) if bruto else 0
            except (InvalidOperation, ValueError):
                quantidade = 0
            respostas[criterio.pk] = (max(0, quantidade), None)
    return respostas


def _montar_perguntas(criterios, respostas):
    """Junta critério + resposta + pontos, na ordem, para o template."""
    perguntas = []
    total = Decimal("0")
    for numero, criterio in enumerate(criterios, start=1):
        quantidade, opcao = respostas.get(criterio.pk, (0, None))
        pontos = criterio.pontuar(quantidade=quantidade, opcao=opcao)
        total += pontos
        perguntas.append(
            {
                "numero": numero,
                "criterio": criterio,
                "quantidade": quantidade,
                "opcao": opcao,
                "opcao_id": opcao.pk if opcao else None,
                "pontos": pontos,
                "e_escolha": criterio.tipo == TipoCriterio.ESCOLHA,
            }
        )
    return perguntas, total


@login_required
def chamadas_lista(request):
    """Página 'Minhas inscrições': chamadas abertas + histórico do candidato."""
    inscricoes = (
        Inscricao.objects.filter(usuario=request.user)
        .select_related("chamada", "vaga")
        .order_by("-criado_em")
    )
    inscritas = {i.chamada_id for i in inscricoes}
    abertas = [
        {"chamada": c, "ja_inscrito": c.pk in inscritas}
        for c in chamadas_abertas_para(request.user)
    ]
    return render(
        request,
        "inscricoes/chamadas_lista.html",
        {"abertas": abertas, "inscricoes": inscricoes},
    )


@login_required
def chamada_detalhe(request, pk):
    chamada = get_object_or_404(ChamadaInterna, pk=pk, publicada=True, legado=False)
    inscricao = Inscricao.objects.filter(usuario=request.user, chamada=chamada).first()
    vagas = chamada.vagas.all()
    return render(
        request,
        "inscricoes/chamada_detalhe.html",
        {
            "chamada": chamada,
            "vagas": vagas,
            "vagas_do_meu_vinculo": vagas.filter(modalidade=request.user.vinculo),
            "inscricao": inscricao,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def inscricao_chamada(request, pk):
    """O formulário da chamada — a tela que o candidato preenche."""
    chamada = get_object_or_404(ChamadaInterna, pk=pk, publicada=True, legado=False)
    usuario = request.user
    inscricao = Inscricao.objects.filter(usuario=usuario, chamada=chamada).first()

    # Já enviada: vai para a confirmação, a menos que o RH tenha devolvido
    # para "Pendente" (mesmo comportamento do fluxo antigo).
    if inscricao and inscricao.enviada_em and inscricao.status != StatusInscricao.PENDENTE:
        return redirect("inscricao_detalhe", pk=inscricao.pk)

    # Portão de prazo. Checado também no POST — formulário salvo, botão
    # "voltar" do navegador e curl não podem furar o prazo da chamada.
    if not chamada.aberta:
        return render(request, "inscricoes/chamada_fora_do_prazo.html", {"chamada": chamada})

    tipo_servidor = inscricao.tipo_servidor if inscricao else ""
    criterios = list(_criterios_da(chamada, usuario, tipo_servidor))

    if request.method == "GET":
        respostas = {}
        if inscricao:
            for item in inscricao.itens.select_related("criterio", "opcao"):
                respostas[item.criterio_id] = (item.quantidade, item.opcao)
        perguntas, total = _montar_perguntas(criterios, respostas)
        form = InscricaoChamadaForm(
            chamada=chamada,
            usuario=usuario,
            initial={
                "vaga": inscricao.vaga_id if inscricao else None,
                "licencas_maternidade": inscricao.licencas_maternidade if inscricao else 0,
                "declara_disponibilidade": inscricao.declara_disponibilidade if inscricao else False,
                "declara_nao_redistribuicao": inscricao.declara_nao_redistribuicao if inscricao else False,
            },
        )
        return _render_formulario(request, chamada, form, perguntas, total, inscricao)

    # ------------------------------------------------------------------ POST
    acao = request.POST.get("action", "rascunho")
    form = InscricaoChamadaForm(
        request.POST,
        request.FILES,
        chamada=chamada,
        usuario=usuario,
        acao=acao,
        tem_pdf=bool(inscricao and inscricao.comprovantes_pdf),
    )
    respostas = _parse_respostas(request.POST, criterios)
    perguntas, total = _montar_perguntas(criterios, respostas)

    if not form.is_valid():
        return _render_formulario(request, chamada, form, perguntas, total, inscricao)

    with transaction.atomic():
        if inscricao is None:
            inscricao = Inscricao(usuario=usuario, chamada=chamada)
        inscricao.modalidade = usuario.vinculo
        vaga = form.cleaned_data.get("vaga")
        inscricao.vaga = vaga
        if vaga is not None:
            inscricao.tipo_servidor = vaga.tipo_servidor
        inscricao.licencas_maternidade = form.cleaned_data.get("licencas_maternidade") or 0
        inscricao.declara_disponibilidade = bool(form.cleaned_data.get("declara_disponibilidade"))
        inscricao.declara_nao_redistribuicao = bool(
            form.cleaned_data.get("declara_nao_redistribuicao")
        )
        inscricao.total = total

        pdf = form.cleaned_data.get("comprovantes_pdf")
        if pdf:
            inscricao.comprovantes_pdf = pdf
            inscricao.comprovantes_pdf_nome_original = pdf.name[:255]
            inscricao.comprovantes_pdf_tamanho = pdf.size
            inscricao.comprovantes_pdf_mime = getattr(pdf, "content_type", "")[:120]

        if acao == "enviar":
            inscricao.status = StatusInscricao.EM_ANALISE
            inscricao.enviada_em = timezone.now()
        else:
            inscricao.status = StatusInscricao.PENDENTE
        inscricao.save()

        pks_do_quadro = []
        for pergunta in perguntas:
            criterio = pergunta["criterio"]
            pks_do_quadro.append(criterio.pk)
            InscricaoItem.objects.update_or_create(
                inscricao=inscricao,
                criterio=criterio,
                defaults={
                    "quantidade": pergunta["quantidade"],
                    "opcao": pergunta["opcao"],
                    "pontuacao": pergunta["pontos"],
                },
            )
        # Critério que saiu do quadro da chamada (o coordenador editou) não
        # pode continuar pontuando a inscrição.
        inscricao.itens.exclude(criterio_id__in=pks_do_quadro).delete()

    AuditLog.objects.create(
        ator=usuario,
        alvo=usuario,
        acao=AuditAction.INSCRICAO_SALVA,
        ip=_get_client_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
        detalhes={"chamada": chamada.pk, "acao": acao, "total": str(total)},
    )

    if acao == "enviar":
        messages.success(request, "Inscrição enviada com sucesso.")
        return redirect("inscricao_detalhe", pk=inscricao.pk)
    messages.success(request, "Rascunho salvo. Você pode continuar depois.")
    return redirect("inscricao_chamada", pk=chamada.pk)


def _render_formulario(request, chamada, form, perguntas, total, inscricao):
    return render(
        request,
        "inscricoes/chamada_formulario.html",
        {
            "chamada": chamada,
            "form": form,
            "perguntas": perguntas,
            "total": total,
            "inscricao": inscricao,
            "lattes_ausente": not request.user.lattes,
            "perfil_incompleto": not request.user.perfil_completo,
        },
    )


@login_required
def inscricao_detalhe(request, pk):
    """Comprovante da inscrição, somente leitura. Serve também para o legado."""
    inscricao = get_object_or_404(
        Inscricao.objects.select_related("chamada", "vaga", "usuario"),
        pk=pk,
        usuario=request.user,
    )
    itens = inscricao.itens.select_related("criterio", "opcao").order_by("criterio__ordem")
    return render(
        request,
        "inscricoes/inscricao_detalhe.html",
        {"inscricao": inscricao, "itens": itens},
    )
