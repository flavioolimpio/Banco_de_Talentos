from django.test import TestCase
from django.contrib.auth import get_user_model

User = get_user_model()


class AuditLogAdminTest(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            cpf="52998224725",
            email="admin@ifg.edu.br",
            nome_completo="Admin RH",
            password="AdminPass123!",
        )
        self.client.force_login(self.admin_user)

    def test_lista_auditlogs_retorna_200(self):
        response = self.client.get("/admin/auditoria/auditlog/")
        self.assertEqual(response.status_code, 200)

    def test_nao_permite_adicionar(self):
        response = self.client.get("/admin/auditoria/auditlog/add/")
        self.assertEqual(response.status_code, 403)
