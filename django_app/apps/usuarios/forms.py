from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.core.exceptions import ValidationError

from apps.usuarios.models import Usuario, Vinculo
from apps.usuarios.validators import somente_digitos, validar_cpf


class LoginForm(forms.Form):
    identificador = forms.CharField(
        label="CPF ou e-mail",
        max_length=180,
        widget=forms.TextInput(attrs={"autocomplete": "username"}),
    )
    senha = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )
    lembrar = forms.BooleanField(label="Lembrar de mim neste navegador", required=False)

    error_messages = {
        "invalid_login": "CPF/e-mail ou senha inválidos.",
        "inactive": "Esta conta está inativa.",
    }

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        identificador = cleaned_data.get("identificador")
        senha = cleaned_data.get("senha")

        if identificador and senha:
            self.user_cache = authenticate(self.request, username=identificador, password=senha)
            if self.user_cache is None:
                raise ValidationError(self.error_messages["invalid_login"], code="invalid_login")
            if not self.user_cache.is_active:
                raise ValidationError(self.error_messages["inactive"], code="inactive")
        return cleaned_data

    def get_user(self):
        return self.user_cache


class CadastroUsuarioForm(forms.ModelForm):
    senha = forms.CharField(
        label="Senha",
        min_length=8,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    confirmar_senha = forms.CharField(
        label="Confirmar senha",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    aceite_lgpd = forms.BooleanField(
        label="Declaro que li e concordo com o uso dos meus dados para fins de cadastro, seleção e comunicação do Banco de Especialistas do Polo de Inovação do IFG."
    )

    class Meta:
        model = Usuario
        fields = ["vinculo", "nome_completo", "email", "cpf", "telefone", "lattes", "senha", "confirmar_senha", "aceite_lgpd"]
        widgets = {
            "cpf": forms.TextInput(attrs={"inputmode": "numeric", "autocomplete": "off"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
            "telefone": forms.TextInput(attrs={"autocomplete": "tel"}),
            "lattes": forms.URLInput(attrs={"placeholder": "http://lattes.cnpq.br/0000000000000000"}),
        }
        help_texts = {
            "lattes": "Necessário para cálculo automático de pontuação via IFGProduz (servidores). Pode ser preenchido depois em Meu Cadastro.",
        }

    def clean_cpf(self):
        cpf = validar_cpf(self.cleaned_data["cpf"])
        if Usuario.objects.filter(cpf=cpf).exists():
            raise ValidationError("Já existe cadastro com este CPF.")
        return cpf

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if Usuario.objects.filter(email__iexact=email).exists():
            raise ValidationError("Já existe cadastro com este e-mail.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        senha = cleaned_data.get("senha")
        confirmar_senha = cleaned_data.get("confirmar_senha")
        if senha and confirmar_senha and senha != confirmar_senha:
            self.add_error("confirmar_senha", "As senhas não conferem.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.cpf = somente_digitos(user.cpf)
        user.perfil = "candidato"
        user.set_password(self.cleaned_data["senha"])
        if commit:
            user.save()
        return user


class RecuperacaoSenhaForm(PasswordResetForm):
    email = forms.EmailField(label="E-mail cadastrado", max_length=254)


class NovaSenhaForm(SetPasswordForm):
    pass


class MeuCadastroForm(forms.ModelForm):
    nao_afastado_licenciado = forms.BooleanField(required=False, label="não afastado(a)/licenciado(a)")

    class Meta:
        model = Usuario
        fields = [
            "nome_completo", "telefone", "data_nascimento",
            "genero", "resumo",
            "uf", "cidade",
            "nivel_formacao", "area_atuacao", "lattes", "linkedin", "instituicao",
            "categoria_pretendida", "servidor_ativo", "maior_titulacao",
            "disponibilidade_semanal", "nao_afastado_licenciado",
        ]
        widgets = {
            "data_nascimento": forms.DateInput(
                attrs={"type": "date"}, format="%Y-%m-%d"
            ),
            "resumo": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.data_nascimento:
            self.initial["data_nascimento"] = self.instance.data_nascimento.strftime(
                "%Y-%m-%d"
            )
        for field in self.fields.values():
            field.required = False

    def clean_disponibilidade_semanal(self):
        horas = self.cleaned_data.get("disponibilidade_semanal")
        if horas is None:
            return horas
        servidor_ativo = self.instance.vinculo == Vinculo.SERVIDOR and self.cleaned_data.get("servidor_ativo")
        maximo = 20 if servidor_ativo else 40
        if not (5 <= horas <= maximo):
            raise ValidationError(f"Disponibilidade deve estar entre 5 e {maximo} horas semanais.")
        return horas
