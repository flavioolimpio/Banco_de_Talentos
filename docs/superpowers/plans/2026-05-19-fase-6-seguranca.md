# Fase 6 — Hardening de Segurança: Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fechar três lacunas de segurança: PDFs protegidos por autenticação, `check --deploy` sem avisos, e CSP sem `unsafe-inline` em scripts.

**Architecture:** View protegida para download de PDFs com AuditLog; correção pontual em `prod.py`; extração do JS inline para arquivo estático + `django-csp` via middleware.

**Tech Stack:** Django 5.2, django-csp 3.8, FileResponse, `manage.py check --deploy`

---

## Mapa de arquivos

| Arquivo | Ação |
|---------|------|
| `apps/inscricoes/tests.py` | + `InscricaoDownloadTest` (6 testes) |
| `apps/inscricoes/urls.py` | + rota `inscricoes/<pk>/comprovante/` |
| `apps/inscricoes/views.py` | + `download_comprovante` view |
| `apps/inscricoes/admin.py` | + `pdf_download_link` em `readonly_fields` |
| `config/settings/prod.py` | + `CSRF_COOKIE_HTTPONLY`, CSP settings |
| `config/settings/dev.py` | + `CSP_REPORT_ONLY = True` |
| `config/settings/base.py` | + `csp.middleware.CSPMiddleware` em MIDDLEWARE |
| `static/js/inscricao_form.js` | criar — JS extraído do template |
| `templates/inscricoes/formulario.html` | substituir `<script>` inline por `<script src>` |
| `requirements.txt` | + `django-csp==3.8` |

---

## Task 1: View protegida de download de PDF

**Arquivos:**
- Modificar: `apps/inscricoes/tests.py`
- Modificar: `apps/inscricoes/urls.py`
- Modificar: `apps/inscricoes/views.py`
- Modificar: `apps/inscricoes/admin.py`

- [ ] **Passo 1: Escrever os testes que vão falhar**

Adicionar ao final de `django_app/apps/inscricoes/tests.py`:

```python
class InscricaoDownloadTest(TestCase):
    def setUp(self):
        call_command("popular_criterios", verbosity=0)
        self.staff_user = Usuario.objects.create_user(
            cpf="52998224725",
            email="rh@ifg.edu.br",
            nome_completo="RH Staff",
            password="senha123",
            is_staff=True,
        )
        self.candidato = Usuario.objects.create_user(
            cpf="11144477735",
            email="candidato@test.com",
            nome_completo="Candidato Teste",
            vinculo=Vinculo.ESTUDANTE,
            password="senha123",
        )
        self.inscricao = Inscricao.objects.create(
            usuario=self.candidato,
            modalidade="estudante",
            status=StatusInscricao.EM_ANALISE,
            enviada_em=timezone.now(),
        )

    def _url(self):
        return reverse("download_comprovante", args=[self.inscricao.pk])

    def _add_pdf(self):
        from django.core.files.base import ContentFile
        self.inscricao.comprovantes_pdf.save(
            "comp.pdf", ContentFile(b"%PDF-1.4 ok"), save=False
        )
        self.inscricao.comprovantes_pdf_nome_original = "comp.pdf"
        self.inscricao.save()

    def test_sem_login_redireciona(self):
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response["Location"])

    def test_nao_staff_retorna_403(self):
        self.client.force_login(self.candidato)
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 403)

    def test_sem_pdf_retorna_404(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 404)

    def test_com_pdf_retorna_200_e_content_disposition(self):
        self._add_pdf()
        self.client.force_login(self.staff_user)
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200)
        self.assertIn("comp.pdf", response.get("Content-Disposition", ""))

    def test_com_pdf_registra_auditlog(self):
        from apps.auditoria.models import AuditAction, AuditLog
        self._add_pdf()
        self.client.force_login(self.staff_user)
        self.client.get(self._url())
        self.assertTrue(
            AuditLog.objects.filter(acao=AuditAction.COMPROVANTE_DOWNLOAD).exists()
        )

    def test_media_direta_retorna_404(self):
        response = self.client.get("/media/comprovantes/estudante/11144477735/comp.pdf")
        self.assertEqual(response.status_code, 404)
```

