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

    def test_home_com_inscricao_pendente_mostra_status(self):
        Inscricao.objects.create(
            usuario=self.candidato,
            modalidade="estudante",
            status=StatusInscricao.PENDENTE,
        )
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Pendente")

    def test_home_com_inscricao_enviada_mostra_link_confirmacao(self):
        from django.utils import timezone
        Inscricao.objects.create(
            usuario=self.candidato,
            modalidade="estudante",
            status=StatusInscricao.EM_ANALISE,
            enviada_em=timezone.now(),
        )
        response = self.client.get(reverse("home"))
        self.assertContains(response, reverse("inscricao_confirmacao"))


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
