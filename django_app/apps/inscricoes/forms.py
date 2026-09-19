# apps/inscricoes/forms.py
# Banco de Talentos — Polo de Inovação IFG
# Formulário de inscrição: valida PDF, tipo_servidor e aceite de envio.

from pathlib import Path

from django import forms
from django.core.exceptions import ValidationError

from apps.inscricoes.models import TipoServidor, Vaga
from apps.usuarios.models import Vinculo

MAX_PDF_SIZE = 10 * 1024 * 1024  # 10 MB


class InscricaoForm(forms.Form):
    tipo_servidor = forms.ChoiceField(
        label="Categoria",
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
        widget=forms.CheckboxInput(attrs={"style": "margin:0;padding:0;flex-shrink:0;cursor:pointer;width:14px;height:14px"}),
    )

    def __init__(self, *args, usuario=None, acao=None, tem_pdf=False, **kwargs):
        self.usuario = usuario
        self.acao = acao
        # tem_pdf indica que a inscrição já possui um PDF guardado (caso de
        # reenvio): nesse caso não exigimos um novo upload para enviar.
        self.tem_pdf = tem_pdf
        super().__init__(*args, **kwargs)

    def clean_comprovantes_pdf(self):
        pdf = self.cleaned_data.get("comprovantes_pdf")
        if not pdf:
            return pdf
        if Path(pdf.name).suffix.lower() != ".pdf":
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
        needs_subtipo = self.usuario and self.usuario.vinculo in (Vinculo.SERVIDOR, Vinculo.COLABORADOR_EXTERNO)
        if needs_subtipo and not cleaned_data.get("tipo_servidor"):
            self.add_error("tipo_servidor", "Selecione a categoria.")
        if self.acao == "enviar":
            if not cleaned_data.get("aceite_envio"):
                self.add_error(
                    "aceite_envio",
                    "É necessário confirmar que os dados são verdadeiros para enviar.",
                )
            # Exige PDF de comprovantes no envio. Aceita o já anexado (reenvio).
            if not cleaned_data.get("comprovantes_pdf") and not self.tem_pdf:
                self.add_error(
                    "comprovantes_pdf",
                    "É necessário anexar o PDF de comprovantes para enviar a inscrição.",
                )
        return cleaned_data


class InscricaoChamadaForm(forms.Form):
    """Formulário de inscrição numa Chamada Interna.

    É o "Google Forms" do candidato: os critérios não são campos declarados
    aqui — eles variam de chamada para chamada e são lidos do POST em
    views_chamadas._parse_respostas. O que fica aqui é o que vale para toda
    chamada: a vaga pretendida, o PDF de comprovantes e as declarações que o
    item 5.6, "b", manda firmar no próprio formulário.
    """

    vaga = forms.ModelChoiceField(
        label="Vaga pretendida",
        queryset=Vaga.objects.none(),
        empty_label="Selecione a vaga",
        required=False,
    )
    comprovantes_pdf = forms.FileField(
        label="PDF único dos comprovantes",
        required=False,
        help_text=(
            "Um único PDF com todos os comprovantes, na ordem dos critérios. "
            "Máx. 10 MB. O currículo Lattes não vale como comprovante "
            "(item 5.14 do Edital)."
        ),
    )
    licencas_maternidade = forms.IntegerField(
        label="Licenças à gestante ou à adotante usufruídas no período",
        required=False,
        min_value=0,
        max_value=10,
        help_text=(
            "Cada licença amplia em 2 anos a janela de 5 anos dos critérios "
            "(item 5.8, III). Deixe 0 se não se aplica. Será comprovada na "
            "etapa de análise documental."
        ),
    )
    declara_disponibilidade = forms.BooleanField(
        label="Declaro ter disponibilidade de carga horária para a vaga pretendida.",
        required=False,
        widget=forms.CheckboxInput(attrs={"style": "margin-top:3px;flex-shrink:0;width:16px;height:16px"}),
    )
    declara_nao_redistribuicao = forms.BooleanField(
        label="Declaro não estar em processo de redistribuição para outra instituição.",
        required=False,
        widget=forms.CheckboxInput(attrs={"style": "margin-top:3px;flex-shrink:0;width:16px;height:16px"}),
    )
    aceite_envio = forms.BooleanField(
        label=(
            "Declaro, sob as penas do art. 299 do Código Penal, que as informações "
            "acima são verdadeiras e que possuo os comprovantes correspondentes."
        ),
        required=False,
        widget=forms.CheckboxInput(attrs={"style": "margin-top:3px;flex-shrink:0;width:16px;height:16px"}),
    )

    def __init__(self, *args, chamada=None, usuario=None, acao=None, tem_pdf=False, **kwargs):
        self.chamada = chamada
        self.usuario = usuario
        self.acao = acao
        self.tem_pdf = tem_pdf
        super().__init__(*args, **kwargs)
        if chamada is not None and usuario is not None:
            # Só as vagas compatíveis com o vínculo do candidato: estudante não
            # concorre a vaga de servidor.
            self.fields["vaga"].queryset = chamada.vagas.filter(
                modalidade=usuario.vinculo
            )

    clean_comprovantes_pdf = InscricaoForm.clean_comprovantes_pdf

    def clean_licencas_maternidade(self):
        return self.cleaned_data.get("licencas_maternidade") or 0

    def clean(self):
        cleaned_data = super().clean()
        if self.acao != "enviar":
            return cleaned_data

        # As três declarações e o PDF só são exigidos no ENVIO. Salvar rascunho
        # tem que funcionar com o formulário pela metade.
        if not cleaned_data.get("vaga") and self.fields["vaga"].queryset.exists():
            self.add_error("vaga", "Selecione a vaga a que deseja concorrer.")
        if not cleaned_data.get("declara_disponibilidade"):
            self.add_error("declara_disponibilidade", "Declaração obrigatória para enviar.")
        if not cleaned_data.get("declara_nao_redistribuicao"):
            self.add_error("declara_nao_redistribuicao", "Declaração obrigatória para enviar.")
        if not cleaned_data.get("aceite_envio"):
            self.add_error("aceite_envio", "Declaração obrigatória para enviar.")
        if not cleaned_data.get("comprovantes_pdf") and not self.tem_pdf:
            self.add_error(
                "comprovantes_pdf",
                "É necessário anexar o PDF de comprovantes para enviar a inscrição.",
            )
        return cleaned_data
