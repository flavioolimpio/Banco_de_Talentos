from datetime import date

from django.test import TestCase
from django.urls import reverse

from apps.usuarios.models import (
    DECLARACOES_CADASTRO,
    CategoriaPretendida,
    MaiorTitulacao,
    Usuario,
    Vinculo,
)
from apps.usuarios.validators import validar_cpf

RESUMO_VALIDO = " ".join(["palavra"] * 60)

_VALORES_CADASTRO = {
    "data_nascimento": date(1980, 5, 17),
    "telefone": "(62) 99999-9999",
    "uf": "GO",
    "cidade": "Anápolis",
    "categoria_pretendida": CategoriaPretendida.PESQUISADOR,
    "servidor_ativo": True,
    "maior_titulacao": MaiorTitulacao.DOUTORADO,
    "instituicao": "IFG — Câmpus Anápolis",
    "area_atuacao": "Química",
    "resumo": RESUMO_VALIDO,
    "lattes": "http://lattes.cnpq.br/1234567890123456",
}


def preencher_campos_cadastro(usuario, exceto=()):
    """Preenche os campos que o vínculo exige (sem as declarações e sem salvar)."""
    for campo in usuario.campos_cadastro_exigidos():
        if campo not in exceto:
            setattr(usuario, campo, _VALORES_CADASTRO[campo])


def completar_cadastro(usuario):
    """Cadastro completo (item 4.4.2): campos do vínculo + declarações, salvo."""
    preencher_campos_cadastro(usuario)
    for campo in DECLARACOES_CADASTRO:
        usuario.confirmar_declaracao(campo)
    usuario.save()


class CpfValidatorTests(TestCase):
    def test_accepts_valid_cpf_with_mask(self):
        self.assertEqual(validar_cpf("529.982.247-25"), "52998224725")

    def test_rejects_invalid_cpf(self):
        with self.assertRaises(Exception):
            validar_cpf("111.111.111-11")


class LoginFlowTests(TestCase):
    def setUp(self):
        self.user = Usuario.objects.create_user(
            cpf="52998224725",
            email="teste@ifg.edu.br",
            nome_completo="Usuário Teste",
            vinculo=Vinculo.SERVIDOR,
            password="senha-forte-123",
        )

    def test_login_with_cpf(self):
        response = self.client.post(reverse("login"), {"identificador": self.user.cpf, "senha": "senha-forte-123"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], reverse("home"))

    def test_login_with_email(self):
        response = self.client.post(reverse("login"), {"identificador": self.user.email, "senha": "senha-forte-123"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], reverse("home"))


from apps.inscricoes.models import Inscricao, StatusInscricao


class HomeViewTest(TestCase):
    def setUp(self):
        self.candidato = Usuario.objects.create_user(
            cpf="11144477735",
            email="candidato@test.com",
            nome_completo="Candidata Teste",
            vinculo=Vinculo.ESTUDANTE,
            password="senha123",
        )
        self.client.force_login(self.candidato)

    def test_home_retorna_200(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)

    def test_home_aponta_para_minhas_inscricoes(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, reverse("chamadas"))


    def test_home_exibe_foto_do_polo(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, "imagens/polo.jpg")

    def test_home_nao_menciona_energia(self):
        # A home deixou de carregar o escopo antigo do Polo (energia) — decisão
        # da gestão em 18/09/2026.
        response = self.client.get(reverse("home"))
        self.assertNotContains(response, "Energ")
        self.assertNotContains(response, "energ")


class SidebarTest(TestCase):
    def setUp(self):
        self.user = Usuario.objects.create_user(
            cpf="52998224725",
            email="sidebar@test.com",
            nome_completo="Usuário Sidebar",
            vinculo=Vinculo.SERVIDOR,
            password="senha123",
        )
        self.client.force_login(self.user)

    def test_home_tem_sidebar(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, 'class="sidebar"')

    def test_home_tem_link_de_inscricoes_na_sidebar(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, reverse("chamadas"))

    def test_login_nao_tem_sidebar(self):
        self.client.logout()
        response = self.client.get(reverse("login"))
        self.assertNotContains(response, 'class="sidebar"')


