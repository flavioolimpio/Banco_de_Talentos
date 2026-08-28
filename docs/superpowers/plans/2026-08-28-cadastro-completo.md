# Cadastro Completo (Perfil Profissional) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the Bloco B/C/F/G profile fields (categoria pretendida, titulação fechada, disponibilidade semanal, declarações) to `Usuario`, expose them in a new "Perfil profissional" tab of Meu Cadastro, and show a non-blocking banner on the home page while the profile is incomplete.

**Architecture:** Everything lands in the existing `apps/usuarios` app — no new app, no new views, no new templates. New `Usuario` fields (all optional) computed into a `perfil_completo` property; a fourth tab (`aba=perfil`) added to the existing `_ABAS_CAMPOS` dict that already drives `meu_cadastro_view` and `meu_cadastro.html`; three consent checkboxes handled outside the `ModelForm` (mirroring the existing `registrar_aceite_lgpd` pattern) so an unchecked box can never erase a prior "yes".

**Tech Stack:** Django 5.x, SQLite (dev), Django TestCase.

**Spec:** `docs/superpowers/specs/2026-08-28-cadastro-completo-design.md`

## Global Constraints

- All new `Usuario` columns are optional (`blank=True`, `null=True` where applicable) — no existing account may be blocked by this migration.
- Nothing in this plan blocks login, navigation, or any existing page. The only enforcement is the home banner (informational).
- `disponibilidade_semanal` range: 5–20h when `vinculo == SERVIDOR and servidor_ativo is True`; 5–40h otherwise (Res. IFG nº 209/2024).
- Once `ciencia_credenciamento`, `declaracao_veracidade` or `consentimento_verificacao_bases` is `True`, it can never be flipped back to `False`, and its `_em` timestamp is set exactly once.
- `categoria_pretendida`'s two values must be `"pesquisador"` / `"apoio_tecnico"` (matches `apps.inscricoes.models.TipoServidor` by convention, not by import — importing it would create a circular import since `inscricoes` already imports `Vinculo` from `usuarios`).

---

### Task 1: `Usuario` model — new fields, `perfil_completo`, `confirmar_declaracao`

**Files:**
- Modify: `django_app/apps/usuarios/models.py`
- Test: `django_app/apps/usuarios/tests.py`
- Create: `django_app/apps/usuarios/migrations/0002_perfil_profissional.py` (via `makemigrations`, not hand-written)

**Interfaces:**
- Produces: `Usuario.CategoriaPretendida` (`TextChoices`: `PESQUISADOR="pesquisador"`, `APOIO_TECNICO="apoio_tecnico"`), `Usuario.MaiorTitulacao` (`TextChoices`: `TECNICO`, `GRADUACAO`, `ESPECIALIZACAO`, `MESTRADO`, `DOUTORADO`), fields `categoria_pretendida`, `servidor_ativo`, `maior_titulacao`, `disponibilidade_semanal`, `nao_afastado_licenciado`, `ciencia_credenciamento` (+`_em`), `declaracao_veracidade` (+`_em`), `consentimento_verificacao_bases` (+`_em`) on `Usuario`; `Usuario.confirmar_declaracao(campo: str) -> None`; `Usuario.perfil_completo` (property, `bool`).
- Consumes: `django.utils.timezone` (already imported in this file, line 4), `Vinculo` (already defined in this file, line 7).

- [ ] **Step 1: Write the failing tests**

Append to `django_app/apps/usuarios/tests.py`:

