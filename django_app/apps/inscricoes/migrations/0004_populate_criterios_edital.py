# apps/inscricoes/migrations/0004_populate_criterios_edital.py
# Banco de Talentos — Polo de Inovação IFG
# Data migration: popula CriterioEdital a partir de QUADROS_INSCRICAO.

from django.db import migrations

# Mapeamento: chave do quadros.py → (modalidade, tipo_servidor)
_KEY_MAP = {
    "servidor": ("servidor", ""),
    "servidor_apoio_tecnico": ("servidor", "apoio_tecnico"),
    "estudante": ("estudante", ""),
    "colaborador_externo": ("colaborador_externo", ""),
}


def _populate(apps, schema_editor):
    from apps.inscricoes.quadros import QUADROS_INSCRICAO

    CriterioEdital = apps.get_model("inscricoes", "CriterioEdital")

    for quadro_key, itens in QUADROS_INSCRICAO.items():
        if quadro_key not in _KEY_MAP:
            continue
        modalidade, tipo_servidor = _KEY_MAP[quadro_key]
        for ordem, item in enumerate(itens, start=1):
            CriterioEdital.objects.get_or_create(
                modalidade=modalidade,
                tipo_servidor=tipo_servidor,
                item_id=item["id"],
                defaults={
                    "ordem": ordem,
                    "criterio": item["criterio"],
                    "regra": item["regra"],
                    "maximo": item["maximo"],
                    "ativo": True,
                },
            )


def _depopulate(apps, schema_editor):
    CriterioEdital = apps.get_model("inscricoes", "CriterioEdital")
    CriterioEdital.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("inscricoes", "0003_historicalinscricao_parecer_geral_and_more"),
    ]

    operations = [
        migrations.RunPython(_populate, reverse_code=_depopulate),
    ]
