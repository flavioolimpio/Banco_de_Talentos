# Banco de Talentos — Polo de Inovação IFG
# Critérios e regras de pontuação do edital, por modalidade.
# Mapeados do Streamlit original para os choices do model Vinculo.

QUADROS_INSCRICAO: dict[str, list[dict]] = {
    "servidor": [
        {
            "id": "ifgproduz",
            "criterio": "Produção Acadêmica (IFGProduz)",
            "regra": "Pontuação calculada automaticamente a partir do Lattes via IFGProduz.",
            "maximo": 100.0,
            "is_api": True,
        },
        {
            "id": "exp_profissional_fora_ict",
            "criterio": "Experiência profissional comprovada em sua área de formação/atuação fora da sua ICT",
            "regra": "0,3 ponto por semestre.",
            "maximo": 9.0,
        },
        {
            "id": "exp_gestao_inovacao_fora_ict",
            "criterio": "Experiência profissional comprovada em nível de gestão de inovação em sua área de formação/atuação fora da sua ICT",
            "regra": "0,4 ponto por semestre.",
            "maximo": 12.0,
        },
        {
            "id": "coord_projetos_empresas_fundacao",
            "criterio": "Experiência na coordenação de projetos com/em empresas privada/públicas e interveniência de fundação de apoio",
            "regra": "0,8 pontos por projeto, por semestre.",
            "maximo": 16.0,
        },
        {
            "id": "pdi_polo",
            "criterio": "Experiência em desenvolvimento e execução de projetos de PD&I com empresas privada/pública no âmbito do Polo de Inovação do IFG",
            "regra": "1 ponto por projeto, por semestre.",
            "maximo": 10.0,
        },
        {
            "id": "pdi_fora_polo",
            "criterio": "Experiência em desenvolvimento e execução de projetos de PD&I e/ou ET com empresas privadas/públicas fora do âmbito do Polo de Inovação",
            "regra": "0,6 ponto por projeto, por semestre.",
            "maximo": 12.0,
        },
        {
            "id": "coord_projetos_fomento_publico",
            "criterio": "Experiência na coordenação de projetos de pesquisa e inovação fomentados por agências públicas, por exemplo, CNPq, ou por meio de Editais internos de uma ICT",
            "regra": "0,8 pontos por projeto, por semestre.",
            "maximo": 16.0,
        },
        {
            "id": "orientacao_coord_participacao",
            "criterio": "Experiência na orientação/coordenação/participação de projetos de pesquisa e/ou inovação fomentados por agências públicas ou por meio de Editais internos de uma ICT",
            "regra": "0,4 ponto por projeto, por semestre.",
            "maximo": 16.0,
        },
        {
            "id": "capacitacoes_polo",
            "criterio": "Participação concluída em capacitações promovidas pelo Polo de Inovação do IFG",
            "regra": "0,3 ponto por participação.",
            "maximo": 9.0,
        },
    ],
    "estudante": [
        {
            "id": "cre",
            "criterio": "CRE (Coeficiente de Rendimento Escolar)",
            "regra": "De 60 a 100.",
            "maximo": 100.0,
        },
        {
            "id": "projetos_pdi_et_polo",
            "criterio": "Experiência em desenvolvimento e execução de projetos de PD&I e/ou ET com empresas privadas/públicas no âmbito do Polo de Inovação do IFG",
            "regra": "6 pontos por projeto, por semestre.",
            "maximo": 60.0,
        },
        {
            "id": "projetos_pdi_et_fora_polo",
            "criterio": "Experiência em desenvolvimento e execução de projetos de PD&I e/ou ET com empresas privadas/públicas fora do âmbito do Polo de Inovação",
            "regra": "4 pontos por projeto, por semestre.",
            "maximo": 40.0,
        },
        {
            "id": "projetos_pesquisa_inovacao_extensao",
            "criterio": "Experiência na participação ou execução de projetos de pesquisa, inovação e/ou extensão fomentados por agências públicas ou por meio de editais internos de uma ICT",
            "regra": "2 pontos por projeto, por semestre.",
            "maximo": 20.0,
        },
        {
            "id": "patente_depositada",
            "criterio": "Patente depositada",
            "regra": "2 pontos por objeto.",
            "maximo": 20.0,
        },
        {
            "id": "registro_software",
            "criterio": "Registro de Software",
            "regra": "1 ponto por objeto.",
            "maximo": 10.0,
        },
        {
            "id": "artigos_qualis",
            "criterio": "Artigos científicos com Qualis em sua área de avaliação",
            "regra": "1 ponto por artigo.",
            "maximo": 10.0,
        },
        {
            "id": "capacitacoes_polo",
            "criterio": "Participação concluída em capacitações promovidas pelo Polo de Inovação do IFG",
            "regra": "0,3 ponto por participação.",
            "maximo": 9.0,
        },
    ],
    "servidor_apoio_tecnico": [
        {
            "id": "formacao_academica",
            "criterio": "Formação acadêmica",
            "regra": "Médio completo: 10 pts / Graduando: 15 pts / Graduado: 25 pts / Especialista: 35 pts / Mestre: 50 pts / Doutor: 70 pts",
            "maximo": 70.0,
        },
        {
            "id": "experiencia_profissional_area",
            "criterio": "Experiência profissional na área de formação/atuação",
            "regra": "0,3 ponto por mês",
            "maximo": 120.0,
        },
        {
            "id": "gestao_projetos_pdi_ict",
            "criterio": "Experiência em gestão de projetos de PD&I e/ou ET no Polo de Inovação do IFG ou de outra ICT",
            "regra": "1,5 ponto por projeto, por mês",
            "maximo": 180.0,
        },
        {
            "id": "gestao_projetos_externos",
            "criterio": "Experiência em gestão de projetos externos: empresas, agências de fomento, editais públicos",
            "regra": "1,0 ponto por projeto, por mês",
            "maximo": 120.0,
        },
        {
            "id": "comunicacao_cientifica",
            "criterio": "Experiência em comunicação científica, divulgação e popularização da ciência",
            "regra": "0,5 ponto por mês",
            "maximo": 60.0,
        },
        {
            "id": "analise_dados_relatorios",
            "criterio": "Experiência comprovada em análise de dados, produção de relatórios técnicos ou gestão de informações em projetos",
            "regra": "0,5 ponto por mês",
            "maximo": 60.0,
        },
        {
            "id": "capacitacoes_polo",
            "criterio": "Participação concluída em capacitações promovidas pelo Polo de Inovação do IFG",
            "regra": "0,3 ponto por participação",
            "maximo": 9.0,
        },
        {
            "id": "producao_tecnica",
            "criterio": "Produção técnica relevante: artigo, relatório técnico publicado, produto de comunicação científica documentado",
            "regra": "1 ponto por produção",
            "maximo": 10.0,
        },
    ],
    # Quadro I — Colaborador Externo / Pesquisador.
    # Critérios conforme o Edital PROPPG nº 30/2026, item 5.3 (13 itens).
    # Fonte: docs/criterios-colab-externo-edital-30-2026.md
    "colaborador_externo": [
        {
            "id": "titulacao",
            "criterio": "Titulação",
            "regra": "Técnico Nível Médio: 10 pts | Graduado: 20 pts | Especialista (Lato Sensu): 40 pts | Mestre: 60 pts | Doutor: 100 pts.",
            "maximo": 100.0,
        },
        {
            "id": "estagio_posdoc",
            "criterio": "Estágio pós-doutoramento",
            "regra": "5 pontos (valor fixo).",
            "maximo": 5.0,
        },
        {
            "id": "experiencia_profissional_area",
            "criterio": "Experiência profissional comprovada em sua área de formação/atuação fora da sua ICT",
            "regra": "0,3 ponto por mês.",
            "maximo": 120.0,
        },
        {
            "id": "exp_gestao_fora_ict",
            "criterio": "Experiência profissional comprovada em nível de gestão em sua área de formação/atuação fora da sua ICT",
            "regra": "0,4 ponto por mês.",
            "maximo": 180.0,
        },
        {
            "id": "coord_projetos_empresas_fundacao",
            "criterio": "Experiência na coordenação de projetos com/em empresas privadas/públicas e interveniência de fundação de apoio",
            "regra": "1,3 ponto por projeto, por mês.",
            "maximo": 480.0,
        },
        {
            "id": "projetos_pdi_et_polo",
            "criterio": "Experiência em desenvolvimento e execução de projetos de PD&I com empresas privadas/públicas no âmbito do Polo de Inovação do IFG",
            "regra": "1 ponto por projeto, por mês.",
            "maximo": 360.0,
        },
        {
            "id": "projetos_pdi_et_fora_polo",
            "criterio": "Experiência em desenvolvimento e execução de projetos de PD&I e/ou ET com empresas privadas/públicas fora do âmbito do Polo de Inovação",
            "regra": "0,7 ponto por projeto, por mês.",
            "maximo": 200.0,
        },
        {
            "id": "coord_projetos_fomento_publico",
            "criterio": "Experiência na coordenação de projetos de pesquisa e inovação fomentados por agências públicas (ex.: CNPq) ou Editais internos de uma ICT",
            "regra": "0,8 ponto por projeto, por semestre.",
            "maximo": 200.0,
        },
        {
            "id": "orientacao_participacao_fomento",
            "criterio": "Experiência na orientação/coorientação/participação de projetos de pesquisa e/ou inovação fomentados por agências públicas ou Editais internos de uma ICT",
            "regra": "0,3 ponto por projeto, por semestre.",
            "maximo": 120.0,
        },
        {
            "id": "patente_depositada",
            "criterio": "Patente depositada",
            "regra": "2 pontos por objeto.",
            "maximo": 20.0,
        },
        {
            "id": "registro_software",
            "criterio": "Registro de software",
            "regra": "1 ponto por objeto.",
            "maximo": 10.0,
        },
        {
            "id": "artigos_qualis",
            "criterio": "Artigos científicos com Qualis em sua área de avaliação",
            "regra": "1 ponto por artigo.",
            "maximo": 10.0,
        },
        {
            "id": "capacitacoes_polo",
            "criterio": "Participação concluída em capacitações promovidas pelo Polo de Inovação do IFG",
            "regra": "0,3 ponto por participação.",
            "maximo": 9.0,
        },
    ],
}