class MeuCadastroFormTest(TestCase):
    def setUp(self):
        self.user = Usuario.objects.create_user(
            cpf="52998224725",
            email="formtest@test.com",
            nome_completo="Form Teste",
            vinculo=Vinculo.SERVIDOR,
            password="senha123",
        )

    def test_form_salva_nome_completo(self):
        from apps.usuarios.forms import MeuCadastroForm
        form = MeuCadastroForm(
            {"nome_completo": "Novo Nome", "email": self.user.email, "telefone": "", "resumo": ""},
            instance=self.user,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_nao_tem_campo_cpf(self):
        from apps.usuarios.forms import MeuCadastroForm
        form = MeuCadastroForm(instance=self.user)
        self.assertNotIn("cpf", form.fields)

    def test_form_tem_campo_email_obrigatorio(self):
        # O e-mail passou a ser editável pelo candidato (ele é o canal de
        # divulgação das chamadas). Continua obrigatório: salvar em branco
        # gravaria email="" e colidiria no unique com o próximo que fizesse
        # o mesmo, além de derrubar a recuperação de senha.
        from apps.usuarios.forms import MeuCadastroForm
        form = MeuCadastroForm(instance=self.user)
        self.assertIn("email", form.fields)
        self.assertTrue(form.fields["email"].required)

    def test_form_rejeita_email_em_branco(self):
        from apps.usuarios.forms import MeuCadastroForm
        form = MeuCadastroForm({"nome_completo": "X", "email": ""}, instance=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_form_rejeita_email_de_outro_usuario(self):
        from apps.usuarios.forms import MeuCadastroForm
        Usuario.objects.create_user(
            cpf="11144477735",
            email="ocupado@test.com",
            nome_completo="Outro",
            vinculo=Vinculo.SERVIDOR,
            password="senha123",
        )
        form = MeuCadastroForm(
            {"nome_completo": "X", "email": "OCUPADO@test.com"}, instance=self.user
        )
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_form_aceita_o_proprio_email_sem_alteracao(self):
        # Sem o exclude(pk=...) no clean_email, salvar sem mudar o e-mail
        # colidiria com o próprio registro.
        from apps.usuarios.forms import MeuCadastroForm
        form = MeuCadastroForm(
            {"nome_completo": "X", "email": self.user.email}, instance=self.user
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_valida_tamanho_do_resumo(self):
        from apps.usuarios.forms import MeuCadastroForm
        curto = MeuCadastroForm(
            {"nome_completo": "X", "email": self.user.email, "resumo": "palavra " * 10},
            instance=self.user,
        )
        self.assertFalse(curto.is_valid())
        self.assertIn("resumo", curto.errors)

        longo = MeuCadastroForm(
            {"nome_completo": "X", "email": self.user.email, "resumo": "palavra " * 300},
            instance=self.user,
        )
        self.assertFalse(longo.is_valid())

        ok = MeuCadastroForm(
            {"nome_completo": "X", "email": self.user.email, "resumo": "palavra " * 80},
            instance=self.user,
        )
        self.assertTrue(ok.is_valid(), ok.errors)

    def test_form_nao_tem_campo_vinculo(self):
        from apps.usuarios.forms import MeuCadastroForm
        form = MeuCadastroForm(instance=self.user)
        self.assertNotIn("vinculo", form.fields)


class MeuCadastroViewTest(TestCase):
    def setUp(self):
        self.user = Usuario.objects.create_user(
            cpf="52998224725",
            email="mcadastro@test.com",
            nome_completo="Cadastro Teste",
            vinculo=Vinculo.SERVIDOR,
            password="senha123",
        )
        self.client.force_login(self.user)

    def test_get_retorna_200(self):
        response = self.client.get(reverse("meu_cadastro"))
        self.assertEqual(response.status_code, 200)

    def test_get_exibe_nome_usuario(self):
        response = self.client.get(reverse("meu_cadastro"))
        self.assertContains(response, "Cadastro Teste")

    def test_get_exibe_cpf_formatado(self):
        response = self.client.get(reverse("meu_cadastro"))
        self.assertContains(response, "529.982.247-25")

    def test_get_aba_padrao_e_dados(self):
        response = self.client.get(reverse("meu_cadastro"))
        self.assertContains(response, "Dados Pessoais")

    def test_aba_dados_tem_estado_e_cidade(self):
        # A aba "Endereço" deixou de existir: estado e cidade subiram para
        # "Dados", e viraram selects encadeados.
        response = self.client.get(reverse("meu_cadastro") + "?aba=dados")
        self.assertContains(response, 'name="uf"')
        self.assertContains(response, 'name="cidade"')
        self.assertContains(response, "Goiás (GO)")

    def test_link_antigo_de_endereco_cai_em_dados(self):
        response = self.client.get(reverse("meu_cadastro") + "?aba=endereco")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dados Pessoais")

    def test_get_aba_formacao(self):
        response = self.client.get(reverse("meu_cadastro") + "?aba=formacao")
        self.assertContains(response, "Lattes")

    def test_post_salva_nome_completo(self):
        self.client.post(
            reverse("meu_cadastro") + "?aba=dados",
            {"nome_completo": "Nome Atualizado", "email": self.user.email, "telefone": ""},
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.nome_completo, "Nome Atualizado")

    def test_post_altera_email(self):
        from apps.auditoria.models import AuditAction, AuditLog
        email_original = self.user.email
        self.client.post(
            reverse("meu_cadastro") + "?aba=dados",
            {"nome_completo": "X", "email": "Novo.Email@IFG.edu.br"},
        )
        self.user.refresh_from_db()
        # normalizado para minúsculas, igual ao cadastro inicial
        self.assertEqual(self.user.email, "novo.email@ifg.edu.br")
        log = AuditLog.objects.filter(
            ator=self.user, acao=AuditAction.CADASTRO_ATUALIZADO
        ).latest("id")
        self.assertEqual(log.detalhes["email_anterior"], email_original)
        self.assertEqual(log.detalhes["email_novo"], "novo.email@ifg.edu.br")

    def test_post_nao_altera_email_para_o_de_outro_usuario(self):
        Usuario.objects.create_user(
            cpf="11144477735",
            email="ocupado@test.com",
            nome_completo="Outro",
            vinculo=Vinculo.SERVIDOR,
            password="senha123",
        )
        email_original = self.user.email
        self.client.post(
            reverse("meu_cadastro") + "?aba=dados",
            {"nome_completo": "X", "email": "ocupado@test.com"},
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, email_original)

    def test_post_nao_altera_vinculo(self):
        vinculo_original = self.user.vinculo
        self.client.post(
            reverse("meu_cadastro") + "?aba=dados",
            {"nome_completo": "X", "email": self.user.email, "vinculo": "estudante"},
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.vinculo, vinculo_original)

    def test_post_salva_apenas_aba_dados_sem_sobrescrever_endereco(self):
        self.user.cep = "75000000"
        self.user.save(update_fields=["cep"])
        self.client.post(
            reverse("meu_cadastro") + "?aba=dados",
            {"nome_completo": "Novo Nome", "email": self.user.email},
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.cep, "75000000")

    def test_get_sem_login_redireciona(self):
        self.client.logout()
        response = self.client.get(reverse("meu_cadastro"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('meu_cadastro')}")

    def test_post_cross_tab_nao_salva_campo_de_outra_aba(self):
        """POST com cep para ?aba=dados NÃO deve persistir o cep."""
        self.user.cep = "75000000"
        self.user.save(update_fields=["cep"])
        self.client.post(
            reverse("meu_cadastro") + "?aba=dados",
            {"nome_completo": "Novo Nome", "email": self.user.email, "cep": "99999999"},
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.cep, "75000000")

    def test_post_nao_altera_cpf(self):
        """CPF nunca pode ser alterado via POST."""
        cpf_original = self.user.cpf
        self.client.post(
            reverse("meu_cadastro") + "?aba=dados",
            {"nome_completo": "X", "email": self.user.email, "cpf": "11144477735"},
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.cpf, cpf_original)

    def test_get_aba_invalida_usa_aba_dados(self):
        """?aba=hacker deve ser tratado como ?aba=dados."""
        response = self.client.get(reverse("meu_cadastro") + "?aba=hacker")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dados Pessoais")

    def test_post_registra_auditlog(self):
        """Salvar cadastro deve criar um AuditLog com CADASTRO_ATUALIZADO."""
        from apps.auditoria.models import AuditLog, AuditAction
        self.client.post(
            reverse("meu_cadastro") + "?aba=dados",
            {"nome_completo": "Log Teste", "email": self.user.email},
        )
        self.assertTrue(
            AuditLog.objects.filter(
                ator=self.user,
                acao=AuditAction.CADASTRO_ATUALIZADO,
            ).exists()
        )


from apps.usuarios.models import CategoriaPretendida, MaiorTitulacao


class PerfilProfissionalModelTest(TestCase):
    def setUp(self):
        self.servidor = Usuario.objects.create_user(
            cpf="11144477735",
            email="perfilservidor@test.com",
            nome_completo="Servidor Perfil",
            vinculo=Vinculo.SERVIDOR,
            password="senha123",
        )
        self.externo = Usuario.objects.create_user(
            cpf="52998224725",
            email="perfilexterno@test.com",
            nome_completo="Externo Perfil",
            vinculo=Vinculo.COLABORADOR_EXTERNO,
            password="senha123",
        )

    def _preencher_campos_base(self, usuario):
        preencher_campos_cadastro(usuario, exceto={"servidor_ativo"})

    def _confirmar_todas_declaracoes(self, usuario):
        usuario.confirmar_declaracao("ciencia_credenciamento")
        usuario.confirmar_declaracao("ciencia_comunicacoes")
        usuario.confirmar_declaracao("declaracao_veracidade")
        usuario.confirmar_declaracao("consentimento_verificacao_bases")

    def test_perfil_incompleto_por_padrao(self):
        self.assertFalse(self.servidor.perfil_completo)
        self.assertFalse(self.externo.perfil_completo)

    def test_perfil_completo_para_colaborador_externo(self):
        self._preencher_campos_base(self.externo)
        self._confirmar_todas_declaracoes(self.externo)
        self.assertTrue(self.externo.perfil_completo)

    def test_servidor_ativo_nao_precisa_mais_declarar_afastamento(self):
        # A caixa "não afastado(a)/licenciado(a)" saiu do cadastro em
        # 23/09/2026: o requisito do item 4.1.1 é verificado em bases internas.
        self._preencher_campos_base(self.servidor)
        self._confirmar_todas_declaracoes(self.servidor)
        self.servidor.servidor_ativo = True
        self.assertTrue(self.servidor.perfil_completo)

    def test_servidor_precisa_informar_se_esta_ativo(self):
        self._preencher_campos_base(self.servidor)
        self._confirmar_todas_declaracoes(self.servidor)
        self.assertFalse(self.servidor.perfil_completo)

    def test_servidor_inativo_nao_precisa_declarar_afastamento(self):
        self._preencher_campos_base(self.servidor)
        self._confirmar_todas_declaracoes(self.servidor)
        self.servidor.servidor_ativo = False
        self.assertTrue(self.servidor.perfil_completo)

    def test_confirmar_declaracao_grava_booleano_e_timestamp(self):
        self.assertFalse(self.externo.declaracao_veracidade)
        self.assertIsNone(self.externo.declaracao_veracidade_em)
        self.externo.confirmar_declaracao("declaracao_veracidade")
        self.assertTrue(self.externo.declaracao_veracidade)
        self.assertIsNotNone(self.externo.declaracao_veracidade_em)

    def test_confirmar_declaracao_nao_atualiza_timestamp_se_ja_confirmada(self):
        self.externo.confirmar_declaracao("declaracao_veracidade")
        primeira_data = self.externo.declaracao_veracidade_em
        self.externo.confirmar_declaracao("declaracao_veracidade")
        self.assertEqual(self.externo.declaracao_veracidade_em, primeira_data)


class CamposRetiradosDoCadastroTest(TestCase):
    """Campos que saíram do formulário em 23/09/2026. As colunas continuam no
    banco — tirar do form não apaga dado."""

    def test_form_nao_tem_mais_os_campos(self):
        from apps.usuarios.forms import MeuCadastroForm
        form = MeuCadastroForm()
        for campo in ("cnpq_area", "disponibilidade_semanal", "nao_afastado_licenciado"):
            self.assertNotIn(campo, form.fields)

    def test_rotulo_do_curso(self):
        from apps.usuarios.forms import MeuCadastroForm
        form = MeuCadastroForm()
        self.assertEqual(form.fields["area_atuacao"].label, "Curso e área de concentração")


class MeuCadastroPerfilViewTest(TestCase):
    def setUp(self):
        self.servidor = Usuario.objects.create_user(
            cpf="11144477735",
            email="viewservidor@test.com",
            nome_completo="Servidor View",
            vinculo=Vinculo.SERVIDOR,
            password="senha123",
        )
        self.externo = Usuario.objects.create_user(
            cpf="52998224725",
            email="viewexterno@test.com",
            nome_completo="Externo View",
            vinculo=Vinculo.COLABORADOR_EXTERNO,
            password="senha123",
        )

    def test_aba_dados_para_servidor_mostra_campo_servidor_ativo(self):
        # servidor_ativo e categoria_pretendida subiram da aba "perfil" para
        # "dados" — são identificação/vínculo (Bloco A da especificação).
        self.client.force_login(self.servidor)
        response = self.client.get(reverse("meu_cadastro") + "?aba=dados")
        self.assertContains(response, "name=\"servidor_ativo\"")

    def test_aba_dados_para_externo_esconde_campo_servidor_ativo(self):
        self.client.force_login(self.externo)
        response = self.client.get(reverse("meu_cadastro") + "?aba=dados")
        self.assertNotContains(response, "name=\"servidor_ativo\"")

    def test_post_dados_salva_categoria(self):
        self.client.force_login(self.externo)
        self.client.post(
            reverse("meu_cadastro") + "?aba=dados",
            {"nome_completo": "X", "email": self.externo.email,
             "categoria_pretendida": "pesquisador"},
        )
        self.externo.refresh_from_db()
        self.assertEqual(self.externo.categoria_pretendida, "pesquisador")

    def test_maior_titulacao_fica_na_aba_formacao(self):
        # Voltou ao formulário (lista fechada), na aba Formação — não na Perfil.
        self.client.force_login(self.externo)
        perfil = self.client.get(reverse("meu_cadastro") + "?aba=perfil")
        self.assertNotContains(perfil, "name=\"maior_titulacao\"")
        formacao = self.client.get(reverse("meu_cadastro") + "?aba=formacao")
        self.assertContains(formacao, "name=\"maior_titulacao\"")
        self.assertNotContains(formacao, "name=\"cnpq_area\"")

    def test_aba_perfil_se_chama_declaracoes_e_nao_tem_disponibilidade(self):
        self.client.force_login(self.servidor)
        resposta = self.client.get(reverse("meu_cadastro") + "?aba=perfil")
        self.assertContains(resposta, "Declara&ccedil;&otilde;es")
        self.assertNotContains(resposta, "Perfil Profissional")
        self.assertNotContains(resposta, "name=\"disponibilidade_semanal\"")
        self.assertNotContains(resposta, "afastado")

    def test_post_formacao_sem_email_salva(self):
        # Regressão: o POST da aba Formação não traz o e-mail (ele está na aba
        # Dados). Com o e-mail obrigatório no form inteiro, a aba era recusada
        # sem mostrar erro nenhum e nada era gravado.
        self.client.force_login(self.externo)
        resposta = self.client.post(
            reverse("meu_cadastro") + "?aba=formacao",
            {"area_atuacao": "Química — Química Computacional"},
        )
        self.assertEqual(resposta.status_code, 302)
        self.externo.refresh_from_db()
        self.assertEqual(self.externo.area_atuacao, "Química — Química Computacional")
        self.assertEqual(self.externo.email, "viewexterno@test.com")

    def test_post_declaracoes_sem_email_salva(self):
        self.client.force_login(self.externo)
        resposta = self.client.post(
            reverse("meu_cadastro") + "?aba=perfil",
            {"declaracao_veracidade": "on"},
        )
        self.assertEqual(resposta.status_code, 302)
        self.externo.refresh_from_db()
        self.assertTrue(self.externo.declaracao_veracidade)

    def test_consentimento_so_aparece_para_quem_ainda_nao_deu(self):
        self.client.force_login(self.servidor)
        url = reverse("meu_cadastro") + "?aba=perfil"
        self.assertContains(self.client.get(url), 'name="consentimento_verificacao_bases"')
        self.servidor.confirmar_declaracao("consentimento_verificacao_bases")
        self.servidor.save()
        self.assertNotContains(self.client.get(url), 'name="consentimento_verificacao_bases"')

    def test_externo_nao_firma_consentimento_de_bases(self):
        """Edital 30: não há verificação em bases internas do IFG para o externo."""
        self.client.force_login(self.externo)
        url = reverse("meu_cadastro") + "?aba=perfil"
        self.assertNotContains(self.client.get(url), 'name="consentimento_verificacao_bases"')
        completar_cadastro(self.externo)
        self.externo.consentimento_verificacao_bases = False
        self.assertTrue(self.externo.perfil_completo)

    def test_post_perfil_grava_declaracao_com_timestamp(self):
        self.client.force_login(self.externo)
        self.client.post(
            reverse("meu_cadastro") + "?aba=perfil",
            {"nome_completo": "X", "email": self.externo.email, "declaracao_veracidade": "on"},
        )
        self.externo.refresh_from_db()
        self.assertTrue(self.externo.declaracao_veracidade)
        self.assertIsNotNone(self.externo.declaracao_veracidade_em)

    def test_post_perfil_nao_desmarca_declaracao_ja_confirmada(self):
        self.externo.confirmar_declaracao("declaracao_veracidade")
        self.externo.save(update_fields=["declaracao_veracidade", "declaracao_veracidade_em"])
        primeira_data = self.externo.declaracao_veracidade_em
        self.client.force_login(self.externo)
        self.client.post(
            reverse("meu_cadastro") + "?aba=perfil",
            {"nome_completo": "X", "email": self.externo.email},
        )
        self.externo.refresh_from_db()
        self.assertTrue(self.externo.declaracao_veracidade)
        self.assertEqual(self.externo.declaracao_veracidade_em, primeira_data)

    def test_post_perfil_servidor_nao_persiste_servidor_ativo_de_externo(self):
        """Colaborador externo postando a aba perfil não grava servidor_ativo (nem existe no form pra ele)."""
        self.client.force_login(self.externo)
        self.client.post(
            reverse("meu_cadastro") + "?aba=perfil",
            {"nome_completo": "X", "email": self.externo.email, "servidor_ativo": "true"},
        )
        self.externo.refresh_from_db()
        self.assertIsNone(self.externo.servidor_ativo)


class HomeBannerPerfilTest(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            cpf="11144477735",
            email="bannerhome@test.com",
            nome_completo="Banner Teste",
            vinculo=Vinculo.COLABORADOR_EXTERNO,
            password="senha123",
        )
        self.client.force_login(self.usuario)

    def test_banner_aparece_quando_perfil_incompleto(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Complete seu perfil")

    def test_banner_some_quando_perfil_completo(self):
        completar_cadastro(self.usuario)
        response = self.client.get(reverse("home"))
        self.assertNotContains(response, "Complete seu perfil")


class CienciaComunicacoesTest(TestCase):
    """Ciência de que receberá a divulgação de vagas.

    NÃO é consentimento: avisar quem está no Banco a cada chamada é obrigação
    do Polo (item 5.2.2 do Edital), e ser avisado de vagas é o motivo de
    existir do cadastro. Segue o mesmo padrão de via única das demais
    declarações — marcou, fica marcado. Quem não quiser mais receber pede
    descredenciamento (item 7.1).
    """

    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            cpf="11144477735",
            email="comunicacoes@test.com",
            nome_completo="Comunicações Teste",
            vinculo=Vinculo.COLABORADOR_EXTERNO,
            password="senha123",
        )
        self.client.force_login(self.usuario)

    def _post_perfil(self, **extra):
        dados = {"nome_completo": "X", "email": self.usuario.email}
        dados.update(extra)
        return self.client.post(reverse("meu_cadastro") + "?aba=perfil", dados)

    def test_comeca_desmarcada(self):
        self.assertFalse(self.usuario.ciencia_comunicacoes)
        self.assertIsNone(self.usuario.ciencia_comunicacoes_em)

    def test_marcar_grava_timestamp(self):
        self._post_perfil(ciencia_comunicacoes="on")
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.ciencia_comunicacoes)
        self.assertIsNotNone(self.usuario.ciencia_comunicacoes_em)

    def test_nao_desmarca_depois_de_confirmada(self):
        self._post_perfil(ciencia_comunicacoes="on")
        self.usuario.refresh_from_db()
        primeira_data = self.usuario.ciencia_comunicacoes_em

        self._post_perfil()  # sem o checkbox
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.ciencia_comunicacoes)
        self.assertEqual(self.usuario.ciencia_comunicacoes_em, primeira_data)

    def test_aparece_no_bloco_de_declaracoes(self):
        resposta = self.client.get(reverse("meu_cadastro") + "?aba=perfil")
        self.assertContains(resposta, 'name="ciencia_comunicacoes"')
        # A divulgação oficial é a publicação; o e-mail é aviso complementar.
        self.assertContains(resposta, "aviso complementar")

    def test_entra_no_perfil_completo(self):
        preencher_campos_cadastro(self.usuario)
        for campo in ("ciencia_credenciamento", "declaracao_veracidade",
                      "consentimento_verificacao_bases"):
            self.usuario.confirmar_declaracao(campo)
        self.assertFalse(self.usuario.perfil_completo)
        self.usuario.confirmar_declaracao("ciencia_comunicacoes")
        self.assertTrue(self.usuario.perfil_completo)


class GrandeAreaCnpqTest(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            cpf="52998224725",
            email="cnpq@test.com",
            nome_completo="CNPq Teste",
            vinculo=Vinculo.SERVIDOR,
            password="senha123",
        )

    def test_vazio_quando_area_nao_informada(self):
        self.assertEqual(self.usuario.grande_area_cnpq, "")

    def test_derivada_do_prefixo_do_codigo(self):
        self.usuario.cnpq_area = "3.04"
        self.assertEqual(self.usuario.grande_area_cnpq, "3. Engenharias")
        self.usuario.cnpq_area = "1.06"
        self.assertEqual(self.usuario.grande_area_cnpq, "1. Ciências Exatas e da Terra")


class EstadoCidadeTest(TestCase):
    """Selects encadeados de estado -> cidade.

    A lista de cidades é montada no servidor (o formulário funciona sem
    JavaScript); o JS só troca a lista quando o estado muda.
    """

    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            cpf="52998224725",
            email="ufcidade@test.com",
            nome_completo="UF Cidade Teste",
            vinculo=Vinculo.SERVIDOR,
            password="senha123",
        )
        self.client.force_login(self.usuario)

    def test_cidade_vazia_quando_nao_ha_estado(self):
        from apps.usuarios.forms import MeuCadastroForm
        form = MeuCadastroForm(instance=self.usuario)
        self.assertEqual(
            [valor for valor, _ in form.fields["cidade"].choices], [""]
        )

    def test_cidades_do_estado_salvo_vem_preenchidas(self):
        from apps.usuarios.forms import MeuCadastroForm
        self.usuario.uf = "GO"
        self.usuario.save(update_fields=["uf"])
        form = MeuCadastroForm(instance=self.usuario)
        valores = [valor for valor, _ in form.fields["cidade"].choices]
        self.assertIn("Anápolis", valores)
        self.assertIn("Goiânia", valores)
        self.assertNotIn("Campinas", valores)  # SP

    def test_post_aceita_cidade_do_estado_recem_escolhido(self):
        # Sem ler a UF do POST em _preparar_cidades, o Django recusaria a
        # cidade por não constar das opções montadas a partir do valor antigo.
        self.client.post(
            reverse("meu_cadastro") + "?aba=dados",
            {
                "nome_completo": "X",
                "email": self.usuario.email,
                "uf": "GO",
                "cidade": "Anápolis",
            },
        )
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.uf, "GO")
        self.assertEqual(self.usuario.cidade, "Anápolis")

    def test_post_recusa_cidade_de_outro_estado(self):
        self.client.post(
            reverse("meu_cadastro") + "?aba=dados",
            {
                "nome_completo": "X",
                "email": self.usuario.email,
                "uf": "GO",
                "cidade": "Campinas",
            },
        )
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.cidade, "")

    def test_dataset_cobre_os_27_estados(self):
        from apps.usuarios.municipios import UF_CHOICES, municipios_de, municipios_por_uf
        self.assertEqual(len(UF_CHOICES), 27)
        self.assertEqual(len(municipios_por_uf()), 27)
        self.assertEqual(sum(len(v) for v in municipios_por_uf().values()), 5571)
        self.assertEqual(municipios_de(""), [])
        self.assertEqual(municipios_de("XX"), [])
        self.assertIn("Itumbiara", municipios_de("go"))  # aceita minúscula


