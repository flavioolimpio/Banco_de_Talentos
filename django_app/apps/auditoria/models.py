from django.conf import settings
from django.db import models


class AuditAction(models.TextChoices):
    LOGIN = "login", "Login"
    LOGOUT = "logout", "Logout"
    CADASTRO_CRIADO = "cadastro_criado", "Cadastro criado"
    CADASTRO_ATUALIZADO = "cadastro_atualizado", "Cadastro atualizado"
    INSCRICAO_SALVA = "inscricao_salva", "Inscrição salva"
    PONTUACAO_ALTERADA = "pontuacao_alterada", "Pontuação alterada"
    COMPROVANTE_UPLOAD = "comprovante_upload", "Upload de comprovante"
    COMPROVANTE_DOWNLOAD = "comprovante_download", "Download de comprovante"
    CSV_EXPORTADO = "csv_exportado", "CSV exportado"
    DADOS_EXPORTADOS_TITULAR = "dados_exportados_titular", "Dados do titular exportados"
    DADOS_EXCLUIDOS_TITULAR = "dados_excluidos_titular", "Dados do titular excluídos"
    INSCRICAO_REVISADA = "inscricao_revisada", "Inscrição revisada"


class AuditLog(models.Model):
    ator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    alvo = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs_como_alvo",
    )
    acao = models.CharField(max_length=40, choices=AuditAction.choices)
    objeto_tipo = models.CharField(max_length=120, blank=True)
    objeto_id = models.CharField(max_length=120, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    detalhes = models.JSONField(default=dict, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "log de auditoria"
        verbose_name_plural = "logs de auditoria"
        ordering = ["-criado_em"]
        indexes = [
            models.Index(fields=["acao", "criado_em"]),
            models.Index(fields=["ator", "criado_em"]),
            models.Index(fields=["alvo", "criado_em"]),
        ]

    def __str__(self) -> str:
        return f"{self.get_acao_display()} em {self.criado_em:%d/%m/%Y %H:%M}"
