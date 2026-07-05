# scripts/analisar_lattes_xml.py
# Banco de Talentos — Polo de Inovação IFG
# Consolida os currículos Lattes baixados manualmente numa planilha CSV
# comparável — um candidato por linha — para apoiar a montagem de shortlists
# de indicação de especialistas. Aceita:
#   .zip/.xml — export XML do CNPq (só o DONO do currículo consegue exportar)
#   .html     — página pública do Lattes salva pelo navegador (Ctrl+S na
#               visualização do CV; é o caminho para currículos de terceiros,
#               já que o CNPq não permite baixar o XML de outra pessoa)
#
# Roda FORA do Django, direto no Windows, só com a biblioteca padrão:
#   python scripts/analisar_lattes_xml.py <pasta_com_arquivos> [--saida arquivo.csv]
#   python scripts/analisar_lattes_xml.py --selfcheck
#
# O CSV sai em UTF-8 com BOM (abre certo no Excel). O "join" com a planilha
# do comando exportar_inscritos_lattes é feito pela coluna id_lattes (ID de
# 16 dígitos no fim da URL http://lattes.cnpq.br/<id>).
#
# Apenas leitura de arquivos locais. Não acessa rede nem altera nada.

import argparse
import csv
import io
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

ANOS_RECENTES = 5  # "recente" = últimos 5 anos

# Ordem de senioridade da titulação no XML do Lattes.
TITULACOES = [
    ("POS-DOUTORADO", "Pós-doutorado"),
    ("DOUTORADO", "Doutorado"),
    ("MESTRADO", "Mestrado"),
    ("ESPECIALIZACAO", "Especialização"),
    ("GRADUACAO", "Graduação"),
]

COLUNAS = [
    "arquivo",
    "id_lattes",
    "nome",
    "atualizado_em",
    "maior_titulacao",
    "curso_titulacao",
    "areas_atuacao",
    "n_projetos_pesquisa",
    "projetos_recentes",
    "n_artigos_total",
    "n_artigos_recentes",
    "n_trabalhos_eventos",
    "n_patentes",
    "n_softwares",
    "n_orientacoes_mestrado",
    "n_orientacoes_doutorado",
    "n_outras_orientacoes",
    "palavras_chave",
    "resumo_cv",
]


def _ano(texto):
    """Converte um atributo de ano do Lattes em int; texto vazio/lixo vira 0."""
    try:
        return int(texto)
    except (TypeError, ValueError):
        return 0


