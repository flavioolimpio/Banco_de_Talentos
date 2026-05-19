# Modelo de Dados - Fase 2

## Decisoes principais

### Usuario customizado

Foi criado `usuarios.Usuario` como `AUTH_USER_MODEL`.

Motivo: em Django, o modelo de usuario deve ser definido no inicio do projeto. Trocar depois de migrations em producao e trabalhoso e arriscado.

Escolha adotada:

- CPF como identificador de login (`USERNAME_FIELD = "cpf"`).
- `id` interno padrao do Django como chave primaria.
- `cpf` unico, mas nao chave primaria.

Por que manter `id` interno?

- Facilita integracoes futuras.
- Evita expor CPF como identificador tecnico em URLs, logs e relacionamentos.
- Mantem compatibilidade com Django Admin, permissoes e pacotes de terceiros.

### Criterios do edital em tabela

Os criterios sairam do formato de constante Python e foram modelados como `inscricoes.CriterioEdital`.

Motivo:

- Editais mudam.
- Pontuacao maxima e regra podem ser ajustadas sem alterar codigo.
- A administracao pode futuramente cadastrar criterios via Django Admin.

### Inscricao e itens

- `Inscricao` representa a inscricao unica do candidato.
- `InscricaoItem` guarda a pontuacao solicitada e, futuramente, a pontuacao validada pela equipe.
- O PDF unico fica associado a `Inscricao`.

### Auditoria

Foi criado `auditoria.AuditLog` para eventos sensiveis:

- login/logout;
- criacao/alteracao de cadastro;
- salvamento de inscricao;
- upload/download de comprovante;
- exportacao CSV;
- exportacao/exclusao de dados do titular.

## Impactos LGPD

- CPF nao e chave primaria tecnica.
- Aceite LGPD tem timestamp, versao do termo e IP.
- Downloads e exportacoes terao rastreabilidade por `AuditLog`.
- PDFs ficarao em `MEDIA_ROOT`, mas deverao ser servidos apenas por views autenticadas em fase posterior.
