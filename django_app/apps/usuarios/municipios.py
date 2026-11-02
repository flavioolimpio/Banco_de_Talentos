# apps/usuarios/municipios.py
# Banco de Talentos — Polo de Inovação IFG
#
# Estados e municípios do Brasil, para os selects encadeados de Estado -> Cidade
# do formulário de cadastro (Bloco A da especificação de perfil).
#
# Os dados vivem em UM lugar só: `static/js/municipios.json`, um dicionário
# {"GO": ["Abadia de Goiás", ...], ...} com os 5.571 municípios do IBGE.
# O mesmo arquivo é lido:
#   - aqui, pelo Python, para montar as opções já no HTML (assim o formulário
#     funciona mesmo sem JavaScript);
#   - pelo navegador, via fetch em /static/js/municipios.json, para trocar a
#     lista de cidades quando o usuário muda o estado.
#
# Uma cópia só evita o clássico "o Python e o JS discordam sobre quais cidades
# existem". A CSP de produção é `default-src 'self'`, então o fetch de um
# arquivo servido pelo próprio site é permitido.
#
# Origem: API de localidades do IBGE
# (https://servicodados.ibge.gov.br/api/v1/localidades/municipios), baixada em
# 19/09/2026. Município novo é raro; quando acontecer, é só rebaixar o JSON.

import json
from functools import lru_cache
from pathlib import Path

from django.conf import settings

# Nome de cada estado, para o select não mostrar só a sigla.
UF_NOMES = {
    "AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas",
    "BA": "Bahia", "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo",
    "GO": "Goiás", "MA": "Maranhão", "MT": "Mato Grosso", "MS": "Mato Grosso do Sul",
    "MG": "Minas Gerais", "PA": "Pará", "PB": "Paraíba", "PR": "Paraná",
    "PE": "Pernambuco", "PI": "Piauí", "RJ": "Rio de Janeiro",
    "RN": "Rio Grande do Norte", "RS": "Rio Grande do Sul", "RO": "Rondônia",
    "RR": "Roraima", "SC": "Santa Catarina", "SP": "São Paulo",
    "SE": "Sergipe", "TO": "Tocantins",
}

# Goiás em primeiro por ser o estado da maioria dos candidatos; o resto em
# ordem alfabética de nome.
UF_CHOICES = [("GO", "Goiás (GO)")] + [
    (sigla, f"{nome} ({sigla})")
    for sigla, nome in sorted(UF_NOMES.items(), key=lambda par: par[1])
    if sigla != "GO"
]

_CAMINHO_JSON = Path(settings.BASE_DIR) / "static" / "js" / "municipios.json"


@lru_cache(maxsize=1)
def municipios_por_uf() -> dict[str, list[str]]:
    """{"GO": ["Abadia de Goiás", ...], ...} — lido do disco uma única vez."""
    return json.loads(_CAMINHO_JSON.read_text(encoding="utf-8"))


def municipios_de(uf: str) -> list[str]:
    """Municípios de um estado. UF vazia ou desconhecida devolve lista vazia."""
    if not uf:
        return []
    return municipios_por_uf().get(uf.strip().upper(), [])
