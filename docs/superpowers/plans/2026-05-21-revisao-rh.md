# Interface de Revisão RH — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Criar interface de revisão para o time de RH validar inscrições critério a critério, registrar parecer e tomar decisão (aprovada/indeferida), com PDF embutido lado a lado.

**Architecture:** Admin Django já existente recebe coluna "Revisar →"; nova view `revisao_view` em `/rh/inscricoes/<pk>/revisar/` protegida por `@staff_member_required` renderiza layout dividido (PDF iframe + formulário de critérios); ao submeter, persiste `pontuacao_validada`, `observacao_avaliacao`, `parecer_geral`, muda status e registra `AuditLog`.

**Tech Stack:** Django 5.x, Python 3.12, SQLite (dev), `django.contrib.admin`, `simple_history`, `apps.auditoria.models.AuditLog`

---

## Mapa de arquivos

| Arquivo | Ação | Responsabilidade |
|---|---|---|
| `apps/inscricoes/models.py` | Modificar | +4 campos em `Inscricao` |
| `apps/inscricoes/migrations/` | Criar | Migration para os 4 campos |
| `apps/auditoria/models.py` | Modificar | +`INSCRICAO_REVISADA` em `AuditAction` |
| `apps/inscricoes/forms_rh.py` | Criar | `RevisaoForm` com validação de parecer |
| `apps/inscricoes/views_rh.py` | Criar | `revisao_view` + `view_comprovante` |
| `apps/inscricoes/urls.py` | Modificar | +2 rotas `/rh/` |
| `templates/rh/revisao.html` | Criar | Template com layout dividido |
| `apps/inscricoes/admin.py` | Modificar | +coluna `link_revisar` |
| `apps/inscricoes/tests.py` | Modificar | +testes para model, form e views |

---

## Task 1: Campos no model + AuditAction + migration

**Files:**
- Modify: `django_app/apps/inscricoes/models.py`
- Modify: `django_app/apps/auditoria/models.py`
- Create: `django_app/apps/inscricoes/migrations/` (auto-gerado)
- Test: `django_app/apps/inscricoes/tests.py`

- [ ] **Step 1: Escrever os testes que vão falhar**

Adicione ao final de `django_app/apps/inscricoes/tests.py`:

```python
class InscricaoNovoCamposTest(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user(
            cpf="11144477735",
            email="cand@test.com",
            nome_completo="Candidato",
            vinculo="estudante",
            password="Pass123!",
        )
        self.inscricao = Inscricao.objects.create(
            usuario=self.usuario,
            modalidade="estudante",
        )

    def test_total_validado_default_zero(self):
        self.assertEqual(self.inscricao.total_validado, Decimal("0"))

    def test_parecer_geral_default_vazio(self):
        self.assertEqual(self.inscricao.parecer_geral, "")

    def test_revisado_em_default_none(self):
        self.assertIsNone(self.inscricao.revisado_em)

    def test_revisado_por_default_none(self):
        self.assertIsNone(self.inscricao.revisado_por)

    def test_auditaction_inscricao_revisada_existe(self):
        from apps.auditoria.models import AuditAction
        self.assertIn("inscricao_revisada", [c for c, _ in AuditAction.choices])
```

- [ ] **Step 2: Rodar os testes — verificar que falham**

```powershell
cd django_app
.\.venv\Scripts\python.exe manage.py test apps.inscricoes.tests.InscricaoNovoCamposTest --verbosity 2
```

Esperado: FAIL — campos não existem ainda.

- [ ] **Step 3: Adicionar os 4 campos ao model `Inscricao`**

Em `django_app/apps/inscricoes/models.py`, após o campo `total`:

```python
    total_validado = models.DecimalField(
        "pontuação total validada", max_digits=9, decimal_places=2, default=0
    )
    parecer_geral = models.TextField("parecer geral", blank=True)
    revisado_em = models.DateTimeField("revisado em", null=True, blank=True)
    revisado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inscricoes_revisadas",
        verbose_name="revisado por",
    )
```

- [ ] **Step 4: Adicionar `INSCRICAO_REVISADA` ao `AuditAction`**

Em `django_app/apps/auditoria/models.py`, adicione dentro de `AuditAction`:

```python
    INSCRICAO_REVISADA = "inscricao_revisada", "Inscrição revisada"
```

