# apps/inscricoes/services.py
# Banco de Talentos — Polo de Inovação IFG
# Integração com a API IFGProduz para buscar pontuação de produção acadêmica.

import json
import logging
import urllib.error
import urllib.parse
import urllib.request

logger = logging.getLogger(__name__)


def buscar_dados_ifgproduz(lattes_url: str) -> dict | None:
    """
    Busca no IFGProduz o bloco de totais da produção acadêmica extraída
    do Lattes: dict com subtotalA (titulação), subtotalB (produção),
    subtotalC (orientações), subtotalD (bancas) e total.

    Retorna None se o Lattes não foi informado, o ID não existe na base
    ou a API estiver indisponível.
    """
    if not lattes_url or not lattes_url.strip():
        return None

    # safe=":/" mantém o http:// do URL do Lattes sem percentencoding
    lattes_id = urllib.parse.quote(lattes_url.strip(), safe=":/")
    url = (
        "https://api.lattes.bcc.ifg.edu.br/api/informacoes_docentes"
        f"?infor_docentes=informacoes_docentesProducao&lattes_id={lattes_id}"
    )

    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
        # Os subtotais e o total ponderado já vêm calculados em data["total"]
        return data["total"]
    except Exception as e:
        logger.error("IFGProduz falhou para %s: %s", lattes_url, e)
        return None


def buscar_pontuacao_ifgproduz(lattes_url: str) -> float | None:
    """
    Busca a pontuação total de produção acadêmica do servidor no IFGProduz.

    Mantida com a mesma assinatura/retorno de sempre (float ou None) —
    é o que o fluxo de inscrição usa. O detalhamento por subtotal fica
    em buscar_dados_ifgproduz.
    """
    dados = buscar_dados_ifgproduz(lattes_url)
    if dados is None:
        return None
    try:
        return float(dados["total"])
    except (KeyError, TypeError, ValueError) as e:
        logger.error("IFGProduz: resposta sem total para %s: %s", lattes_url, e)
        return None
