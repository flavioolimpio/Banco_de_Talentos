# Spec: Fase 6 — Hardening de Segurança
**Data:** 2026-05-19
**Branch:** fase-6-seguranca
**Status:** aprovado

---

## Contexto

As fases 3–5 entregaram autenticação, admin e telas de inscrição com 56 testes passando.
A Fase 6 fecha as lacunas de segurança antes do deploy na VM do IFG:

1. PDFs de comprovantes expostos via URL pública
2. `check --deploy` não verificado formalmente
3. Ausência de Content Security Policy

Deploy na VM é para mais adiante; esta fase ainda é em ambiente de desenvolvimento local.

---

## Escopo

### 1. PDF Protegido

**Problema:** `/media/comprovantes/<modalidade>/<cpf>/comprovantes.pdf` é acessível
sem autenticação por qualquer pessoa que conheça ou adivinhe a URL. Viola LGPD.

**Solução:**

- Nova URL: `GET /inscricoes/<pk>/comprovante/`
- Nova view `download_comprovante(request, pk)` em `apps/inscricoes/views.py`:
  - `@login_required` + verifica `request.user.is_staff` (403 se não for staff)
  - Busca `Inscricao` pelo `pk`; 404 se não existir ou não tiver PDF
  - Registra `AuditLog` com `acao=AuditAction.COMPROVANTE_DOWNLOAD`, IP, user_agent,
    `detalhes={"inscricao_id": pk, "arquivo": nome_original}`
  - Retorna `FileResponse(open(path, "rb"), as_attachment=True, filename=nome_original)`
- Link "Baixar PDF" no `InscricaoAdmin` (campo calculado `pdf_download_link` no
  `readonly_fields` da tela de detalhe)
- Remover serving direto de mídia do `config/urls.py`:
  - Retirar `+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)`
  - Sem isso, `/media/` retorna 404 — o único caminho é a view protegida

**Fora do escopo:** candidatos baixarem o próprio PDF (fase futura se necessário).

**Permissão:** `is_staff=True`. Não cria novo grupo — staff já equivale à equipe de RH
que usa o Admin.

---

### 2. `check --deploy` sem erros

**Objetivo:** `python manage.py check --deploy --settings=config.settings.prod`
terminar com `System check identified no issues (0 silenced)`.

**Processo:**
1. Rodar o comando e capturar todos os avisos
2. Corrigir item a item em `prod.py` (e `base.py` se aplicável)
3. Rodar novamente até passar limpo

Correções esperadas (baseadas no que já está em `prod.py`):
- `CSRF_COOKIE_HTTPONLY = True` — provável ausente
- `SESSION_COOKIE_HTTPONLY = True` — Django padrão é True, mas melhor declarar explicitamente
- Qualquer outro aviso que aparecer

---

### 3. Content Security Policy (CSP)

**Pacote:** `django-csp` (Mozilla) — padrão do ecossistema Django para CSP.

**Pré-requisito:** mover script inline de `formulario.html` para arquivo estático.

#### 3a. Extração do script inline

`formulario.html` tem um `<script>` IIFE inline que calcula o total de pontuação.
Mover para `static/js/inscricao_form.js` e referenciar com:
```html
<script src="{% static 'js/inscricao_form.js' %}"></script>
```

Nenhuma outra mudança de comportamento — o JS é idêntico, só muda onde fica.

#### 3b. Configuração em `prod.py`

```python
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC  = ("'self'",)           # sem unsafe-inline
CSP_STYLE_SRC   = ("'self'", "'unsafe-inline'")  # templates usam style=""
CSP_IMG_SRC     = ("'self'", "data:")
CSP_FONT_SRC    = ("'self'",)
CSP_FRAME_ANCESTORS = ("'none'",)       # reforça X-Frame-Options DENY
```

`'unsafe-inline'` em estilos é aceitável: CSS injection não executa código arbitrário
e reescrever centenas de `style=""` inline nos templates seria impacto desproporcional.

#### 3c. Configuração em `dev.py`

```python
CSP_REPORT_ONLY = True  # reporta violações no console sem bloquear
```

Permite detectar violações durante desenvolvimento sem quebrar a aplicação.

#### 3d. Middleware

Adicionar `csp.middleware.CSPMiddleware` em `MIDDLEWARE` no `base.py`,
logo após `SecurityMiddleware`.

---

## Testes

| # | Teste | Onde |
|---|-------|------|
| 1 | GET `/inscricoes/<pk>/comprovante/` sem login → redirect para `/login/` | `InscricaoDownloadTest` |
| 2 | GET com usuário não-staff → 403 | `InscricaoDownloadTest` |
| 3 | GET com staff sem PDF na inscrição → 404 | `InscricaoDownloadTest` |
| 4 | GET com staff e PDF presente → 200, Content-Disposition com nome do arquivo | `InscricaoDownloadTest` |
| 5 | GET com staff → AuditLog registrado com ação COMPROVANTE_DOWNLOAD | `InscricaoDownloadTest` |
| 6 | GET `/media/comprovantes/...` direto → 404 (mídia não servida) | `InscricaoDownloadTest` |

`check --deploy` e CSP não têm testes unitários — verificados via comando e inspeção
de cabeçalhos HTTP respectivamente.

---

## Arquivos afetados

| Arquivo | Mudança |
|---------|---------|
| `apps/inscricoes/views.py` | + `download_comprovante` view |
| `apps/inscricoes/urls.py` | + rota `inscricoes/<pk>/comprovante/` |
| `apps/inscricoes/admin.py` | + `pdf_download_link` em `readonly_fields` |
| `apps/inscricoes/tests.py` | + `InscricaoDownloadTest` (6 testes) |
| `config/urls.py` | remover `static()` de mídia |
| `config/settings/base.py` | + `csp.middleware.CSPMiddleware` em MIDDLEWARE |
| `config/settings/prod.py` | + `CSRF_COOKIE_HTTPONLY`, `SESSION_COOKIE_HTTPONLY`, CSP settings |
| `config/settings/dev.py` | + `CSP_REPORT_ONLY = True` |
| `static/js/inscricao_form.js` | novo arquivo (JS extraído do template) |
| `templates/inscricoes/formulario.html` | substituir `<script>` inline por `<script src>` |
| `requirements.txt` | + `django-csp` |

---

## Fora do escopo desta fase

- Configuração de nginx / gunicorn (Fase 7)
- E-mail de produção (Fase 7)
- Rate limiting adicional (django-axes já cobre brute-force de login)
- Candidatos acessando o próprio PDF
- django-ratelimit em outras views
