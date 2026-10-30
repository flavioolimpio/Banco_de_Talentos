from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.core.exceptions import ValidationError
from django.templatetags.static import static
from django.utils import timezone

from apps.usuarios.models import DECLARACOES_FORA_DO_VINCULO, Usuario, Vinculo, resumo_tem_tamanho_valido
from apps.usuarios.municipios import UF_CHOICES, municipios_de
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
    # Fora do Meta.fields de propósito: o ModelForm gravaria o True sem a data,
    # e confirmar_declaracao() — chamado na view — só grava a data se o campo
    # ainda estiver False.
    consentimento_verificacao_bases = forms.BooleanField(
        label="Consinto com a verificação das informações prestadas em bases internas do IFG "
              "(Lei nº 13.709/2018). Obrigatório para servidores(as) e estudantes.",
        required=False,
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
        vinculo = cleaned_data.get("vinculo")
        exige = "consentimento_verificacao_bases" not in DECLARACOES_FORA_DO_VINCULO.get(vinculo, set())
        if vinculo and exige and not cleaned_data.get("consentimento_verificacao_bases"):
            # Erro geral: o template não mostra erro de campo nas caixas de seleção.
            self.add_error(None, "Para servidores(as) e estudantes, é obrigatório consentir com a verificação em bases internas do IFG.")
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


class ServidorAtivoSelect(forms.NullBooleanSelect):
    def __init__(self, attrs=None):
        super().__init__(attrs)
        self.choices = (
            ("unknown", "Selecione"),
            ("true", "Sim"),
            ("false", "Não"),
        )


class MeuCadastroForm(forms.ModelForm):
    # Estado e cidade são selects encadeados. O estado tem lista fixa; a cidade
    # é preenchida em __init__ com os municípios do estado escolhido, para o
    # formulário funcionar mesmo sem JavaScript. Com JS (uf_cidade.js), a lista
    # troca na hora em que o estado muda.
    uf = forms.ChoiceField(
        label="Estado",
        required=False,
        choices=[("", "Selecione o estado")] + UF_CHOICES,
    )
    cidade = forms.ChoiceField(
        label="Cidade",
        required=False,
        choices=[("", "Selecione primeiro o estado")],
    )

    class Meta:
        model = Usuario
        # Campos do cadastro enxuto, conforme os blocos A–G de
        # docs/Estrutura_Perfil_Cadastro_Banco_Especialistas.md. Vários campos
        # que existiam aqui (gênero, LinkedIn, nível de formação em texto
        # livre) saíram do formulário — mas as COLUNAS continuam no banco.
        # Tirar do form não apaga dado. O mesmo vale para cnpq_area,
        # disponibilidade_semanal e nao_afastado_licenciado, que saíram em
        # 23/09/2026. Instituição (só estudante) e data de nascimento (desempate
        # por idade) voltaram em 28/10/2026.
        fields = [
            "nome_completo", "data_nascimento", "email", "telefone",
            "uf", "cidade",
            "categoria_pretendida", "servidor_ativo",
            "maior_titulacao", "instituicao", "area_atuacao", "resumo", "lattes",
        ]
        widgets = {
            # `placeholder` é o texto cinza-claro que aparece dentro do campo
            # vazio e some quando a pessoa digita: serve de EXEMPLO do formato
            # esperado. Não é máscara — não impede nem corrige nada. A máscara
            # de verdade (a que formata enquanto se digita) está em
            # static/js/mascaras.js e hoje só o telefone precisa dela.
            "telefone": forms.TextInput(attrs={
                "placeholder": "(62) 99999-9999",
                "inputmode": "tel",
                "data-mascara": "telefone",
            }),
            "email": forms.EmailInput(attrs={"placeholder": "nome@exemplo.com"}),
            "nome_completo": forms.TextInput(attrs={
                "placeholder": "Como consta no seu documento de identificação",
            }),
            # type="date" usa o calendário do próprio navegador. O format ISO
            # é obrigatório: é o único que o <input type="date"> entende para
            # mostrar a data já gravada.
            "data_nascimento": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "instituicao": forms.TextInput(attrs={
                "placeholder": "Ex.: IFG — Câmpus Anápolis",
            }),
            "area_atuacao": forms.TextInput(attrs={
                "placeholder": "Ex.: Engenharia Elétrica — Sistemas de Potência",
            }),
            "lattes": forms.URLInput(attrs={
                "placeholder": "http://lattes.cnpq.br/0000000000000000",
            }),
            "resumo": forms.Textarea(attrs={
                "rows": 6,
                "placeholder": (
                    "Descreva sua atuação profissional: formação, principais áreas "
                    "de trabalho, projetos e competências técnicas relevantes."
                ),
            }),
            "servidor_ativo": ServidorAtivoSelect,
        }
        labels = {
            "uf": "Estado (UF)",
            "email": "E-mail",
            "maior_titulacao": "Maior titulação concluída",
            "instituicao": "Instituição de ensino",
            "area_atuacao": "Curso e área de concentração",
            "resumo": "Resumo da atuação profissional",
        }
        help_texts = {
            "email": "Usado para a divulgação de vagas e para recuperar a senha.",
            "lattes": "Currículo atualizado nos últimos 6 meses.",
            "data_nascimento": "Usada no desempate por maior idade.",
            "resumo": "Entre 50 e 200 palavras.",
        }

    def __init__(self, *args, campos=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Só os campos da aba aberta. Sem isso o e-mail, obrigatório e presente
        # apenas na aba Dados, faltava no POST das outras abas: o formulário era
        # recusado e o erro não aparecia, porque o campo não estava na tela.
        if campos is not None:
            for nome in list(self.fields):
                if nome not in campos:
                    del self.fields[nome]
        for field in self.fields.values():
            field.required = False
        # ATENÇÃO: esta linha vem DEPOIS do laço acima de propósito. Sem ela o
        # e-mail ficaria opcional e salvar a aba com o campo vazio gravaria
        # email="" — o segundo usuário a fazer isso bateria no unique=True
        # (erro 500) e o primeiro perderia a recuperação de senha.
        if "email" in self.fields:
            self.fields["email"].required = True
        if "cidade" in self.fields:
            self._preparar_cidades()
        # Para o estudante, "curso" é o que ele cursa agora (Edital 31), não a
        # formação concluída de servidores e externos.
        if getattr(self.instance, "vinculo", "") == Vinculo.ESTUDANTE and "area_atuacao" in self.fields:
            self.fields["area_atuacao"].label = "Curso em andamento"
            self.fields["area_atuacao"].widget.attrs["placeholder"] = "Ex.: Bacharelado em Engenharia Civil"

    def _preparar_cidades(self):
        """Preenche as opções de cidade com os municípios do estado atual.

        No POST vale a UF que veio no formulário — senão o Django recusaria a
        cidade que o usuário acabou de escolher, por não constar das opções
        montadas a partir do valor antigo.
        """
        if self.is_bound:
            uf = self.data.get(self.add_prefix("uf"), "")
        else:
            uf = getattr(self.instance, "uf", "") or ""

        # O JS lê a URL daqui em vez de ter o caminho fixo no código: assim o
        # hash que o WhiteNoise põe no nome do arquivo em produção é respeitado.
        self.fields["cidade"].widget.attrs["data-municipios-url"] = static(
            "js/municipios.json"
        )

        cidades = municipios_de(uf)
        if cidades:
            self.fields["cidade"].choices = [("", "Selecione a cidade")] + [
                (nome, nome) for nome in cidades
            ]
        else:
            self.fields["cidade"].choices = [("", "Selecione primeiro o estado")]

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        # exclude(pk=...) é obrigatório: sem ele, quem salvasse a aba sem mudar
        # o e-mail colidiria com o próprio registro.
        duplicado = (
            Usuario.objects.filter(email__iexact=email)
            .exclude(pk=self.instance.pk)
            .exists()
        )
        if duplicado:
            raise ValidationError("Já existe um cadastro com este e-mail.")
        return email

    def clean_data_nascimento(self):
        # Pega erro de digitação (2062 no lugar de 1962). O piso de 14 anos
        # cobre o estudante de curso técnico integrado ao ensino médio.
        data = self.cleaned_data.get("data_nascimento")
        if data:
            hoje = timezone.localdate()
            idade = hoje.year - data.year - ((hoje.month, hoje.day) < (data.month, data.day))
            if not 14 <= idade <= 100:
                raise ValidationError("Confira a data de nascimento.")
        return data

    def clean_resumo(self):
        # Só valida quando preenchido: todos os campos são opcionais e exigir o
        # resumo aqui impediria de salvar qualquer outra aba.
        texto = (self.cleaned_data.get("resumo") or "").strip()
        if texto and not resumo_tem_tamanho_valido(texto):
            raise ValidationError(
                f"O resumo deve ter entre 50 e 200 palavras "
                f"(o seu tem {len(texto.split())})."
            )
        return texto
