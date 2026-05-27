# apps/inscricoes/migrations/0006_servidor_criterios_quadro_i.py
# Atualiza critérios do servidor (Pesquisador) conforme Quadro I revisado pela comissão.
# Desativa critérios antigos e insere os 8 novos critérios manuais.

from django.db import migrations


IDS_ANTIGOS_SERVIDOR = [
    "pos_doutoramento",
    "experiencia_fora_ict",
    "gestao_fora_ict",
    "coordenacao_empresas_fundacao",
    "projetos_pdi_polo",
    "projetos_pdi_fora_polo",
]

NOVOS_CRITERIOS = [
    {
        "item_id": "exp_profissional_fora_ict",
        "ordem": 2,
        "criterio": "Experiência profissional comprovada em sua área de formação/atuação fora da sua ICT",
        "regra": "0,3 ponto por semestre.",
        "maximo": 9.0,
    },
    {
        "item_id": "exp_gestao_inovacao_fora_ict",
        "ordem": 3,
        "criterio": "Experiência profissional comprovada em nível de gestão de inovação em sua área de formação/atuação fora da sua ICT",
        "regra": "0,4 ponto por semestre.",
        "maximo": 12.0,
    },
    {
        "item_id": "coord_projetos_empresas_fundacao",
        "ordem": 4,
        "criterio": "Experiência na coordenação de projetos com/em empresas privada/públicas e interveniência de fundação de apoio",
        "regra": "0,8 pontos por projeto, por semestre.",
        "maximo": 16.0,
    },
    {
        "item_id": "pdi_polo",
        "ordem": 5,
        "criterio": "Experiência em desenvolvimento e execução de projetos de PD&I com empresas privada/pública no âmbito do Polo de Inovação do IFG",
        "regra": "1 ponto por projeto, por semestre.",
        "maximo": 10.0,
    },
    {
        "item_id": "pdi_fora_polo",
        "ordem": 6,
        "criterio": "Experiência em desenvolvimento e execução de projetos de PD&I e/ou ET com empresas privadas/públicas fora do âmbito do Polo de Inovação",
        "regra": "0,6 ponto por projeto, por semestre.",
        "maximo": 12.0,
    },
    {
        "item_id": "coord_projetos_fomento_publico",
        "ordem": 7,
        "criterio": "Experiência na coordenação de projetos de pesquisa e inovação fomentados por agências públicas, por exemplo, CNPq, ou por meio de Editais internos de uma ICT",
        "regra": "0,8 pontos por projeto, por semestre.",
        "maximo": 16.0,
    },
    {
        "item_id": "orientacao_coord_participacao",
        "ordem": 8,
        "criterio": "Experiência na orientação/coordenação/participação de projetos de pesquisa e/ou inovação fomentados por agências públicas ou por meio de Editais internos de uma ICT",
        "regra": "0,4 ponto por projeto, por semestre.",
        "maximo": 16.0,
    },
]


def atualizar_criterios_servidor(apps, schema_editor):
    CriterioEdital = apps.get_model("inscricoes", "CriterioEdital")

    # Desativa critérios antigos
    CriterioEdital.objects.filter(
        modalidade="servidor",
        tipo_servidor="",
        item_id__in=IDS_ANTIGOS_SERVIDOR,
    ).update(ativo=False)

    # Cria os 7 novos critérios
    for dados in NOVOS_CRITERIOS:
        if not CriterioEdital.objects.filter(
            modalidade="servidor", tipo_servidor="", item_id=dados["item_id"]
        ).exists():
            CriterioEdital.objects.create(
                modalidade="servidor",
                tipo_servidor="",
                ativo=True,
                is_api=False,
                **dados,
            )

    # Reativa capacitacoes_polo (mesmo conteúdo, apenas estava desativado)
    CriterioEdital.objects.filter(
        modalidade="servidor", tipo_servidor="", item_id="capacitacoes_polo"
    ).update(ativo=True, ordem=9)


def reverter_criterios_servidor(apps, schema_editor):
    CriterioEdital = apps.get_model("inscricoes", "CriterioEdital")
    ids_novos = [c["item_id"] for c in NOVOS_CRITERIOS]
    CriterioEdital.objects.filter(
        modalidade="servidor", tipo_servidor="", item_id__in=ids_novos
    ).delete()
    CriterioEdital.objects.filter(
        modalidade="servidor", tipo_servidor="", item_id="capacitacoes_polo"
    ).update(ativo=False)
    CriterioEdital.objects.filter(
        modalidade="servidor", tipo_servidor="", item_id__in=IDS_ANTIGOS_SERVIDOR
    ).update(ativo=True)


class Migration(migrations.Migration):

    dependencies = [
        ("inscricoes", "0005_criterioedital_is_api_ifgproduz"),
    ]

    operations = [
        migrations.RunPython(atualizar_criterios_servidor, reverter_criterios_servidor),
    ]
