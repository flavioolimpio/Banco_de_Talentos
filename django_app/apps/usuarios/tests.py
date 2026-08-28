from django.test import TestCase
from django.urls import reverse

from apps.usuarios.models import Usuario, Vinculo
from apps.usuarios.validators import validar_cpf


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

    def test_home_sem_inscricao_mostra_link_iniciar(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, reverse("inscricao"))


    def test_home_exibe_imagem_home(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, "imagens/home.png")


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

    def test_home_tem_link_inscricao_na_sidebar(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, reverse("inscricao"))

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
            {"nome_completo": "Novo Nome", "telefone": "", "resumo": ""},
            instance=self.user,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_nao_tem_campo_cpf(self):
        from apps.usuarios.forms import MeuCadastroForm
        form = MeuCadastroForm(instance=self.user)
        self.assertNotIn("cpf", form.fields)

    def test_form_nao_tem_campo_email(self):
        from apps.usuarios.forms import MeuCadastroForm
        form = MeuCadastroForm(instance=self.user)
        self.assertNotIn("email", form.fields)

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

    def test_get_aba_endereco(self):
        response = self.client.get(reverse("meu_cadastro") + "?aba=endereco")
        self.assertContains(response, "CEP")

    def test_get_aba_formacao(self):
        response = self.client.get(reverse("meu_cadastro") + "?aba=formacao")
        self.assertContains(response, "Lattes")

    def test_post_salva_nome_completo(self):
        self.client.post(
            reverse("meu_cadastro") + "?aba=dados",
            {"nome_completo": "Nome Atualizado", "telefone": ""},
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.nome_completo, "Nome Atualizado")

    def test_post_nao_altera_email(self):
        email_original = self.user.email
        self.client.post(
            reverse("meu_cadastro") + "?aba=dados",
            {"nome_completo": "X", "email": "hacker@evil.com"},
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, email_original)

    def test_post_nao_altera_vinculo(self):
        vinculo_original = self.user.vinculo
        self.client.post(
            reverse("meu_cadastro") + "?aba=dados",
            {"nome_completo": "X", "vinculo": "estudante"},
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.vinculo, vinculo_original)

    def test_post_salva_apenas_aba_dados_sem_sobrescrever_endereco(self):
        self.user.cep = "75000000"
        self.user.save(update_fields=["cep"])
        self.client.post(
            reverse("meu_cadastro") + "?aba=dados",
            {"nome_completo": "Novo Nome"},
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
            {"nome_completo": "Novo Nome", "cep": "99999999"},
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.cep, "75000000")

    def test_post_nao_altera_cpf(self):
        """CPF nunca pode ser alterado via POST."""
        cpf_original = self.user.cpf
        self.client.post(
            reverse("meu_cadastro") + "?aba=dados",
            {"nome_completo": "X", "cpf": "11144477735"},
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
            {"nome_completo": "Log Teste"},
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
        usuario.categoria_pretendida = CategoriaPretendida.PESQUISADOR
        usuario.maior_titulacao = MaiorTitulacao.DOUTORADO
        usuario.area_atuacao = "Engenharia"
        usuario.disponibilidade_semanal = 20

    def _confirmar_todas_declaracoes(self, usuario):
        usuario.confirmar_declaracao("ciencia_credenciamento")
        usuario.confirmar_declaracao("declaracao_veracidade")
        usuario.confirmar_declaracao("consentimento_verificacao_bases")

    def test_perfil_incompleto_por_padrao(self):
        self.assertFalse(self.servidor.perfil_completo)
        self.assertFalse(self.externo.perfil_completo)

    def test_perfil_completo_para_colaborador_externo(self):
        self._preencher_campos_base(self.externo)
        self._confirmar_todas_declaracoes(self.externo)
        self.assertTrue(self.externo.perfil_completo)

    def test_servidor_ativo_exige_declaracao_de_nao_afastamento(self):
        self._preencher_campos_base(self.servidor)
        self._confirmar_todas_declaracoes(self.servidor)
        self.servidor.servidor_ativo = True
        self.assertFalse(self.servidor.perfil_completo)
        self.servidor.nao_afastado_licenciado = True
        self.assertTrue(self.servidor.perfil_completo)

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


class MeuCadastroFormPerfilTest(TestCase):
    def setUp(self):
        self.servidor_ativo = Usuario.objects.create_user(
            cpf="11144477735",
            email="formservativo@test.com",
            nome_completo="Servidor Ativo",
            vinculo=Vinculo.SERVIDOR,
            password="senha123",
        )
        self.externo = Usuario.objects.create_user(
            cpf="52998224725",
            email="formexterno@test.com",
            nome_completo="Externo Form",
            vinculo=Vinculo.COLABORADOR_EXTERNO,
            password="senha123",
        )

    def test_form_aceita_disponibilidade_dentro_da_faixa_servidor_ativo(self):
        from apps.usuarios.forms import MeuCadastroForm
        form = MeuCadastroForm(
            {"nome_completo": "X", "servidor_ativo": "on", "disponibilidade_semanal": "20"},
            instance=self.servidor_ativo,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_rejeita_disponibilidade_acima_da_faixa_servidor_ativo(self):
        from apps.usuarios.forms import MeuCadastroForm
        form = MeuCadastroForm(
            {"nome_completo": "X", "servidor_ativo": "on", "disponibilidade_semanal": "30"},
            instance=self.servidor_ativo,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("disponibilidade_semanal", form.errors)

    def test_form_aceita_disponibilidade_ate_40h_para_colaborador_externo(self):
        from apps.usuarios.forms import MeuCadastroForm
        form = MeuCadastroForm(
            {"nome_completo": "X", "disponibilidade_semanal": "40"},
            instance=self.externo,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_rejeita_disponibilidade_abaixo_de_5h(self):
        from apps.usuarios.forms import MeuCadastroForm
        form = MeuCadastroForm(
            {"nome_completo": "X", "disponibilidade_semanal": "3"},
            instance=self.externo,
        )
        self.assertFalse(form.is_valid())