def extrair_indicadores(root, nome_arquivo=""):
    """
    Extrai os indicadores de um XML de currículo Lattes já parseado.
    Tolerante a tags ausentes: currículo incompleto gera campos vazios/zero,
    nunca exceção.
    """
    ano_corte = date.today().year - ANOS_RECENTES
    dados_gerais = root.find("DADOS-GERAIS")
    dg = dados_gerais.attrib if dados_gerais is not None else {}

    # Maior titulação concluída (varre da mais alta para a mais baixa).
    maior_titulacao, curso = "", ""
    for tag, rotulo in TITULACOES:
        formacoes = [
            f for f in root.iter(tag)
            if f.get("STATUS-DO-CURSO", "CONCLUIDO") == "CONCLUIDO"
        ]
        if formacoes:
            maior_titulacao = rotulo
            curso = formacoes[0].get("NOME-CURSO", "")
            break

    areas = []
    for area in root.iter("AREA-DE-ATUACAO"):
        nome_area = area.get("NOME-DA-AREA-DO-CONHECIMENTO", "")
        sub = area.get("NOME-DA-SUB-AREA-DO-CONHECIMENTO", "")
        rotulo = f"{nome_area}/{sub}" if sub else nome_area
        if rotulo and rotulo not in areas:
            areas.append(rotulo)

    projetos = list(root.iter("PROJETO-DE-PESQUISA"))
    projetos_recentes = [
        p.get("NOME-DO-PROJETO", "")
        for p in projetos
        if _ano(p.get("ANO-INICIO")) >= ano_corte or not p.get("ANO-FIM")
    ]

    artigos = [
        a.find("DADOS-BASICOS-DO-ARTIGO")
        for a in root.iter("ARTIGO-PUBLICADO")
    ]
    artigos = [a for a in artigos if a is not None]
    artigos_recentes = [
        a for a in artigos if _ano(a.get("ANO-DO-ARTIGO")) >= ano_corte
    ]

    orientacoes_mestrado = len(list(root.iter("ORIENTACOES-CONCLUIDAS-PARA-MESTRADO")))
    orientacoes_doutorado = len(list(root.iter("ORIENTACOES-CONCLUIDAS-PARA-DOUTORADO")))
    outras_orientacoes = len(list(root.iter("OUTRAS-ORIENTACOES-CONCLUIDAS")))

    # Palavras-chave espalhadas pelas produções — deduplicadas, até 15.
    palavras = []
    for pc in root.iter("PALAVRAS-CHAVE"):
        for i in range(1, 7):
            p = pc.get(f"PALAVRA-CHAVE-{i}", "").strip()
            if p and p.lower() not in (x.lower() for x in palavras):
                palavras.append(p)
    palavras = palavras[:15]

    resumo_el = root.find("DADOS-GERAIS/RESUMO-CV")
    resumo = resumo_el.get("TEXTO-RESUMO-CV-RH", "") if resumo_el is not None else ""

    return {
        "arquivo": nome_arquivo,
        "id_lattes": root.get("NUMERO-IDENTIFICADOR", ""),
        "nome": dg.get("NOME-COMPLETO", ""),
        "atualizado_em": root.get("DATA-ATUALIZACAO", ""),
        "maior_titulacao": maior_titulacao,
        "curso_titulacao": curso,
        "areas_atuacao": "; ".join(areas),
        "n_projetos_pesquisa": len(projetos),
        "projetos_recentes": "; ".join(t for t in projetos_recentes if t),
        "n_artigos_total": len(artigos),
        "n_artigos_recentes": len(artigos_recentes),
        "n_trabalhos_eventos": len(list(root.iter("TRABALHO-EM-EVENTOS"))),
        "n_patentes": len(list(root.iter("PATENTE"))),
        "n_softwares": len(list(root.iter("SOFTWARE"))),
        "n_orientacoes_mestrado": orientacoes_mestrado,
        "n_orientacoes_doutorado": orientacoes_doutorado,
        "n_outras_orientacoes": outras_orientacoes,
        "palavras_chave": "; ".join(palavras),
        "resumo_cv": resumo[:500],
    }


def carregar_xml(caminho: Path):
    """Abre um .xml direto ou o curriculo.xml de dentro de um .zip do CNPq."""
    if caminho.suffix.lower() == ".zip":
        with zipfile.ZipFile(caminho) as zf:
            nome_xml = next(n for n in zf.namelist() if n.lower().endswith(".xml"))
            with zf.open(nome_xml) as fh:
                return ET.parse(io.BytesIO(fh.read())).getroot()
    return ET.parse(caminho).getroot()


# ---------------------------------------------------------------------------
# Parser do HTML público do Lattes (visualizacv.do salvo pelo navegador).
# O HTML não tem a estrutura rica do XML: alguns campos ficam vazios
# (palavras-chave, orientações por nível) e as contagens usam a numeração
# "1. 2. 3." dos itens de cada seção.
# ---------------------------------------------------------------------------

# Âncoras <a name="..."> que delimitam as seções no visualizacv.
_TODAS_ANCORAS_FIM = [
    "FormacaoComplementar", "AtuacaoProfissional", "ProjetosPesquisa",
    "ProjetosDesenvolvimento", "ProducoesCientificas", "ProducaoBibliografica",
    "ArtigosCompletos", "TrabalhosPublicadosAnaisCongresso",
    "ApresentacoesTrabalho", "ProducaoTecnica", "TrabalhosTecnicos",
    "DemaisProducaoTecnica", "PatentesRegistros", "Orientacoes", "Bancas",
    "ParticipacaoBancasComissoes", "Eventos", "PotencialInovacao",
]


