# CLAUDE.md — Polo de Inovação IFG · Banco de Especialistas

Este arquivo é lido automaticamente pelo Claude Code em toda sessão.
Ele contém o contexto institucional, decisões técnicas já tomadas e
regras de operação que nunca devem ser esquecidas.

---

## Quem sou eu

**Prof. Flávio** — integrante da equipe de RH do Polo EMBRAPII do IFG
(Instituto Federal de Goiás), campus Anápolis/GO.

- Formação: química computacional
- Python: intermediário-avançado (uso diário em pesquisa)
- Django: iniciante — **sempre explique o porquê de cada decisão**
- Redes/DevOps: básico
- Frontend: HTML/CSS sim, JavaScript mínimo

**Quando eu não entender algo, explique como se fosse aula, com exemplos.**

---

## O que este projeto é

Sistema web institucional chamado **Banco de Especialistas** do Polo de
Inovação IFG (o repositório, o serviço systemd e o diretório na VM ainda
usam o nome legado "banco-talentos").

Candidatos (estudantes, servidores e colaboradores externos) se **credenciam**
no Banco preenchendo um perfil. Quando surge demanda, o Polo publica uma
**Chamada Interna** com vagas, prazo e quadro de critérios próprios; quem se
interessa se **inscreve naquela chamada**, responde ao quadro, anexa os
comprovantes em PDF e firma as declarações. A equipe de RH revisa e aprova.

### Contexto EMBRAPII

O polo opera sob normas da EMBRAPII (Empresa Brasileira de Pesquisa e
Inovação Industrial). Projetos seguem um workflow de 16 etapas. Este
webapp apoia principalmente a **Etapa 0** (banco de especialistas) e
pode ser expandido para apoiar etapas de alocação e cadastro no SRInfo.

---

## Estado atual do projeto

**O Django está EM PRODUÇÃO, no ar, com candidatos reais usando.**

| Item | Status |
|------|--------|
| App Django | em `django_app/` — **em produção** |
| App Streamlit original | `app.py` na raiz — legado, **NÃO APAGAR** sem autorização |
| Domínio em produção | `https://banco-de-especialistas.ifg.edu.br` |
| Banco de produção | PostgreSQL na VM IFG |
| Banco de dev local | SQLite (`django_app/dev.sqlite3`) — só teste |
| PDFs de candidatos (prod) | `media/` na VM — servidos só por view autenticada |
| Servidor de produção | nginx + gunicorn + systemd (`banco-talentos.service`) |
| Assets visuais IFG | `imagens/` (originais) e `django_app/static/imagens/` (servidos) |
| Operação de chamadas | `CHAMADAS_INTERNAS/` — fora do git, dados pessoais |

### Reforma de setembro/2026 — NÃO ESTÁ EM PRODUÇÃO

A reunião com a gestão em 18/09/2026 decidiu duas mudanças ligadas, hoje
implementadas na branch **`feat/home-limpa-e-migrations`** (16 commits, 243
testes passando, **não mergeada em `main`**; tudo commitado em 30/10/2026):

1. **O cadastro virou só perfil.** A Análise Curricular saiu do credenciamento.
2. **A inscrição passou a ser por Chamada Interna.** Cada chamada tem as suas
   vagas, o seu prazo e o **seu** quadro de critérios, montado pela Coordenação
   do Projeto no admin, sem deploy. O candidato clica num botão na home e se
   inscreve naquela chamada — resolve a reclamação de candidatos convocados
   repetidamente para chamadas em que não tinham interesse.

Base normativa: proposta de **Retificação nº 3/2026** ao Edital PROPPG 29/2026 (até 28/10/2026
chamada de "Ret. 4" — código, handoffs e nomes de arquivo ainda usam esse nome) e
**Ret. 1/2026** ao Edital 30/2026; os dois valem até 31/12/2026,
itens 5.1 a 5.16. **A versão de trabalho do Edital fica no OneDrive, não no repositório:**
`C:\Users\user\OneDrive\Flavio\Aulas\IFG_Valparaiso\EMBRAPII\01_Editais\2026_Banco_de_Especialistas\Edital_29-2026_Servidores\Retificacao_04-2026`
— **`Edital29_2026_consolidado_Ret4.docx`** (mestre; o `.md`/`.html` de 23/09 têm o mesmo
texto, conferido em 21/10/2026). Os demais arquivos da pasta são rascunhos superados. Editar só lá.

