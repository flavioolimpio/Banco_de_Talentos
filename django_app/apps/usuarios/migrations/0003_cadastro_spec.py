# apps/usuarios/migrations/0003_cadastro_spec.py
# Banco de Talentos — Polo de Inovação IFG
#
# Cadastro enxuto, conforme os blocos A–G de
# docs/Estrutura_Perfil_Cadastro_Banco_Especialistas.md:
#
#   - cnpq_area: área do conhecimento (Tabela CNPq), lista fechada. É o filtro
#     principal para pré-selecionar candidatos por chamada.
#   - aceite_comunicacoes (+ _em): consentimento de receber e-mail sobre novas
#     vagas. É o que alimenta a lista de divulgação de cada chamada.
#   - migração de dados de nivel_formacao (texto livre) para maior_titulacao
#     (lista fechada), que já existia no model desde a migration 0002 mas havia
#     sido tirado do formulário.
#
# TUDO É ADITIVO: nenhum RemoveField, nenhuma coluna apagada. Os campos que
# saíram do formulário (nivel_formacao, data_nascimento, genero, instituicao,
# linkedin e o endereço completo) continuam no banco, com os dados intactos —
# tirar do formulário não é apagar dado.

from django.db import migrations, models


# Texto livre que os candidatos digitaram -> opção fechada de MaiorTitulacao.
# Comparação por "contém", em minúsculas e sem acento não é necessário porque
# as variantes reais observadas são estas. O que não casar fica em branco e é
# listado na saída do migrate, para conferência manual.
_EQUIVALENCIAS = [
    ("doutor", "doutorado"),
    ("phd", "doutorado"),
    ("ph.d", "doutorado"),
    ("mestr", "mestrado"),
    ("especializ", "especializacao"),
    ("pós-graduaç", "especializacao"),
    ("pos-graduac", "especializacao"),
    ("lato sensu", "especializacao"),
    ("gradua", "graduacao"),
    ("superior", "graduacao"),
    ("licenciatura", "graduacao"),
    ("bacharel", "graduacao"),
    ("técnico", "tecnico"),
    ("tecnico", "tecnico"),
    ("médio", "tecnico"),
    ("medio", "tecnico"),
]


def migrar_nivel_formacao(apps, schema_editor):
    Usuario = apps.get_model("usuarios", "Usuario")
    nao_convertidos = []
    for usuario in Usuario.objects.exclude(nivel_formacao="").filter(maior_titulacao=""):
        texto = (usuario.nivel_formacao or "").strip().lower()
        escolhido = ""
        for trecho, valor in _EQUIVALENCIAS:
            if trecho in texto:
                escolhido = valor
                break
        if escolhido:
            usuario.maior_titulacao = escolhido
            usuario.save(update_fields=["maior_titulacao"])
        else:
            nao_convertidos.append(usuario.nivel_formacao)

    if nao_convertidos:
        print(
            "\n  [0003_cadastro_spec] nivel_formacao sem equivalente em "
            f"MaiorTitulacao ({len(nao_convertidos)}): {sorted(set(nao_convertidos))}"
            "\n  Esses cadastros ficaram com a titulação em branco e o candidato "
            "será solicitado a preenchê-la (banner de perfil incompleto)."
        )


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0002_perfil_profissional'),
    ]

    operations = [
        migrations.AddField(
            model_name='usuario',
            name='aceite_comunicacoes',
            field=models.BooleanField(default=False, verbose_name='aceito receber e-mail com divulgação de vagas'),
        ),
        migrations.AddField(
            model_name='usuario',
            name='aceite_comunicacoes_em',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='usuario',
            name='cnpq_area',
            field=models.CharField(blank=True, choices=[('1. Ciências Exatas e da Terra', [('1.01', 'Matemática'), ('1.02', 'Probabilidade e Estatística'), ('1.03', 'Ciência da Computação'), ('1.04', 'Astronomia'), ('1.05', 'Física'), ('1.06', 'Química'), ('1.07', 'Geociências'), ('1.08', 'Oceanografia')]), ('2. Ciências Biológicas', [('2.01', 'Biologia Geral'), ('2.02', 'Genética'), ('2.03', 'Botânica'), ('2.04', 'Zoologia'), ('2.05', 'Ecologia'), ('2.06', 'Morfologia'), ('2.07', 'Fisiologia'), ('2.08', 'Bioquímica'), ('2.09', 'Biofísica'), ('2.10', 'Farmacologia'), ('2.11', 'Imunologia'), ('2.12', 'Microbiologia'), ('2.13', 'Parasitologia')]), ('3. Engenharias', [('3.01', 'Engenharia Civil'), ('3.02', 'Engenharia de Minas'), ('3.03', 'Engenharia de Materiais e Metalúrgica'), ('3.04', 'Engenharia Elétrica'), ('3.05', 'Engenharia Mecânica'), ('3.06', 'Engenharia Química'), ('3.07', 'Engenharia Sanitária'), ('3.08', 'Engenharia de Produção'), ('3.09', 'Engenharia Nuclear'), ('3.10', 'Engenharia de Transportes'), ('3.11', 'Engenharia Naval e Oceânica'), ('3.12', 'Engenharia Aeroespacial'), ('3.13', 'Engenharia Biomédica')]), ('4. Ciências da Saúde', [('4.01', 'Medicina'), ('4.02', 'Odontologia'), ('4.03', 'Farmácia'), ('4.04', 'Enfermagem'), ('4.05', 'Nutrição'), ('4.06', 'Saúde Coletiva'), ('4.07', 'Fonoaudiologia'), ('4.08', 'Fisioterapia e Terapia Ocupacional'), ('4.09', 'Educação Física')]), ('5. Ciências Agrárias', [('5.01', 'Agronomia'), ('5.02', 'Recursos Florestais e Engenharia Florestal'), ('5.03', 'Engenharia Agrícola'), ('5.04', 'Zootecnia'), ('5.05', 'Medicina Veterinária'), ('5.06', 'Recursos Pesqueiros e Engenharia de Pesca'), ('5.07', 'Ciência e Tecnologia de Alimentos')]), ('6. Ciências Sociais Aplicadas', [('6.01', 'Direito'), ('6.02', 'Administração'), ('6.03', 'Economia'), ('6.04', 'Arquitetura e Urbanismo'), ('6.05', 'Planejamento Urbano e Regional'), ('6.06', 'Demografia'), ('6.07', 'Ciência da Informação'), ('6.08', 'Museologia'), ('6.09', 'Comunicação'), ('6.10', 'Serviço Social'), ('6.11', 'Economia Doméstica'), ('6.12', 'Desenho Industrial'), ('6.13', 'Turismo')]), ('7. Ciências Humanas', [('7.01', 'Filosofia'), ('7.02', 'Sociologia'), ('7.03', 'Antropologia'), ('7.04', 'Arqueologia'), ('7.05', 'História'), ('7.06', 'Geografia'), ('7.07', 'Psicologia'), ('7.08', 'Educação'), ('7.09', 'Ciência Política'), ('7.10', 'Teologia')]), ('8. Linguística, Letras e Artes', [('8.01', 'Linguística'), ('8.02', 'Letras'), ('8.03', 'Artes')]), ('9. Outros', [('9.00', 'Outros')])], max_length=10, verbose_name='área do conhecimento (CNPq)'),
        ),
        # reverse_code=noop: desfazer não tem como saber qual titulação
        # já estava preenchida antes; o nivel_formacao de origem continua
        # no banco, então nada se perde ao reverter.
        migrations.RunPython(migrar_nivel_formacao, migrations.RunPython.noop),
    ]