- [ ] **Step 5: Gerar e aplicar a migration**

```powershell
.\.venv\Scripts\python.exe manage.py makemigrations inscricoes
.\.venv\Scripts\python.exe manage.py migrate
```

Esperado: `Migrations for 'inscricoes': ... 0005_inscricao_parecer_geral_...`

- [ ] **Step 6: Rodar os testes — verificar que passam**

```powershell
.\.venv\Scripts\python.exe manage.py test apps.inscricoes.tests.InscricaoNovoCamposTest --verbosity 2
```

Esperado: 5 testes PASS.

- [ ] **Step 7: Commit**

```powershell
git add apps/inscricoes/models.py apps/auditoria/models.py apps/inscricoes/migrations/ apps/inscricoes/tests.py
git commit -m "feat: campos total_validado, parecer_geral, revisado_em, revisado_por em Inscricao"
```

---

## Task 2: forms_rh.py

**Files:**
- Create: `django_app/apps/inscricoes/forms_rh.py`
- Test: `django_app/apps/inscricoes/tests.py`

- [ ] **Step 1: Escrever os testes que vão falhar**

Adicione ao final de `django_app/apps/inscricoes/tests.py`:

```python
class RevisaoFormTest(TestCase):
    def test_aprovar_sem_parecer_valido(self):
        from apps.inscricoes.forms_rh import RevisaoForm
        form = RevisaoForm({"parecer_geral": ""}, acao="aprovar")
        self.assertTrue(form.is_valid())

    def test_indeferir_sem_parecer_invalido(self):
        from apps.inscricoes.forms_rh import RevisaoForm
        form = RevisaoForm({"parecer_geral": ""}, acao="indeferir")
        self.assertFalse(form.is_valid())
        self.assertIn("parecer_geral", form.errors)

    def test_indeferir_com_parecer_valido(self):
        from apps.inscricoes.forms_rh import RevisaoForm
        form = RevisaoForm({"parecer_geral": "Documentação incompleta."}, acao="indeferir")
        self.assertTrue(form.is_valid())

    def test_parecer_so_espacos_invalido_ao_indeferir(self):
        from apps.inscricoes.forms_rh import RevisaoForm
        form = RevisaoForm({"parecer_geral": "   "}, acao="indeferir")
        self.assertFalse(form.is_valid())
```

- [ ] **Step 2: Rodar os testes — verificar que falham**

```powershell
.\.venv\Scripts\python.exe manage.py test apps.inscricoes.tests.RevisaoFormTest --verbosity 2
```

Esperado: FAIL — `forms_rh` não existe.

- [ ] **Step 3: Criar `apps/inscricoes/forms_rh.py`**

```python
# apps/inscricoes/forms_rh.py
# Banco de Talentos — Polo de Inovação IFG
# Formulário de revisão RH: parecer geral e decisão final.

from django import forms


class RevisaoForm(forms.Form):
    parecer_geral = forms.CharField(
        label="Parecer geral",
        widget=forms.Textarea(attrs={
            "rows": 3,
            "style": "width:100%;box-sizing:border-box;padding:6px 8px;border:1px solid #ccc;border-radius:6px;font-size:13px",
            "placeholder": "Registro da análise para o candidato...",
        }),
        required=False,
    )

    def __init__(self, *args, acao=None, **kwargs):
        self.acao = acao
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        if self.acao == "indeferir" and not cleaned.get("parecer_geral", "").strip():
            self.add_error("parecer_geral", "O parecer é obrigatório ao indeferir.")
        return cleaned
```

- [ ] **Step 4: Rodar os testes — verificar que passam**

```powershell
.\.venv\Scripts\python.exe manage.py test apps.inscricoes.tests.RevisaoFormTest --verbosity 2
```

Esperado: 4 testes PASS.

- [ ] **Step 5: Commit**

```powershell
git add apps/inscricoes/forms_rh.py apps/inscricoes/tests.py
git commit -m "feat: RevisaoForm com validacao de parecer obrigatorio ao indeferir"
```

---

## Task 3: views_rh.py + URLs

**Files:**
- Create: `django_app/apps/inscricoes/views_rh.py`
- Modify: `django_app/apps/inscricoes/urls.py`
- Test: `django_app/apps/inscricoes/tests.py`

- [ ] **Step 1: Escrever os testes que vão falhar**