> 🚧 **Bloqueio para o lançamento, e não é código:** a seção 6 duplicada (item
> 6.12, formulário em conta @ifg.edu.br) **já foi suprimida no consolidado**, mas
> o texto **ainda não foi aprovado pela PROPPG**. Em 28/10/2026 ficaram prontas as
> versões limpas do 29 (Ret. 3/2026, `..._v05_limpo.docx`) e do 30 (Ret. 1/2026,
> `..._v03_limpo.docx`), e a proposta com marcas do 31 (Ret. 1/2026), que aguarda
> revisão do Prof. Flávio. Detalhes em `CHAMADAS_INTERNAS/HANDOFF_retificacao4_2026-10-28.md`.

### Acesso à VM / deploy

```bash
# Na VM, para publicar alterações já commitadas e enviadas (push):
cd /var/www/html/banco-talentos
git pull
source django_app/.venv/bin/activate
# se mudou models:    python django_app/manage.py migrate
# se mudou static/JS: python django_app/manage.py collectstatic --noinput
sudo systemctl restart banco-talentos
```

Comandos de management (ex.: `colab_sem_tipo`, `recalcular_totais_servidores`)
**não** exigem restart do serviço — são executados na linha de comando.

---

## Stack tecnológica decidida

```
Backend:    Django 5.x LTS
Linguagem:  Python 3.12+
Banco:      PostgreSQL 15+ (produção) / SQLite (dev local apenas)
Servidor:   Gunicorn + nginx
Auth:       Django auth nativo com CPF como username
Hash senha: Argon2 (django[argon2])
Config:     python-decouple (.env)
Auditoria:  django-simple-history
Brute force: django-axes
Frontend:   Django Templates + CSS existente do Streamlit
Reatividade: JS externo mínimo (ex.: cálculo da pontuação em tempo real).
             Sem HTMX; a CSP bloqueia <script> inline, então o JS fica em
             arquivos servidos por static/ (script-src 'self').
Upload:     Django FileField com validação rigorosa
Deploy dev: manage.py runserver + ngrok para testes do time
Deploy prod: VM Linux IFG (.ifg.edu.br) — provisionada pela TI
```

---

## Estrutura de apps Django

```
django_app/
├── manage.py
├── config/                  ← configurações do projeto
│   ├── settings/
│   │   ├── base.py          ← compartilhado dev + prod
│   │   ├── dev.py           ← DEBUG=True, SQLite ok
│   │   └── prod.py          ← PostgreSQL, HTTPS, sem DEBUG
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── usuarios/            ← CustomUser, login, cadastro, LGPD
│   ├── inscricoes/          ← Inscrição, itens de pontuação, upload PDF
│   └── auditoria/           ← AuditLog, registro de acessos
├── templates/               ← HTML base + por app
├── static/
│   ├── css/app.css          ← CSS migrado do Streamlit
│   ├── imagens/             ← polo.jpg, favicon.png
│   └── js/                  ← JS externo (a CSP bloqueia inline)
└── media/                   ← PDFs e uploads (NUNCA no git)
```

**Não existe `apps/core`.** A home mora em `apps/usuarios/views.py`. O fluxo
por chamada está em `apps/inscricoes/views_chamadas.py`; `views.py` guarda só
as rotas antigas, que redirecionam, e o download de comprovante.

Arquivos em `static/js/`:

| Arquivo | Para quê |
|---|---|
| `revisao.js` | total ao vivo na revisão do RH |
| `uf_cidade.js` | troca a lista de cidades ao mudar o estado |
| `mascaras.js` | máscara de telefone |
| `municipios.json` | 5.571 municípios do IBGE — lido pelo JS **e** pelo Python |
| `inscricao_form.js` | legado do fluxo antigo |

---

## Modelos de dados

### app `usuarios` — model `Usuario`
- CPF é o identificador principal (`USERNAME_FIELD`). O backend
  `CpfEmailBackend` aceita login por **CPF ou e-mail**.
- `perfil` distingue candidato / RH / coordenador / admin.
- LGPD: `aceite_lgpd` + `_em` + `_versao` + `_ip`.
- **Cadastro enxuto (set/2026):** o formulário segue os blocos A–G de
  `docs/Estrutura_Perfil_Cadastro_Banco_Especialistas.md`, em 3 abas —
  Dados Pessoais, Formação e Perfil Profissional. Campos que saíram do
  formulário (`nivel_formacao`, `data_nascimento`, `genero`, `instituicao`,
  `linkedin`, endereço completo) **continuam no banco**: tirar do form não é
  apagar coluna.
