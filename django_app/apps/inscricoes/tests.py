from django.test import TestCase
from apps.inscricoes.quadros import QUADROS_INSCRICAO


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
