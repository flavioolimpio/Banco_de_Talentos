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
usam o nome legado "banco-talentos"). Permite que candidatos (estudantes,
servidores, colaboradores externos) se cadastrem em editais do Polo,
informem pontuação por critério e enviem comprovantes em PDF para
avaliação da equipe de RH.

### Contexto EMBRAPII

O polo opera sob normas da EMBRAPII (Empresa Brasileira de Pesquisa e
Inovação Industrial). Projetos seguem um workflow de 16 etapas. Este
webapp apoia principalmente a **Etapa 0** (banco de especialistas) e
pode ser expandido para apoiar etapas de alocação e cadastro no SRInfo.

---

## Estado atual do projeto

**A migração Streamlit → Django está concluída. O Django está EM PRODUÇÃO,
no ar, com candidatos reais usando.** O foco atual é **manutenção e ajustes
finos**, não mais "construção".

| Item | Status |
|------|--------|
| App Django | em `django_app/` — **em produção** |
| App Streamlit original | `app.py` na raiz — legado, **NÃO APAGAR** sem autorização |
| Domínio em produção | `https://banco-de-especialistas.ifg.edu.br` |
| Banco de produção | PostgreSQL na VM IFG |
| Banco de dev local | SQLite (`django_app/dev.sqlite3` / `local.sqlite3`) — só teste |
| PDFs de candidatos (prod) | `media/` na VM — servidos só por view autenticada |
| Servidor de produção | nginx + gunicorn + systemd (`banco-talentos.service`) |
| Assets visuais IFG | `imagens/` |

**Progresso por fase:** Fases 1–7 (setup, models, auth, admin, inscrição,
segurança, deploy) **concluídas**. O sistema está implantado e operacional.

**Regra de ouro:** o Streamlit original (`app.py`) e a pasta `data/` ficam
intactos — não apagar sem autorização explícita do Prof. Flávio.

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
│   ├── auditoria/           ← AuditLog, registro de acessos
│   └── core/                ← views genéricas, home, utilitários
├── templates/               ← HTML base + por app
├── static/                  ← CSS do Streamlit migrado + assets IFG
└── media/                   ← PDFs e uploads (NUNCA no git)
```

---

## Modelos de dados — schema SQLite atual → Django

### Tabela `usuarios` → app `usuarios`, model `Usuario`
- CPF é o identificador principal (username do Django Auth)
- Campo `perfil` vira grupos Django: "candidato", "admin_rh"
- Campo `aceite_lgpd` vira `lgpd_aceito_em` (DateTimeField) +
  `lgpd_versao_termo` (CharField)

### Tabela `sessoes` → substituída por Django sessions nativo
- Django cuida disso automaticamente
- Adicionar `SESSION_COOKIE_AGE` e expiração

### Tabela `inscricoes` → app `inscricoes`, model `Inscricao`
- Um candidato, uma inscrição por edital (adicionar FK para Edital no futuro)
- Status (StatusInscricao): "pendente", "completa", "em_analise",
  "aprovada", "indeferida"

### Tabela `inscricao_itens` → model `InscricaoItem`
- Chave composta (cpf, item_id) vira FK para Inscricao + campo `item_id`
- Pontuação validada no backend — nunca confiar no cliente

### Nova tabela `AuditLog` → app `auditoria`
- Campos: usuario, acao, recurso, detalhe, ip, timestamp
- Ações registradas: LOGIN, LOGOUT, CADASTRO, ALTERACAO_PONTUACAO,
  UPLOAD_PDF, DOWNLOAD_PDF_ADMIN, EXPORT_CSV, EXCLUSAO_DADOS

---

## Constantes de negócio (vêm do Streamlit)

`QUADROS_INSCRICAO` — dict Python com critérios, regras e pontuação
máxima por modalidade (Servidor, Estudante, Colaborador Externo).

**Decisão tomada:** manter como constante Python em
`apps/inscricoes/quadros.py` por enquanto. Virar tabela de banco
apenas quando houver necessidade de edição sem deploy (futuros editais).

---

## Regras de operação — Claude Code deve seguir sempre

### Antes de qualquer mudança
1. `git status` — verificar estado atual
2. `view` nos arquivos que serão afetados
3. Comunicar o que vai mudar e pedir OK para mudanças destrutivas

### Estrutura de branches
```
main          ← código estável, sempre funcionando
fase-1-setup  ← setup inicial do Django
fase-2-models ← modelos de dados e migrations
fase-3-auth   ← autenticação e cadastro
fase-4-admin  ← área administrativa Django Admin
fase-5-inscricao ← telas de inscrição e pontuação
fase-6-seguranca ← hardening de produção
fase-7-deploy    ← configuração de VM e nginx
```
Cada fase = 1 branch. Merge para main só após revisão do Prof. Flávio.

### Arquivos que NUNCA devem ser tocados sem autorização explícita
- `data/` — pode conter dados pessoais reais de candidatos (LGPD)
- `app.py` — Streamlit original em produção durante migração
- `.env` — variáveis de ambiente com segredos

### Arquivos que NUNCA vão para o git
```
.env
data/
media/
*.db
__pycache__/
venv/
*.pyc
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
source django_app/.venv/bin/activate

# Rodar localmente
python manage.py runserver

# Migrations após alterar models
python manage.py makemigrations
python manage.py migrate

# Criar superusuário admin
python manage.py createsuperuser

# Rodar testes
python manage.py test

# Abrir túnel para testes com o time
ngrok http 8000

# Verificar segurança antes de deploy
python manage.py check --deploy

# Coletar arquivos estáticos para produção
python manage.py collectstatic
```

---

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

**Manutenção em produção.** O sistema está no ar; as tarefas agora são
ajustes pontuais e correções pedidas pelo Prof. Flávio.

Concluído recentemente (em produção): fórmula da nota validada na revisão
RH, Servidor Apoio Técnico passando a usar o quadro do Pesquisador, quadro
do Colaborador Externo conforme o Edital PROPPG 30/2026, reabertura de
formulário em status "Pendente", troca de categoria recarregando o quadro
certo, PDF obrigatório no envio (com aviso para anexar o comprovante do
IFGProduz quando a API falha), aposentadoria dos critérios antigos do
Servidor/Apoio Técnico e link do edital por modalidade na página de
inscrição.

Pendências menores em aberto:
- Atualizar os testes de contagem de critérios em
  `apps/inscricoes/tests.py` (desatualizados após a revisão dos quadros).
- Investigar o aviso de "model drift" que o `migrate` mostra na VM
  (mudanças de model sem migration) — **nunca** rodar `makemigrations`
  direto em produção; criar a migration no dev, commitar e dar pull.

Ver skill `django-ifg` para os padrões de código e referências por domínio.
