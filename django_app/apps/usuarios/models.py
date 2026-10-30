from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

from apps.usuarios.cnpq import CNPQ_AREAS, GRANDES_AREAS_CNPQ


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


def resumo_tem_tamanho_valido(texto: str) -> bool:
    """Item 4.2 V do Edital: resumo de 50 a 200 palavras."""
    return 50 <= len(texto.split()) <= 200


# Cadastro completo (item 4.4.2 do Edital): os campos do item 4.2 mais as
# declarações. Cada vínculo tem o seu Edital — 29 (servidores), 30 (externos),
# 31 (estudantes) — e o estudante não tem categoria nem titulação: a categoria
# dele é "Estudante". Em troca, informa a instituição de ensino (IFG ou outra
# ICT) e o curso em andamento.
#
# A data de nascimento é o último critério de desempate (maior idade, Anexos I
# e III do Edital 29); pedida no cadastro, o desempate não depende de consulta
# posterior. A finalidade está declarada no item 4.2, I (LGPD, art. 6º, I).
#
# CAMPOS_CADASTRO é a lista completa; o que não se aplica ao vínculo some do
# formulário (CAMPOS_FORA_DO_VINCULO) e o que aparece mas não é obrigatório
# está em CAMPOS_OPCIONAIS_DO_VINCULO. Nome e e-mail ficam de fora porque o
# cadastro inicial já os exige.
CAMPOS_CADASTRO = [
    "data_nascimento", "telefone", "uf", "cidade",
    "categoria_pretendida", "servidor_ativo",
    "maior_titulacao", "instituicao", "area_atuacao", "resumo", "lattes",
]
CAMPOS_FORA_DO_VINCULO = {
    Vinculo.SERVIDOR: {"instituicao"},
    Vinculo.COLABORADOR_EXTERNO: {"instituicao", "servidor_ativo"},
    Vinculo.ESTUDANTE: {"categoria_pretendida", "servidor_ativo", "maior_titulacao"},
}
CAMPOS_OPCIONAIS_DO_VINCULO = {
    Vinculo.ESTUDANTE: {"resumo"},
}
DECLARACOES_CADASTRO = [
    "ciencia_credenciamento",
    "ciencia_comunicacoes",
    "declaracao_veracidade",
    "consentimento_verificacao_bases",
]
# Como cada pendência aparece para o candidato.
ROTULOS_PENDENCIA = {
    "data_nascimento": "data de nascimento",
    "telefone": "telefone",
    "uf": "estado",
    "cidade": "município",
    "categoria_pretendida": "categoria pretendida",
    "servidor_ativo": "situação funcional (ativo ou inativo)",
    "maior_titulacao": "maior titulação concluída",
    "instituicao": "instituição de ensino",
    "area_atuacao": "curso",
    "resumo": "resumo da atuação profissional (50 a 200 palavras)",
    "lattes": "link do currículo Lattes",
}


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

    cnpq_area = models.CharField(
        "área do conhecimento (CNPq)", max_length=10, choices=CNPQ_AREAS, blank=True
    )

    # Ciência de que receberá e-mail com a divulgação de vagas (Bloco F da
    # especificação). É CIÊNCIA, não consentimento: avisar quem está no Banco
    # a cada chamada é obrigação do Polo (item 5.2.2 do Edital), e ser avisado
    # de vagas é o próprio motivo de existir do cadastro. Por isso segue o
    # mesmo padrão de via única das demais declarações — ver
    # confirmar_declaracao(). Quem não quiser mais receber pede
    # descredenciamento do Banco (item 7.1), que é a saída prevista.
    ciencia_comunicacoes = models.BooleanField(
        "ciência de que receberá e-mail com a divulgação de vagas", default=False
    )
    ciencia_comunicacoes_em = models.DateTimeField(null=True, blank=True)

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
    def grande_area_cnpq(self) -> str:
        """Grande área derivada do prefixo do código — ex.: "1.06" → Exatas.

        Derivada em vez de armazenada numa segunda coluna, que só teria como
        ficar dessincronizada com a área.
        """
        if not self.cnpq_area:
            return ""
        return GRANDES_AREAS_CNPQ.get(self.cnpq_area[0], "")

    def pendencias_cadastro(self) -> list[str]:
        """O que falta para o cadastro ficar completo (item 4.4.2 do Edital).

        Lista vazia = credenciado(a) e apto(a) a se inscrever em Chamada
        Interna (item 5.3). Os campos exigidos dependem do vínculo: ver
        CAMPOS_CADASTRO e campos_cadastro_exigidos().
        """
        faltam = []
        for campo in self.campos_cadastro_exigidos():
            valor = getattr(self, campo)
            if valor in (None, ""):
                faltam.append(ROTULOS_PENDENCIA.get(campo, campo))
            elif campo == "resumo" and not resumo_tem_tamanho_valido(valor):
                # Resumo do cadastro antigo, gravado antes da regra das
                # 50 a 200 palavras: preenchido, mas fora do item 4.2 V.
                faltam.append(ROTULOS_PENDENCIA["resumo"])
        if not all(getattr(self, d) for d in DECLARACOES_CADASTRO):
            faltam.append("declarações (aba Declarações)")
        return faltam

    def campos_cadastro_exigidos(self) -> list[str]:
        """Campos do formulário que o vínculo precisa preencher."""
        fora = CAMPOS_FORA_DO_VINCULO.get(self.vinculo, set())
        opcionais = CAMPOS_OPCIONAIS_DO_VINCULO.get(self.vinculo, set())
        return [c for c in CAMPOS_CADASTRO if c not in fora | opcionais]

    @property
    def perfil_completo(self) -> bool:
        return not self.pendencias_cadastro()
