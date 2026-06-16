# apps/inscricoes/migrations/0008_desativa_item_colab_ext_fora_edital.py
# Desativa o critério de Colaborador Externo / Pesquisador que não existe no
# Edital PROPPG nº 30/2026 ("projetos de pesquisa/inovação/extensão durante o
# curso de formação"). Foi substituído pelo item 9 do edital
# (orientacao_participacao_fomento), agora em quadros.py.
#
# Não apagamos a linha porque há InscricaoItem referenciando-a (FK PROTECT) em
# inscrições já avaliadas — apenas marcamos ativo=False para que ela deixe de
# aparecer em NOVAS inscrições, preservando as antigas.

from django.db import migrations

ALVO = {
    "modalidade": "colaborador_externo",
    "tipo_servidor": "",
    "item_id": "projetos_pesquisa_inovacao_extensao_formacao",
}


def desativar(apps, schema_editor):
    CriterioEdital = apps.get_model("inscricoes", "CriterioEdital")
    CriterioEdital.objects.filter(**ALVO).update(ativo=False)


def reativar(apps, schema_editor):
    CriterioEdital = apps.get_model("inscricoes", "CriterioEdital")
    CriterioEdital.objects.filter(**ALVO).update(ativo=True)


class Migration(migrations.Migration):

    dependencies = [
        ("inscricoes", "0007_apoio_tecnico_ifgproduz_e_colab_ext"),
    ]

    operations = [
        migrations.RunPython(desativar, reativar),
    ]