class CadastroInicialConsentimentoTest(TestCase):
    """O consentimento de verificação em bases (LGPD) passou para a tela de
    cadastro inicial, ao lado do aceite do termo, em 23/09/2026."""

    def _dados(self, **extra):
        dados = {
            "vinculo": Vinculo.COLABORADOR_EXTERNO,
            "nome_completo": "Nova Pessoa",
            "email": "nova@test.com",
            "cpf": "11144477735",
            "telefone": "",
            "lattes": "",
            "senha": "Senha-forte-2026",
            "confirmar_senha": "Senha-forte-2026",
            "aceite_lgpd": "on",
            "consentimento_verificacao_bases": "on",
        }
        dados.update(extra)
        return dados

    def test_tela_de_cadastro_mostra_o_consentimento(self):
        resposta = self.client.get(reverse("cadastro"))
        self.assertContains(resposta, 'name="consentimento_verificacao_bases"')

    def test_cadastro_grava_consentimento_com_data(self):
        resposta = self.client.post(reverse("cadastro"), self._dados())
        self.assertEqual(resposta.status_code, 302)
        usuario = Usuario.objects.get(cpf="11144477735")
        self.assertTrue(usuario.consentimento_verificacao_bases)
        self.assertIsNotNone(usuario.consentimento_verificacao_bases_em)

    def test_cadastro_sem_consentimento_e_recusado(self):
        dados = self._dados(vinculo=Vinculo.SERVIDOR)
        del dados["consentimento_verificacao_bases"]
        resposta = self.client.post(reverse("cadastro"), dados)
        self.assertEqual(resposta.status_code, 200)
        self.assertFalse(Usuario.objects.filter(cpf="11144477735").exists())

    def test_externo_se_cadastra_sem_consentimento(self):
        dados = self._dados()
        del dados["consentimento_verificacao_bases"]
        self.assertEqual(self.client.post(reverse("cadastro"), dados).status_code, 302)
        self.assertFalse(Usuario.objects.get(cpf="11144477735").consentimento_verificacao_bases)


