# Banco de Talentos - Polo de Inovacao IFG

Aplicacao piloto em Streamlit para cadastro de estudantes, servidores e colaboradores externos do Polo de Inovacao do IFG.

## Como rodar localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

## O que esta versao ja faz

- Tela publica de login e cadastro.
- Cadastro por categoria: Estudante, Servidor e Colaborador Externo.
- Aceite simples de uso de dados/LGPD no cadastro.
- Login com senha armazenada em hash.
- Area logada com Home, Meu Cadastro e Minha Pontuacao.
- Persistencia dos dados pessoais, endereco e formacao.
- Area administrativa para listar e baixar os cadastros em CSV.
- Banco SQLite local em `data/banco_talentos.db`.

## Usuario de teste

```text
admim
admim
```

Esse usuario tem perfil de administrador para testar a tela **Administracao**.

## Publicacao piloto

Para um piloto com dados reais, publique em um ambiente com disco persistente, como VPS, Render com persistent disk, Railway/VM, ou outro host que mantenha o arquivo `data/banco_talentos.db`.

O Streamlit Community Cloud serve para demonstracao visual, mas nao e ideal para cadastro oficial porque o arquivo SQLite local pode nao ser persistente entre reinicios.

Antes de abrir para um grupo maior, recomenda-se trocar a senha administrativa, revisar o texto de consentimento/LGPD e definir rotina de backup do banco `data/banco_talentos.db`.
