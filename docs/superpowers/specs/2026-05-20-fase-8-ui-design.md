# Fase 8 — UI: Sidebar, Home com Imagem e Meu Cadastro

## Objetivo

Melhorar a navegação e completude do dashboard do candidato adicionando:
- Sidebar de navegação fixa (4 itens)
- Imagem `home.png` na página inicial
- Página "Meu Cadastro" com 3 abas para edição do perfil

---

## Contexto

Durante testes locais, identificou-se que o dashboard Django carecia de:
1. Navegação entre as seções (só existia o botão "Sair" no topo)
2. A imagem ilustrativa da home (presente no Streamlit original)
3. Página para o candidato visualizar e editar seus próprios dados cadastrais

O modelo `Usuario` já possui todos os campos necessários (dados pessoais, endereço, formação). Não são necessárias novas migrations.

---

## Arquitetura

### Novo template base: `base_dashboard.html`

Todos os templates do dashboard herdarão de `base_dashboard.html` (em vez de `base.html` diretamente). Este novo base renderiza a sidebar fixa à esquerda e o conteúdo à direita.

```
base.html
└── base_dashboard.html   ← novo: sidebar + área de conteúdo
    ├── home.html         ← atualizado
    ├── formulario.html   ← atualizado
    ├── confirmacao.html  ← atualizado
    └── meu_cadastro.html ← novo
```

Templates de autenticação (login, cadastro, reset de senha) continuam herdando de `base.html` diretamente.

### Sidebar

- Fundo `#223342` (azul escuro, já usado no CSS do IFG)
- Logo/título "Banco de Talentos · IFG" no topo
- Nome do usuário logado abaixo do título
- 4 itens de navegação:
  1. **Home** → `/`
  2. **Minha inscrição** → `/inscricao/`
  3. **Meu cadastro** → `/meu-cadastro/`
  4. **Sair** → `POST /logout/` (form com CSRF)
- Item ativo destacado com borda esquerda `#d6f000` e fundo levemente verde

### Home (`/`)

Mantém o card de "Minha inscrição" existente. Adiciona:
- Banner com `home.png` acima do card, servido via `{% static 'imagens/home.png' %}`
- A imagem já existe em `imagens/` — precisa ser copiada para `static/imagens/`

### Meu Cadastro (`/meu-cadastro/`)

Nova view `meu_cadastro_view` em `apps/usuarios/views.py`.

**Campos somente leitura** (exibidos, não editáveis):
- CPF
- E-mail
- Vínculo

**3 abas com campos editáveis:**

| Aba | Campos |
|-----|--------|
| Dados Pessoais | nome_completo, telefone, data_nascimento, rg, orgao_emissor, genero, resumo |
| Endereço | cep, endereco, numero, complemento, bairro, cidade, uf |
| Formação | nivel_formacao, area_atuacao, lattes, linkedin, instituicao |

A aba ativa é controlada por query string: `?aba=dados` (padrão), `?aba=endereco`, `?aba=formacao`.

**Validações:**
- `lattes` e `linkedin`: validação de URL (já feita pelo `URLField` do model)
- `cep`: máximo 9 caracteres
- Nenhum campo é obrigatório (todos `blank=True` no model)

**Fluxo:**
1. GET → exibe a aba ativa com os dados atuais do usuário
2. POST → valida, salva, redireciona de volta com `?aba=<aba>&salvo=1`
3. Se `salvo=1` na query string → exibe mensagem de sucesso

**AuditLog:** Salvar alterações registra `AuditAction.CADASTRO_ATUALIZADO` (já existe no enum).

---

## Arquivos a criar ou modificar

| Arquivo | Ação |
|---------|------|
| `templates/base_dashboard.html` | Criar — layout com sidebar |
| `templates/usuarios/home.html` | Modificar — herdar de `base_dashboard.html`, adicionar imagem |
| `templates/usuarios/meu_cadastro.html` | Criar — 3 abas, campos editáveis |
| `templates/inscricoes/formulario.html` | Modificar — herdar de `base_dashboard.html` |
| `templates/inscricoes/confirmacao.html` | Modificar — herdar de `base_dashboard.html` |
| `apps/usuarios/views.py` | Modificar — adicionar `meu_cadastro_view` |
| `apps/usuarios/forms.py` | Criar — `MeuCadastroForm` (um `ModelForm` com todos os campos editáveis; a view filtra quais renderizar por aba) |
| `apps/usuarios/urls.py` | Modificar — adicionar path `/meu-cadastro/` |
| `static/imagens/home.png` | Criar — copiar de `imagens/home.png` |

---

## Segurança

- `meu_cadastro_view` protegida com `@login_required`
- CPF nunca aparece em URLs (campo interno)
- AuditLog registra alterações de dados pessoais (LGPD)
- Campos CPF, e-mail e vínculo: somente leitura no form — não aceitos via POST mesmo se enviados manualmente

---

## Testes

- `MeuCadastroViewGetTest`: GET exibe dados atuais nas 3 abas
- `MeuCadastroViewPostTest`: POST salva e redireciona, campos read-only ignorados mesmo se enviados
- `MeuCadastroBloqueioTest`: acesso sem login redireciona para `/login/`
- `HomeImagemTest`: página home contém referência a `imagens/home.png`
- `SidebarTest`: sidebar presente em home, formulario e meu_cadastro; ausente em login/cadastro