def _texto(html):
    """Remove tags e comprime espaços."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def _secao(html, ancora):
    """Recorta o trecho entre <a name="ancora"> e a próxima âncora conhecida."""
    partes = html.split(f'name="{ancora}"', 1)
    if len(partes) < 2:
        return ""
    trecho = partes[1]
    corte = len(trecho)
    for fim in _TODAS_ANCORAS_FIM:
        if fim == ancora:
            continue
        pos = trecho.find(f'name="{fim}"')
        if 0 <= pos < corte:
            corte = pos
    return trecho[:corte]


def _conta_itens(html_secao):
    """Conta os itens numerados (<b>1.</b>, <b>2.</b>...) de uma seção."""
    return len(re.findall(r"<b>\d+\.\s*</b>", html_secao))


def carregar_html(caminho: Path) -> str:
    """Decodifica o HTML salvo: usa o charset do meta se houver, senão latin-1
    (o visualizacv do CNPq é ISO-8859-1 e normalmente não declara charset)."""
    raw = caminho.read_bytes()
    m = re.search(rb"charset=([a-zA-Z0-9_-]+)", raw[:2000])
    encoding = m.group(1).decode() if m else "latin-1"
    try:
        return raw.decode(encoding)
    except (LookupError, UnicodeDecodeError):
        return raw.decode("latin-1", errors="replace")


def extrair_indicadores_html(html: str, nome_arquivo=""):
    """
    Extrai do HTML público do Lattes os mesmos indicadores do parser XML.
    Campos sem equivalente no HTML ficam vazios. Seção ausente = zero/vazio,
    nunca exceção.
    """
    ano_corte = date.today().year - ANOS_RECENTES

    m = re.search(r'class="nome"[^>]*>([^<]+)', html)
    nome = m.group(1).strip() if m else ""

    m = re.search(r"lattes\.cnpq\.br/(\d{16})", html)
    id_lattes = m.group(1) if m else ""
    if not id_lattes:  # fallback: ID K da URL de origem salva pelo navegador
        m = re.search(r"visualizacv\.do\?id=(K\w+)", html)
        id_lattes = m.group(1) if m else ""

    m = re.search(r"ltima atualiza[^0-9]*(\d{2}/\d{2}/\d{4})", html)
    atualizado = m.group(1) if m else ""

    # Maior titulação: procura na seção de formação, da mais alta para a mais baixa.
    formacao = _texto(_secao(html, "FormacaoAcademicaTitulacao"))
    maior_titulacao, curso = "", ""
    for rotulo in ["Pós-Doutorado", "Doutorado", "Mestrado", "Especialização", "Graduação"]:
        m = re.search(rf"{rotulo}\s+em\s+([^.]+)\.", formacao, re.IGNORECASE)
        if m:
            maior_titulacao = rotulo
            curso = m.group(1).strip()
            break

    # Projetos: períodos "AAAA - AAAA" ou "AAAA - Atual"; título = texto entre
    # o período e "Descrição:".
    proj_html = _secao(html, "ProjetosPesquisa") + _secao(html, "ProjetosDesenvolvimento")
    proj_texto = _texto(proj_html)
    projetos = re.findall(
        r"(\d{4})\s*-\s*(\d{4}|Atual)\s+(.{5,120}?)(?:\s+Descri|\s+\d{4}\s*-|$)",
        proj_texto,
    )
    projetos_recentes = [
        titulo.strip()
        for inicio, fim, titulo in projetos
        if fim == "Atual" or _ano(inicio) >= ano_corte
    ]

    # Artigos: um item numerado por artigo; ano = maior ano citado no item.
    # ponytail: heurística — o ano de publicação costuma ser o último do item,
    # mas anos de volume/citação podem inflar; bom o bastante para triagem.
    art_html = _secao(html, "ArtigosCompletos")
    itens_artigo = re.split(r"<b>\d+\.\s*</b>", art_html)[1:]
    anos_artigo = []
    for item in itens_artigo:
        anos = [_ano(a) for a in re.findall(r"\b((?:19|20)\d{2})\b", _texto(item))]
        anos_artigo.append(max(anos) if anos else 0)

    resumo = ""
    # O texto do resumo vem logo depois de class="resumo" (com ou sem <p>).
    m = re.search(r'class="resumo"[^>]*>(.*?)</(?:p|div|span)>', html, re.DOTALL)
    if m:
        resumo = _texto(m.group(1)).strip()

    return {
        "arquivo": nome_arquivo,
        "id_lattes": id_lattes,
        "nome": nome,
        "atualizado_em": atualizado,
        "maior_titulacao": maior_titulacao,
        "curso_titulacao": curso,
        "areas_atuacao": "",  # sem âncora estável no HTML público
        "n_projetos_pesquisa": len(projetos),
        "projetos_recentes": "; ".join(projetos_recentes),
        "n_artigos_total": len(itens_artigo),
        "n_artigos_recentes": sum(1 for a in anos_artigo if a >= ano_corte),
        "n_trabalhos_eventos": _conta_itens(_secao(html, "TrabalhosPublicadosAnaisCongresso")),
        "n_patentes": _conta_itens(_secao(html, "PatentesRegistros")),
        "n_softwares": "",  # sem seção própria no HTML público
        "n_orientacoes_mestrado": "",  # HTML não separa orientações por nível
        "n_orientacoes_doutorado": "",
        "n_outras_orientacoes": _conta_itens(_secao(html, "Orientacoes")),
        "palavras_chave": "",  # só existe no XML
        "resumo_cv": resumo[:500],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pasta", nargs="?", help="Pasta com os .zip/.xml do Lattes")
    parser.add_argument("--saida", default=f"lattes_consolidado_{date.today()}.csv")
    parser.add_argument("--selfcheck", action="store_true", help="Roda o autoteste e sai")
    args = parser.parse_args()

    if args.selfcheck:
        selfcheck()
        return

    if not args.pasta:
        parser.error("informe a pasta com os arquivos do Lattes (ou use --selfcheck)")

    pasta = Path(args.pasta)
    arquivos = sorted(
        p for p in pasta.iterdir()
        if p.suffix.lower() in (".zip", ".xml", ".html", ".htm")
    )
    if not arquivos:
        sys.exit(f"Nenhum .zip, .xml ou .html encontrado em {pasta}")

    linhas, falhas = [], []
    for arq in arquivos:
        try:
            if arq.suffix.lower() in (".html", ".htm"):
                linhas.append(extrair_indicadores_html(carregar_html(arq), arq.name))
            else:
                linhas.append(extrair_indicadores(carregar_xml(arq), arq.name))
        except Exception as exc:  # currículo corrompido não pode abortar o lote
            falhas.append((arq.name, str(exc)))

    with open(args.saida, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUNAS)
        writer.writeheader()
        writer.writerows(linhas)

    print(f"OK: {len(linhas)} currículo(s) consolidado(s) em {args.saida}")
    if falhas:
        print(f"FALHAS ({len(falhas)}):")
        for nome, erro in falhas:
            print(f"  - {nome}: {erro}")


def selfcheck():
    """Autoteste mínimo com um currículo sintético — falha se a extração quebrar."""
    xml = """<?xml version="1.0" encoding="ISO-8859-1"?>