Adicione ao final de `django_app/apps/inscricoes/tests.py`:

```python
from django.core.management import call_command


class RevisaoViewTest(TestCase):
    def setUp(self):
        call_command("popular_criterios", verbosity=0)
        self.revisor = User.objects.create_user(
            cpf="52998224725",
            email="revisor@ifg.edu.br",
            nome_completo="Revisor RH",
            password="Revisor123!",
            is_staff=True,
        )
        self.candidato = User.objects.create_user(
            cpf="11144477735",
            email="cand@test.com",
            nome_completo="João Silva",
            vinculo="estudante",
            password="Cand123!",
        )
        self.inscricao = Inscricao.objects.create(
            usuario=self.candidato,
            modalidade="estudante",
            status=StatusInscricao.EM_ANALISE,
            total=Decimal("30.00"),
        )
        from apps.inscricoes.models import InscricaoItem
        criterios = list(
            CriterioEdital.objects.filter(modalidade="estudante").order_by("ordem")
        )
        for c in criterios:
            InscricaoItem.objects.create(
                inscricao=self.inscricao,
                criterio=c,
                pontuacao=Decimal("5.00"),
            )
        self.url = f"/rh/inscricoes/{self.inscricao.pk}/revisar/"

    def _scores_post(self):
        from apps.inscricoes.models import InscricaoItem
        itens = InscricaoItem.objects.filter(inscricao=self.inscricao)
        return {f"validado_{item.pk}": "5.0" for item in itens}

    def test_get_requer_staff(self):
        self.client.login(username="11144477735", password="Cand123!")
        response = self.client.get(self.url)
        self.assertNotEqual(response.status_code, 200)

    def test_get_retorna_200_para_staff(self):
        self.client.login(username="52998224725", password="Revisor123!")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_get_inscricao_nao_em_analise_redireciona(self):
        self.inscricao.status = StatusInscricao.PENDENTE
        self.inscricao.save()
        self.client.login(username="52998224725", password="Revisor123!")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_post_aprovar_muda_status(self):
        self.client.login(username="52998224725", password="Revisor123!")
        data = {"parecer_geral": "", "acao": "aprovar", **self._scores_post()}
        self.client.post(self.url, data)
        self.inscricao.refresh_from_db()
        self.assertEqual(self.inscricao.status, StatusInscricao.APROVADA)

    def test_post_indeferir_muda_status(self):
        self.client.login(username="52998224725", password="Revisor123!")
        data = {"parecer_geral": "Docs incompletos.", "acao": "indeferir", **self._scores_post()}
        self.client.post(self.url, data)
        self.inscricao.refresh_from_db()
        self.assertEqual(self.inscricao.status, StatusInscricao.INDEFERIDA)

    def test_post_salva_total_validado(self):
        self.client.login(username="52998224725", password="Revisor123!")
        data = {"parecer_geral": "", "acao": "aprovar", **self._scores_post()}
        self.client.post(self.url, data)
        self.inscricao.refresh_from_db()
        self.assertGreater(self.inscricao.total_validado, 0)

    def test_post_salva_revisado_por(self):
        self.client.login(username="52998224725", password="Revisor123!")
        data = {"parecer_geral": "", "acao": "aprovar", **self._scores_post()}
        self.client.post(self.url, data)
        self.inscricao.refresh_from_db()
        self.assertEqual(self.inscricao.revisado_por, self.revisor)

    def test_post_registra_auditlog(self):
        from apps.auditoria.models import AuditAction, AuditLog
        self.client.login(username="52998224725", password="Revisor123!")
        data = {"parecer_geral": "", "acao": "aprovar", **self._scores_post()}
        self.client.post(self.url, data)
        self.assertTrue(
            AuditLog.objects.filter(acao=AuditAction.INSCRICAO_REVISADA).exists()
        )

    def test_post_indeferir_sem_parecer_retorna_form_com_erro(self):
        self.client.login(username="52998224725", password="Revisor123!")
        data = {"parecer_geral": "", "acao": "indeferir", **self._scores_post()}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)

    def test_post_silencio_usa_pontuacao_candidato(self):
        from apps.inscricoes.models import InscricaoItem
        self.client.login(username="52998224725", password="Revisor123!")
        # POST sem nenhum campo validado_ — silêncio = concordância
        data = {"parecer_geral": "", "acao": "aprovar"}
        self.client.post(self.url, data)
        item = InscricaoItem.objects.filter(inscricao=self.inscricao).first()
        item.refresh_from_db()
        self.assertEqual(item.pontuacao_validada, item.pontuacao)

    def test_view_comprovante_requer_staff(self):
        url = f"/rh/inscricoes/{self.inscricao.pk}/pdf/"
        self.client.login(username="11144477735", password="Cand123!")
        response = self.client.get(url)
        self.assertNotEqual(response.status_code, 200)
```