class CadastroCompletoPorVinculoTest(TestCase):
    """Item 4.4.2: cadastro completo = campos do item 4.2 + declarações.

    Cada vínculo tem o seu Edital (29 servidores, 30 externos, 31 estudantes).
    O estudante não tem categoria nem titulação; informa instituição e curso.
    """

    def _usuario(self, vinculo, cpf):
        return Usuario.objects.create_user(
            cpf=cpf,
            email=f"{vinculo}@test.com",
            nome_completo="Pessoa Teste",
            vinculo=vinculo,
            password="senha123",
        )

    def setUp(self):
        self.servidor = self._usuario(Vinculo.SERVIDOR, "11144477735")
        self.externo = self._usuario(Vinculo.COLABORADOR_EXTERNO, "52998224725")
        self.estudante = self._usuario(Vinculo.ESTUDANTE, "39053344705")

    def test_todos_completos_com_o_helper(self):
        for usuario in (self.servidor, self.externo, self.estudante):
            completar_cadastro(usuario)
            self.assertTrue(usuario.perfil_completo, usuario.vinculo)

    def test_cada_campo_do_4_2_e_exigido_do_servidor(self):
        for campo in ("telefone", "uf", "cidade", "area_atuacao", "resumo", "lattes"):
            completar_cadastro(self.servidor)
            setattr(self.servidor, campo, "")
            self.assertFalse(self.servidor.perfil_completo, campo)

    def test_estudante_nao_tem_categoria_nem_titulacao(self):
        completar_cadastro(self.estudante)
        self.assertEqual(self.estudante.categoria_pretendida, "")
        self.assertEqual(self.estudante.maior_titulacao, "")
        self.assertTrue(self.estudante.perfil_completo)

    def test_estudante_precisa_da_instituicao(self):
        completar_cadastro(self.estudante)
        self.estudante.instituicao = ""
        self.assertEqual(self.estudante.pendencias_cadastro(), ["instituição de ensino"])

    def test_resumo_e_opcional_para_estudante(self):
        completar_cadastro(self.estudante)
        self.estudante.resumo = ""
        self.assertTrue(self.estudante.perfil_completo)

    def test_externo_nao_informa_situacao_funcional(self):
        completar_cadastro(self.externo)
        self.assertIsNone(self.externo.servidor_ativo)
        self.assertTrue(self.externo.perfil_completo)

    def test_resumo_antigo_fora_do_tamanho_e_pendencia(self):
        completar_cadastro(self.externo)
        self.externo.resumo = "Resumo curto do cadastro antigo."
        self.assertEqual(
            self.externo.pendencias_cadastro(),
            ["resumo da atuação profissional (50 a 200 palavras)"],
        )

    def test_banner_lista_o_que_falta(self):
        completar_cadastro(self.externo)
        self.externo.telefone = ""
        self.externo.save()
        self.client.force_login(self.externo)
        resposta = self.client.get(reverse("home"))
        self.assertContains(resposta, "Falta: telefone.")

    def test_formulario_do_estudante(self):
        self.client.force_login(self.estudante)
        dados = self.client.get(reverse("meu_cadastro") + "?aba=dados")
        self.assertNotContains(dados, 'name="categoria_pretendida"')
        formacao = self.client.get(reverse("meu_cadastro") + "?aba=formacao")
        self.assertContains(formacao, 'name="instituicao"')
        self.assertContains(formacao, "Curso em andamento")
        self.assertNotContains(formacao, 'name="maior_titulacao"')

    def test_formulario_do_servidor_nao_pede_instituicao(self):
        self.client.force_login(self.servidor)
        formacao = self.client.get(reverse("meu_cadastro") + "?aba=formacao")
        self.assertNotContains(formacao, 'name="instituicao"')
        self.assertContains(formacao, 'name="maior_titulacao"')
        self.assertContains(self.client.get(reverse("meu_cadastro")), 'name="servidor_ativo"')

