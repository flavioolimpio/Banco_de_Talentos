# Fase 5 — Telas de Inscrição: Design Spec

**Projeto:** Banco de Talentos — Polo de Inovação IFG  
**Data:** 2026-05-19  
**Fase:** 5 de 7  
**Pré-requisito:** Fase 4 concluída — `CriterioEdital` populado via `popular_criterios`

---

## Objetivo

Implementar a área do candidato: três telas que permitem preencher pontuação por critério, fazer upload do PDF comprovante, salvar como rascunho e enviar definitivamente a inscrição para análise do RH.

---

## Fluxo do candidato

```
Login → Home (card de status) → Formulário (salvar rascunho N vezes)
                                      ↓ "Enviar inscrição"
                                Confirmação pós-envio (somente leitura)
```

Após o envio, o formulário fica **bloqueado para edição**. O status da inscrição muda de `pendente`/`completa` para `em_analise`.

---

## Telas

### Tela 1 — Home (`/`)

URL existente em `usuarios/urls.py`. O template `templates/usuarios/home.html` (atualmente placeholder) é atualizado para exibir:

- Saudação com nome do candidato e sua modalidade
- Card único com status colorido da inscrição:
  - `pendente` → amarelo
  - `completa` → azul
  - `em_analise` (enviada) → verde
  - `aprovada` → verde escuro
  - `indeferida` → vermelho
- Botão "Preencher inscrição →" (se não enviada) ou "Ver confirmação →" (se enviada)
- Texto informativo abaixo do card

O status `completa` é calculado ao salvar o rascunho: se PDF presente + total ≥ 10 pts + ≥ 2 itens, persiste `status="completa"`; caso contrário, `status="pendente"`. A home lê o status salvo diretamente do banco.

### Tela 2 — Formulário (`/inscricao/`)

Exibida apenas para candidatos com inscrição não enviada. Se já enviada, redireciona para `/inscricao/confirmacao/`.

**Componentes:**

1. **Aviso** — "Lattes não é aceito como comprovante. Envie um único PDF com todos os documentos na ordem do quadro."
2. **Seleção tipo_servidor** — radio Pesquisador/Apoio técnico, exibido apenas se `usuario.vinculo == "servidor"`
3. **Upload PDF** — campo único, validação MIME (`application/pdf`) + extensão `.pdf` + máx. 10 MB. Se já existe um PDF salvo, exibe o nome do arquivo atual.
4. **Cards de critério** — um card por `CriterioEdital` da modalidade, com:
   - Número de ordem, título do critério
   - Regra de pontuação
   - Pontuação máxima
   - Campo `number` (0 a máximo, passo 0.1) com atributo `data-score`
5. **Painel de resumo** — pontuação total (atualizada em tempo real via JS) + dois botões:
   - "Salvar rascunho" — salva sem validar requisitos de envio
   - "Enviar inscrição ✓" — valida e envia

**Botões:**

Ambos fazem POST para `/inscricao/` com campo `action` diferente:
- `action=rascunho`
- `action=enviar`

### Tela 3 — Confirmação (`/inscricao/confirmacao/`)

Somente leitura. Se acessada sem inscrição enviada, redireciona para `/inscricao/`.

Exibe:
- Ícone de sucesso
- Modalidade, tipo_servidor (se servidor), pontuação total, data/hora do envio
- Botão "← Voltar ao início"

---

## Arquitetura

### Arquivos novos

| Arquivo | Responsabilidade |
|---------|-----------------|
| `apps/inscricoes/forms.py` | `InscricaoForm`: valida PDF (MIME, tamanho), tipo_servidor, aceite_envio |
| `apps/inscricoes/views.py` | `inscricao_view`, `confirmacao_view` |
| `apps/inscricoes/urls.py` | URL patterns de `/inscricao/` |
| `templates/inscricoes/formulario.html` | Template do formulário com JS inline |
| `templates/inscricoes/confirmacao.html` | Template da confirmação pós-envio |

### Arquivos alterados

| Arquivo | O que muda |
|---------|-----------|
| `templates/usuarios/home.html` | Substituir placeholder por card de status da inscrição |
| `apps/usuarios/views.py` | `home_view` passa `inscricao` ao contexto (pode ser `None` para candidatos novos) |
| `config/urls.py` | `include("apps.inscricoes.urls")` |

---

## Forms

### `InscricaoForm`

```python
class InscricaoForm(forms.Form):
    tipo_servidor  # CharField com choices TipoServidor — exibido/validado só se vinculo=="servidor"
    comprovantes_pdf  # FileField, opcional (pode já existir salvo)
    aceite_envio  # BooleanField — exigido apenas na ação "enviar"
```

Os scores dos critérios **não** passam por um ModelForm. A view lê `request.POST.get(f"score_{criterio.pk}")` para cada critério da modalidade e valida min=0, max=criterio.maximo.

---

## Views

### `inscricao_view` (GET + POST)

