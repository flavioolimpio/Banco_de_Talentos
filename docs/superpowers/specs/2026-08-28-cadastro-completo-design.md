# Cadastro Completo (Perfil Profissional) — Design

**Data:** 2026-08-28
**Autor:** Prof. Flávio (RH Polo EMBRAPII IFG) + Claude Code

---

## Objetivo

Primeira parte da reforma do Banco de Especialistas: acrescentar ao cadastro do candidato os campos de perfil profissional especificados em `docs/Estrutura_Perfil_Cadastro_Banco_Especialistas.md` (Blocos A, B, C, F, G), sem quebrar quem já está cadastrado, e sinalizar quando o perfil está incompleto.

Esta é a base para a segunda parte (fora do escopo aqui): o sistema de vagas nativo, que vai depender de `categoria_pretendida`, `maior_titulacao`, `area_atuacao` e `disponibilidade_semanal` para filtrar candidatos. Ver seção "Fora do escopo".

---

## Contexto

Hoje o cadastro (`Usuario`) já cobre identificação básica e parte da formação (Bloco A parcial, `lattes`, `resumo`, `nivel_formacao` e `area_atuacao` como texto livre). O que falta:

- Distinguir servidor ativo de inativo (hoje `vinculo` só tem 3 opções: estudante/servidor/colaborador_externo)
- Categoria pretendida (Pesquisador vs Apoio Técnico) — hoje só existe como `TipoServidor` dentro de `Inscricao`, presa a um edital
- Titulação e área de formação como listas fechadas, não texto livre
- Disponibilidade semanal, checkboxes de elegibilidade e declarações (Blocos F e G)

Quem já se cadastrou não pode ficar bloqueado: os campos novos nascem opcionais e um aviso pede pra completar depois.

---

## Arquitetura

### 1. Novos campos em `Usuario` (`apps/usuarios/models.py`)

Todos opcionais no banco (`blank=True`, com `null=True` nos booleanos/data), preenchidos em "Meu Cadastro" depois do cadastro inicial.

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


# em Usuario:
categoria_pretendida = models.CharField(max_length=30, choices=CategoriaPretendida.choices, blank=True)
servidor_ativo = models.BooleanField(null=True, blank=True)  # só relevante quando vinculo == SERVIDOR
maior_titulacao = models.CharField(max_length=30, choices=MaiorTitulacao.choices, blank=True)
disponibilidade_semanal = models.PositiveSmallIntegerField(null=True, blank=True)  # horas/semana

nao_afastado_licenciado = models.BooleanField(null=True, blank=True)
ciencia_credenciamento_em = models.DateTimeField(null=True, blank=True)
declaracao_veracidade_em = models.DateTimeField(null=True, blank=True)
consentimento_verificacao_bases_em = models.DateTimeField(null=True, blank=True)
```

`CategoriaPretendida` é definida em `usuarios`, não importada de `inscricoes.TipoServidor` — evita import circular (hoje `inscricoes` já importa `Vinculo` de `usuarios`; o caminho inverso criaria ciclo). Os valores textuais (`pesquisador`/`apoio_tecnico`) ficam iguais aos de `TipoServidor` de propósito, pra facilitar migração de dados se um dia unificarmos.

Os quatro campos `*_em` seguem o mesmo padrão já usado em `aceite_lgpd_em`: gravam a data/hora da declaração, não um booleano solto — dá rastro de auditoria de quando a pessoa confirmou cada item.

`area_atuacao` (já existe, texto livre) continua sendo usado para "curso e área de formação" por enquanto. A tabela hierárquica do CNPq (Bloco C) fica de fora desta fase — ver "Decisões em aberto".

### 2. Propriedade `perfil_completo`

```python
# em Usuario
@property
def perfil_completo(self) -> bool:
    campos = [
        self.categoria_pretendida,
        self.maior_titulacao,
        self.area_atuacao,
        self.disponibilidade_semanal,
        self.ciencia_credenciamento_em,
        self.declaracao_veracidade_em,
        self.consentimento_verificacao_bases_em,
    ]
    if self.vinculo == Vinculo.SERVIDOR:
        campos.append(self.servidor_ativo)
    if self.vinculo == Vinculo.SERVIDOR and self.servidor_ativo:
        # nao_afastado_licenciado é uma declaração (precisa ser True, não só not-None)
        return all(c not in (None, "") for c in campos) and self.nao_afastado_licenciado is True
    return all(c not in (None, "") for c in campos)
