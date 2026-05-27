# apps/inscricoes/migrations/0005_criterioedital_is_api_ifgproduz.py
# Adiciona campo is_api em CriterioEdital, desativa critérios substituídos pelo IFGProduz
# e insere o critério unificado de Produção Acadêmica.

from django.db import migrations, models


IDS_SUBSTITUIDOS_SERVIDOR = [
    "titulacao",
    "coordenacao_fomento_publico",
    "participacao_orientacao_projetos",
    "patente_depositada",
    "registro_software",
    "artigos_cientificos",
    "capacitacoes_polo",
]


def adicionar_criterio_ifgproduz(apps, schema_editor):
    CriterioEdital = apps.get_model("inscricoes", "CriterioEdital")

    CriterioEdital.objects.filter(
        modalidade="servidor",
        tipo_servidor="",
        item_id__in=IDS_SUBSTITUIDOS_SERVIDOR,
    ).update(ativo=False)

    if not CriterioEdital.objects.filter(modalidade="servidor", item_id="ifgproduz").exists():
        CriterioEdital.objects.create(
            modalidade="servidor",
            tipo_servidor="",
            item_id="ifgproduz",
            ordem=1,
            criterio="Produção Acadêmica (IFGProduz)",
            regra="Pontuação calculada automaticamente a partir do Lattes via IFGProduz.",
            maximo=100,
            is_api=True,
            ativo=True,
        )

def reverter_criterio_ifgproduz(apps, schema_editor):
    CriterioEdital = apps.get_model("inscricoes", "CriterioEdital")
    CriterioEdital.objects.filter(modalidade="servidor", item_id="ifgproduz").delete()
    CriterioEdital.objects.filter(
        modalidade="servidor",
        tipo_servidor="",
        item_id__in=IDS_SUBSTITUIDOS_SERVIDOR,
    ).update(ativo=True)


class Migration(migrations.Migration):

    dependencies = [
        ("inscricoes", "0004_populate_criterios_edital"),
    ]

    operations = [
        migrations.AddField(
            model_name="criterioedital",
            name="is_api",
            field=models.BooleanField(default=False, verbose_name="preenchido via API"),
        ),
        migrations.RunPython(adicionar_criterio_ifgproduz, reverter_criterio_ifgproduz),
    ]