- [ ] **Step 2: Rodar os testes — verificar que falham**

```powershell
.\.venv\Scripts\python.exe manage.py test apps.inscricoes.tests.RevisaoViewTest --verbosity 2
```

Esperado: FAIL — views e URLs não existem.

- [ ] **Step 3: Criar `apps/inscricoes/views_rh.py`**

```python
# apps/inscricoes/views_rh.py
# Banco de Talentos — Polo de Inovação IFG
# Views de revisão de inscrições pelo time de RH.

from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.auditoria.models import AuditAction, AuditLog
from apps.inscricoes.forms_rh import RevisaoForm
from apps.inscricoes.models import Inscricao, StatusInscricao


def _get_client_ip(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _parse_validacoes(post_data, itens):
    validacoes = {}
    total = Decimal("0.00")
    for item in itens:
        raw = post_data.get(f"validado_{item.pk}", "").strip()
        obs = post_data.get(f"obs_{item.pk}", "").strip()
        if raw:
            try:
                valor = Decimal(raw.replace(",", "."))
            except InvalidOperation:
                valor = Decimal("0")
            valor = max(Decimal("0"), min(valor, item.criterio.maximo))
        else:
            valor = item.pontuacao
        validacoes[item.pk] = {"pontuacao_validada": valor, "observacao": obs}
        total += valor
    return validacoes, total


@staff_member_required
def revisao_view(request, pk):
    inscricao = get_object_or_404(Inscricao, pk=pk)

    if inscricao.status != StatusInscricao.EM_ANALISE:
        messages.warning(request, "Esta inscrição não está em análise e não pode ser revisada.")
        return redirect("admin:inscricoes_inscricao_changelist")

    itens = list(inscricao.itens.select_related("criterio").order_by("criterio__ordem"))

    if request.method == "GET":
        itens_com_score = [
            (item, item.pontuacao_validada if item.pontuacao_validada is not None else "")
            for item in itens
        ]
        return render(request, "rh/revisao.html", {
            "inscricao": inscricao,
            "itens_com_score": itens_com_score,
            "form": RevisaoForm(initial={"parecer_geral": inscricao.parecer_geral}),
        })

    acao = request.POST.get("acao", "")
    form = RevisaoForm(request.POST, acao=acao)

    if not form.is_valid():
        itens_com_score = [
            (item, request.POST.get(f"validado_{item.pk}", ""))
            for item in itens
        ]
        return render(request, "rh/revisao.html", {
            "inscricao": inscricao,
            "itens_com_score": itens_com_score,
            "form": form,
        })

    validacoes, total_validado = _parse_validacoes(request.POST, itens)

    with transaction.atomic():
        for item in itens:
            v = validacoes[item.pk]
            item.pontuacao_validada = v["pontuacao_validada"]
            item.observacao_avaliacao = v["observacao"]
            item.save(update_fields=["pontuacao_validada", "observacao_avaliacao"])

        inscricao.total_validado = total_validado
        inscricao.parecer_geral = form.cleaned_data["parecer_geral"]
        inscricao.revisado_em = timezone.now()
        inscricao.revisado_por = request.user
        inscricao.status = (
            StatusInscricao.APROVADA if acao == "aprovar" else StatusInscricao.INDEFERIDA
        )
        inscricao.save(update_fields=[
            "total_validado", "parecer_geral", "revisado_em", "revisado_por", "status",
        ])

        AuditLog.objects.create(
            ator=request.user,
            alvo=inscricao.usuario,
            acao=AuditAction.INSCRICAO_REVISADA,
            ip=_get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            detalhes={
                "inscricao_id": pk,
                "decisao": inscricao.get_status_display(),
                "total_validado": str(total_validado),
            },
        )

    messages.success(
        request,
        f"Inscrição de {inscricao.usuario.nome_completo} {inscricao.get_status_display().lower()}.",
    )
    return redirect("admin:inscricoes_inscricao_changelist")


@staff_member_required
def view_comprovante(request, pk):
    inscricao = get_object_or_404(Inscricao, pk=pk)
    if not inscricao.comprovantes_pdf:
        raise Http404
    return FileResponse(inscricao.comprovantes_pdf.open("rb"), content_type="application/pdf")
```