```

Não é um campo de banco — é calculado na hora, sempre reflete o estado real. Usado pelo banner (seção 3) e, na próxima fase, pelo botão "tenho interesse".

### 3. Nova aba "Perfil profissional" em Meu Cadastro

`apps/usuarios/views.py::meu_cadastro_view` já organiza os campos em abas via `_ABAS_CAMPOS` (`dados`, `endereco`, `formacao`). Acrescentar uma quarta:

```python
"perfil": [
    "categoria_pretendida", "servidor_ativo", "maior_titulacao",
    "disponibilidade_semanal", "nao_afastado_licenciado",
],
```

As três declarações (`ciencia_credenciamento`, `declaracao_veracidade`, `consentimento_verificacao_bases`) aparecem como checkboxes na mesma aba; ao marcar e salvar, a view grava o timestamp no campo `_em` correspondente (só grava na primeira vez — se already preenchido, mantém a data original e não deixa desmarcar depois de confirmado, mesmo padrão do aceite LGPD).

`servidor_ativo`, `nao_afastado_licenciado` e o próprio rótulo de "categoria pretendida" só aparecem no formulário quando `request.user.vinculo == Vinculo.SERVIDOR` — a view já teria que filtrar `_ABAS_CAMPOS["perfil"]` condicionalmente antes de construir o form.

### 4. Banner de perfil incompleto

Em `usuarios/home.html`, exibir um banner (sem bloquear nada) sempre que `request.user.perfil_completo` for `False`, com link direto para `/meu-cadastro/?aba=perfil`. Passar `perfil_completo` no contexto de `home_view`.

---

## Regras de negócio

### Faixa de disponibilidade por vínculo
`disponibilidade_semanal` aceita 5–20h se `vinculo == SERVIDOR and servidor_ativo == True`, e 5–40h nos demais casos (servidor inativo, estudante, colaborador externo) — conforme Res. IFG nº 209/2024. Validado no `clean()` do form da aba "perfil", não como `validators` fixos no model (a faixa depende de outro campo).

### Declaração confirmada não se desfaz
Uma vez que `ciencia_credenciamento_em`, `declaracao_veracidade_em` ou `consentimento_verificacao_bases_em` for gravado, o checkbox correspondente aparece marcado e desabilitado — salvar o formulário de novo não apaga a data nem permite desmarcar. Mesmo padrão já usado no aceite LGPD (`aceite_lgpd_em`).

### Perfil incompleto nunca bloqueia login ou navegação
`perfil_completo == False` só liga o banner. Não impede acessar nenhuma tela desta fase — a trava (botão "tenho interesse" desabilitado) é do próximo design, quando o sistema de vagas existir.

---

## Alterações no banco de dados

Uma migration em `apps/usuarios/migrations/`, aditiva e reversível:

| Campo | Tipo | Nulo/opcional |
|---|---|---|
| `categoria_pretendida` | `CharField(30, choices)` | sim |
| `servidor_ativo` | `BooleanField` | sim |
| `maior_titulacao` | `CharField(30, choices)` | sim |
| `disponibilidade_semanal` | `PositiveSmallIntegerField` | sim |
| `nao_afastado_licenciado` | `BooleanField` | sim |
| `ciencia_credenciamento_em` | `DateTimeField` | sim |
| `declaracao_veracidade_em` | `DateTimeField` | sim |
| `consentimento_verificacao_bases_em` | `DateTimeField` | sim |

Nenhuma coluna existente muda de tipo ou tamanho. Sem impacto em `Inscricao`/`InscricaoItem`/`CriterioEdital`.

---

## Novos arquivos

Nenhum — tudo entra em arquivos já existentes.

## Arquivos modificados

| Arquivo | O que muda |
|---|---|
| `apps/usuarios/models.py` | +2 `TextChoices`, +8 campos, `+perfil_completo` (property) |
| `apps/usuarios/migrations/` | Nova migration aditiva |
| `apps/usuarios/views.py` | `_ABAS_CAMPOS["perfil"]`, filtro condicional por vínculo em `meu_cadastro_view`, `perfil_completo` no contexto de `home_view` |
| `apps/usuarios/forms.py` | Formulário da aba "perfil" (reaproveita o padrão de `ModelForm` por aba já usado) |
| `templates/usuarios/meu_cadastro.html` | Nova aba + campos condicionais por vínculo |
| `templates/usuarios/home.html` | Banner de perfil incompleto |

---

## Decisões em aberto

- **Fonte da tabela CNPq (Bloco C)** — não entra nesta fase; `area_atuacao` continua texto livre até haver um fixture com a lista oficial de grandes áreas/áreas.
- **Consentimento de verificação em bases internas** — pode acabar virando uma nova versão do termo LGPD (`aceite_lgpd_versao`) em vez de um campo próprio. Mantido como campo separado por ora; fácil de descontinuar depois se a via jurídica for essa.
- **Blocos D e E do documento fonte** — não existem no `.docx` recebido; confirmar com quem escreveu antes de considerar o mapeamento de campos definitivo.

---

## Fora do escopo (fica para o próximo design: "Sistema de vagas nativo")

- Model `Vaga`, tela "Vagas abertas", botão "tenho interesse" e o formulário de pontuação por vaga
- Quadro de critérios único (sem IFGProduz) e a regra de janela de recência (5/7 anos)
- Desligamento da página "Minha Inscrição" e do fluxo antigo de `Inscricao`
- Envio de e-mail avisando vaga aberta e o anexo padrão do coordenador

Esses itens dependem de `categoria_pretendida`, `maior_titulacao` e `disponibilidade_semanal` já existirem no cadastro — por isso esta fase vem primeiro.
