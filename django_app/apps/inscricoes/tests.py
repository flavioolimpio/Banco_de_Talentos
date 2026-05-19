from django.test import TestCase
from django.core.management import call_command
from apps.inscricoes.quadros import QUADROS_INSCRICAO
from apps.inscricoes.models import CriterioEdital


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
