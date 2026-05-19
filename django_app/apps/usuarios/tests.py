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
