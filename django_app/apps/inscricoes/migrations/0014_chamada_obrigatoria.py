# apps/inscricoes/migrations/0014_chamada_obrigatoria.py
# Banco de Talentos — Polo de Inovação IFG
#
# Passo 3 de 3 da mudança para inscrição por chamada interna.
#
# Depois que a 0013 preencheu todas as linhas, `chamada` deixa de aceitar nulo
# em CriterioEdital e em Inscricao. A partir daqui o resto do sistema pode
# assumir que toda inscrição e todo critério pertencem a uma chamada — sem
# `if chamada is None` espalhado por views, exportações e templates.
#
# Escrita à mão de propósito: o `makemigrations` fica interativo ao tornar um
# campo anulável obrigatório (pede um default) e trava num terminal não
# interativo.
#
# HistoricalInscricao continua aceitando nulo. A tabela histórica registra
# fotografias de estados passados, inclusive de antes desta coluna existir;
# exigir valor lá quebraria a auditoria sem ganho nenhum.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("inscricoes", "0013_backfill_chamadas_legado"),
    ]

    operations = [
        migrations.AlterField(
            model_name="criterioedital",
            name="chamada",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="criterios",
                to="inscricoes.chamadainterna",
            ),
        ),
        migrations.AlterField(
            model_name="inscricao",
            name="chamada",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="inscricoes",
                to="inscricoes.chamadainterna",
            ),
        ),
    ]