```python
from apps.usuarios.models import CategoriaPretendida, MaiorTitulacao


class PerfilProfissionalModelTest(TestCase):
    def setUp(self):
        self.servidor = Usuario.objects.create_user(
            cpf="11144477735",
            email="perfilservidor@test.com",
            nome_completo="Servidor Perfil",
            vinculo=Vinculo.SERVIDOR,
            password="senha123",
        )
        self.externo = Usuario.objects.create_user(
            cpf="52998224725",
            email="perfilexterno@test.com",
            nome_completo="Externo Perfil",
            vinculo=Vinculo.COLABORADOR_EXTERNO,
            password="senha123",
        )

    def _preencher_campos_base(self, usuario):
        usuario.categoria_pretendida = CategoriaPretendida.PESQUISADOR
        usuario.maior_titulacao = MaiorTitulacao.DOUTORADO
        usuario.area_atuacao = "Engenharia"
        usuario.disponibilidade_semanal = 20

    def _confirmar_todas_declaracoes(self, usuario):
        usuario.confirmar_declaracao("ciencia_credenciamento")
        usuario.confirmar_declaracao("declaracao_veracidade")
        usuario.confirmar_declaracao("consentimento_verificacao_bases")

    def test_perfil_incompleto_por_padrao(self):
        self.assertFalse(self.servidor.perfil_completo)
        self.assertFalse(self.externo.perfil_completo)

    def test_perfil_completo_para_colaborador_externo(self):
        self._preencher_campos_base(self.externo)
        self._confirmar_todas_declaracoes(self.externo)
        self.assertTrue(self.externo.perfil_completo)

    def test_servidor_ativo_exige_declaracao_de_nao_afastamento(self):
        self._preencher_campos_base(self.servidor)
        self._confirmar_todas_declaracoes(self.servidor)
        self.servidor.servidor_ativo = True
        self.assertFalse(self.servidor.perfil_completo)
        self.servidor.nao_afastado_licenciado = True
        self.assertTrue(self.servidor.perfil_completo)

    def test_servidor_inativo_nao_precisa_declarar_afastamento(self):
        self._preencher_campos_base(self.servidor)
        self._confirmar_todas_declaracoes(self.servidor)
        self.servidor.servidor_ativo = False
        self.assertTrue(self.servidor.perfil_completo)

    def test_confirmar_declaracao_grava_booleano_e_timestamp(self):
        self.assertFalse(self.externo.declaracao_veracidade)
        self.assertIsNone(self.externo.declaracao_veracidade_em)
        self.externo.confirmar_declaracao("declaracao_veracidade")
        self.assertTrue(self.externo.declaracao_veracidade)
        self.assertIsNotNone(self.externo.declaracao_veracidade_em)

    def test_confirmar_declaracao_nao_atualiza_timestamp_se_ja_confirmada(self):
        self.externo.confirmar_declaracao("declaracao_veracidade")
        primeira_data = self.externo.declaracao_veracidade_em
        self.externo.confirmar_declaracao("declaracao_veracidade")
        self.assertEqual(self.externo.declaracao_veracidade_em, primeira_data)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `django_app/.venv/Scripts/python.exe django_app/manage.py test apps.usuarios.tests.PerfilProfissionalModelTest -v 2`
Expected: FAIL/ERROR — `ImportError: cannot import name 'CategoriaPretendida'` (or `AttributeError` once the import is stubbed out) because none of the new fields/methods exist yet.

- [ ] **Step 3: Add the choices, fields, method and property**

In `django_app/apps/usuarios/models.py`, insert after the `Genero` class (after line 23, before `class UsuarioManager`):

```python
class CategoriaPretendida(models.TextChoices):
    PESQUISADOR = "pesquisador", "Pesquisador(a)"
    APOIO_TECNICO = "apoio_tecnico", "Apoio técnico"


class MaiorTitulacao(models.TextChoices):
    TECNICO = "tecnico", "Médio/Técnico"
    GRADUACAO = "graduacao", "Graduação"
    ESPECIALIZACAO = "especializacao", "Especialização"
    MESTRADO = "mestrado", "Mestrado"
    DOUTORADO = "doutorado", "Doutorado"