- `cnpq_area` — Tabela CNPq em `apps/usuarios/cnpq.py`, `<select>` com
  `<optgroup>` nativo do Django, sem JavaScript. A grande área é **derivada do
  prefixo** do código, não tem coluna própria.
- `uf` / `cidade` — selects encadeados. Os 5.571 municípios do IBGE vivem em
  **um arquivo só**, `static/js/municipios.json`, lido pelo Python
  (`apps/usuarios/municipios.py`) **e** pelo JavaScript, para as duas listas
  nunca discordarem.
- Declarações de via única (`confirmar_declaracao`): `ciencia_credenciamento`,
  `ciencia_comunicacoes`, `declaracao_veracidade`,
  `consentimento_verificacao_bases`.

### app `inscricoes` — o fluxo por Chamada Interna

```
ChamadaInterna ──< Vaga                        (Quadro 1 do Aviso)
       ├──< CriterioEdital ──< OpcaoCriterio   (Quadro 2 do Aviso)
       │            └──< InscricaoItem
       └──< Inscricao (usuario FK, unique(usuario, chamada), vaga FK)
```

- **`ChamadaInterna`** — número/ano, título, projeto, datas de abertura e
  encerramento, `publicada`, `legado`. **Sem campo de status**: `aberta` é uma
  property derivada de `publicada` + as duas datas. **Sem campo de modalidades
  elegíveis**: a elegibilidade sai das vagas, para não haver como divergir do
  que foi publicado.
- **`CriterioEdital`** — o nome da classe é legado; desde a Retificação 4 o
  quadro é **de cada chamada**. Tem `chamada` (FK PROTECT), `tipo`
  (contagem ou escolha), `pontos_por_unidade`, `unidade_rotulo` e `maximo`.
- **`Inscricao`** — FK para o usuário, **uma por candidato POR chamada**.
  Guarda as declarações do item 5.6 e as licenças à gestante/adotante do
  item 5.8, III.
- **`InscricaoItem`** — guarda a RESPOSTA (`quantidade` ou `opcao`); a
  `pontuacao` é sempre **calculada**, nunca digitada.

**Regra central:** ninguém digita pontuação — nem o candidato, nem a banca.
Os dois passam por `CriterioEdital.pontuar()`. O JavaScript só atualiza o
número na tela; a conta que vale é a do servidor.

**Chamadas de legado:** três chamadas sintéticas (29, 30 e 31/2026),
`publicada=False` e `legado=True`, guardam as inscrições do credenciamento
antigo. São somente leitura e nunca aparecem para o candidato. Critérios delas
não têm pontos por unidade — por isso a revisão do RH mantém, **só para elas**,
o campo de pontuação digitada: recalcular zeraria a inscrição histórica.

### app `auditoria` — `AuditLog`
Campos: ator, alvo, acao, detalhes (JSON), ip, user_agent, timestamp.

---

## Constantes de negócio

`QUADROS_INSCRICAO`, em `apps/inscricoes/quadros.py`, **deixou de ser a
verdade**. Desde a Retificação 4 cada chamada tem o seu quadro, montado pela
Coordenação do Projeto no Django admin, sem deploy. O arquivo virou uma
**biblioteca de quadros modelo**, copiada para dentro de uma chamada por
`popular_criterios --chamada <id>` — para o coordenador não começar com a
folha em branco.

> ⚠️ A migration `0004_populate_criterios_edital` importa `quadros.py` **em
> tempo de execução**. Mexer na estrutura do dicionário quebra bancos criados
> do zero (dev novo, CI). Foi assim que nasceu o bug do `is_api` corrigido pela
> migration `0011`.

---

## Regras de operação — Claude Code deve seguir sempre

### Antes de qualquer mudança
1. `git status` — verificar estado atual
2. `view` nos arquivos que serão afetados
3. Comunicar o que vai mudar e pedir OK para mudanças destrutivas

### Estrutura de branches
```
main                          ← código estável, é o que está em produção
feat/<assunto>                ← funcionalidade nova
fix/<assunto>                 ← correção
chore/<assunto>               ← manutenção, migrations, limpeza
```
As branches `fase-1` a `fase-7` são históricas — a migração terminou.

