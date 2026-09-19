from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from simple_history.models import HistoricalRecords

from apps.usuarios.models import Vinculo


class TipoServidor(models.TextChoices):
    PESQUISADOR = "pesquisador", "Pesquisador(a)"
    APOIO_TECNICO = "apoio_tecnico", "Apoio técnico"


class StatusInscricao(models.TextChoices):
    PENDENTE = "pendente", "Pendente"
    COMPLETA = "completa", "Completa"
    EM_ANALISE = "em_analise", "Em análise"
    APROVADA = "aprovada", "Aprovada"
    INDEFERIDA = "indeferida", "Indeferida"


class TipoCriterio(models.TextChoices):
    """Como o candidato responde a um critério no formulário da chamada.

    CONTAGEM: ele informa uma quantidade ("quantos projetos?") e o sistema
    multiplica por `pontos_por_unidade`, respeitando o teto `maximo`.
    ESCOLHA:  ele escolhe uma opção de uma lista (ex.: titulação), e cada
    opção tem a sua própria pontuação (ver OpcaoCriterio).

    Em nenhum dos dois o candidato digita pontos — é o sistema que calcula.
    Isso fecha a porta para a divergência de conta que aparecia na conferência
    do RH, e é o que deixa o formulário parecido com um Google Forms.
    """

    CONTAGEM = "contagem", "Quantidade (pontos por unidade)"
    ESCOLHA = "escolha", "Escolha única (cada opção vale uma pontuação)"


def comprovante_upload_to(instance: "Inscricao", filename: str) -> str:
    """comprovantes/chamada-<id>/<modalidade>/<cpf>/comprovantes.pdf

    O segmento da chamada usa o pk, não numero/ano: o RH pode corrigir a
    numeração no admin, e o caminho já gravado no banco não se reescreve
    sozinho. Sem esse segmento, uma segunda inscrição do mesmo CPF
    sobrescreveria o PDF da primeira.

    Arquivos já salvos não se movem: o upload_to só é consultado ao gravar um
    arquivo novo, e o caminho antigo continua guardado no FileField.
    """
    suffix = Path(filename).suffix.lower() or ".pdf"
    cpf = instance.usuario.cpf
    modalidade = instance.modalidade
    chamada = f"chamada-{instance.chamada_id}" if instance.chamada_id else "legado"
    return f"comprovantes/{chamada}/{modalidade}/{cpf}/comprovantes{suffix}"


