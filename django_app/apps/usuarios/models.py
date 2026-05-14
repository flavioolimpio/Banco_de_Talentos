from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone


class Vinculo(models.TextChoices):
    ESTUDANTE = "estudante", "Estudante"
    SERVIDOR = "servidor", "Servidor"
    COLABORADOR_EXTERNO = "colaborador_externo", "Colaborador Externo"


class Perfil(models.TextChoices):
    CANDIDATO = "candidato", "Candidato"
    RH = "rh", "RH"
    COORDENADOR = "coordenador", "Coordenador"
    ADMIN = "admin", "Administrador"


class Genero(models.TextChoices):
    FEMININO = "feminino", "Feminino"
    MASCULINO = "masculino", "Masculino"
    NAO_INFORMADO = "nao_informado", "Prefiro não informar"


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
