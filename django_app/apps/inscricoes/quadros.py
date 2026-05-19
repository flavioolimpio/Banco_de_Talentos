# Banco de Talentos — Polo de Inovação IFG
# Critérios e regras de pontuação do edital, por modalidade.
# Mapeados do Streamlit original para os choices do model Vinculo.

QUADROS_INSCRICAO: dict[str, list[dict]] = {
    "servidor": [
        {
            "id": "titulacao",
            "criterio": "Titulação",
            "regra": "Pontuação conforme maior titulação comprovada.",
            "maximo": 100.0,
        },
        {
            "id": "pos_doutoramento",
            "criterio": "Estágio pós-doutoramento",
            "regra": "5 pts por comprovação.",
            "maximo": 5.0,
        },
        {
            "id": "experiencia_fora_ict",
            "criterio": "Experiência profissional fora da ICT",
            "regra": "0,3 ponto por mês.",
            "maximo": 120.0,
        },
        {
            "id": "gestao_fora_ict",
            "criterio": "Experiência em gestão fora da ICT",
            "regra": "0,4 ponto por mês.",
            "maximo": 180.0,
        },
        {
            "id": "coordenacao_empresas_fundacao",
            "criterio": "Coordenação de projetos com empresas + fundação",
            "regra": "1,3 ponto por projeto por mês.",
            "maximo": 480.0,
        },
        {
            "id": "projetos_pdi_polo",
            "criterio": "Projetos de PD&I no Polo de Inovação IFG",
            "regra": "1 ponto por projeto por mês.",
            "maximo": 360.0,
        },
        {
            "id": "projetos_pdi_fora_polo",
            "criterio": "Projetos de PD&I fora do Polo",
            "regra": "0,7 ponto por projeto por mês.",
            "maximo": 200.0,
        },
        {
            "id": "coordenacao_fomento_publico",
            "criterio": "Coordenação de projetos com fomento público",
            "regra": "0,8 ponto por projeto por semestre.",
            "maximo": 200.0,
        },
        {
            "id": "participacao_orientacao_projetos",
            "criterio": "Participação/orientação em projetos",
            "regra": "0,3 ponto por projeto por semestre.",
            "maximo": 120.0,
        },
        {
            "id": "patente_depositada",
            "criterio": "Patente depositada",
            "regra": "2 pts por item.",
            "maximo": 20.0,
        },
        {
            "id": "registro_software",
            "criterio": "Registro de software",
            "regra": "1 pt por item.",
            "maximo": 10.0,
        },
        {
            "id": "artigos_cientificos",
            "criterio": "Artigos científicos",
            "regra": "1 pt por artigo.",
            "maximo": 10.0,
        },
        {
            "id": "capacitacoes_polo",
            "criterio": "Capacitações no Polo",
            "regra": "0,3 pt por participação.",
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
    "colaborador_externo": [
        {
            "id": "titulacao",
            "criterio": "Titulação",
            "regra": "Técnico de Nível Médio/Graduando: 10 pts | Graduado: 20 pts | Especialista (Lato Sensu): 30 pts | Mestre: 40 pts | Doutor: 70 pts.",
            "maximo": 70.0,
        },
        {
            "id": "experiencia_profissional_area",
            "criterio": "Experiência profissional comprovada em sua área de formação/atuação",
            "regra": "2 pontos por mês.",
            "maximo": 720.0,
        },
        {
            "id": "projetos_pdi_et_polo",
            "criterio": "Experiência em desenvolvimento e execução de projetos de PD&I e/ou ET com empresa privada/pública no âmbito do Polo de Inovação do IFG",
            "regra": "2 pontos por mês.",
            "maximo": 360.0,
        },
        {
            "id": "projetos_pdi_et_fora_polo",
            "criterio": "Experiência em desenvolvimento e execução de projetos de PD&I e/ou ET com empresa privada/pública fora do âmbito do Polo de Inovação",
            "regra": "1,5 ponto por mês.",
            "maximo": 180.0,
        },
        {
            "id": "projetos_pesquisa_inovacao_extensao_formacao",
            "criterio": "Experiência na participação em projetos de pesquisa, inovação e/ou extensão durante seu curso de formação",
            "regra": "0,5 ponto por projeto, por mês.",
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