**Merge para `main` só após revisão do Prof. Flávio.** Nunca mergear nem fazer
deploy por conta própria.

### Arquivos que NUNCA devem ser tocados sem autorização explícita
- `data/` — pode conter dados pessoais reais de candidatos (LGPD)
- `app.py` — Streamlit original em produção durante migração
- `.env` — variáveis de ambiente com segredos

### Arquivos que NUNCA vão para o git
```
.env
data/
media/
CHAMADAS_INTERNAS/    ← toda a operação de chamadas: nomes, CPFs, PDFs
*.db  *.sqlite3
*.csv  *.xlsx  *.pdf
__pycache__/  venv/  *.pyc
```

### Instalação de pacotes
```bash
# SEMPRE dentro do virtualenv
source django_app/.venv/bin/activate
pip install <pacote>
pip freeze > requirements.txt  # atualizar após cada instalação
```

---

## Segurança e LGPD — princípios não-negociáveis

1. **Senhas** — Argon2, nunca em texto puro, nunca em log
2. **CPF** — campo sensível, nunca em URL, nunca em log
3. **PDFs** — servidos via view autenticada, nunca por URL direta
4. **Aceite LGPD** — registrar timestamp, IP e versão do termo
5. **Auditoria** — toda ação sensível registrada em `AuditLog`
6. **Export CSV** — apenas admin_rh, sempre registrado em AuditLog
7. **Sessões** — expiração configurada, regeneração de token no login
8. **CSRF** — ativo em todos os formulários (Django padrão)
9. **Upload** — validar MIME, extensão, tamanho máximo (10MB)
10. **Segredos** — apenas em `.env`, nunca hardcoded

Quando uma decisão impactar qualquer um desses pontos,
**sinalize explicitamente antes de implementar**.

---

## Identidade visual IFG

```python
LIME  = "#d6f000"   # destaque / botão primário
GREEN = "#168241"   # verde IFG principal
INK   = "#202124"   # texto
```

O CSS do Streamlit (~660 linhas) é reaproveitado integralmente.
Os templates Django herdam de `base.html` que importa esse CSS.
Não redesenhar — manter a identidade visual existente.

---

## Comandos frequentes do projeto

```bash
# Ativar ambiente
source django_app/.venv/bin/activate     # Windows: django_app/.venv/Scripts/activate

# Rodar localmente
python manage.py runserver

# Migrations após alterar models
python manage.py makemigrations --check --dry-run   # não pode sugerir nada
python manage.py makemigrations
python manage.py migrate

# Rodar testes  (243 e contando — devem passar TODOS antes de commitar)
python manage.py test

# Verificar segurança antes de deploy
python manage.py check --deploy

# Coletar arquivos estáticos para produção
python manage.py collectstatic --noinput
```

### Comandos de operação das chamadas

```bash
# Ver os IDs das chamadas cadastradas
python manage.py exportar_convocados --listar-chamadas

# Copiar um quadro MODELO de quadros.py para dentro de uma chamada
python manage.py popular_criterios --chamada <id> [--quadro servidor]

# Lista de e-mails + rascunho do aviso de divulgação
python manage.py emails_chamada --chamada <id> [--csv lista.csv]

# Convocados de uma chamada, em ordem de pontuação
python manage.py exportar_convocados --chamada <id> [--modalidade ...] [--vaga "Pq 12"]

# Comprovantes dos aprovados de uma chamada
python manage.py exportar_pdfs_aprovados --chamada <id>

# Relatórios
python manage.py exportar_aprovadas [--chamada <id>]
python manage.py exportar_inscritos_lattes [--chamada <id>]
python manage.py itens_orfaos [--chamada <id>]
```

> O sistema **não envia e-mail**. `emails_chamada` gera a lista e o texto; o
> disparo sai de `rh.embrapii@ifg.edu.br` com os endereços em Cco. O item 5.2.2
> do Edital trata a mensagem como *aviso complementar* — o ato que abre o prazo
> é a publicação na página da PROPPG. Não há SMTP configurado em produção.

### Armadilhas do ambiente local

