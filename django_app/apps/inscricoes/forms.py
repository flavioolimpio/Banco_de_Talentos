# apps/inscricoes/forms.py
# Banco de Talentos — Polo de Inovação IFG
# Formulários de inscrição: o antigo (PDF) e o da Chamada Interna (XML do Lattes).

import re
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.inscricoes.models import TipoServidor, Vaga
from apps.usuarios.models import Vinculo

MAX_PDF_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_XML_SIZE = 10 * 1024 * 1024  # 10 MB — currículo grande passa de 2 MB
LATTES_VALIDADE_DIAS = 183  # 6 meses


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


def ler_curriculo_lattes(conteudo: bytes):
    """Devolve a raiz do XML do Lattes, ou None se não for um currículo legível.

    Segurança: o arquivo vem do candidato. Recusamos qualquer declaração de
    entidade (<!ENTITY), que é o que os ataques de XML usam ("billion laughs",
    entidade externa lendo arquivo do servidor). O XML exportado pelo Lattes
    não tem nenhuma. Sem isso, a proteção ficaria a cargo da versão da libexpat
    instalada na VM.

    Leitura tolerante, como na skill lattes-xml-extrator: há currículos
    exportados com caractere de controle ou "&" solto que quebram o parser, e
    recusá-los barraria candidatos por defeito do próprio Lattes.
    """
    if b"<!ENTITY" in conteudo:
        return None
    try:
        return ET.fromstring(conteudo)
    except ET.ParseError:
        pass
    texto = conteudo.decode("latin-1", errors="replace")
    texto = re.sub(r"^<\?xml[^>]*\?>", "", texto.lstrip())
    texto = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", texto)
    texto = re.sub(r"&(?!#?\w+;)", "&amp;", texto)
    try:
        return ET.fromstring(texto)
    except ET.ParseError:
        return None


class InscricaoChamadaForm(forms.Form):
    """Formulário de inscrição numa Chamada Interna.

    Desde 23/09/2026 o candidato não responde mais o quadro de critérios nem
    anexa comprovantes: envia o currículo Lattes em XML e declara a
    disponibilidade de horas. A pontuação é apurada pelo RH a partir do XML
    (skill lattes-xml-extrator) e lançada na tela de revisão.
    """

    vaga = forms.ModelChoiceField(
        label="Vaga pretendida",
        queryset=Vaga.objects.none(),
        empty_label="Selecione a vaga",
        required=False,
    )
    lattes_xml = forms.FileField(
        label="Currículo Lattes em XML",
        required=False,
        widget=forms.ClearableFileInput(attrs={"accept": ".xml"}),
        help_text=(
            "Na Plataforma Lattes, abra o seu currículo e use a opção de exportar "
            "em XML. O Lattes baixa um arquivo .zip: extraia e envie o .xml que "
            "está dentro. O currículo deve ter sido atualizado nos últimos 6 meses."
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

    def __init__(self, *args, chamada=None, usuario=None, acao=None, tem_xml=False, tem_pdf=False, **kwargs):
        self.chamada = chamada
        self.usuario = usuario
        self.acao = acao
        # A inscrição já tem um XML guardado (rascunho salvo antes): não exige
        # um novo upload para enviar.
        self.tem_xml = tem_xml
        self.tem_pdf = tem_pdf
        super().__init__(*args, **kwargs)
        if chamada is not None and usuario is not None:
            # Só as vagas compatíveis com o vínculo do candidato: estudante não
            # concorre a vaga de servidor.
            self.fields["vaga"].queryset = chamada.vagas.filter(
                modalidade=usuario.vinculo
            )

    def clean_lattes_xml(self):
        arquivo = self.cleaned_data.get("lattes_xml")
        if not arquivo:
            return arquivo
        if Path(arquivo.name).suffix.lower() != ".xml":
            raise ValidationError(
                "Envie o arquivo .xml. Se o Lattes baixou um .zip, extraia o .xml "
                "que está dentro dele."
            )
        if arquivo.size > MAX_XML_SIZE:
            mb = arquivo.size // 1024 // 1024
            raise ValidationError(f"O arquivo não pode ter mais de 10 MB (atual: {mb} MB).")
        raiz = ler_curriculo_lattes(arquivo.read())
        arquivo.seek(0)
        if raiz is None or raiz.tag != "CURRICULO-VITAE":
            raise ValidationError("O arquivo não é um currículo Lattes em XML.")
        # Item 5.4.2 da proposta de Edital: atualizado nos 6 meses anteriores à
        # inscrição, pela data que o próprio arquivo registra (DDMMAAAA).
        bruto = raiz.get("DATA-ATUALIZACAO", "")
        try:
            atualizado = date(int(bruto[4:]), int(bruto[2:4]), int(bruto[:2]))
        except ValueError:
            raise ValidationError("O arquivo não traz a data de atualização do currículo.")
        if (timezone.localdate() - atualizado).days > LATTES_VALIDADE_DIAS:
            raise ValidationError(
                f"Este currículo foi atualizado em {atualizado:%d/%m/%Y}, há mais de "
                "6 meses. Atualize o Lattes e exporte o XML de novo."
            )
        return arquivo

    def clean_licencas_maternidade(self):
        return self.cleaned_data.get("licencas_maternidade") or 0

    def clean(self):
        cleaned_data = super().clean()
        if self.acao != "enviar":
            return cleaned_data

        # Só exigidos no ENVIO. Salvar rascunho tem que funcionar com o
        # formulário pela metade.
        if not cleaned_data.get("vaga") and self.fields["vaga"].queryset.exists():
            self.add_error("vaga", "Selecione a vaga a que deseja concorrer.")
        if not cleaned_data.get("declara_disponibilidade"):
            self.add_error("declara_disponibilidade", "Declaração obrigatória para enviar.")
        if not cleaned_data.get("lattes_xml") and not self.tem_xml and "lattes_xml" not in self.errors:
            self.add_error("lattes_xml", "Envie o currículo Lattes em XML para concluir a inscrição.")
        return cleaned_data
