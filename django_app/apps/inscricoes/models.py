from pathlib import Path

from django.conf import settings
from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import models
from simple_history.models import HistoricalRecords

from apps.usuarios.models import Vinculo


class TipoServidor(models.TextChoices):
    PESQUISADOR = "pesquisador", "Pesquisador"
    APOIO_TECNICO = "apoio_tecnico", "Apoio técnico"


class StatusInscricao(models.TextChoices):
    PENDENTE = "pendente", "Pendente"
    COMPLETA = "completa", "Completa"
    EM_ANALISE = "em_analise", "Em análise"
    APROVADA = "aprovada", "Aprovada"
    INDEFERIDA = "indeferida", "Indeferida"


def comprovante_upload_to(instance: "Inscricao", filename: str) -> str:
    suffix = Path(filename).suffix.lower() or ".pdf"
    cpf = instance.usuario.cpf
    modalidade = instance.modalidade
    return f"comprovantes/{modalidade}/{cpf}/comprovantes{suffix}"


class CriterioEdital(models.Model):
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
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "critério do edital"
        verbose_name_plural = "critérios do edital"
        ordering = ["modalidade", "tipo_servidor", "ordem"]
        constraints = [
            models.UniqueConstraint(
                fields=["modalidade", "tipo_servidor", "item_id"],
                name="uniq_criterio_por_modalidade_tipo_item",
            )
        ]

    def __str__(self) -> str:
        return f"{self.get_modalidade_display()} - {self.ordem}. {self.criterio}"


class Inscricao(models.Model):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inscricao",
    )
    modalidade = models.CharField("modalidade", max_length=30, choices=Vinculo.choices)
    tipo_servidor = models.CharField(
        "tipo de servidor",
        max_length=30,
        choices=TipoServidor.choices,
        blank=True,
    )
    total = models.DecimalField("pontuação total", max_digits=9, decimal_places=2, default=0)
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

    def __str__(self) -> str:
        return f"Inscrição de {self.usuario.nome_completo}"


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
    pontuacao = models.DecimalField(
        "pontuação solicitada",
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