<CURRICULO-VITAE NUMERO-IDENTIFICADOR="1234567890123456" DATA-ATUALIZACAO="01012026">
  <DADOS-GERAIS NOME-COMPLETO="Maria Teste">
    <RESUMO-CV TEXTO-RESUMO-CV-RH="Doutora em energia."/>
    <FORMACAO-ACADEMICA-TITULACAO>
      <MESTRADO NOME-CURSO="Quimica" STATUS-DO-CURSO="CONCLUIDO"/>
      <DOUTORADO NOME-CURSO="Energia" STATUS-DO-CURSO="CONCLUIDO"/>
    </FORMACAO-ACADEMICA-TITULACAO>
    <AREAS-DE-ATUACAO>
      <AREA-DE-ATUACAO NOME-DA-AREA-DO-CONHECIMENTO="Engenharia de Energia"/>
    </AREAS-DE-ATUACAO>
    <ATUACOES-PROFISSIONAIS>
      <ATUACAO-PROFISSIONAL>
        <ATIVIDADES-DE-PARTICIPACAO-EM-PROJETO>
          <PARTICIPACAO-EM-PROJETO>
            <PROJETO-DE-PESQUISA NOME-DO-PROJETO="Solar X" ANO-INICIO="2025" ANO-FIM=""/>
          </PARTICIPACAO-EM-PROJETO>
        </ATIVIDADES-DE-PARTICIPACAO-EM-PROJETO>
      </ATUACAO-PROFISSIONAL>
    </ATUACOES-PROFISSIONAIS>
  </DADOS-GERAIS>
  <PRODUCAO-BIBLIOGRAFICA>
    <ARTIGOS-PUBLICADOS>
      <ARTIGO-PUBLICADO>
        <DADOS-BASICOS-DO-ARTIGO ANO-DO-ARTIGO="2025" TITULO-DO-ARTIGO="Artigo novo"/>
        <PALAVRAS-CHAVE PALAVRA-CHAVE-1="energia solar" PALAVRA-CHAVE-2="IA"/>
      </ARTIGO-PUBLICADO>
      <ARTIGO-PUBLICADO>
        <DADOS-BASICOS-DO-ARTIGO ANO-DO-ARTIGO="2010" TITULO-DO-ARTIGO="Artigo velho"/>
      </ARTIGO-PUBLICADO>
    </ARTIGOS-PUBLICADOS>
  </PRODUCAO-BIBLIOGRAFICA>
