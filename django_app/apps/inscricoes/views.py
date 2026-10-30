# apps/inscricoes/views.py
# Banco de Talentos — Polo de Inovação IFG
# Views da área de inscrição do candidato (formulário + confirmação).

from decimal import Decimal, InvalidOperation

from django.conf import settings
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


# Editais da Chamada Pública por vínculo (links oficiais do site do IFG).
# Exibidos no topo da página "Minha Inscrição" para o candidato consultar
# o edital da sua modalidade antes de preencher.
EDITAIS = {
    Vinculo.ESTUDANTE: {
        "descricao": "Estudantes",
        "nome": "Edital PROPPG nº 31/2026",
        "url": "https://www.ifg.edu.br/editais-pesquisa-e-pos-graduacao/pesquisa-inovacao-em-andamento/46637-edital-proppg-n-31-2026-de-28-de-maio-de-2026",
    },
    Vinculo.COLABORADOR_EXTERNO: {
        "descricao": "Colaboradores Externos",
        "nome": "Edital PROPPG nº 30/2026",
        "url": "https://www.ifg.edu.br/editais-pesquisa-e-pos-graduacao/pesquisa-inovacao-em-andamento/46636-edital-proppg-n-30-2026-de-28-de-maio-de-2026",
    },
    Vinculo.SERVIDOR: {
        "descricao": "Servidores do IFG",
        "nome": "Edital PROPPG nº 29/2026",
        "url": "https://www.ifg.edu.br/editais-pesquisa-e-pos-graduacao/pesquisa-inovacao-em-andamento/46583-edital-proppg-n-29-2026",
    },
}


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
        "edital": EDITAIS.get(vinculo),
        "editais_todos": list(EDITAIS.values()),
    })


@login_required
def inscricao_view(request):
    """Rota antiga de inscrição — aposentada pela Retificação 4.

    A Análise Curricular deixou de existir no credenciamento e passou a
    acontecer dentro de cada Chamada Interna (Seção 5: itens 5.1 a 5.13 nos
    Editais 29 e 30; 5.1 a 5.14 no 31). Quem chegar
    aqui por link salvo ou favorito é levado à lista de chamadas.

    O fluxo antigo não foi reescrito: as inscrições já enviadas continuam
    visíveis como histórico, somente leitura.
    """
    return redirect("chamadas")


@login_required
def confirmacao_view(request):
    """Rota antiga da confirmação — aposentada junto com a inscrição única.

    Agora existe uma inscrição por chamada, então não há "a" inscrição do
    candidato para mostrar. A lista de Minhas Inscrições faz esse papel, com
    link para o comprovante de cada uma.
    """
    return redirect("chamadas")


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


@login_required
def download_lattes_xml(request, pk):
    # O XML do Lattes traz CPF, RG, filiação e endereço: só o RH baixa, e todo
    # download fica no AuditLog. A ação reaproveita COMPROVANTE_DOWNLOAD; o
    # campo "arquivo" distingue o XML do PDF.
    if not request.user.is_staff:
        raise PermissionDenied
    inscricao = get_object_or_404(Inscricao, pk=pk)
    if not inscricao.lattes_xml:
        raise Http404("Esta inscrição não possui currículo Lattes em XML.")
    AuditLog.objects.create(
        ator=request.user,
        alvo=inscricao.usuario,
        acao=AuditAction.COMPROVANTE_DOWNLOAD,
        ip=_get_client_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
        detalhes={"inscricao_id": pk, "arquivo": "lattes_xml"},
    )
    return FileResponse(
        inscricao.lattes_xml.open("rb"),
        as_attachment=True,
        filename=f"lattes_inscricao_{pk}.xml",
    )