```

In the same file, insert after the `aceite_lgpd_ip` line (currently line 99, right before `created_at`):

```python
    categoria_pretendida = models.CharField(
        "categoria pretendida", max_length=30, choices=CategoriaPretendida.choices, blank=True
    )
    servidor_ativo = models.BooleanField("servidor(a) ativo(a)", null=True, blank=True)
    maior_titulacao = models.CharField(
        "maior titulação", max_length=30, choices=MaiorTitulacao.choices, blank=True
    )
    disponibilidade_semanal = models.PositiveSmallIntegerField(
        "disponibilidade semanal (horas)", null=True, blank=True
    )
    nao_afastado_licenciado = models.BooleanField(
        "não afastado(a)/licenciado(a)", null=True, blank=True
    )

    ciencia_credenciamento = models.BooleanField("ciência de que o credenciamento não garante vaga", default=False)
    ciencia_credenciamento_em = models.DateTimeField(null=True, blank=True)
    declaracao_veracidade = models.BooleanField("declaração de veracidade (art. 299 CP)", default=False)
    declaracao_veracidade_em = models.DateTimeField(null=True, blank=True)
    consentimento_verificacao_bases = models.BooleanField(
        "consentimento de verificação em bases internas", default=False
    )
    consentimento_verificacao_bases_em = models.DateTimeField(null=True, blank=True)
```

At the end of the `Usuario` class, after `registrar_aceite_lgpd` (currently ending at line 121), add:

```python

    def confirmar_declaracao(self, campo: str) -> None:
        if not getattr(self, campo):
            setattr(self, campo, True)
            setattr(self, f"{campo}_em", timezone.now())

    @property
    def perfil_completo(self) -> bool:
        campos = [
            self.categoria_pretendida,
            self.maior_titulacao,
            self.area_atuacao,
            self.disponibilidade_semanal,
        ]
        if self.vinculo == Vinculo.SERVIDOR:
            campos.append(self.servidor_ativo)
            if self.servidor_ativo:
                campos.append(self.nao_afastado_licenciado)
        declaracoes = [
            self.ciencia_credenciamento,
            self.declaracao_veracidade,
            self.consentimento_verificacao_bases,
        ]
        return all(c not in (None, "") for c in campos) and all(declaracoes)