</CURRICULO-VITAE>"""
    root = ET.fromstring(xml)
    d = extrair_indicadores(root, "teste.xml")
    assert d["id_lattes"] == "1234567890123456", d
    assert d["nome"] == "Maria Teste", d
    assert d["maior_titulacao"] == "Doutorado", d
    assert d["curso_titulacao"] == "Energia", d
    assert d["n_artigos_total"] == 2 and d["n_artigos_recentes"] == 1, d
    assert d["n_projetos_pesquisa"] == 1 and "Solar X" in d["projetos_recentes"], d
    assert "energia solar" in d["palavras_chave"], d
    assert d["areas_atuacao"] == "Engenharia de Energia", d
    # Currículo vazio não pode quebrar.
    vazio = extrair_indicadores(ET.fromstring("<CURRICULO-VITAE/>"), "vazio.xml")
    assert vazio["nome"] == "" and vazio["n_artigos_total"] == 0, vazio

    # --- caso HTML (visualizacv salvo do navegador) ---
    html = """<!-- saved from url=(0060)https://buscatextual.cnpq.br/buscatextual/visualizacv.do?id=K123 -->
    <h2 class="nome">Joao HTML Teste</h2>
    <span>Endereço para acessar este CV: http://lattes.cnpq.br/1234567890123456</span>
    <span>Última atualização do currículo em 01/06/2026</span>
    <a name="FormacaoAcademicaTitulacao"></a>
    2018 - 2022 Doutorado em Fisico-Quimica. Universidade X.
    <a name="ProjetosDesenvolvimento"></a>
    2025 - Atual Projeto Hidrogenio Verde Descrição: piloto industrial.
    2010 - 2012 Projeto Antigo Descrição: encerrado.
    <a name="ArtigosCompletos"></a>
    <b>1. </b>FULANO. Artigo recente. Revista Y, 2026.
    <b>2. </b>FULANO. Artigo antigo. Revista Z, 2009.
    <a name="Bancas"></a>
    <a name="Eventos"></a>"""
    h = extrair_indicadores_html(html, "teste.html")
    assert h["nome"] == "Joao HTML Teste", h
    assert h["id_lattes"] == "1234567890123456", h
    assert h["atualizado_em"] == "01/06/2026", h
    assert h["maior_titulacao"] == "Doutorado" and "Fisico-Quimica" in h["curso_titulacao"], h
    assert h["n_projetos_pesquisa"] == 2, h
    assert "Hidrogenio Verde" in h["projetos_recentes"] and "Antigo" not in h["projetos_recentes"], h
    assert h["n_artigos_total"] == 2 and h["n_artigos_recentes"] == 1, h
    # HTML vazio não pode quebrar.
    hv = extrair_indicadores_html("<html></html>", "vazio.html")
    assert hv["nome"] == "" and hv["n_artigos_total"] == 0, hv
    print("selfcheck OK")


if __name__ == "__main__":
    main()