- [ ] **Passo 2: Rodar os testes para confirmar que falham**

```powershell
Set-Location "C:\Users\user\Documents\GitHub\Banco_de_Talentos\django_app"
& ".\.venv\Scripts\python.exe" manage.py test apps.inscricoes.tests.InscricaoDownloadTest --verbosity=2
```

Esperado: `NoReverseMatch` ou `AttributeError` — `download_comprovante` não existe.

- [ ] **Passo 3: Adicionar a URL em `apps/inscricoes/urls.py`**

Substituir o conteúdo completo do arquivo:

```python
# apps/inscricoes/urls.py
# Banco de Talentos — Polo de Inovação IFG
# URL patterns da área de inscrição do candidato.

from django.urls import path

from apps.inscricoes import views

urlpatterns = [
    path("inscricao/", views.inscricao_view, name="inscricao"),
    path("inscricao/confirmacao/", views.confirmacao_view, name="inscricao_confirmacao"),
    path("inscricoes/<int:pk>/comprovante/", views.download_comprovante, name="download_comprovante"),
]
```

- [ ] **Passo 4: Implementar a view em `apps/inscricoes/views.py`**

Adicionar ao final do arquivo (após `confirmacao_view`):

```python
@login_required
def download_comprovante(request, pk):
    if not request.user.is_staff:
        raise PermissionDenied
    inscricao = get_object_or_404(Inscricao, pk=pk)
    if not inscricao.comprovantes_pdf:
        raise Http404("Esta inscrição não possui comprovante em PDF.")
    AuditLog.objects.create(
        ator=request.user,
        acao=AuditAction.COMPROVANTE_DOWNLOAD,
        ip=_get_client_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
        detalhes={
            "inscricao_id": pk,
            "arquivo": inscricao.comprovantes_pdf_nome_original,
        },
    )
    return FileResponse(
        inscricao.comprovantes_pdf.open("rb"),
        as_attachment=True,
        filename=inscricao.comprovantes_pdf_nome_original or "comprovantes.pdf",
    )
```

Adicionar os imports que faltam no topo de `views.py` (junto aos existentes):

```python
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
```

- [ ] **Passo 5: Adicionar link de download no `InscricaoAdmin`**

Em `apps/inscricoes/admin.py`, adicionar imports no topo (junto aos existentes):

```python
from django.urls import reverse
from django.utils.html import format_html
```

Substituir a classe `InscricaoAdmin` inteira:

```python
@admin.register(Inscricao)
class InscricaoAdmin(admin.ModelAdmin):
    list_display = ("usuario", "modalidade", "tipo_servidor", "total", "status", "atualizado_em")
    list_filter = ("modalidade", "tipo_servidor", "status")
    search_fields = ("usuario__cpf", "usuario__nome_completo", "usuario__email")
    readonly_fields = ("criado_em", "atualizado_em", "enviada_em", "pdf_download_link")
    inlines = [InscricaoItemInline]
    actions = ["aprovar_selecionadas", "reprovar_selecionadas", "marcar_em_analise", "exportar_csv"]

    def pdf_download_link(self, obj):
        if not obj.comprovantes_pdf:
            return "—"
        url = reverse("download_comprovante", args=[obj.pk])
        return format_html('<a href="{}" target="_blank">⬇ Baixar PDF</a>', url)
    pdf_download_link.short_description = "Comprovantes"

    @admin.action(description="Aprovar inscrições selecionadas")
    def aprovar_selecionadas(self, request, queryset):
        atualizadas = queryset.update(status=StatusInscricao.APROVADA)
        self.message_user(request, f"{atualizadas} inscrição(ões) aprovada(s).", messages.SUCCESS)

    @admin.action(description="Reprovar inscrições selecionadas")
    def reprovar_selecionadas(self, request, queryset):
        atualizadas = queryset.update(status=StatusInscricao.INDEFERIDA)
        self.message_user(request, f"{atualizadas} inscrição(ões) indeferida(s).", messages.WARNING)

    @admin.action(description="Marcar como Em análise")
    def marcar_em_analise(self, request, queryset):
        atualizadas = queryset.update(status=StatusInscricao.EM_ANALISE)
        self.message_user(request, f"{atualizadas} inscrição(ões) marcada(s) como Em análise.", messages.INFO)

    @admin.action(description="Exportar selecionadas como CSV")
    def exportar_csv(self, request, queryset):
        from apps.auditoria.models import AuditAction, AuditLog
        AuditLog.objects.create(
            ator=request.user,
            acao=AuditAction.CSV_EXPORTADO,
            detalhes={"total": queryset.count()},
            ip=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )
        return _exportar_inscricoes_csv(queryset)
```

