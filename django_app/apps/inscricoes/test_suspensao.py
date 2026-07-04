# apps/inscricoes/test_suspensao.py
# Banco de Talentos — Polo de Inovação IFG
# Testes da suspensão temporária de inscrições (flag INSCRICOES_ABERTAS no .env):
# GET e POST bloqueados quando fechada, fluxo intacto quando aberta.

from django.test import Client, TestCase, override_settings

from apps.usuarios.models import Usuario, Vinculo


class SuspensaoInscricoesTest(TestCase):
    def setUp(self):
        self.user = Usuario.objects.create_user(
            cpf="52998224725",
            email="teste@example.com",
            password="senha-Forte-123",
            nome_completo="Candidato Teste",
            vinculo=Vinculo.ESTUDANTE,
        )
        self.client = Client()
        self.client.force_login(self.user)

    @override_settings(INSCRICOES_ABERTAS=False)
    def test_get_bloqueado_mostra_pagina_suspensao(self):
        resp = self.client.get("/inscricao/")
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "inscricoes/suspensas.html")

    @override_settings(INSCRICOES_ABERTAS=False)
    def test_post_bloqueado_nao_grava_nada(self):
        from apps.inscricoes.models import Inscricao
        resp = self.client.post("/inscricao/", {"action": "enviar"})
        self.assertTemplateUsed(resp, "inscricoes/suspensas.html")
        self.assertEqual(Inscricao.objects.count(), 0)

    @override_settings(INSCRICOES_ABERTAS=True)
    def test_flag_ligada_fluxo_normal(self):
        resp = self.client.get("/inscricao/")
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateNotUsed(resp, "inscricoes/suspensas.html")

    @override_settings(INSCRICOES_ABERTAS=False)
    def test_home_mostra_aviso_no_lugar_do_cta(self):
        resp = self.client.get("/")
        self.assertContains(resp, "temporariamente suspensas")
        self.assertNotContains(resp, "Fazer inscri")
