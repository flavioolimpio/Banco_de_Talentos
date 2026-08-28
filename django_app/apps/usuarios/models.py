from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone


class Vinculo(models.TextChoices):
    ESTUDANTE = "estudante", "Estudante"
    SERVIDOR = "servidor", "Servidor(a)"
    COLABORADOR_EXTERNO = "colaborador_externo", "Colaborador(a) Externo(a)"


class Perfil(models.TextChoices):
    CANDIDATO = "candidato", "Candidato(a)"
    RH = "rh", "RH"
    COORDENADOR = "coordenador", "Coordenador"
    ADMIN = "admin", "Administrador"


class Genero(models.TextChoices):
    FEMININO = "feminino", "Feminino"
    MASCULINO = "masculino", "Masculino"
    NAO_INFORMADO = "nao_informado", "Prefiro não informar"


class CategoriaPretendida(models.TextChoices):
    PESQUISADOR = "pesquisador", "Pesquisador(a)"
    APOIO_TECNICO = "apoio_tecnico", "Apoio técnico"


class MaiorTitulacao(models.TextChoices):
    TECNICO = "tecnico", "Médio/Técnico"
    GRADUACAO = "graduacao", "Graduação"
    ESPECIALIZACAO = "especializacao", "Especialização"
    MESTRADO = "mestrado", "Mestrado"
    DOUTORADO = "doutorado", "Doutorado"


class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, cpf: str, email: str, password: str | None, **extra_fields):
        if not cpf:
            raise ValueError("O CPF é obrigatório.")
        if not email:
            raise ValueError("O e-mail é obrigatório.")

        email = self.normalize_email(email)
        user = self.model(cpf=cpf, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, cpf: str, email: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(cpf, email, password, **extra_fields)

    def create_superuser(self, cpf: str, email: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("perfil", Perfil.ADMIN)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superusuário precisa ter is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superusuário precisa ter is_superuser=True.")

        return self._create_user(cpf, email, password, **extra_fields)


class Usuario(AbstractUser):
    username = None
    first_name = None
    last_name = None

    cpf_validator = RegexValidator(
        regex=r"^\d{11}$",
        message="Informe o CPF com 11 dígitos, sem pontos ou traços.",
    )

    cpf = models.CharField("CPF", max_length=11, unique=True, validators=[cpf_validator])
    nome_completo = models.CharField("nome completo", max_length=180)
    email = models.EmailField("e-mail", unique=True)
    telefone = models.CharField("telefone", max_length=30, blank=True)
    vinculo = models.CharField("vínculo", max_length=30, choices=Vinculo.choices)
    instituicao = models.CharField("instituição", max_length=180, blank=True)
    lattes = models.URLField("currículo Lattes", blank=True)
    resumo = models.TextField("resumo profissional", blank=True)
    perfil = models.CharField(max_length=30, choices=Perfil.choices, default=Perfil.CANDIDATO)

    data_nascimento = models.DateField("data de nascimento", null=True, blank=True)
    rg = models.CharField("RG", max_length=30, blank=True)
    orgao_emissor = models.CharField("órgão emissor", max_length=30, blank=True)
    genero = models.CharField("gênero", max_length=30, choices=Genero.choices, blank=True)

    cep = models.CharField("CEP", max_length=9, blank=True)
    endereco = models.CharField("endereço", max_length=220, blank=True)
    numero = models.CharField("número", max_length=20, blank=True)
    complemento = models.CharField("complemento", max_length=120, blank=True)
    bairro = models.CharField("bairro", max_length=120, blank=True)
    cidade = models.CharField("cidade", max_length=120, blank=True)
    uf = models.CharField("UF", max_length=2, blank=True)

    nivel_formacao = models.CharField("nível de formação", max_length=80, blank=True)
    area_atuacao = models.CharField("área de atuação", max_length=120, blank=True)
    linkedin = models.URLField("LinkedIn", blank=True)

    aceite_lgpd = models.BooleanField("aceite LGPD", default=False)
    aceite_lgpd_em = models.DateTimeField("data/hora do aceite LGPD", null=True, blank=True)
    aceite_lgpd_versao = models.CharField("versão do termo LGPD", max_length=30, blank=True)
    aceite_lgpd_ip = models.GenericIPAddressField("IP do aceite LGPD", null=True, blank=True)

    categoria_pretendida = models.CharField(
        "categoria pretendida", max_length=30, choices=CategoriaPretendida.choices, blank=True
    )
    servidor_ativo = models.BooleanField("servidor(a) ativo(a)", null=True, blank=True)
    maior_titulacao = models.CharField(
        "maior titulação", max_length=30, choices=MaiorTitulacao.choices, blank=True
    )
    disponibilidade_semanal = models.PositiveSmallIntegerField(
        "disponibilidade semanal (horas)", null=True, blank=True
    )
    nao_afastado_licenciado = models.BooleanField(
        "não afastado(a)/licenciado(a)", null=True, blank=True
    )

    ciencia_credenciamento = models.BooleanField("ciência de que o credenciamento não garante vaga", default=False)
    ciencia_credenciamento_em = models.DateTimeField(null=True, blank=True)
    declaracao_veracidade = models.BooleanField("declaração de veracidade (art. 299 CP)", default=False)
    declaracao_veracidade_em = models.DateTimeField(null=True, blank=True)
    consentimento_verificacao_bases = models.BooleanField(
        "consentimento de verificação em bases internas", default=False
    )
    consentimento_verificacao_bases_em = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField("criado em", auto_now_add=True)
    updated_at = models.DateTimeField("atualizado em", auto_now=True)

    objects = UsuarioManager()

    USERNAME_FIELD = "cpf"
    REQUIRED_FIELDS = ["email", "nome_completo"]

    class Meta:
        verbose_name = "usuário"
        verbose_name_plural = "usuários"
        ordering = ["nome_completo"]

    def __str__(self) -> str:
        return f"{self.nome_completo} ({self.cpf})"

    def registrar_aceite_lgpd(self, versao: str, ip: str | None = None) -> None:
        self.aceite_lgpd = True
        self.aceite_lgpd_em = timezone.now()
        self.aceite_lgpd_versao = versao
        self.aceite_lgpd_ip = ip

    def confirmar_declaracao(self, campo: str) -> None:
        if not getattr(self, campo):
            setattr(self, campo, True)
            setattr(self, f"{campo}_em", timezone.now())

    @property
    def perfil_completo(self) -> bool:
        campos = [
            self.categoria_pretendida,
            self.maior_titulacao,
            self.area_atuacao,
            self.disponibilidade_semanal,
        ]
        if self.vinculo == Vinculo.SERVIDOR:
            campos.append(self.servidor_ativo)
        declaracoes = [
            self.ciencia_credenciamento,
            self.declaracao_veracidade,
            self.consentimento_verificacao_bases,
        ]
        if self.vinculo == Vinculo.SERVIDOR and self.servidor_ativo:
            declaracoes.append(self.nao_afastado_licenciado)
        return all(c not in (None, "") for c in campos) and all(declaracoes)