class ChamadaInterna(models.Model):
    """Uma chamada interna (Aviso de Abertura de Vagas), item 5.1 do Edital 29.

    É a unidade que substitui o "edital único": cada chamada tem as suas vagas,
    o seu prazo e o SEU quadro de critérios, montado pela Coordenação do
    Projeto (item 5.1, VI). O RH cadastra tudo pelo Django admin, sem deploy.
    """

    numero = models.PositiveSmallIntegerField("número")
    ano = models.PositiveSmallIntegerField("ano")
    titulo = models.CharField("título", max_length=200)
    projeto = models.CharField("projeto", max_length=200, blank=True)
    edital = models.CharField(
        "edital de origem",
        max_length=60,
        blank=True,
        help_text='Apenas para exibição. Ex.: "Edital PROPPG nº 29/2026".',
    )
    aviso_url = models.URLField("link do aviso publicado", blank=True)
    texto = models.TextField(
        "objeto / resumo",
        blank=True,
        help_text="Aparece na página da chamada, acima das vagas.",
    )
    abertura = models.DateTimeField("abertura das inscrições")
    encerramento = models.DateTimeField("encerramento das inscrições")
    publicada = models.BooleanField(
        "publicada",
        default=False,
        help_text="Enquanto desmarcada, a chamada fica invisível para os candidatos.",
    )
    legado = models.BooleanField(
        "chamada de legado",
        default=False,
        help_text=(
            "Marca as três chamadas sintéticas que guardam as inscrições do "
            "credenciamento antigo. Elas existem só para o histórico não ficar "
            "solto; nunca recebem inscrição nova."
        ),
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "chamada interna"
        verbose_name_plural = "chamadas internas"
        ordering = ["-ano", "-numero"]
        constraints = [
            models.UniqueConstraint(
                fields=["numero", "ano"], name="uniq_chamada_numero_ano"
            )
        ]

    def __str__(self) -> str:
        return f"Chamada Interna {self.numero:02d}/{self.ano} — {self.titulo}"

    @property
    def rotulo_curto(self) -> str:
        return f"Chamada Interna {self.numero:02d} — {self.titulo}"

    @property
    def aberta(self) -> bool:
        """Sem campo de status: o estado sai de `publicada` + as duas datas.

        Comparação com timezone.now(), nunca datetime.now(): a janela de
        inscrição é o prazo legal da chamada, e três horas de diferença viram
        recurso administrativo.
        """
        if not self.publicada:
            return False
        agora = timezone.now()
        return self.abertura <= agora <= self.encerramento

    @property
    def encerrada(self) -> bool:
        return self.publicada and timezone.now() > self.encerramento

    def get_absolute_url(self) -> str:
        return reverse("chamada_detalhe", args=[self.pk])

    def modalidades(self) -> set[str]:
        """Vínculos elegíveis, derivados das vagas — não há campo para isso.

        O caso real ("servidor e externo, mas não estudante") não cabe num
        campo com choices, e derivar das vagas nunca fica inconsistente com o
        que foi de fato publicado.
        """
        return {vaga.modalidade for vaga in self.vagas.all()}


class Vaga(models.Model):
    """Uma posição ofertada na chamada — o Quadro 1 do Aviso."""

    chamada = models.ForeignKey(
        ChamadaInterna, on_delete=models.CASCADE, related_name="vagas"
    )
    codigo = models.CharField("código", max_length=20, help_text='Ex.: "Pq 12", "AT3", "ES-IT".')
    funcao = models.CharField("função", max_length=200)
    perfil = models.TextField("perfil e competências esperadas", blank=True)
    quantidade = models.PositiveSmallIntegerField("vagas", default=1)
    bolsa = models.DecimalField(
        "valor da bolsa (R$/mês)", max_digits=10, decimal_places=2, null=True, blank=True
    )
    carga_horaria = models.PositiveSmallIntegerField(
        "carga horária semanal (h)", null=True, blank=True
    )
    modalidade = models.CharField("modalidade", max_length=30, choices=Vinculo.choices)
    tipo_servidor = models.CharField(
        "categoria", max_length=30, choices=TipoServidor.choices, blank=True
    )
    ordem = models.PositiveSmallIntegerField("ordem", default=0)

    class Meta:
        verbose_name = "vaga"
        verbose_name_plural = "vagas"
        ordering = ["ordem", "codigo"]
        constraints = [
            models.UniqueConstraint(
                fields=["chamada", "codigo"], name="uniq_vaga_por_chamada_codigo"
            )
        ]

    def __str__(self) -> str:
        return f"{self.codigo} — {self.funcao}"


class CriterioEdital(models.Model):
    """Uma linha do quadro de critérios — o Quadro 2 do Aviso (item 5.1, VI).

    O nome da classe é legado ("do edital"); desde a Retificação 4 o quadro é
    de CADA CHAMADA. Renomear custaria imports, admin, migrations e comandos,
    sem mudar nada de comportamento.
    """

    chamada = models.ForeignKey(
        ChamadaInterna,
        on_delete=models.PROTECT,
        related_name="criterios",
    )
    tipo = models.CharField(
        "como o candidato responde",
        max_length=20,
        choices=TipoCriterio.choices,
        default=TipoCriterio.CONTAGEM,
    )
    pontos_por_unidade = models.DecimalField(
        "pontos por unidade",
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Só para critérios de quantidade. Ex.: 40 pontos por projeto.",
    )
    unidade_rotulo = models.CharField(
        "o que é contado",
        max_length=60,
        blank=True,
        help_text='Vira a pergunta do formulário. Ex.: "projetos" → "Quantos projetos?".',
    )
    modalidade = models.CharField("modalidade", max_length=30, choices=Vinculo.choices)
    tipo_servidor = models.CharField(
        "tipo de servidor",
        max_length=30,
        choices=TipoServidor.choices,
        blank=True,
    )
    item_id = models.CharField("identificador do item", max_length=80)
    ordem = models.PositiveSmallIntegerField("ordem")
    criterio = models.CharField("critério", max_length=500)
    regra = models.CharField("regra de pontuação", max_length=500)
    maximo = models.DecimalField("pontuação máxima", max_digits=8, decimal_places=2)
    is_api = models.BooleanField("preenchido via API", default=False)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "critério do edital"
        verbose_name_plural = "critérios do edital"
        ordering = ["chamada", "modalidade", "tipo_servidor", "ordem"]
        constraints = [
            # A chamada entra na chave: o mesmo item_id ("titulacao") precisa
            # poder existir em toda chamada.
            models.UniqueConstraint(
                fields=["chamada", "modalidade", "tipo_servidor", "item_id"],
                name="uniq_criterio_por_chamada_modalidade_tipo_item",
            )
        ]

    def __str__(self) -> str:
        return f"{self.get_modalidade_display()} - {self.ordem}. {self.criterio}"

    @property
    def pergunta(self) -> str:
        """Texto da pergunta no formulário, para critérios de quantidade."""
        unidade = (self.unidade_rotulo or "itens").strip()
        return f"Quantos(as) {unidade}?"

    def pontuar(self, quantidade=None, opcao=None) -> Decimal:
        """Converte a resposta do candidato em pontos. Nunca passa do máximo."""
        if self.tipo == TipoCriterio.ESCOLHA:
            pontos = Decimal(opcao.pontos) if opcao is not None else Decimal("0")
        else:
            por_unidade = self.pontos_por_unidade or Decimal("0")
            pontos = Decimal(quantidade or 0) * por_unidade
        return max(Decimal("0"), min(pontos, self.maximo))


class OpcaoCriterio(models.Model):
    """Uma alternativa de um critério do tipo ESCOLHA.

    Existe para os critérios que não são contagem — titulação é o caso
    clássico: Doutorado 100, Mestrado 70, e assim por diante.
    """

    criterio = models.ForeignKey(
        CriterioEdital, on_delete=models.CASCADE, related_name="opcoes"
    )
    rotulo = models.CharField("opção", max_length=200)
    pontos = models.DecimalField("pontos", max_digits=8, decimal_places=2)
    ordem = models.PositiveSmallIntegerField("ordem", default=0)

    class Meta:
        verbose_name = "opção do critério"
        verbose_name_plural = "opções do critério"
        ordering = ["ordem", "-pontos"]

    def __str__(self) -> str:
        return f"{self.rotulo} ({self.pontos} pts)"


class Inscricao(models.Model):
    # FK, não OneToOne: a partir da Retificação 4 o candidato se inscreve uma
    # vez POR CHAMADA. A unicidade vira a constraint (usuario, chamada).
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inscricoes",
    )
    chamada = models.ForeignKey(
        ChamadaInterna,
        on_delete=models.PROTECT,
        related_name="inscricoes",
    )
    vaga = models.ForeignKey(
        Vaga,
        on_delete=models.SET_NULL,
        related_name="inscricoes",
        null=True,
        blank=True,
        verbose_name="vaga pretendida",
    )
    # Declarações firmadas no próprio formulário da inscrição (item 5.6, b).
    declara_disponibilidade = models.BooleanField(
        "declara disponibilidade para a carga horária da vaga", default=False
    )
    declara_nao_redistribuicao = models.BooleanField(
        "declara não estar em processo de redistribuição", default=False
    )
    # Item 5.8, III: cada licença à gestante/adotante usufruída no período
    # amplia em 2 anos a janela de recência de 5 anos. Declarado aqui e
    # comprovado na etapa do item 6.3.
    licencas_maternidade = models.PositiveSmallIntegerField(
        "licenças à gestante/adotante no período", default=0
    )
    modalidade = models.CharField("modalidade", max_length=30, choices=Vinculo.choices)
    tipo_servidor = models.CharField(
        "tipo de servidor",
        max_length=30,
        choices=TipoServidor.choices,
        blank=True,
    )
    total = models.DecimalField("pontuação total", max_digits=9, decimal_places=2, default=0)
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
    status = models.CharField(
        "status",
        max_length=30,
        choices=StatusInscricao.choices,
        default=StatusInscricao.PENDENTE,
    )
    comprovantes_pdf = models.FileField(
        "PDF único de comprovantes",
        upload_to=comprovante_upload_to,
        validators=[FileExtensionValidator(["pdf"])],
        blank=True,
    )
    comprovantes_pdf_nome_original = models.CharField(max_length=255, blank=True)
    comprovantes_pdf_tamanho = models.PositiveIntegerField(default=0)
    comprovantes_pdf_mime = models.CharField(max_length=120, blank=True)
    enviada_em = models.DateTimeField("enviada em", null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "inscrição"
        verbose_name_plural = "inscrições"
        ordering = ["-atualizado_em"]
        constraints = [
            # Substitui o antigo OneToOne: uma inscrição por candidato POR
            # chamada, em vez de uma por candidato para sempre.
            models.UniqueConstraint(
                fields=["usuario", "chamada"], name="uniq_inscricao_por_usuario_chamada"
            )
        ]

    def __str__(self) -> str:
        if self.chamada_id:
            return f"{self.usuario.nome_completo} — {self.chamada.rotulo_curto}"
        return f"Inscrição de {self.usuario.nome_completo}"

    @property
    def e_legado(self) -> bool:
        """Inscrição do credenciamento antigo, anterior às chamadas.

        Fica visível como histórico, somente leitura — o candidato não reenvia
        nem edita.
        """
        return bool(self.chamada_id and self.chamada.legado)

    @property
    def editavel(self) -> bool:
        """Só dá para mexer enquanto a chamada está aberta e o RH não fechou."""
        if self.e_legado or not self.chamada_id:
            return False
        if not self.chamada.aberta:
            return False
        return self.status in (StatusInscricao.PENDENTE, StatusInscricao.COMPLETA)


class InscricaoItem(models.Model):
    inscricao = models.ForeignKey(
        Inscricao,
        on_delete=models.CASCADE,
        related_name="itens",
    )
    criterio = models.ForeignKey(
        CriterioEdital,
        on_delete=models.PROTECT,
        related_name="itens_inscricao",
    )
    # A resposta do candidato. Uma das duas é usada, conforme o tipo do
    # critério; `pontuacao` abaixo é SEMPRE calculada a partir daqui, nunca
    # digitada.
    quantidade = models.PositiveIntegerField("quantidade declarada", default=0)
    opcao = models.ForeignKey(
        OpcaoCriterio,
        on_delete=models.PROTECT,
        related_name="itens_inscricao",
        null=True,
        blank=True,
        verbose_name="opção escolhida",
    )
    pontuacao = models.DecimalField(
        "pontuação calculada",
        max_digits=8,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )
    pontuacao_validada = models.DecimalField(
        "pontuação validada",
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )
    observacao_avaliacao = models.TextField("observação da avaliação", blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "item da inscrição"
        verbose_name_plural = "itens da inscrição"
        ordering = ["criterio__ordem"]
        constraints = [
            models.UniqueConstraint(
                fields=["inscricao", "criterio"],
                name="uniq_item_por_inscricao_criterio",
            )
        ]

    def __str__(self) -> str:
        return f"{self.inscricao} - {self.criterio.ordem}"
