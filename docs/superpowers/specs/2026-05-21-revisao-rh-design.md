# Interface de Revisão RH — Design

**Data:** 2026-05-21
**Autor:** Prof. Flávio (RH Polo EMBRAPII IFG) + Claude Code

---

## Objetivo

Permitir que membros da equipe de RH (`is_staff = True`) revisem inscrições enviadas pelos candidatos, validem as pontuações critério a critério, registrem um parecer geral e tomem a decisão final (aprovada ou indeferida) — tudo dentro do sistema Banco de Talentos.

---

## Arquitetura

Dois componentes independentes que trabalham juntos:

### 1. Admin personalizado (`/admin/`)

Customização do `InscricaoAdmin` para que a lista de inscrições no Django Admin mostre as informações relevantes para o RH e ofereça um link direto para a tela de revisão.

- `list_display`: nome do candidato, modalidade, tipo_servidor, status (com badge colorido), total autodeclarado, data de envio
- `list_filter`: status, modalidade
- `search_fields`: CPF do usuário, nome completo
- Coluna extra com link "Revisar →" apontando para `/rh/inscricoes/<pk>/revisar/`
- Ação de exportação CSV (nome, CPF, modalidade, total, status)

### 2. Tela de revisão (`/rh/inscricoes/<pk>/revisar/`)

View customizada protegida por `@staff_member_required`, com o visual padrão do sistema (estende `base_dashboard.html`).

Layout dividido em dois painéis:

```
┌─────────────────────────────────────────────────────────────┐
│ sidebar │  Nome · Modalidade · Tipo · Enviada em DD/MM/AAAA │
│         │──────────────────────────────────────────────────  │
│         │  [PDF embutido — 48%]  │  Critérios (52%)         │
│         │                        │  1. Titulação             │
│         │                        │     Candidato:  70,0 pts  │
│         │                        │     Validado:  [_____]    │
│         │                        │     Obs: [_____________]  │
│         │                        │  2. Pós-doutoramento...   │
│         │                        │     ...                   │
│         │                        │────────────────────────── │
│         │                        │  Total candidato: 245 pts │
│         │                        │  Total validado:  230 pts │
│         │                        │  Parecer geral:           │
│         │                        │  [_____________________]  │
│         │                        │  (obrig. ao indeferir)    │
│         │                        │  [Indeferir] [Aprovar ✓]  │
└─────────────────────────────────────────────────────────────┘
```

---

## Regras de negócio

### Silêncio = concordância
O campo `pontuacao_validada` fica vazio por padrão. Ao salvar, se o campo estiver vazio, o sistema persiste `pontuacao_validada = pontuacao` (copia o valor autodeclarado). O total validado é recalculado como `sum(pontuacao_validada for item in itens)` e salvo em `Inscricao.total_validado`.

### Campo `total_validado` em `Inscricao`
Acrescentar também `total_validado = DecimalField(default=0)` ao model `Inscricao` para armazenar o total após revisão sem precisar recalcular na listagem do Admin.

### Parecer obrigatório ao indeferir
Se a ação for `indeferir` e o campo `parecer_geral` estiver vazio, o formulário retorna erro de validação.

### Inscrição bloqueada após decisão
Após aprovar ou indeferir, o status muda e a inscrição fica somente-leitura para o candidato (já era) e também para o RH (a tela mostra os dados mas os campos ficam desabilitados).

### Apenas inscrições `em_analise` podem ser revisadas
Se o RH tentar acessar `/rh/inscricoes/<pk>/revisar/` de uma inscrição com status diferente de `em_analise`, recebe redirecionamento de volta ao Admin com mensagem de aviso.

---

## Alterações no banco de dados

### `Inscricao` — 4 novos campos

```python
total_validado = models.DecimalField("pontuação total validada", max_digits=9, decimal_places=2, default=0)
parecer_geral  = models.TextField("parecer geral", blank=True)
revisado_em    = models.DateTimeField("revisado em", null=True, blank=True)
revisado_por   = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.SET_NULL,
    null=True, blank=True,
    related_name="inscricoes_revisadas",
    verbose_name="revisado por",
)
```

Os campos `pontuacao_validada` e `observacao_avaliacao` já existem em `InscricaoItem` — nenhuma mudança neste model.

---

## Novos arquivos

| Arquivo | Responsabilidade |
|---|---|
| `apps/inscricoes/admin.py` | `InscricaoAdmin` com filtros, busca, link revisar, ação CSV |
| `apps/inscricoes/views_rh.py` | `revisao_view(request, pk)` — GET e POST da tela de revisão |
| `apps/inscricoes/forms_rh.py` | `RevisaoItemFormSet` (pontuacao_validada + observacao) + `RevisaoForm` (parecer_geral + acao) |
| `templates/rh/revisao.html` | Template da tela de revisão com layout dividido |

## Arquivos modificados

| Arquivo | O que muda |
|---|---|
| `apps/inscricoes/models.py` | +3 campos em `Inscricao` |
| `apps/inscricoes/migrations/` | Nova migration para os 3 campos |
| `apps/auditoria/models.py` | `+INSCRICAO_REVISADA` em `AuditAction` |
| `config/urls.py` | Rota `rh/inscricoes/<pk>/revisar/` |

---

## Auditoria

Toda ação de revisão registra um `AuditLog`:
- `acao`: `AuditAction.INSCRICAO_REVISADA`
- `detalhes`: `{"decisao": "aprovada" | "indeferida", "total_validado": "230.00", "inscricao_id": 42}`
- `ip` e `user_agent` do revisor

---

## Fora do escopo desta fase

- Notificação por e-mail ao candidato após decisão
- Candidato visualizar o parecer no sistema
- Histórico de revisões anteriores (já coberto pelo `simple_history` no model)