class DataNascimentoTest(TestCase):
    """Data de nascimento: último critério de desempate (maior idade)."""

    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            cpf="11144477735",
            email="nascimento@test.com",
            nome_completo="Nascimento Teste",
            vinculo=Vinculo.ESTUDANTE,
            password="senha123",
        )
        self.client.force_login(self.usuario)

    def _post_dados(self, data):
        return self.client.post(reverse("meu_cadastro") + "?aba=dados", {
            "nome_completo": "Nascimento Teste",
            "email": self.usuario.email,
            "data_nascimento": data,
        })

    def test_exigida_no_cadastro_completo(self):
        completar_cadastro(self.usuario)
        self.usuario.data_nascimento = None
        self.assertEqual(self.usuario.pendencias_cadastro(), ["data de nascimento"])

    def test_aparece_na_aba_dados_com_calendario(self):
        resposta = self.client.get(reverse("meu_cadastro") + "?aba=dados")
        self.assertContains(resposta, 'type="date"')

    def test_grava_data_valida(self):
        self._post_dados("2008-03-09")
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.data_nascimento, date(2008, 3, 9))

    def test_recusa_data_implausivel(self):
        for data in ("2062-01-01", "1900-01-01"):
            resposta = self._post_dados(data)
            self.assertContains(resposta, "Confira a data de nascimento.")
        self.usuario.refresh_from_db()
        self.assertIsNone(self.usuario.data_nascimento)
