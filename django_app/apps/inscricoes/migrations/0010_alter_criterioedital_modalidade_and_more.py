# apps/inscricoes/migrations/0010_alter_criterioedital_modalidade_and_more.py
# Banco de Talentos — Polo de Inovação IFG
#
# Sincroniza o estado das migrations com os models. NÃO altera nada no banco.
#
# Contexto: o `migrate` na VM vinha avisando que havia mudanças de model sem
# migration ("model drift"). Rodando `makemigrations --check --dry-run` no dev,
# o que aparece são apenas alterações de `choices` em `modalidade` e
# `tipo_servidor` — sobras das revisões de quadros (migrations 0006 a 0009).
#
# `choices` é validação do Django, no nível da aplicação: não vira constraint
# nem altera a coluna no PostgreSQL. Por isso esta migration é inofensiva em
# produção. Ela precisa existir mesmo assim, porque enquanto o estado das
# migrations não bate com os models, TODA migration nova nasce sobre um estado
# inconsistente — e o aviso continua aparecendo a cada deploy.
#
# Gerada no dev, commitada e aplicada na VM com `git pull` + `migrate`.
# NUNCA rodar `makemigrations` em produção.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inscricoes', '0009_aposenta_criterios_servidor_apoio_tecnico'),
    ]

    operations = [
        migrations.AlterField(
            model_name='criterioedital',
            name='modalidade',
            field=models.CharField(choices=[('estudante', 'Estudante'), ('servidor', 'Servidor(a)'), ('colaborador_externo', 'Colaborador(a) Externo(a)')], max_length=30, verbose_name='modalidade'),
        ),
        migrations.AlterField(
            model_name='criterioedital',
            name='tipo_servidor',
            field=models.CharField(blank=True, choices=[('pesquisador', 'Pesquisador(a)'), ('apoio_tecnico', 'Apoio técnico')], max_length=30, verbose_name='tipo de servidor'),
        ),
        migrations.AlterField(
            model_name='historicalinscricao',
            name='modalidade',
            field=models.CharField(choices=[('estudante', 'Estudante'), ('servidor', 'Servidor(a)'), ('colaborador_externo', 'Colaborador(a) Externo(a)')], max_length=30, verbose_name='modalidade'),
        ),
        migrations.AlterField(
            model_name='historicalinscricao',
            name='tipo_servidor',
            field=models.CharField(blank=True, choices=[('pesquisador', 'Pesquisador(a)'), ('apoio_tecnico', 'Apoio técnico')], max_length=30, verbose_name='tipo de servidor'),
        ),
        migrations.AlterField(
            model_name='inscricao',
            name='modalidade',
            field=models.CharField(choices=[('estudante', 'Estudante'), ('servidor', 'Servidor(a)'), ('colaborador_externo', 'Colaborador(a) Externo(a)')], max_length=30, verbose_name='modalidade'),
        ),
        migrations.AlterField(
            model_name='inscricao',
            name='tipo_servidor',
            field=models.CharField(blank=True, choices=[('pesquisador', 'Pesquisador(a)'), ('apoio_tecnico', 'Apoio técnico')], max_length=30, verbose_name='tipo de servidor'),
        ),
    ]