```

- [ ] **Step 4: Generate and apply the migration**

Run: `django_app/.venv/Scripts/python.exe django_app/manage.py makemigrations usuarios`
Expected: creates `django_app/apps/usuarios/migrations/0002_perfil_profissional.py` (or similar auto-generated name — rename the file to `0002_perfil_profissional.py` if Django names it something else, for clarity).

Run: `django_app/.venv/Scripts/python.exe django_app/manage.py migrate usuarios`
Expected: `Applying usuarios.0002_...  OK`

- [ ] **Step 5: Run tests to verify they pass**

Run: `django_app/.venv/Scripts/python.exe django_app/manage.py test apps.usuarios.tests.PerfilProfissionalModelTest -v 2`
Expected: PASS (7 tests)

- [ ] **Step 6: Commit**

```bash
git add django_app/apps/usuarios/models.py django_app/apps/usuarios/migrations/0002_perfil_profissional.py django_app/apps/usuarios/tests.py
git commit -m "feat(usuarios): adiciona campos de perfil profissional em Usuario"
```

---

### Task 2: `MeuCadastroForm` — novos campos e validação de disponibilidade

**Files:**
- Modify: `django_app/apps/usuarios/forms.py`
- Test: `django_app/apps/usuarios/tests.py`

**Interfaces:**
- Consumes: `Usuario.CategoriaPretendida`, `Usuario.MaiorTitulacao`, `Vinculo` (Task 1; `Vinculo` already imported in this file, line 6).
- Produces: `MeuCadastroForm` now includes `categoria_pretendida`, `servidor_ativo`, `maior_titulacao`, `disponibilidade_semanal`, `nao_afastado_licenciado` in `Meta.fields`, and validates `disponibilidade_semanal` against the vínculo-dependent range.

- [ ] **Step 1: Write the failing tests**

Append to `django_app/apps/usuarios/tests.py`:

```python
class MeuCadastroFormPerfilTest(TestCase):
    def setUp(self):
        self.servidor_ativo = Usuario.objects.create_user(
            cpf="11144477735",
            email="formservativo@test.com",
            nome_completo="Servidor Ativo",
            vinculo=Vinculo.SERVIDOR,
            password="senha123",
        )
        self.externo = Usuario.objects.create_user(
            cpf="52998224725",
            email="formexterno@test.com",
            nome_completo="Externo Form",
            vinculo=Vinculo.COLABORADOR_EXTERNO,
            password="senha123",
        )

    def test_form_aceita_disponibilidade_dentro_da_faixa_servidor_ativo(self):
        from apps.usuarios.forms import MeuCadastroForm
        form = MeuCadastroForm(
            {"nome_completo": "X", "servidor_ativo": "on", "disponibilidade_semanal": "20"},
            instance=self.servidor_ativo,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_rejeita_disponibilidade_acima_da_faixa_servidor_ativo(self):
        from apps.usuarios.forms import MeuCadastroForm
        form = MeuCadastroForm(
            {"nome_completo": "X", "servidor_ativo": "on", "disponibilidade_semanal": "30"},
            instance=self.servidor_ativo,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("disponibilidade_semanal", form.errors)

    def test_form_aceita_disponibilidade_ate_40h_para_colaborador_externo(self):
        from apps.usuarios.forms import MeuCadastroForm
        form = MeuCadastroForm(
            {"nome_completo": "X", "disponibilidade_semanal": "40"},
            instance=self.externo,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_rejeita_disponibilidade_abaixo_de_5h(self):
        from apps.usuarios.forms import MeuCadastroForm
        form = MeuCadastroForm(
            {"nome_completo": "X", "disponibilidade_semanal": "3"},
            instance=self.externo,
        )
        self.assertFalse(form.is_valid())
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `django_app/.venv/Scripts/python.exe django_app/manage.py test apps.usuarios.tests.MeuCadastroFormPerfilTest -v 2`
Expected: FAIL — `disponibilidade_semanal` etc. not recognized as form fields (form ignores unknown keys, so the "accepts" tests pass vacuously but the "rejects" tests fail because there's nothing to reject yet); confirm by checking `"disponibilidade_semanal" in form.fields` is `False` before Step 3.

- [ ] **Step 3: Add the fields and validation**

In `django_app/apps/usuarios/forms.py`, modify `MeuCadastroForm.Meta.fields` (currently ends with `"lattes", "linkedin", "instituicao",`):

```python
class Meta:
    model = Usuario
    fields = [
        "nome_completo", "telefone", "data_nascimento", "rg",
        "orgao_emissor", "genero", "resumo",
        "cep", "endereco", "numero", "complemento",
        "bairro", "cidade", "uf",
        "nivel_formacao", "area_atuacao", "lattes", "linkedin", "instituicao",
        "categoria_pretendida", "servidor_ativo", "maior_titulacao",
        "disponibilidade_semanal", "nao_afastado_licenciado",
    ]
    widgets = {
        "data_nascimento": forms.DateInput(
            attrs={"type": "date"}, format="%Y-%m-%d"
        ),
        "resumo": forms.Textarea(attrs={"rows": 3}),
    }
```

Add after `__init__` (after the existing `field.required = False` loop, still inside the class):

```python

    def clean_disponibilidade_semanal(self):
        horas = self.cleaned_data.get("disponibilidade_semanal")
        if horas is None:
            return horas
        servidor_ativo = self.instance.vinculo == Vinculo.SERVIDOR and self.cleaned_data.get("servidor_ativo")
        maximo = 20 if servidor_ativo else 40
        if not (5 <= horas <= maximo):
            raise ValidationError(f"Disponibilidade deve estar entre 5 e {maximo} horas semanais.")
        return horas
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `django_app/.venv/Scripts/python.exe django_app/manage.py test apps.usuarios.tests.MeuCadastroFormPerfilTest -v 2`
Expected: PASS (4 tests)

- [ ] **Step 5: Run the full existing form test class to check for regressions**

Run: `django_app/.venv/Scripts/python.exe django_app/manage.py test apps.usuarios.tests.MeuCadastroFormTest -v 2`
Expected: PASS (unchanged — these tests only assert absence of `cpf`/`email`/`vinculo`, not the full field list)

- [ ] **Step 6: Commit**

```bash
git add django_app/apps/usuarios/forms.py django_app/apps/usuarios/tests.py
git commit -m "feat(usuarios): adiciona campos de perfil profissional ao MeuCadastroForm"
```

---

### Task 3: View — aba "perfil", campos condicionais por vínculo, declarações

**Files:**
- Modify: `django_app/apps/usuarios/views.py`
- Test: `django_app/apps/usuarios/tests.py`

**Interfaces:**
- Consumes: `MeuCadastroForm` (Task 2), `Usuario.confirmar_declaracao` (Task 1), `Vinculo` (not yet imported in this file — add the import).
- Produces: `_ABAS_CAMPOS["perfil"]`, module-level `_DECLARACOES_PERFIL` list, `meu_cadastro_view` now handles `?aba=perfil` (hiding `servidor_ativo`/`nao_afastado_licenciado` for non-servidores and persisting the three declarations idempotently).

- [ ] **Step 1: Write the failing tests**

Append to `django_app/apps/usuarios/tests.py`:

```python
class MeuCadastroPerfilViewTest(TestCase):
    def setUp(self):
        self.servidor = Usuario.objects.create_user(
            cpf="11144477735",
            email="viewservidor@test.com",
            nome_completo="Servidor View",
            vinculo=Vinculo.SERVIDOR,
            password="senha123",
        )
        self.externo = Usuario.objects.create_user(
            cpf="52998224725",
            email="viewexterno@test.com",
            nome_completo="Externo View",
            vinculo=Vinculo.COLABORADOR_EXTERNO,
            password="senha123",
        )

    def test_get_aba_perfil_para_servidor_mostra_campo_servidor_ativo(self):
        self.client.force_login(self.servidor)
        response = self.client.get(reverse("meu_cadastro") + "?aba=perfil")
        self.assertContains(response, "name=\"servidor_ativo\"")

    def test_get_aba_perfil_para_externo_esconde_campo_servidor_ativo(self):
        self.client.force_login(self.externo)
        response = self.client.get(reverse("meu_cadastro") + "?aba=perfil")
        self.assertNotContains(response, "name=\"servidor_ativo\"")

    def test_post_perfil_salva_categoria_e_titulacao(self):
        self.client.force_login(self.externo)
        self.client.post(
            reverse("meu_cadastro") + "?aba=perfil",
            {"nome_completo": "X", "categoria_pretendida": "pesquisador", "maior_titulacao": "doutorado", "disponibilidade_semanal": "20"},
        )
        self.externo.refresh_from_db()
        self.assertEqual(self.externo.categoria_pretendida, "pesquisador")
        self.assertEqual(self.externo.maior_titulacao, "doutorado")

    def test_post_perfil_grava_declaracao_com_timestamp(self):
        self.client.force_login(self.externo)
        self.client.post(
            reverse("meu_cadastro") + "?aba=perfil",
            {"nome_completo": "X", "declaracao_veracidade": "on"},
        )
        self.externo.refresh_from_db()
        self.assertTrue(self.externo.declaracao_veracidade)
        self.assertIsNotNone(self.externo.declaracao_veracidade_em)

    def test_post_perfil_nao_desmarca_declaracao_ja_confirmada(self):
        self.externo.confirmar_declaracao("declaracao_veracidade")
        self.externo.save(update_fields=["declaracao_veracidade", "declaracao_veracidade_em"])
        primeira_data = self.externo.declaracao_veracidade_em
        self.client.force_login(self.externo)
        self.client.post(
            reverse("meu_cadastro") + "?aba=perfil",
            {"nome_completo": "X"},
        )
        self.externo.refresh_from_db()
        self.assertTrue(self.externo.declaracao_veracidade)
        self.assertEqual(self.externo.declaracao_veracidade_em, primeira_data)

    def test_post_perfil_servidor_nao_persiste_servidor_ativo_de_externo(self):
        """Colaborador externo postando a aba perfil não grava servidor_ativo (nem existe no form pra ele)."""
        self.client.force_login(self.externo)
        self.client.post(
            reverse("meu_cadastro") + "?aba=perfil",
            {"nome_completo": "X", "servidor_ativo": "on"},
        )
        self.externo.refresh_from_db()
        self.assertIsNone(self.externo.servidor_ativo)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `django_app/.venv/Scripts/python.exe django_app/manage.py test apps.usuarios.tests.MeuCadastroPerfilViewTest -v 2`
Expected: FAIL — `?aba=perfil` falls back to `aba="dados"` (not in `_ABAS_CAMPOS` yet), so none of the perfil fields render or save.

- [ ] **Step 3: Add the "perfil" aba to the view**

In `django_app/apps/usuarios/views.py`, add the import (line 10 area):

```python
from apps.usuarios.forms import CadastroUsuarioForm, LoginForm, MeuCadastroForm, NovaSenhaForm, RecuperacaoSenhaForm
from apps.usuarios.models import Vinculo
```

Replace the `_ABAS_CAMPOS` dict (currently lines 90–97):

```python
_ABAS_CAMPOS = {
    "dados": [
        "nome_completo", "telefone", "data_nascimento",
        "rg", "orgao_emissor", "genero", "resumo",
    ],
    "endereco": ["cep", "endereco", "numero", "complemento", "bairro", "cidade", "uf"],
    "formacao": ["nivel_formacao", "area_atuacao", "lattes", "linkedin", "instituicao"],
    "perfil": [
        "categoria_pretendida", "servidor_ativo", "maior_titulacao",
        "disponibilidade_semanal", "nao_afastado_licenciado",
    ],
}

_DECLARACOES_PERFIL = ["ciencia_credenciamento", "declaracao_veracidade", "consentimento_verificacao_bases"]
```

Replace `meu_cadastro_view` (currently lines 100–125):

```python
@login_required
@require_http_methods(["GET", "POST"])
def meu_cadastro_view(request):
    aba = request.GET.get("aba", "dados")
    if aba not in _ABAS_CAMPOS:
        aba = "dados"
    campos_aba = list(_ABAS_CAMPOS[aba])
    if aba == "perfil" and request.user.vinculo != Vinculo.SERVIDOR:
        campos_aba = [c for c in campos_aba if c not in ("servidor_ativo", "nao_afastado_licenciado")]

    form = MeuCadastroForm(request.POST or None, instance=request.user)

    if request.method == "POST" and form.is_valid():
        instance = form.save(commit=False)
        update_fields = list(campos_aba)
        if aba == "perfil":
            for campo in _DECLARACOES_PERFIL:
                if request.POST.get(campo) == "on":
                    instance.confirmar_declaracao(campo)
                    update_fields += [campo, f"{campo}_em"]
        instance.save(update_fields=update_fields)
        audit(request, AuditAction.CADASTRO_ATUALIZADO, alvo=request.user, detalhes={"aba": aba})
        messages.success(request, "Dados atualizados com sucesso.")
        return redirect(f"{reverse('meu_cadastro')}?aba={aba}")

    cpf = request.user.cpf
    cpf_formatado = f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"

    return render(request, "usuarios/meu_cadastro.html", {
        "form": form,
        "aba": aba,
        "campos_aba": campos_aba,
        "cpf_formatado": cpf_formatado,
    })
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `django_app/.venv/Scripts/python.exe django_app/manage.py test apps.usuarios.tests.MeuCadastroPerfilViewTest -v 2`
Expected: FAIL still, on the two `assertContains`/`assertNotContains` tests that check rendered HTML — those need Task 4's template first. The four POST-based tests should already PASS at this point (they only depend on the view + form, not the template markup).

Confirm with: `django_app/.venv/Scripts/python.exe django_app/manage.py test apps.usuarios.tests.MeuCadastroPerfilViewTest.test_post_perfil_salva_categoria_e_titulacao apps.usuarios.tests.MeuCadastroPerfilViewTest.test_post_perfil_grava_declaracao_com_timestamp apps.usuarios.tests.MeuCadastroPerfilViewTest.test_post_perfil_nao_desmarca_declaracao_ja_confirmada apps.usuarios.tests.MeuCadastroPerfilViewTest.test_post_perfil_servidor_nao_persiste_servidor_ativo_de_externo -v 2`
Expected: PASS (4 tests)

- [ ] **Step 5: Run the full existing view test class to check for regressions**

Run: `django_app/.venv/Scripts/python.exe django_app/manage.py test apps.usuarios.tests.MeuCadastroViewTest -v 2`
Expected: PASS (unchanged)

- [ ] **Step 6: Commit**

```bash
git add django_app/apps/usuarios/views.py django_app/apps/usuarios/tests.py
git commit -m "feat(usuarios): adiciona aba perfil a meu_cadastro_view"
```

---

### Task 4: Template — aba "Perfil profissional" e checkboxes de declaração

**Files:**
- Modify: `django_app/templates/usuarios/meu_cadastro.html`
- Test: `django_app/apps/usuarios/tests.py` (the two tests left failing by Task 3)

**Interfaces:**
- Consumes: `aba`, `campos_aba`, `form` (already passed by `meu_cadastro_view`, unchanged).

- [ ] **Step 1: Confirm the two pending tests still fail**

Run: `django_app/.venv/Scripts/python.exe django_app/manage.py test apps.usuarios.tests.MeuCadastroPerfilViewTest.test_get_aba_perfil_para_servidor_mostra_campo_servidor_ativo apps.usuarios.tests.MeuCadastroPerfilViewTest.test_get_aba_perfil_para_externo_esconde_campo_servidor_ativo -v 2`
Expected: FAIL — no `?aba=perfil` tab exists yet, view falls back to `aba="dados"`.

- [ ] **Step 2: Add the tab link and the declaration checkboxes**

In `django_app/templates/usuarios/meu_cadastro.html`, add a fourth tab link after the "Formação" link (inside the tab-bar `<div>`):

```html
        <a href="?aba=perfil"
           style="padding:10px 20px;text-decoration:none;font-size:14px;
                  {% if aba == 'perfil' %}font-weight:600;color:#168241;border-bottom:2px solid #168241;margin-bottom:-2px{% else %}color:#666{% endif %}">
            Perfil Profissional
        </a>
```

After the `{% for field in form %}...{% endfor %}` loop, still inside the `<form>` tag and before the submit button `<div>`, add:

```html
        {% if aba == 'perfil' %}
        <div style="margin-bottom:16px;padding:14px 16px;background:#f7f9f6;border-radius:8px">
            <label style="display:flex;gap:8px;align-items:flex-start;font-size:13px;margin-bottom:12px">
                <input type="checkbox" name="ciencia_credenciamento" style="margin-top:3px"
                       {% if request.user.ciencia_credenciamento %}checked disabled{% endif %}>
                <span>Tenho ciência de que o credenciamento no Banco de Especialistas não garante direito a vaga.</span>
            </label>
            <label style="display:flex;gap:8px;align-items:flex-start;font-size:13px;margin-bottom:12px">
                <input type="checkbox" name="declaracao_veracidade" style="margin-top:3px"
                       {% if request.user.declaracao_veracidade %}checked disabled{% endif %}>
                <span>Declaro, sob as penas do art. 299 do Código Penal, que as informações prestadas são verdadeiras.</span>
            </label>
            <label style="display:flex;gap:8px;align-items:flex-start;font-size:13px">
                <input type="checkbox" name="consentimento_verificacao_bases" style="margin-top:3px"
                       {% if request.user.consentimento_verificacao_bases %}checked disabled{% endif %}>
                <span>Consinto com a verificação destas informações em bases internas do IFG (Lei nº 13.709/2018).</span>
            </label>
        </div>
        {% endif %}
```

- [ ] **Step 3: Run the two pending tests to verify they pass**

Run: `django_app/.venv/Scripts/python.exe django_app/manage.py test apps.usuarios.tests.MeuCadastroPerfilViewTest -v 2`
Expected: PASS (all 6 tests in this class)

- [ ] **Step 4: Run the full usuarios test suite to check for regressions**

Run: `django_app/.venv/Scripts/python.exe django_app/manage.py test apps.usuarios -v 2`
Expected: PASS (all tests)

- [ ] **Step 5: Commit**

```bash
git add django_app/templates/usuarios/meu_cadastro.html
git commit -m "feat(usuarios): adiciona aba Perfil Profissional ao template de Meu Cadastro"
```

---

### Task 5: Banner de perfil incompleto na home

**Files:**
- Modify: `django_app/templates/usuarios/home.html`
- Test: `django_app/apps/usuarios/tests.py`

**Interfaces:**
- Consumes: `request.user.perfil_completo` (Task 1 property) — read directly in the template, no `home_view` context change needed since `request` is already available in this template (it already reads `request.user.get_vinculo_display`).

- [ ] **Step 1: Write the failing tests**

Append to `django_app/apps/usuarios/tests.py`:

```python
class HomeBannerPerfilTest(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            cpf="11144477735",
            email="bannerhome@test.com",
            nome_completo="Banner Teste",
            vinculo=Vinculo.COLABORADOR_EXTERNO,
            password="senha123",
        )
        self.client.force_login(self.usuario)

    def test_banner_aparece_quando_perfil_incompleto(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Complete seu perfil")

    def test_banner_some_quando_perfil_completo(self):
        self.usuario.categoria_pretendida = CategoriaPretendida.PESQUISADOR
        self.usuario.maior_titulacao = MaiorTitulacao.DOUTORADO
        self.usuario.area_atuacao = "Engenharia"
        self.usuario.disponibilidade_semanal = 20
        self.usuario.confirmar_declaracao("ciencia_credenciamento")
        self.usuario.confirmar_declaracao("declaracao_veracidade")
        self.usuario.confirmar_declaracao("consentimento_verificacao_bases")
        self.usuario.save()
        response = self.client.get(reverse("home"))
        self.assertNotContains(response, "Complete seu perfil")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `django_app/.venv/Scripts/python.exe django_app/manage.py test apps.usuarios.tests.HomeBannerPerfilTest -v 2`
Expected: FAIL on `test_banner_aparece_quando_perfil_incompleto` — banner text doesn't exist yet. `test_banner_some_quando_perfil_completo` will pass vacuously; that's fine, Step 4 re-confirms both together.

- [ ] **Step 3: Add the banner**

In `django_app/templates/usuarios/home.html`, insert immediately before `<div class="home-hero">`:

```html
{% if not request.user.perfil_completo %}
<div style="margin:20px 32px 0;padding:14px 18px;background:#fff8e1;border:1px solid #f0d97a;border-radius:8px;display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap">
    <span style="font-size:14px;color:#7a5a00">
        <strong>Complete seu perfil</strong> — faltam informações no seu cadastro (categoria pretendida, titulação, área de atuação, disponibilidade e declarações).
    </span>
    <a href="{% url 'meu_cadastro' %}?aba=perfil" class="home-cta" style="white-space:nowrap">Completar agora</a>
</div>
{% endif %}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `django_app/.venv/Scripts/python.exe django_app/manage.py test apps.usuarios.tests.HomeBannerPerfilTest -v 2`
Expected: PASS (2 tests)

- [ ] **Step 5: Run the full usuarios test suite one more time**

Run: `django_app/.venv/Scripts/python.exe django_app/manage.py test apps.usuarios -v 2`
Expected: PASS (all tests, no regressions)

- [ ] **Step 6: Commit**

```bash
git add django_app/templates/usuarios/home.html django_app/apps/usuarios/tests.py
git commit -m "feat(usuarios): adiciona banner de perfil incompleto na home"
```

---

## Fora do escopo (ver spec)

- Model `Vaga`, tela "Vagas abertas", botão "tenho interesse" e formulário de pontuação por vaga
- Quadro de critérios único (sem IFGProduz) e a regra de janela de recência (5/7 anos)
- Desligamento da página "Minha Inscrição" e do fluxo antigo de `Inscricao`
- Tabela hierárquica do CNPq para `area_atuacao` (continua texto livre nesta fase)
