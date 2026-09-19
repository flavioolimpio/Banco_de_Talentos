# apps/usuarios/cnpq.py
# Banco de Talentos — Polo de Inovação IFG
#
# Tabela de Áreas do Conhecimento do CNPq, nos dois primeiros níveis:
# grande área (1 dígito) e área (2 dígitos). É o "Bloco C" da especificação
# em docs/Estrutura_Perfil_Cadastro_Banco_Especialistas.md, que pede um campo
# FECHADO e hierárquico — é o filtro principal para pré-selecionar candidatos
# por chamada.
#
# Formato do código: "<grande_area>.<area>", ex.: "1.06" = Química. O código
# oficial completo do CNPq tem quatro níveis e dígito verificador
# ("1.06.00.00-6"); aqui guardamos só o prefixo dos dois níveis que o
# formulário usa. A grande área é derivada do primeiro caractere — ver
# Usuario.grande_area_cnpq — para não existir uma segunda coluna que possa
# ficar dessincronizada.
#
# Por que constante Python e não tabela no banco: a tabela do CNPq muda a cada
# década e nunca é editada pelo usuário nem pelo RH. Um model + admin + fixture
# + migration seriam quatro arquivos para um dado imutável na prática.
#
# O formato abaixo — lista de (rótulo do grupo, lista de opções) — é o que o
# Django usa para renderizar <optgroup> nativamente num único <select>. Por
# isso o campo não precisa de JavaScript nenhum (e a CSP de produção bloqueia
# <script> inline).
#
# Fonte: Tabela de Áreas do Conhecimento do CNPq.
# Conferir em https://www.cnpq.br antes de uma revisão de edital.

CNPQ_AREAS = [
    (
        "1. Ciências Exatas e da Terra",
        [
            ("1.01", "Matemática"),
            ("1.02", "Probabilidade e Estatística"),
            ("1.03", "Ciência da Computação"),
            ("1.04", "Astronomia"),
            ("1.05", "Física"),
            ("1.06", "Química"),
            ("1.07", "Geociências"),
            ("1.08", "Oceanografia"),
        ],
    ),
    (
        "2. Ciências Biológicas",
        [
            ("2.01", "Biologia Geral"),
            ("2.02", "Genética"),
            ("2.03", "Botânica"),
            ("2.04", "Zoologia"),
            ("2.05", "Ecologia"),
            ("2.06", "Morfologia"),
            ("2.07", "Fisiologia"),
            ("2.08", "Bioquímica"),
            ("2.09", "Biofísica"),
            ("2.10", "Farmacologia"),
            ("2.11", "Imunologia"),
            ("2.12", "Microbiologia"),
            ("2.13", "Parasitologia"),
        ],
    ),
    (
        "3. Engenharias",
        [
            ("3.01", "Engenharia Civil"),
            ("3.02", "Engenharia de Minas"),
            ("3.03", "Engenharia de Materiais e Metalúrgica"),
            ("3.04", "Engenharia Elétrica"),
            ("3.05", "Engenharia Mecânica"),
            ("3.06", "Engenharia Química"),
            ("3.07", "Engenharia Sanitária"),
            ("3.08", "Engenharia de Produção"),
            ("3.09", "Engenharia Nuclear"),
            ("3.10", "Engenharia de Transportes"),
            ("3.11", "Engenharia Naval e Oceânica"),
            ("3.12", "Engenharia Aeroespacial"),
            ("3.13", "Engenharia Biomédica"),
        ],
    ),
    (
        "4. Ciências da Saúde",
        [
            ("4.01", "Medicina"),
            ("4.02", "Odontologia"),
            ("4.03", "Farmácia"),
            ("4.04", "Enfermagem"),
            ("4.05", "Nutrição"),
            ("4.06", "Saúde Coletiva"),
            ("4.07", "Fonoaudiologia"),
            ("4.08", "Fisioterapia e Terapia Ocupacional"),
            ("4.09", "Educação Física"),
        ],
    ),
    (
        "5. Ciências Agrárias",
        [
            ("5.01", "Agronomia"),
            ("5.02", "Recursos Florestais e Engenharia Florestal"),
            ("5.03", "Engenharia Agrícola"),
            ("5.04", "Zootecnia"),
            ("5.05", "Medicina Veterinária"),
            ("5.06", "Recursos Pesqueiros e Engenharia de Pesca"),
            ("5.07", "Ciência e Tecnologia de Alimentos"),
        ],
    ),
    (
        "6. Ciências Sociais Aplicadas",
        [
            ("6.01", "Direito"),
            ("6.02", "Administração"),
            ("6.03", "Economia"),
            ("6.04", "Arquitetura e Urbanismo"),
            ("6.05", "Planejamento Urbano e Regional"),
            ("6.06", "Demografia"),
            ("6.07", "Ciência da Informação"),
            ("6.08", "Museologia"),
            ("6.09", "Comunicação"),
            ("6.10", "Serviço Social"),
            ("6.11", "Economia Doméstica"),
            ("6.12", "Desenho Industrial"),
            ("6.13", "Turismo"),
        ],
    ),
    (
        "7. Ciências Humanas",
        [
            ("7.01", "Filosofia"),
            ("7.02", "Sociologia"),
            ("7.03", "Antropologia"),
            ("7.04", "Arqueologia"),
            ("7.05", "História"),
            ("7.06", "Geografia"),
            ("7.07", "Psicologia"),
            ("7.08", "Educação"),
            ("7.09", "Ciência Política"),
            ("7.10", "Teologia"),
        ],
    ),
    (
        "8. Linguística, Letras e Artes",
        [
            ("8.01", "Linguística"),
            ("8.02", "Letras"),
            ("8.03", "Artes"),
        ],
    ),
    (
        "9. Outros",
        [
            ("9.00", "Outros"),
        ],
    ),
]

# {"1": "1. Ciências Exatas e da Terra", ...} — usado pela property
# Usuario.grande_area_cnpq e por filtros do admin.
GRANDES_AREAS_CNPQ = {rotulo[0]: rotulo for rotulo, _ in CNPQ_AREAS}
