# apps/inscricoes/migrations/0009_aposenta_criterios_servidor_apoio_tecnico.py
# Aposenta (ativo=False) os critérios antigos do Servidor / Apoio Técnico.
#
# Contexto: o Servidor tipo Apoio Técnico passou a usar o mesmo quadro do
# Pesquisador. Os critérios próprios antigos (Formação Acadêmica etc. +
# o IFGProduz criado na migration 0007 para servidor/apoio_tecnico) ficaram
# sem uso, mas continuavam ativos e apareciam no admin.
#
# NÃO apagamos as linhas porque inscrições já avaliadas as referenciam
# (FK PROTECT) — apenas desativamos. ALVO CIRÚRGICO: somente
# modalidade="servidor" E tipo_servidor="apoio_tecnico". O Colaborador
# Externo / Apoio Técnico (Quadro II) NÃO é afetado. Operação reversível.

from django.db import migrations

ALVO = {"modalidade": "servidor", "tipo_servidor": "apoio_tecnico"}


def desativar(apps, schema_editor):
    CriterioEdital = apps.get_model("inscricoes", "CriterioEdital")
    CriterioEdital.objects.filter(**ALVO).update(ativo=False)


def reativar(apps, schema_editor):
    CriterioEdital = apps.get_model("inscricoes", "CriterioEdital")
    CriterioEdital.objects.filter(**ALVO).update(ativo=True)


class Migration(migrations.Migration):

    dependencies = [
        ("inscricoes", "0008_desativa_item_colab_ext_fora_edital"),
    ]

    operations = [
        migrations.RunPython(desativar, reativar),
    ]