- [ ] **Passo 6: Rodar os testes para confirmar que passam**

```powershell
Set-Location "C:\Users\user\Documents\GitHub\Banco_de_Talentos\django_app"
& ".\.venv\Scripts\python.exe" manage.py test apps.inscricoes.tests.InscricaoDownloadTest --verbosity=2
```

Esperado: `Ran 6 tests ... OK`

- [ ] **Passo 7: Rodar a suíte completa**

```powershell
& ".\.venv\Scripts\python.exe" manage.py test --verbosity=1
```

Esperado: `Ran 62 tests ... OK`

- [ ] **Passo 8: Commit**

```powershell
git add django_app/apps/inscricoes/tests.py `
        django_app/apps/inscricoes/urls.py `
        django_app/apps/inscricoes/views.py `
        django_app/apps/inscricoes/admin.py
git commit -m "feat: view protegida de download de PDF com AuditLog"
```

---

## Task 2: `check --deploy` sem avisos

**Arquivos:**
- Modificar: `config/settings/prod.py`

- [ ] **Passo 1: Rodar `check --deploy` com settings de produção**

```powershell
Set-Location "C:\Users\user\Documents\GitHub\Banco_de_Talentos\django_app"
$env:SECRET_KEY = "check-deploy-dummy-key-nao-usar-em-producao-123456789"
$env:ALLOWED_HOSTS = "banco-talentos.ifg.edu.br"
$env:DJANGO_READ_DOT_ENV_FILE = "false"
& ".\.venv\Scripts\python.exe" manage.py check --deploy --settings=config.settings.prod
```

Esperado: aviso sobre `CSRF_COOKIE_HTTPONLY`:
```
?: (security.W003) You have not set CSRF_COOKIE_HTTPONLY to True.
```

- [ ] **Passo 2: Corrigir `config/settings/prod.py`**

Substituir o conteúdo completo do arquivo:

```python
from .base import *  # noqa: F403


