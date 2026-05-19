from decimal import Decimal

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.management import call_command
from django.test import RequestFactory, TestCase

from apps.inscricoes.admin import InscricaoAdmin
from apps.inscricoes.models import CriterioEdital, Inscricao, StatusInscricao
from apps.inscricoes.quadros import QUADROS_INSCRICAO

User = get_user_model()


class QuadrosInscricaoTest(TestCase):
    def test_modalidades_presentes(self):
        self.assertIn("servidor", QUADROS_INSCRICAO)
        self.assertIn("estudante", QUADROS_INSCRICAO)
        self.assertIn("colaborador_externo", QUADROS_INSCRICAO)

    def test_quantidade_criterios_servidor(self):
        self.assertEqual(len(QUADROS_INSCRICAO["servidor"]), 13)

    def test_quantidade_criterios_estudante(self):
        self.assertEqual(len(QUADROS_INSCRICAO["estudante"]), 8)

    def test_quantidade_criterios_colaborador_externo(self):
        self.assertEqual(len(QUADROS_INSCRICAO["colaborador_externo"]), 9)

    def test_campos_obrigatorios_em_cada_item(self):
        for modalidade, itens in QUADROS_INSCRICAO.items():
            for item in itens:
                with self.subTest(modalidade=modalidade, id=item.get("id")):
                    self.assertIn("id", item)
                    self.assertIn("criterio", item)
                    self.assertIn("regra", item)
                    self.assertIn("maximo", item)
                    self.assertIsInstance(item["maximo"], float)


class PopularCriteriosCommandTest(TestCase):
    def test_cria_criterios_servidor(self):
        call_command("popular_criterios", verbosity=0)
        self.assertEqual(
            CriterioEdital.objects.filter(modalidade="servidor").count(), 13
        )

    def test_cria_criterios_estudante(self):
        call_command("popular_criterios", verbosity=0)
        self.assertEqual(
            CriterioEdital.objects.filter(modalidade="estudante").count(), 8
        )

    def test_cria_criterios_colaborador_externo(self):
        call_command("popular_criterios", verbosity=0)
        self.assertEqual(
            CriterioEdital.objects.filter(modalidade="colaborador_externo").count(), 9
        )

    def test_total_30_criterios(self):
        call_command("popular_criterios", verbosity=0)
        self.assertEqual(CriterioEdital.objects.count(), 30)

    def test_idempotente_sem_duplicar(self):
        call_command("popular_criterios", verbosity=0)
        call_command("popular_criterios", verbosity=0)
        self.assertEqual(CriterioEdital.objects.count(), 30)

    def test_campos_salvos_corretamente(self):
        call_command("popular_criterios", verbosity=0)
        criterio = CriterioEdital.objects.get(modalidade="servidor", item_id="titulacao")
        self.assertEqual(criterio.criterio, "Titulação")
        self.assertEqual(float(criterio.maximo), 100.0)
        self.assertTrue(criterio.ativo)


class InscricaoAdminActionsTest(TestCase):
    def setUp(self):
        self.site = AdminSite()
        self.factory = RequestFactory()
        self.admin_user = User.objects.create_superuser(
            cpf="52998224725",
            email="admin@ifg.edu.br",
            nome_completo="Admin RH",
            password="AdminPass123!",
        )
        self.candidato = User.objects.create_user(
            cpf="11144477735",
            email="candidato@test.com",
            nome_completo="Candidato Teste",
            vinculo="estudante",
            password="CandPass123!",
        )
        self.inscricao = Inscricao.objects.create(
            usuario=self.candidato,
            modalidade="estudante",
            status=StatusInscricao.PENDENTE,
            total=Decimal("50.00"),
        )

    def _make_request(self):
        request = self.factory.post("/")
        request.user = self.admin_user
        setattr(request, "session", {})
        setattr(request, "_messages", FallbackStorage(request))
        return request

    def test_acao_aprovar_muda_status(self):
        ma = InscricaoAdmin(Inscricao, self.site)
        request = self._make_request()
        queryset = Inscricao.objects.filter(pk=self.inscricao.pk)
        ma.aprovar_selecionadas(request, queryset)
        self.inscricao.refresh_from_db()
        self.assertEqual(self.inscricao.status, StatusInscricao.APROVADA)

    def test_acao_reprovar_muda_status(self):
        ma = InscricaoAdmin(Inscricao, self.site)
        request = self._make_request()
        queryset = Inscricao.objects.filter(pk=self.inscricao.pk)
        ma.reprovar_selecionadas(request, queryset)
        self.inscricao.refresh_from_db()
        self.assertEqual(self.inscricao.status, StatusInscricao.INDEFERIDA)

    def test_acao_marcar_em_analise_muda_status(self):
        ma = InscricaoAdmin(Inscricao, self.site)
        request = self._make_request()
        queryset = Inscricao.objects.filter(pk=self.inscricao.pk)
        ma.marcar_em_analise(request, queryset)
        self.inscricao.refresh_from_db()
        self.assertEqual(self.inscricao.status, StatusInscricao.EM_ANALISE)

    def test_export_csv_retorna_200(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(
            "/admin/inscricoes/inscricao/",
            {
                "action": "exportar_csv",
                "_selected_action": [str(self.inscricao.pk)],
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
