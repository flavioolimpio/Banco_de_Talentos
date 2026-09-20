# AGENTS.md — Banco de Especialistas · Polo de Inovação IFG

Instruções para agentes de IA (Codex, Copilot, Cursor, Claude Code, etc.) que
acessarem este repositório. Leia este arquivo inteiro antes de qualquer ação.

**`CLAUDE.md` tem o contexto completo — leia também.**

---

## Contexto do projeto

Sistema web Django para credenciamento de especialistas e gestão de inscrições
em chamadas internas do Polo de Inovação IFG (Instituto Federal de Goiás).
Opera sob normas EMBRAPII e legislação brasileira (LGPD, Lei 13.709/2018).

**Está EM PRODUÇÃO**, em `https://banco-de-especialistas.ifg.edu.br`, com
candidatos reais usando. Nada aqui é rascunho.

**Operador humano:** Prof. Flávio (RH do Polo), iniciante em Django.
**Regra de comunicação:** explique decisões técnicas, não apenas entregue código.

---

## O que este repositório contém

```
.
├── app.py                  ← App Streamlit ORIGINAL (legado, não modificar)
├── django_app/             ← App Django — EM PRODUÇÃO
├── CHAMADAS_INTERNAS/      ← Operação das chamadas: DADOS PESSOAIS, fora do git
├── data/                   ← DADOS SENSÍVEIS — ver restrições abaixo
├── imagens/                ← Assets visuais (originais)
├── docs/                   ← Documentação técnica e institucional
├── CLAUDE.md               ← Contexto detalhado do projeto
├── AGENTS.md               ← Este arquivo
└── .env                    ← NUNCA commitado, NUNCA lido por agentes
```

---

## O modelo de domínio, em um parágrafo

Um candidato se **credencia** no Banco de Especialistas preenchendo um perfil
(permanente, sem pontuação). Quando surge demanda, o Polo publica uma **Chamada
Interna** com as suas vagas, o seu prazo e o **seu** quadro de critérios,
montado pela Coordenação do Projeto no Django admin. O candidato interessado se
**inscreve naquela chamada**: responde ao quadro, anexa um PDF de comprovantes e
firma as declarações. A banca revisa e aprova.

```
ChamadaInterna ──< Vaga
       ├──< CriterioEdital ──< OpcaoCriterio
       │            └──< InscricaoItem
       └──< Inscricao (usuario FK, unique(usuario, chamada))
```

Base normativa: Edital PROPPG 29/2026 na redação da proposta de Retificação
nº 4/2026, itens 5.1 a 5.16.

---

## Restrições absolutas — nunca violar

### Dados pessoais (LGPD)
- **NUNCA** ler, exibir, logar ou processar arquivos em `data/`,
  `CHAMADAS_INTERNAS/` ou `media/`
- **NUNCA** incluir CPF, e-mail ou nome de candidato em logs ou outputs
- **NUNCA** expor conteúdo de PDFs de comprovantes
- Toda exportação de dado pessoal registra um `AuditLog`

### Segredos
- **NUNCA** ler `.env`
- **NUNCA** hardcodar senhas, tokens ou `SECRET_KEY` em código
- Segredos sempre via variável de ambiente com `python-decouple`

### App Streamlit original
- **NUNCA** modificar `app.py` — é o sistema legado, mantido por decisão do
  Prof. Flávio

### Produção
- **NUNCA** rodar `makemigrations` na VM. Migrations nascem no dev, são
  commitadas, e chegam por `git pull`
- **NUNCA** fazer deploy por conta própria
- **NUNCA** `git push --force` em `main`
- **NUNCA** mergear sem revisão do Prof. Flávio
- Trabalhar sempre em branch: `feat/`, `fix/` ou `chore/`

---

## Comportamento esperado dos agentes

### Antes de escrever código
1. Leia `CLAUDE.md`
2. Leia os arquivos relevantes antes de editar
3. Liste o que vai mudar e espere confirmação para mudanças destrutivas
4. Verifique quais testes precisam ser atualizados

### Ao escrever código Django
- Siga a estrutura em `django_app/apps/` — **não existe `apps/core`**;
  a home mora em `apps/usuarios`
- Use o ORM — nunca SQL raw sem justificativa
- **Nunca confie em dado do cliente.** Pontuação, prazo e elegibilidade são
  decididos no servidor. O JavaScript só melhora a experiência
- Adicione `AuditLog` para toda ação sensível
- Docstrings e comentários **em português**
- Comentário explica o **porquê**, não o quê. Se uma decisão pareceu estranha,
  registre a razão — é o que evita alguém "consertar" de volta