DEBUG = False

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
```

- [ ] **Passo 3: Rodar novamente e confirmar zero avisos**

```powershell
$env:SECRET_KEY = "check-deploy-dummy-key-nao-usar-em-producao-123456789"
$env:ALLOWED_HOSTS = "banco-talentos.ifg.edu.br"
$env:DJANGO_READ_DOT_ENV_FILE = "false"
& ".\.venv\Scripts\python.exe" manage.py check --deploy --settings=config.settings.prod
```

Esperado:
```
System check identified no issues (0 silenced).
```

Se aparecer algum aviso inesperado além de `CSRF_COOKIE_HTTPONLY`, registrar aqui e
adicionar a configuração correspondente em `prod.py` antes de continuar.

- [ ] **Passo 4: Commit**

```powershell
git add django_app/config/settings/prod.py
git commit -m "fix: CSRF_COOKIE_HTTPONLY e SESSION_COOKIE_HTTPONLY em prod — check --deploy limpo"
```

---

## Task 3: Content Security Policy

**Arquivos:**
- Criar: `static/js/inscricao_form.js`
- Modificar: `templates/inscricoes/formulario.html`
- Modificar: `config/settings/base.py`
- Modificar: `config/settings/prod.py`
- Modificar: `config/settings/dev.py`
- Modificar: `requirements.txt`

- [ ] **Passo 1: Instalar `django-csp`**

```powershell
Set-Location "C:\Users\user\Documents\GitHub\Banco_de_Talentos\django_app"
& ".\.venv\Scripts\pip.exe" install "django-csp==3.8"
```

Esperado: `Successfully installed django-csp-3.8`

- [ ] **Passo 2: Atualizar `requirements.txt`**

Adicionar uma linha ao final de `django_app/requirements.txt`:

```
django-csp==3.8
```

- [ ] **Passo 3: Criar `static/js/inscricao_form.js`**

Criar o arquivo `django_app/static/js/inscricao_form.js` com o conteúdo:

```javascript
(function () {
    function updateTotal() {
        var inputs = document.querySelectorAll('[data-score]');
        var total = 0;
        inputs.forEach(function (el) {
            var val = parseFloat(el.value) || 0;
            var max = parseFloat(el.dataset.max) || 0;
            total += Math.min(Math.max(val, 0), max);
        });
        var display = document.getElementById('total-display');
        if (display) {
            display.textContent = total.toFixed(1).replace('.', ',');
        }
    }
    document.querySelectorAll('[data-score]').forEach(function (el) {
        el.addEventListener('input', updateTotal);
    });
    updateTotal();
}());
```

- [ ] **Passo 4: Atualizar `templates/inscricoes/formulario.html`**

Substituir o bloco `<script>` inline (linhas finais do arquivo, antes de `{% endblock %}`):

Remover:
```html
<script>
(function () {
    function updateTotal() {
        var inputs = document.querySelectorAll('[data-score]');
        var total = 0;
        inputs.forEach(function (el) {
            var val = parseFloat(el.value) || 0;
            var max = parseFloat(el.dataset.max) || 0;
            total += Math.min(Math.max(val, 0), max);
        });
        var display = document.getElementById('total-display');
        if (display) {
            display.textContent = total.toFixed(1).replace('.', ',');
        }
    }
    document.querySelectorAll('[data-score]').forEach(function (el) {
        el.addEventListener('input', updateTotal);
    });
    updateTotal();
}());
</script>
```

Adicionar no lugar (após o `{% endif %}` que fecha `{% if not criterios_com_score %}`):

```html
{% load static %}
<script src="{% static 'js/inscricao_form.js' %}"></script>
```

A tag `{% load static %}` pode ficar no topo do arquivo logo abaixo de `{% extends "base.html" %}` se preferir — o importante é estar antes do `{% static %}`.

- [ ] **Passo 5: Adicionar `CSPMiddleware` em `config/settings/base.py`**

Localizar `MIDDLEWARE` e adicionar `"csp.middleware.CSPMiddleware"` na segunda posição
(logo após `SecurityMiddleware`):

```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "csp.middleware.CSPMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "axes.middleware.AxesMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
]
```

- [ ] **Passo 6: Adicionar configurações CSP em `config/settings/prod.py`**

Acrescentar ao final do arquivo (após `X_FRAME_OPTIONS`):

```python
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'",)
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")
CSP_IMG_SRC = ("'self'", "data:")
CSP_FONT_SRC = ("'self'",)
CSP_FRAME_ANCESTORS = ("'none'",)
```

- [ ] **Passo 7: Adicionar modo report-only em `config/settings/dev.py`**

Substituir o conteúdo completo do arquivo:

```python
from .base import *  # noqa: F403


DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0", "testserver"]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

CSP_REPORT_ONLY = True
```

- [ ] **Passo 8: Rodar a suíte completa**

```powershell
Set-Location "C:\Users\user\Documents\GitHub\Banco_de_Talentos\django_app"
& ".\.venv\Scripts\python.exe" manage.py test --verbosity=1
```

Esperado: `Ran 62 tests ... OK`

- [ ] **Passo 9: Verificar o header CSP no servidor de desenvolvimento**

```powershell
& ".\.venv\Scripts\python.exe" manage.py runserver
```

Em outro terminal:

```powershell
Invoke-WebRequest -Uri "http://localhost:8000/login/" -Method GET |
    Select-Object -ExpandProperty Headers |
    Where-Object { $_.Keys -match "Content-Security" }
```

Esperado: header `Content-Security-Policy-Report-Only` presente (modo dev = report-only).

- [ ] **Passo 10: Commit**

```powershell
git add django_app/requirements.txt `
        django_app/static/js/inscricao_form.js `
        django_app/templates/inscricoes/formulario.html `
        django_app/config/settings/base.py `
        django_app/config/settings/prod.py `
        django_app/config/settings/dev.py
git commit -m "feat: CSP via django-csp, JS inline extraido para arquivo estatico"
```
