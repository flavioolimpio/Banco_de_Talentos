# apps/inscricoes/forms.py
# Banco de Talentos — Polo de Inovação IFG
# Formulário de inscrição: valida PDF, tipo_servidor e aceite de envio.

from django import forms
from django.core.exceptions import ValidationError

from apps.inscricoes.models import TipoServidor
from apps.usuarios.models import Vinculo

MAX_PDF_SIZE = 10 * 1024 * 1024  # 10 MB


class InscricaoForm(forms.Form):
    tipo_servidor = forms.ChoiceField(
        label="Categoria do servidor",
        choices=[("", "Selecione...")] + list(TipoServidor.choices),
        required=False,
    )
    comprovantes_pdf = forms.FileField(
        label="PDF único dos comprovantes",
        required=False,
        help_text="Envie um único PDF com todos os comprovantes na ordem dos critérios. Máx. 10 MB.",
    )
    aceite_envio = forms.BooleanField(
        label="Confirmo que os dados informados são verdadeiros.",
        required=False,
    )

    def __init__(self, *args, usuario=None, acao=None, **kwargs):
        self.usuario = usuario
        self.acao = acao
        super().__init__(*args, **kwargs)

    def clean_comprovantes_pdf(self):
        pdf = self.cleaned_data.get("comprovantes_pdf")
        if not pdf:
            return pdf
        if not pdf.name.lower().endswith(".pdf"):
            raise ValidationError("Apenas arquivos com extensão .pdf são aceitos.")
        if pdf.size > MAX_PDF_SIZE:
            mb = pdf.size // 1024 // 1024
            raise ValidationError(f"O arquivo não pode ter mais de 10 MB (atual: {mb} MB).")
        header = pdf.read(5)
        pdf.seek(0)
        if header != b"%PDF-":
            raise ValidationError("O arquivo não é um PDF válido.")
        return pdf

    def clean(self):
        cleaned_data = super().clean()
        if self.usuario and self.usuario.vinculo == Vinculo.SERVIDOR:
            if not cleaned_data.get("tipo_servidor"):
                self.add_error("tipo_servidor", "Selecione a categoria do servidor.")
        if self.acao == "enviar" and not cleaned_data.get("aceite_envio"):
            self.add_error(
                "aceite_envio",
                "É necessário confirmar que os dados são verdadeiros para enviar.",
            )
        return cleaned_data