- [ ] **Step 4: Adicionar as rotas em `apps/inscricoes/urls.py`**

Substitua o conteúdo completo do arquivo por:

```python
# apps/inscricoes/urls.py
# Banco de Talentos — Polo de Inovação IFG
# URL patterns da área de inscrição do candidato e revisão do RH.

from django.urls import path

from apps.inscricoes import views, views_rh

urlpatterns = [
    path("inscricao/", views.inscricao_view, name="inscricao"),
    path("inscricao/confirmacao/", views.confirmacao_view, name="inscricao_confirmacao"),
    path("inscricoes/<int:pk>/comprovante/", views.download_comprovante, name="download_comprovante"),
    path("rh/inscricoes/<int:pk>/revisar/", views_rh.revisao_view, name="revisao_rh"),
    path("rh/inscricoes/<int:pk>/pdf/", views_rh.view_comprovante, name="view_comprovante"),
]
```

- [ ] **Step 5: Rodar os testes — verificar que passam**

```powershell
.\.venv\Scripts\python.exe manage.py test apps.inscricoes.tests.RevisaoViewTest --verbosity 2
```

Esperado: 11 testes PASS.

- [ ] **Step 6: Rodar a suíte completa — verificar que nada quebrou**

```powershell
.\.venv\Scripts\python.exe manage.py test apps.inscricoes --verbosity 2
```

Esperado: todos os testes existentes continuam PASS.

- [ ] **Step 7: Commit**

```powershell
git add apps/inscricoes/views_rh.py apps/inscricoes/urls.py apps/inscricoes/tests.py
git commit -m "feat: revisao_view e view_comprovante para o time de RH"
```

---

## Task 4: Template rh/revisao.html

**Files:**
- Create: `django_app/templates/rh/revisao.html`

- [ ] **Step 1: Criar o diretório e o template**

```powershell
mkdir django_app\templates\rh
```

Crie `django_app/templates/rh/revisao.html` com o conteúdo abaixo:

