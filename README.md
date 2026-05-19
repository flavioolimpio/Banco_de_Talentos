# Banco de Talentos — Polo de Inovação IFG

Sistema web para cadastro de candidatos e gestão de inscrições em
editais do Polo de Inovação do Instituto Federal de Goiás.

**Responsável:** Prof. Flávio (RH do Polo EMBRAPII IFG)  
**Contexto:** Etapa 0 do workflow EMBRAPII — banco de especialistas

---

## Versão atual

| Versão | Tecnologia | Status |
|--------|-----------|--------|
| 1.0 (legado) | Streamlit (`app.py`) | Em uso |
| 2.0 (nova) | Django (`django_app/`) | Em construção |

Durante a migração, ambas coexistem na mesma pasta.
O Streamlit original **não deve ser modificado** enquanto estiver em produção.

---

## Rodar localmente (Django)

```bash
# 1. Ativar ambiente
source django_app/venv/bin/activate

# 2. Rodar
cd django_app
python manage.py runserver

# Acesse: http://localhost:8000
```

## Compartilhar com testadores (ngrok)

```bash
# Terminal 1 — Django rodando
python manage.py runserver

# Terminal 2 — túnel público temporário
ngrok http 8000
# Cole a URL gerada no grupo do time
```

---

## Estrutura de arquivos

```
.
├── app.py                    ← Streamlit original (NÃO MODIFICAR)
├── data/                     ← Banco SQLite + PDFs (NÃO COMMITAR)
├── imagens/                  ← Assets visuais IFG
├── django_app/               ← Nova versão Django
│   ├── apps/
│   │   ├── usuarios/         ← Autenticação, cadastro, LGPD
│   │   ├── inscricoes/       ← Inscrições e pontuação
│   │   ├── auditoria/        ← Logs de auditoria
│   │   └── core/             ← Home, utilitários
│   ├── config/settings/      ← base.py, dev.py, prod.py
│   ├── templates/            ← HTML
│   └── static/               ← CSS + assets
├── docs/
│   └── guia-ti-ifg.md        ← Instruções para a TI do IFG
├── CLAUDE.md                 ← Contexto para Claude Code
├── AGENTS.md                 ← Regras para agentes de IA
└── .claude/skills/           ← Skills do projeto
    └── django-ifg/
        ├── SKILL.md
        └── references/
```

---

## Documentação

- `CLAUDE.md` — contexto completo para Claude Code (decisões técnicas, stack, regras)
- `AGENTS.md` — regras de operação para qualquer agente de IA
- `docs/guia-ti-ifg.md` — instruções de deploy e manutenção para a TI do IFG
- `.claude/skills/django-ifg/` — skill de desenvolvimento Django para Claude Code

---

## Conformidade

- **LGPD** (Lei 13.709/2018) — dados pessoais de candidatos
- **EMBRAPII** — normas operacionais do polo
- **IFG** — políticas institucionais de TI e segurança da informação
