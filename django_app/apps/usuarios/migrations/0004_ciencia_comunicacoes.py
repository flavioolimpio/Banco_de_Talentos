# apps/usuarios/migrations/0004_ciencia_comunicacoes.py
# Banco de Talentos — Polo de Inovação IFG
#
# `aceite_comunicacoes` vira `ciencia_comunicacoes`.
#
# A migration 0003 criou o campo como um CONSENTIMENTO opcional e revogável.
# Relendo o Bloco F de docs/Estrutura_Perfil_Cadastro_Banco_Especialistas.md,
# a linha pedida é "De que receberá e-mail com divulgação de vagas
# disponíveis", logo acima de "Ciência de que o credenciamento não garante
# direito a vaga" e no mesmo bloco de caixas de marcação: é uma CIÊNCIA, não
# um consentimento.
#
# A diferença importa na prática. Como consentimento opcional, o campo nascia
# desmarcado para todo mundo, e a lista de divulgação de uma chamada sairia
# vazia — o Polo deixaria de cumprir o item 5.2.2 do Edital, que manda avisar
# "a todos os servidores(as) cadastrados". Consentimento também não é a base
# legal adequada aqui: ser avisado de vagas é o próprio motivo de existir do
# cadastro, e quem não quiser mais receber pede descredenciamento do Banco
# (item 7.1), que é a saída que o Edital prevê.
#
# RenameField preserva os dados. Na prática não há o que preservar: o campo
# nasceu na 0003 e ninguém chegou a marcá-lo.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("usuarios", "0003_cadastro_spec"),
    ]

    operations = [
        migrations.RenameField(
            model_name="usuario",
            old_name="aceite_comunicacoes",
            new_name="ciencia_comunicacoes",
        ),
        migrations.RenameField(
            model_name="usuario",
            old_name="aceite_comunicacoes_em",
            new_name="ciencia_comunicacoes_em",
        ),
        migrations.AlterField(
            model_name="usuario",
            name="ciencia_comunicacoes",
            field=models.BooleanField(
                default=False,
                verbose_name="ciência de que receberá e-mail com a divulgação de vagas",
            ),
        ),
    ]