```html
{% extends "base_dashboard.html" %}
{% load static %}

{% block title %}Revisar Inscrição — Banco de Talentos IFG{% endblock %}

{% block page_content %}
<div style="padding:12px 20px 8px">
    <a href="{% url 'admin:inscricoes_inscricao_changelist' %}" class="back-link">&larr; voltar</a>
    <h2 style="margin:6px 0 2px;color:#202124;font-size:18px">Revisar Inscrição</h2>
    <p style="color:#666;font-size:13px;margin:0">
        <strong>{{ inscricao.usuario.nome_completo }}</strong> &middot;
        {{ inscricao.get_modalidade_display }}{% if inscricao.tipo_servidor %} &middot; {{ inscricao.get_tipo_servidor_display }}{% endif %}
        &middot; Enviada em {{ inscricao.enviada_em|date:"d/m/Y H:i" }}
    </p>
</div>

<div style="display:flex;gap:0;height:calc(100vh - 130px);overflow:hidden">

    <!-- Painel esquerdo: PDF -->
    <div style="flex:0 0 48%;border-right:1px solid #e0e0e0;overflow:hidden;display:flex;flex-direction:column">
        {% if inscricao.comprovantes_pdf %}
            <iframe src="{% url 'view_comprovante' inscricao.pk %}"
                    style="width:100%;flex:1;border:none"></iframe>
        {% else %}
            <div style="flex:1;display:flex;align-items:center;justify-content:center;color:#aaa;font-size:14px">
                Nenhum PDF enviado.
            </div>
        {% endif %}
    </div>

    <!-- Painel direito: critérios + formulário -->
    <div style="flex:1;overflow-y:auto;padding:12px 16px">
        <form method="post" novalidate>
            {% csrf_token %}

            {% for item, valor_validado in itens_com_score %}
            <div style="border:1px solid #e0e0e0;border-radius:8px;padding:10px;margin-bottom:8px">
                <div style="display:flex;gap:10px;align-items:flex-start">
                    <div style="flex:1">
                        <div style="font-weight:600;font-size:13px;color:#202124">
                            {{ forloop.counter }}. {{ item.criterio.criterio }}
                        </div>
                        <div style="font-size:11px;color:#aaa;margin-top:2px">
                            Máx: {{ item.criterio.maximo|floatformat:"-2" }} pts
                        </div>
                    </div>
                    <div style="text-align:center;flex-shrink:0;min-width:56px">
                        <div style="font-size:10px;color:#aaa;margin-bottom:2px">Candidato</div>
                        <div style="font-size:15px;font-weight:600;color:#555">{{ item.pontuacao|floatformat:1 }}</div>
                    </div>
                    <div style="text-align:center;flex-shrink:0;min-width:76px">
                        <div style="font-size:10px;color:#aaa;margin-bottom:2px">Validado</div>
                        <input
                            type="number"
                            name="validado_{{ item.pk }}"
                            data-candidato="{{ item.pontuacao|floatformat:1 }}"
                            min="0"
                            max="{{ item.criterio.maximo }}"
                            step="0.1"
                            value="{{ valor_validado }}"
                            placeholder="{{ item.pontuacao|floatformat:1 }}"
                            style="width:70px;padding:4px;border:1px solid #ccc;border-radius:5px;text-align:center;font-size:14px;font-weight:600"
                        >
                    </div>
                </div>
                <input
                    type="text"
                    name="obs_{{ item.pk }}"
                    value="{{ item.observacao_avaliacao }}"
                    placeholder="Observação (opcional)"
                    style="width:100%;margin-top:8px;padding:5px 8px;font-size:12px;border:1px solid #e0e0e0;border-radius:5px;box-sizing:border-box"
                >
            </div>
            {% endfor %}

            <!-- Rodapé fixo -->
            <div style="background:#f8f8f8;border-radius:8px;padding:14px;margin-top:4px;position:sticky;bottom:0;border:1px solid #e8e8e8">

                <div style="font-size:13px;color:#555;margin-bottom:10px">
                    Total candidato: <strong>{{ inscricao.total|floatformat:1 }} pts</strong>
                    &nbsp;&nbsp;|&nbsp;&nbsp;
                    Total validado: <strong id="total-validado" style="color:#168241">— pts</strong>
                </div>

                <div style="margin-bottom:10px">
                    <label style="display:block;font-size:12px;font-weight:600;color:#555;margin-bottom:4px">
                        {{ form.parecer_geral.label }}
                        <span style="font-weight:400;color:#c00;font-size:11px">(obrigatório ao indeferir)</span>
                    </label>
                    {{ form.parecer_geral }}
                    {% if form.parecer_geral.errors %}
                        <p style="color:#c00;font-size:12px;margin:4px 0 0">{{ form.parecer_geral.errors.0 }}</p>
                    {% endif %}
                </div>

                <div style="display:flex;justify-content:flex-end;gap:10px">
                    <button type="submit" name="acao" value="indeferir"
                            style="background:#dc3545;color:#fff;border:none;padding:8px 20px;border-radius:6px;font-size:14px;font-weight:600;cursor:pointer">
                        Indeferir
                    </button>
                    <button type="submit" name="acao" value="aprovar"
                            style="background:#168241;color:#fff;border:none;padding:8px 20px;border-radius:6px;font-size:14px;font-weight:600;cursor:pointer">
                        Aprovar &#10003;
                    </button>
                </div>
            </div>
        </form>
    </div>
</div>

<script>
(function () {
    function calcTotal() {
        let total = 0;
        document.querySelectorAll('input[name^="validado_"]').forEach(function (input) {
            const raw = input.value.trim();
            const val = raw ? parseFloat(raw.replace(',', '.')) : parseFloat(input.dataset.candidato);
            if (!isNaN(val)) total += val;
        });
        document.getElementById('total-validado').textContent =
            total.toFixed(1).replace('.', ',') + ' pts';
    }
    document.querySelectorAll('input[name^="validado_"]').forEach(function (input) {
        input.addEventListener('input', calcTotal);
    });
    calcTotal();
}());
</script>
{% endblock %}
```

- [ ] **Step 2: Testar manualmente no servidor**

```powershell
.\.venv\Scripts\python.exe manage.py runserver
```

