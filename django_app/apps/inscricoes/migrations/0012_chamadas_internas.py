# apps/inscricoes/migrations/0012_chamadas_internas.py
# Banco de Talentos — Polo de Inovação IFG
#
# Passo 1 de 3 da mudança para inscrição POR CHAMADA INTERNA
# (proposta de Retificação nº 4/2026 ao Edital PROPPG 29/2026, itens 5.1 a 5.16).
#
# Esta migration é APENAS ADITIVA e pode ser aplicada sozinha sem quebrar nada:
#   - cria ChamadaInterna, Vaga e OpcaoCriterio;
#   - acrescenta `chamada` (ainda aceitando nulo) em CriterioEdital e Inscricao;
#   - acrescenta as declarações do item 5.6 e a quantidade declarada do item;
#   - troca Inscricao.usuario de OneToOne para ForeignKey, porque agora existe
#     uma inscrição por candidato POR CHAMADA, e não uma para sempre.
#
# A 0013 preenche os dados e a 0014 fecha as constraints. São três arquivos
# porque, no SQLite do dev, misturar RunPython com AlterField no mesmo arquivo
# provoca erro de "no such column", e porque assim dá para parar no meio do
# ensaio e conferir os dados antes de travar as constraints.
#
# ATENÇÃO: entre a 0012 e a 0014 não existe índice de unicidade por usuário —
# o OneToOne foi derrubado e a constraint (usuario, chamada) ainda não existe.
# Rodar as três no MESMO `migrate`, com o serviço parado.

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inscricoes', '0011_corrige_is_api_ifgproduz'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ChamadaInterna',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('numero', models.PositiveSmallIntegerField(verbose_name='número')),
                ('ano', models.PositiveSmallIntegerField(verbose_name='ano')),
                ('titulo', models.CharField(max_length=200, verbose_name='título')),
                ('projeto', models.CharField(blank=True, max_length=200, verbose_name='projeto')),
                ('edital', models.CharField(blank=True, help_text='Apenas para exibição. Ex.: "Edital PROPPG nº 29/2026".', max_length=60, verbose_name='edital de origem')),
                ('aviso_url', models.URLField(blank=True, verbose_name='link do aviso publicado')),
                ('texto', models.TextField(blank=True, help_text='Aparece na página da chamada, acima das vagas.', verbose_name='objeto / resumo')),
                ('abertura', models.DateTimeField(verbose_name='abertura das inscrições')),
                ('encerramento', models.DateTimeField(verbose_name='encerramento das inscrições')),
                ('publicada', models.BooleanField(default=False, help_text='Enquanto desmarcada, a chamada fica invisível para os candidatos.', verbose_name='publicada')),
                ('legado', models.BooleanField(default=False, help_text='Marca as três chamadas sintéticas que guardam as inscrições do credenciamento antigo. Elas existem só para o histórico não ficar solto; nunca recebem inscrição nova.', verbose_name='chamada de legado')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'chamada interna',
                'verbose_name_plural': 'chamadas internas',
                'ordering': ['-ano', '-numero'],
            },
        ),
        migrations.CreateModel(
            name='OpcaoCriterio',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rotulo', models.CharField(max_length=200, verbose_name='opção')),
                ('pontos', models.DecimalField(decimal_places=2, max_digits=8, verbose_name='pontos')),
                ('ordem', models.PositiveSmallIntegerField(default=0, verbose_name='ordem')),
            ],
            options={
                'verbose_name': 'opção do critério',
                'verbose_name_plural': 'opções do critério',
                'ordering': ['ordem', '-pontos'],
            },
        ),
        migrations.CreateModel(
            name='Vaga',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo', models.CharField(help_text='Ex.: "Pq 12", "AT3", "ES-IT".', max_length=20, verbose_name='código')),
                ('funcao', models.CharField(max_length=200, verbose_name='função')),
                ('perfil', models.TextField(blank=True, verbose_name='perfil e competências esperadas')),
                ('quantidade', models.PositiveSmallIntegerField(default=1, verbose_name='vagas')),
                ('bolsa', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='valor da bolsa (R$/mês)')),
                ('carga_horaria', models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='carga horária semanal (h)')),
                ('modalidade', models.CharField(choices=[('estudante', 'Estudante'), ('servidor', 'Servidor(a)'), ('colaborador_externo', 'Colaborador(a) Externo(a)')], max_length=30, verbose_name='modalidade')),
                ('tipo_servidor', models.CharField(blank=True, choices=[('pesquisador', 'Pesquisador(a)'), ('apoio_tecnico', 'Apoio técnico')], max_length=30, verbose_name='categoria')),
                ('ordem', models.PositiveSmallIntegerField(default=0, verbose_name='ordem')),
            ],
            options={
                'verbose_name': 'vaga',
                'verbose_name_plural': 'vagas',
                'ordering': ['ordem', 'codigo'],
            },
        ),
        migrations.AlterModelOptions(
            name='criterioedital',
            options={'ordering': ['chamada', 'modalidade', 'tipo_servidor', 'ordem'], 'verbose_name': 'critério do edital', 'verbose_name_plural': 'critérios do edital'},
        ),
        migrations.RemoveConstraint(
            model_name='criterioedital',
            name='uniq_criterio_por_modalidade_tipo_item',
        ),
        migrations.AddField(
            model_name='criterioedital',
            name='pontos_por_unidade',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Só para critérios de quantidade. Ex.: 40 pontos por projeto.', max_digits=8, null=True, verbose_name='pontos por unidade'),
        ),
        migrations.AddField(
            model_name='criterioedital',
            name='tipo',
            field=models.CharField(choices=[('contagem', 'Quantidade (pontos por unidade)'), ('escolha', 'Escolha única (cada opção vale uma pontuação)')], default='contagem', max_length=20, verbose_name='como o candidato responde'),
        ),
        migrations.AddField(
            model_name='criterioedital',
            name='unidade_rotulo',
            field=models.CharField(blank=True, help_text='Vira a pergunta do formulário. Ex.: "projetos" → "Quantos projetos?".', max_length=60, verbose_name='o que é contado'),
        ),
        migrations.AddField(
            model_name='historicalinscricao',
            name='declara_disponibilidade',
            field=models.BooleanField(default=False, verbose_name='declara disponibilidade para a carga horária da vaga'),
        ),
        migrations.AddField(
            model_name='historicalinscricao',
            name='declara_nao_redistribuicao',
            field=models.BooleanField(default=False, verbose_name='declara não estar em processo de redistribuição'),
        ),
        migrations.AddField(
            model_name='historicalinscricao',
            name='licencas_maternidade',
            field=models.PositiveSmallIntegerField(default=0, verbose_name='licenças à gestante/adotante no período'),
        ),
        migrations.AddField(
            model_name='historicalinscricaoitem',
            name='quantidade',
            field=models.PositiveIntegerField(default=0, verbose_name='quantidade declarada'),
        ),
        migrations.AddField(
            model_name='inscricao',
            name='declara_disponibilidade',
            field=models.BooleanField(default=False, verbose_name='declara disponibilidade para a carga horária da vaga'),
        ),
        migrations.AddField(
            model_name='inscricao',
            name='declara_nao_redistribuicao',
            field=models.BooleanField(default=False, verbose_name='declara não estar em processo de redistribuição'),
        ),
        migrations.AddField(
            model_name='inscricao',
            name='licencas_maternidade',
            field=models.PositiveSmallIntegerField(default=0, verbose_name='licenças à gestante/adotante no período'),
        ),
        migrations.AddField(
            model_name='inscricaoitem',
            name='quantidade',
            field=models.PositiveIntegerField(default=0, verbose_name='quantidade declarada'),
        ),
        migrations.AlterField(
            model_name='historicalinscricaoitem',
            name='pontuacao',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=8, validators=[django.core.validators.MinValueValidator(0)], verbose_name='pontuação calculada'),
        ),
        migrations.AlterField(
            model_name='inscricao',
            name='usuario',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='inscricoes', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='inscricaoitem',
            name='pontuacao',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=8, validators=[django.core.validators.MinValueValidator(0)], verbose_name='pontuação calculada'),
        ),
        migrations.AddConstraint(
            model_name='chamadainterna',
            constraint=models.UniqueConstraint(fields=('numero', 'ano'), name='uniq_chamada_numero_ano'),
        ),
        migrations.AddField(
            model_name='criterioedital',
            name='chamada',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='criterios', to='inscricoes.chamadainterna'),
        ),
        migrations.AddField(
            model_name='historicalinscricao',
            name='chamada',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='inscricoes.chamadainterna'),
        ),
        migrations.AddField(
            model_name='inscricao',
            name='chamada',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='inscricoes', to='inscricoes.chamadainterna'),
        ),
        migrations.AddConstraint(
            model_name='criterioedital',
            constraint=models.UniqueConstraint(fields=('chamada', 'modalidade', 'tipo_servidor', 'item_id'), name='uniq_criterio_por_chamada_modalidade_tipo_item'),
        ),
        migrations.AddField(
            model_name='opcaocriterio',
            name='criterio',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='opcoes', to='inscricoes.criterioedital'),
        ),
        migrations.AddField(
            model_name='historicalinscricaoitem',
            name='opcao',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='inscricoes.opcaocriterio', verbose_name='opção escolhida'),
        ),
        migrations.AddField(
            model_name='inscricaoitem',
            name='opcao',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='itens_inscricao', to='inscricoes.opcaocriterio', verbose_name='opção escolhida'),
        ),
        migrations.AddField(
            model_name='vaga',
            name='chamada',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='vagas', to='inscricoes.chamadainterna'),
        ),
        migrations.AddField(
            model_name='historicalinscricao',
            name='vaga',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='inscricoes.vaga', verbose_name='vaga pretendida'),
        ),
        migrations.AddField(
            model_name='inscricao',
            name='vaga',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='inscricoes', to='inscricoes.vaga', verbose_name='vaga pretendida'),
        ),
        migrations.AddConstraint(
            model_name='inscricao',
            constraint=models.UniqueConstraint(fields=('usuario', 'chamada'), name='uniq_inscricao_por_usuario_chamada'),
        ),
        migrations.AddConstraint(
            model_name='vaga',
            constraint=models.UniqueConstraint(fields=('chamada', 'codigo'), name='uniq_vaga_por_chamada_codigo'),
        ),
    ]
