# apps/inscricoes/views_chamadas.py
# Banco de Talentos — Polo de Inovação IFG
#
# Fluxo de inscrição por Chamada Interna (Edital 29/2026, itens 5.1 a 5.16 na
# redação da proposta de Retificação nº 4/2026).
#
# Diferença para o fluxo antigo (views.py), que virou histórico:
#   - o quadro de critérios é o DA CHAMADA, montado pela Coordenação do
#     Projeto no admin, e não um quadro fixo por modalidade;
#   - o candidato NÃO digita pontos nem responde o quadro: desde 23/09/2026
#     ele envia o currículo Lattes em XML. O RH apura as quantidades a partir
#     do XML (skill lattes-xml-extrator) e as lança na revisão, onde o
#     servidor calcula os pontos — ver CriterioEdital.pontuar();
#   - existe uma inscrição por candidato POR chamada;
#   - o prazo é o da chamada, não uma flag global.

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
    StatusInscricao,
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

    # Item 5.3 do Edital: só se inscreve quem está credenciado, isto é, com o
    # cadastro completo (item 4.4.2). Vale para o rascunho também — e para o
    # POST, pelo mesmo motivo do prazo acima.
    pendencias = usuario.pendencias_cadastro()
    if pendencias:
        return render(
            request,
            "inscricoes/chamada_cadastro_incompleto.html",
            {"chamada": chamada, "pendencias": pendencias},
        )

    if request.method == "GET":
        form = InscricaoChamadaForm(
            chamada=chamada,
            usuario=usuario,
            initial={
                "vaga": inscricao.vaga_id if inscricao else None,
                "licencas_maternidade": inscricao.licencas_maternidade if inscricao else 0,
                "declara_disponibilidade": inscricao.declara_disponibilidade if inscricao else False,
            },
        )
        return _render_formulario(request, chamada, form, inscricao)

    # ------------------------------------------------------------------ POST
    acao = request.POST.get("action", "rascunho")
    form = InscricaoChamadaForm(
        request.POST,
        request.FILES,
        chamada=chamada,
        usuario=usuario,
        acao=acao,
        tem_xml=bool(inscricao and inscricao.lattes_xml),
        tem_pdf=bool(inscricao and inscricao.comprovantes_pdf),
    )

    if not form.is_valid():
        return _render_formulario(request, chamada, form, inscricao)

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

        xml = form.cleaned_data.get("lattes_xml")
        if xml:
            inscricao.lattes_xml = xml
            inscricao.lattes_xml_nome_original = xml.name[:255]
        # Estudante (Edital 31, item 5.4, c): declaração de matrícula e histórico.
        pdf = form.cleaned_data.get("matricula_pdf")
        if pdf:
            inscricao.comprovantes_pdf = pdf
            inscricao.comprovantes_pdf_nome_original = pdf.name[:255]
            inscricao.comprovantes_pdf_tamanho = pdf.size
            inscricao.comprovantes_pdf_mime = "application/pdf"

        if acao == "enviar":
            inscricao.status = StatusInscricao.EM_ANALISE
            inscricao.enviada_em = timezone.now()
        else:
            inscricao.status = StatusInscricao.PENDENTE
        inscricao.save()

        # Um item zerado por critério do quadro: é a folha que o RH preenche na
        # revisão com as quantidades apuradas do XML. get_or_create, e não
        # update_or_create, para um novo salvamento não apagar o que já
        # estiver lá.
        criterios = _criterios_da(chamada, usuario, inscricao.tipo_servidor)
        for criterio in criterios:
            InscricaoItem.objects.get_or_create(inscricao=inscricao, criterio=criterio)
        # Critério que saiu do quadro da chamada (o coordenador editou) não
        # pode continuar pontuando a inscrição.
        inscricao.itens.exclude(criterio__in=criterios).delete()

    AuditLog.objects.create(
        ator=usuario,
        alvo=usuario,
        acao=AuditAction.INSCRICAO_SALVA,
        ip=_get_client_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
        detalhes={"chamada": chamada.pk, "acao": acao, "xml_enviado": bool(xml), "pdf_enviado": bool(pdf)},
    )

    if acao == "enviar":
        messages.success(request, "Inscrição enviada com sucesso.")
        return redirect("inscricao_detalhe", pk=inscricao.pk)
    messages.success(request, "Rascunho salvo. Você pode continuar depois.")
    return redirect("inscricao_chamada", pk=chamada.pk)


def _render_formulario(request, chamada, form, inscricao):
    return render(
        request,
        "inscricoes/chamada_formulario.html",
        {
            "chamada": chamada,
            "form": form,
            "inscricao": inscricao,
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