1. Acesse `/admin/` com um usuário staff
2. Marque uma inscrição como "Em análise" (ação do Admin)
3. Acesse `/rh/inscricoes/<pk>/revisar/`
4. Verifique: PDF aparece no painel esquerdo, critérios à direita
5. Altere um valor validado — total deve atualizar em tempo real
6. Tente Indeferir sem parecer — deve mostrar erro
7. Preencha parecer e Indeferir — deve redirecionar ao Admin com mensagem de sucesso

- [ ] **Step 3: Commit**

```powershell
git add templates/rh/revisao.html
git commit -m "feat: template de revisao RH com layout PDF lado a lado"
```

---

## Task 5: Admin — coluna link_revisar

**Files:**
- Modify: `django_app/apps/inscricoes/admin.py`
- Test: `django_app/apps/inscricoes/tests.py`

- [ ] **Step 1: Escrever os testes que vão falhar**

Adicione ao final de `django_app/apps/inscricoes/tests.py`:

```python
class InscricaoAdminLinkRevisarTest(TestCase):
    def setUp(self):
        self.site = AdminSite()
        self.admin_user = User.objects.create_superuser(
            cpf="52998224725",
            email="admin@ifg.edu.br",
            nome_completo="Admin RH",
            password="Admin123!",
        )
        self.candidato = User.objects.create_user(
            cpf="11144477735",
            email="cand@test.com",
            nome_completo="Candidato",
            vinculo="estudante",
            password="Cand123!",
        )

    def test_link_revisar_exibido_para_em_analise(self):
        inscricao = Inscricao.objects.create(
            usuario=self.candidato,
            modalidade="estudante",
            status=StatusInscricao.EM_ANALISE,
        )
        ma = InscricaoAdmin(Inscricao, self.site)
        html = ma.link_revisar(inscricao)
        self.assertIn("Revisar", str(html))
        self.assertIn(f"/rh/inscricoes/{inscricao.pk}/revisar/", str(html))

    def test_link_revisar_vazio_para_outros_status(self):
        inscricao = Inscricao.objects.create(
            usuario=self.candidato,
            modalidade="estudante",
            status=StatusInscricao.PENDENTE,
        )
        ma = InscricaoAdmin(Inscricao, self.site)
        resultado = ma.link_revisar(inscricao)
        self.assertEqual(resultado, "—")
```

- [ ] **Step 2: Rodar os testes — verificar que falham**

```powershell
.\.venv\Scripts\python.exe manage.py test apps.inscricoes.tests.InscricaoAdminLinkRevisarTest --verbosity 2
```

Esperado: FAIL — `link_revisar` não existe.

- [ ] **Step 3: Adicionar `link_revisar` ao `InscricaoAdmin`**

Em `django_app/apps/inscricoes/admin.py`, dentro da classe `InscricaoAdmin`:

1. Altere `list_display` para incluir `"link_revisar"`:

```python
    list_display = ("usuario", "modalidade", "tipo_servidor", "total", "total_validado", "status", "link_revisar", "atualizado_em")
```

2. Adicione o método após `pdf_download_link`:

```python
    def link_revisar(self, obj):
        if obj.status == StatusInscricao.EM_ANALISE:
            url = reverse("revisao_rh", args=[obj.pk])
            return format_html('<a href="{}">Revisar &rarr;</a>', url)
        return "—"
    link_revisar.short_description = "Revisão"
```

3. Adicione `"total_validado"` e `"revisado_por"` a `readonly_fields`:

```python
    readonly_fields = ("criado_em", "atualizado_em", "enviada_em", "pdf_download_link", "total_validado", "revisado_em", "revisado_por")
```

- [ ] **Step 4: Rodar os testes — verificar que passam**

```powershell
.\.venv\Scripts\python.exe manage.py test apps.inscricoes.tests.InscricaoAdminLinkRevisarTest --verbosity 2
```

Esperado: 2 testes PASS.

- [ ] **Step 5: Rodar a suíte completa**

```powershell
.\.venv\Scripts\python.exe manage.py test apps.inscricoes apps.usuarios apps.auditoria --verbosity 2
```

Esperado: todos os testes PASS.

- [ ] **Step 6: Commit**

```powershell
git add apps/inscricoes/admin.py apps/inscricoes/tests.py
git commit -m "feat: coluna link_revisar no InscricaoAdmin para inscricoes em analise"
```