- A porta 8000 é bloqueada neste ambiente; usar **8731**.
- **`pkill` do Git Bash não mata processo nativo do Windows.** Para derrubar um
  servidor antigo, usar PowerShell:
  `Get-Process python | Where-Object Path -like "*Banco_de_Talentos*"`.
  Já aconteceu de um `runserver --noreload` velho segurar a porta e servir
  **código de uma hora antes**, enquanto a verificação pelo cliente de teste do
  Django (que lê o disco, não o processo) dizia que estava tudo certo.
  **Conferir sempre por HTTP.**

## Perguntas abertas (a confirmar com TI do IFG)

- [ ] SO da VM (Ubuntu 22.04 LTS esperado)
- [ ] RAM e disco disponíveis
- [ ] Sudo liberado ou ambiente restrito
- [ ] PostgreSQL já instalado ou instalar
- [ ] Política de backup institucional cobre a VM?
- [ ] HTTPS via Let's Encrypt ou certificado institucional IFG?
- [ ] Há SSO institucional (LDAP/SAML) a integrar no futuro?
- [ ] Política institucional sobre uso de IA com acesso a código

---

## Próxima ação pendente

**Colocar a reforma de setembro em produção.** Na ordem:

1. **Fechar as retificações dos Editais 29, 30 e 31 e levar à PROPPG** — é o que
   destrava tudo (ver o bloqueio em "Estado atual do projeto"). Roteiro em
   `CHAMADAS_INTERNAS/HANDOFF_retificacao4_2026-10-28.md`, seções 2.5, 3 e 4. Os
   três editais limpos estão prontos no OneDrive (30/10). O código está todo
   commitado na branch (243 testes OK em 30/10); pendentes do revisor:
   `InscricaoItemInline` ainda deixa digitar `pontuacao_validada` no admin para
   chamadas não-legado, e os quadros modelo de `quadros.py` seguem acima de 100
   (patch de redistribuição em `docs/superpowers/plans/2026-10-30-quadros-modelo-100.patch`,
   não aplicado: decisão de pesos da Coordenação).
2. **Ensaio da migração com dump real.** `pg_dump -Fc` da VM, restaurar num
   PostgreSQL de rascunho, rodar `migrate`. O SQLite do dev não reproduz o
   comportamento de constraint/NOT NULL do Postgres. Parar em `0013`, conferir
   as contagens por `chamada_id`, e só então aplicar a `0014`.
3. **Deploy:** `systemctl stop` → backup do banco e do `media/` → `git pull` →
   `migrate` → `collectstatic` → `systemctl start`.
   **Parar o serviço não é preciosismo:** entre a `0012` e a `0014` não existe
   índice de unicidade por usuário. As três rodam no mesmo `migrate`.
4. **Avisar a gestão** de que o banner "Complete seu perfil" vai reaparecer para
   100% dos cadastrados e que, **sem cadastro completo, a inscrição em Chamada
   fica bloqueada** (item 5.3). `perfil_completo` exige os campos do item 4.2
   conforme o vínculo (`CAMPOS_CADASTRO` em `apps/usuarios/models.py`) e as
   declarações, que ninguém tem ainda.

Pendências menores:

- **Logo do Criar** — não existe arquivo no repositório. O `<img>` está escrito
  e comentado em `templates/usuarios/home.html`; basta soltar `logo-criar.png`
  em `django_app/static/imagens/` e descomentar.
- `senha_sudo.txt` nunca foi rastreado e agora está no `.gitignore`; apagar do disco quando não for mais preciso.

Handoffs, do mais recente: **`CHAMADAS_INTERNAS/HANDOFF_deploy_reforma_2026-10-30.md`**
(roteiro completo: PROPPG → decisões de código → HTTP → push/merge → ensaio da migração → deploy → operação; ler primeiro),
`HANDOFF_retificacao4_2026-10-28.md` (Editais 29, 30 e 31, seções 2.5 e 2.6 = o que foi feito em 30/10),
`HANDOFF_retificacao4_2026-10-26.md` (revisão e cópia com propostas), `HANDOFF_retificacao4_2026-10-21.md`, `HANDOFF_lattes_xml_edital_2026-09-24.md` (código não commitado) e
`HANDOFF_chamadas_internas_2026-09-20.md` (reforma e roteiro de deploy).
Plano que originou a reforma:
`~/.claude/plans/ontem-tive-uma-reuni-o-partitioned-lightning.md`.

Ver skill `django-ifg` para os padrões de código e referências por domínio.