### JavaScript
A CSP de produção é `script-src 'self'`: **`<script>` inline é bloqueado**.
Todo JS vai para arquivo em `static/js/` e é carregado com `{% static %}`.

### Ao criar migrations
```bash
python manage.py makemigrations --check --dry-run   # antes: não pode sugerir nada
python manage.py makemigrations
python manage.py migrate
```
- Documente o porquê de todo `RunPython`
- Migration que muda tabela com dado real: **nunca** `RemoveField` sem
  autorização. Tirar um campo do formulário **não é** apagar a coluna
- Migration que torna coluna obrigatória vai em três passos: aditiva →
  backfill → constraint. Misturar `RunPython` e `AlterField` no mesmo arquivo
  quebra no SQLite do dev
- **Atenção:** `inscricoes/0004_populate_criterios_edital` importa
  `apps/inscricoes/quadros.py` em tempo de execução. Mexer na estrutura desse
  dicionário quebra bancos criados do zero

### Ao instalar dependências
```bash
source django_app/.venv/bin/activate
pip install <pacote>==<versao_exata>
pip freeze > requirements.txt
```
Justifique cada nova dependência. A régua é alta: quando uma dependência nova
resolve o que poucas linhas resolveriam, prefira as linhas.

### Ao fazer commits
```
<tipo>(<escopo>): <descrição em português>

tipos: feat, fix, docs, style, refactor, test, chore
```
O corpo do commit explica **por que**, não o que o diff já mostra. Decisão
contraintuitiva, bug encontrado no caminho, armadilha evitada: tudo isso vai no
corpo.

---

## Stack

```
Python        3.12+
Django        5.x LTS
PostgreSQL    15+ (produção) / SQLite (dev)
Gunicorn + nginx + systemd (banco-talentos.service)
python-decouple, django-axes, django-simple-history, argon2-cffi,
whitenoise, openpyxl, python-docx
```

**Frontend:** Django Templates + CSS. **Sem HTMX, sem framework JS, sem
bundler.** O JS é vanilla, em arquivos pequenos e independentes.

Não atualize versões sem verificar compatibilidade com Django 5.x.

---

## Testes

Os testes ficam em arquivos na raiz de cada app, não em pacotes `tests/`:

```
apps/usuarios/tests.py              ← CPF, login, cadastro, perfil, CNPq, municípios
apps/inscricoes/tests.py            ← quadros, comandos, admin, download, revisão
apps/inscricoes/test_chamadas.py    ← fluxo por chamada, pontuação, revisão do RH
apps/inscricoes/test_exportar_inscritos_lattes.py
```

**Toda a suíte precisa passar antes de qualquer commit:**
```bash
python manage.py test
```

Ao mexer em lógica não trivial (cálculo, prazo, permissão, dado pessoal),
deixe um teste que falha se a lógica quebrar.

---

## Verificação — evidência antes de afirmação

Não diga que algo funciona sem ter rodado. Em particular:

- `python manage.py test` — a saída, não a expectativa
- `python manage.py makemigrations --check --dry-run` — não pode sugerir nada
- `python manage.py check --deploy` antes de falar em deploy

**Ao conferir uma mudança de tela, confira por HTTP**, não pelo cliente de teste
do Django. O cliente de teste roda no processo e lê o código do disco; o
navegador recebe o que o `runserver` carregou na inicialização. Já houve um caso
nesta base em que um servidor antigo segurou a porta e serviu código de uma hora
antes, enquanto a verificação em memória dizia que estava tudo certo.

No Windows, `pkill` do Git Bash **não** mata processo nativo — derrube o
servidor pelo PowerShell.

---

## Sinalizações obrigatórias

Antes de implementar algo que afete os itens abaixo, **sinalize explicitamente**
para o Prof. Flávio:

- 🔐 Autenticação ou controle de acesso
- 📋 LGPD — dados pessoais, aceite de termos, exclusão
- 🗄️ Migrations que alteram tabelas com dados reais
- 📤 Endpoints que sirvam arquivos (PDFs de candidatos)
- 🔑 Leitura ou escrita de variáveis de ambiente
- ⚖️ Qualquer coisa que dependa de texto de Edital — regra de pontuação, prazo,
  elegibilidade, declaração obrigatória. O código não pode prometer o que o
  Edital não autoriza, nem o contrário

---

## Contato institucional

- **Operador:** Prof. Flávio, RH do Polo EMBRAPII/IFG — campus Anápolis/GO
- **E-mail da unidade:** rh.embrapii@ifg.edu.br
- **Editais:** https://www.ifg.edu.br/editais-pesquisa-e-pos-graduacao
