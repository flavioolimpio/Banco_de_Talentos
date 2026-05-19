# Banco de Talentos IFG - Django

Migração gradual da aplicação Streamlit para Django.

## Rodar localmente

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

No Linux:

```bash
source .venv/bin/activate
python manage.py check
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

## Configuracao

Copie `.env.example` para `.env` e ajuste os valores locais.

Em producao, use:

```bash
DJANGO_SETTINGS_MODULE=config.settings.prod
```

## Dados sensiveis

Arquivos `.env`, banco local, uploads e `media/` nao devem ser versionados.

PDFs de comprovantes serao servidos futuramente por views autenticadas, nunca por URL publica direta.
