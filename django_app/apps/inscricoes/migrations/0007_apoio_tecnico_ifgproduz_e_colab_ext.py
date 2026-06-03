# apps/inscricoes/migrations/0007_apoio_tecnico_ifgproduz_e_colab_ext.py
# Adiciona:
# - Critério IFGProduz para servidor/apoio_tecnico (ambas as categorias usam a fórmula)
# - Critérios do Quadro II para colaborador_externo/apoio_tecnico

from django.db import migrations


IFGPRODUZ_APOIO = {
    "item_id": "ifgproduz",
    "ordem": 0,
    "criterio": "Produção Acadêmica (IFGProduz)",
    "regra": "Pontuação calculada automaticamente a partir do Lattes via IFGProduz.",
    "maximo": 100.0,
    "is_api": True,
}

COLAB_EXT_APOIO_TECNICO = [
    {
        "item_id": "formacao_academica",
        "ordem": 1,
        "criterio": "Formação acadêmica",
        "regra": "Médio completo: 10 pts / Graduando: 15 pts / Graduado: 25 pts / Especialista: 35 pts / Mestre: 50 pts / Doutor: 70 pts",
        "maximo": 70.0,
    },
    {
        "item_id": "experiencia_profissional_area",
        "ordem": 2,
        "criterio": "Experiência profissional na área de formação/atuação",
        "regra": "0,3 ponto por mês",
        "maximo": 120.0,
    },
    {
        "item_id": "gestao_projetos_pdi_ict",
        "ordem": 3,
        "criterio": "Experiência em gestão de projetos de PD&I e/ou ET no Polo de Inovação do IFG ou de outra ICT",
        "regra": "1,5 ponto por projeto, por mês",
        "maximo": 180.0,
    },
    {
        "item_id": "gestao_projetos_externos",
        "ordem": 4,
        "criterio": "Experiência em gestão de projetos externos: empresas, agências de fomento, editais públicos",
        "regra": "1,0 ponto por projeto, por mês",
        "maximo": 120.0,
    },
    {
        "item_id": "comunicacao_cientifica",
        "ordem": 5,
        "criterio": "Experiência em comunicação científica, divulgação e popularização da ciência",
        "regra": "0,5 ponto por mês",
        "maximo": 60.0,
    },
    {
        "item_id": "analise_dados_relatorios",
        "ordem": 6,
        "criterio": "Experiência comprovada em análise de dados, produção de relatórios técnicos ou gestão de informações em projetos",
        "regra": "0,5 ponto por mês",
        "maximo": 60.0,
    },
    {
        "item_id": "capacitacoes_polo",
        "ordem": 7,
        "criterio": "Participação concluída em capacitações promovidas pelo Polo de Inovação do IFG",
        "regra": "0,3 ponto por participação",
        "maximo": 9.0,
    },
    {
        "item_id": "producao_tecnica",
        "ordem": 8,
        "criterio": "Produção técnica relevante: artigo, relatório técnico publicado, produto de comunicação científica documentado",
        "regra": "1 ponto por produção",
        "maximo": 10.0,
    },
]


def adicionar_criterios(apps, schema_editor):
    CriterioEdital = apps.get_model("inscricoes", "CriterioEdital")

    # IFGProduz para servidor/apoio_tecnico
    CriterioEdital.objects.get_or_create(
        modalidade="servidor",
        tipo_servidor="apoio_tecnico",
        item_id=IFGPRODUZ_APOIO["item_id"],
        defaults={
            "ordem": IFGPRODUZ_APOIO["ordem"],
            "criterio": IFGPRODUZ_APOIO["criterio"],
            "regra": IFGPRODUZ_APOIO["regra"],
            "maximo": IFGPRODUZ_APOIO["maximo"],
            "is_api": IFGPRODUZ_APOIO["is_api"],
            "ativo": True,
        },
    )

    # Quadro II para colaborador_externo/apoio_tecnico
    for dados in COLAB_EXT_APOIO_TECNICO:
        CriterioEdital.objects.get_or_create(
            modalidade="colaborador_externo",
            tipo_servidor="apoio_tecnico",
            item_id=dados["item_id"],
            defaults={
                "ordem": dados["ordem"],
                "criterio": dados["criterio"],
                "regra": dados["regra"],
                "maximo": dados["maximo"],
                "is_api": False,
                "ativo": True,
            },
        )


def remover_criterios(apps, schema_editor):
    CriterioEdital = apps.get_model("inscricoes", "CriterioEdital")
    CriterioEdital.objects.filter(
        modalidade="servidor",
        tipo_servidor="apoio_tecnico",
        item_id="ifgproduz",
    ).delete()
    CriterioEdital.objects.filter(
        modalidade="colaborador_externo",
        tipo_servidor="apoio_tecnico",
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("inscricoes", "0006_servidor_criterios_quadro_i"),
    ]

    operations = [
        migrations.RunPython(adicionar_criterios, remover_criterios),
    ]
