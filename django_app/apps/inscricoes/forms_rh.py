# apps/inscricoes/forms_rh.py
# Banco de Talentos — Polo de Inovação IFG
# Formulário de revisão RH: parecer geral e decisão final.

from django import forms


class RevisaoForm(forms.Form):
    VALID_ACOES = frozenset({"aprovar", "indeferir"})

    parecer_geral = forms.CharField(
        label="Parecer geral",
        widget=forms.Textarea(attrs={
            "rows": 3,
            "style": "width:100%;box-sizing:border-box;padding:6px 8px;border:1px solid #ccc;border-radius:6px;font-size:13px",
            "placeholder": "Registro da análise para o candidato...",
        }),
        required=False,
    )

    def __init__(self, *args, acao=None, **kwargs):
        self.acao = acao
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        if self.acao not in self.VALID_ACOES:
            return cleaned
        if self.acao == "indeferir" and not cleaned.get("parecer_geral", "").strip():
            self.add_error("parecer_geral", "O parecer é obrigatório ao indeferir.")
        return cleaned