**GET:**
1. Se `inscricao.enviada_em` existe → redirect para `/inscricao/confirmacao/`
2. Carrega `CriterioEdital.objects.filter(modalidade=usuario.vinculo, ativo=True).order_by("ordem")`
3. Carrega `Inscricao` + `InscricaoItem` existentes (ou None/vazio)
4. Renderiza `formulario.html`

**POST `action=rascunho`:**
1. Valida `InscricaoForm` (PDF se enviado, tipo_servidor se servidor)
2. Valida e clipa scores (0 ≤ score ≤ maximo)
3. Dentro de `transaction.atomic()`:
   - `Inscricao.objects.update_or_create(usuario=request.user, defaults={...})`
   - Para cada critério: `InscricaoItem.objects.update_or_create(inscricao=inscricao, criterio=criterio, defaults={"pontuacao": score})`
4. Registra `AuditLog(acao=AuditAction.INSCRICAO_SALVA)`
5. `messages.success(...)` + redirect GET `/inscricao/`

**POST `action=enviar`:**
1. Mesma validação do rascunho
2. Valida requisitos de envio:
   - PDF presente (novo ou já salvo)
   - total ≥ 10
   - count(score > 0) ≥ 2
3. Se inválido: re-renderiza com erros
4. Se válido: salva tudo + `inscricao.enviada_em = timezone.now()` + `inscricao.status = StatusInscricao.EM_ANALISE`
5. Registra `AuditLog(acao=AuditAction.INSCRICAO_SALVA)`
6. Redirect para `/inscricao/confirmacao/`

### `confirmacao_view` (GET)

1. Tenta carregar `Inscricao` do usuário
2. Se não existe ou `enviada_em` é None → redirect `/inscricao/`
3. Renderiza `confirmacao.html` com a inscrição

---

## JavaScript (formulario.html)

Pequeno bloco inline no final do template:

```javascript
// Atualiza #total-display somando todos os campos [data-score]
document.querySelectorAll('[data-score]').forEach(el => {
  el.addEventListener('input', updateTotal);
});
function updateTotal() {
  const total = [...document.querySelectorAll('[data-score]')]
    .reduce((sum, el) => sum + (parseFloat(el.value) || 0), 0);
  document.getElementById('total-display').textContent = total.toFixed(1);
}
updateTotal(); // executa na carga para mostrar total inicial
```

---

## Tratamento de Erros

| Situação | Comportamento |
|----------|---------------|
| Inscrição já enviada → GET `/inscricao/` | Redirect `/inscricao/confirmacao/` |
| Sem inscrição enviada → GET `/inscricao/confirmacao/` | Redirect `/inscricao/` |
| Score > máximo do critério | Clipado para `criterio.maximo` (silencioso) |
| Score < 0 | Zerado |
| PDF inválido (MIME errado ou > 10 MB) | Erro no campo, form re-exibido |
| Envio sem PDF / < 10 pts / < 2 itens | Erro não-field exibido no topo do form |
| Nenhum `CriterioEdital` ativo na modalidade | Mensagem informativa: "Quadro em preparação" |
| Servidor sem selecionar tipo_servidor | Erro de validação no campo |

---

## Testes (TDD)

Arquivo: `apps/inscricoes/tests.py` (adicionar às classes existentes)

### `InscricaoFormTest`
- PDF com MIME inválido → form inválido
- PDF com > 10 MB → form inválido
- PDF válido (< 10 MB, application/pdf) → form válido
- tipo_servidor obrigatório quando vinculo == "servidor"
- aceite_envio obrigatório quando action == "enviar"

### `InscricaoViewTest`
- GET `/inscricao/` retorna 200 para candidato autenticado
- GET `/inscricao/` sem `CriterioEdital` exibe mensagem "Quadro em preparação"
- POST rascunho cria `Inscricao` e `InscricaoItem` no banco
- POST rascunho atualiza dados já existentes (idempotente)
- POST enviar com dados inválidos (sem PDF) → re-exibe form com erro
- POST enviar válido → `inscricao.enviada_em` preenchido + redirect confirmacao
- POST enviar válido → `inscricao.status == "em_analise"`
- GET `/inscricao/` com inscrição já enviada → redirect confirmacao

### `ConfirmacaoViewTest`
- GET sem inscrição enviada → redirect `/inscricao/`
- GET com inscrição enviada → 200

### `AuditLogInscricaoTest`
- POST rascunho → `AuditLog` com `acao=INSCRICAO_SALVA` criado
- POST enviar → `AuditLog` com `acao=INSCRICAO_SALVA` criado

---

## Segurança

- Todas as views protegidas por `@login_required`
- Candidato só acessa/altera a **própria** inscrição (`get_object_or_404(Inscricao, usuario=request.user)`)
- PDF servido via view autenticada (implementado na fase 6)
- Nenhum dado sensível em URL ou query string
- CSRF ativo em todos os formulários (Django padrão)
- Scores validados e clipados no servidor — nunca confiar no valor do cliente

---

## Fora de escopo (fase 5)

- Download do PDF pelo candidato (fase 6)
- Download do PDF pelo RH (fase 6)
- Notificação por e-mail ao candidato ou ao RH
- Edição da inscrição após envio (fluxo de "devolução para correção")
- Paginação dos critérios
