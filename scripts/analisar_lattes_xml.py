# scripts/analisar_lattes_xml.py
# Banco de Talentos — Polo de Inovação IFG
# Consolida os currículos Lattes baixados manualmente (arquivos .zip ou .xml
# na pasta indicada) numa planilha CSV comparável — um candidato por linha —
# para apoiar a montagem de shortlists de indicação de especialistas.
#
# Roda FORA do Django, direto no Windows, só com a biblioteca padrão:
#   python scripts/analisar_lattes_xml.py <pasta_com_zips_ou_xmls> [--saida arquivo.csv]
#   python scripts/analisar_lattes_xml.py --selfcheck
#
# O CSV sai em UTF-8 com BOM (abre certo no Excel). O "join" com a planilha
# do comando exportar_inscritos_lattes é feito pela coluna id_lattes: o zip
# baixado do CNPq é nomeado com o ID de 16 dígitos, o mesmo que aparece no
# fim da URL do Lattes (http://lattes.cnpq.br/<id>).
#
# Apenas leitura de arquivos locais. Não acessa rede nem altera nada.

import argparse
import csv
import io
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
        p for p in pasta.iterdir() if p.suffix.lower() in (".zip", ".xml")
    )
    if not arquivos:
        sys.exit(f"Nenhum .zip ou .xml encontrado em {pasta}")

    linhas, falhas = [], []
    for arq in arquivos:
        try:
            root = carregar_xml(arq)
            linhas.append(extrair_indicadores(root, arq.name))
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
    print("selfcheck OK")


if __name__ == "__main__":
    main()
