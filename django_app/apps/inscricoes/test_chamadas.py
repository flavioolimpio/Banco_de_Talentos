# apps/inscricoes/test_chamadas.py
# Banco de Talentos — Polo de Inovação IFG
# Fluxo de inscrição por Chamada Interna (Retificação 4, itens 5.1 a 5.16).

from datetime import timedelta
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.inscricoes.models import (
    ChamadaInterna,
    CriterioEdital,
    Inscricao,
    OpcaoCriterio,
    StatusInscricao,
    TipoCriterio,
    Vaga,
)
from apps.usuarios.models import Usuario, Vinculo

PDF = SimpleUploadedFile("comprovantes.pdf", b"%PDF-1.4 conteudo", content_type="application/pdf")


def pdf_novo():
    return SimpleUploadedFile("comprovantes.pdf", b"%PDF-1.4 conteudo", content_type="application/pdf")


class BaseChamada(TestCase):
    def setUp(self):
        agora = timezone.now()
        self.chamada = ChamadaInterna.objects.create(
            numero=1,
            ano=2027,
            titulo="Rota do Pescado",
            projeto="Cadeia produtiva do pescado",
            abertura=agora - timedelta(days=1),
            encerramento=agora + timedelta(days=7),
            publicada=True,
        )
        self.vaga = Vaga.objects.create(
            chamada=self.chamada,
            codigo="Pq 12",
            funcao="Pesquisador(a)",
            modalidade=Vinculo.ESTUDANTE,
            quantidade=1,
        )
        # Critério de contagem: 40 pontos por projeto, teto de 120.
        self.contagem = CriterioEdital.objects.create(
            chamada=self.chamada,
            modalidade=Vinculo.ESTUDANTE,
            item_id="projetos_pdi",
            ordem=1,
            criterio="Participação em projeto de PD&I",
            regra="40 pontos por projeto, até 120.",
            maximo=Decimal("120"),
            tipo=TipoCriterio.CONTAGEM,
            pontos_por_unidade=Decimal("40"),
            unidade_rotulo="projetos",
        )
        # Critério de escolha: titulação.
        self.escolha = CriterioEdital.objects.create(
            chamada=self.chamada,
            modalidade=Vinculo.ESTUDANTE,
            item_id="titulacao",
            ordem=2,
            criterio="Titulação",
            regra="Conforme o nível mais alto concluído.",
            maximo=Decimal("100"),
            tipo=TipoCriterio.ESCOLHA,
        )
        self.doutorado = OpcaoCriterio.objects.create(
            criterio=self.escolha, rotulo="Doutorado", pontos=Decimal("100"), ordem=1
        )
        self.mestrado = OpcaoCriterio.objects.create(
            criterio=self.escolha, rotulo="Mestrado", pontos=Decimal("70"), ordem=2
        )
        self.usuario = Usuario.objects.create_user(
            cpf="52998224725",
            email="candidato@test.com",
            nome_completo="Candidata Teste",
            vinculo=Vinculo.ESTUDANTE,
            password="senha123",
        )
        self.client.force_login(self.usuario)

    def _post(self, **extra):
        dados = {
            "action": "enviar",
            "vaga": self.vaga.pk,
            f"qtd_{self.contagem.pk}": "2",
            f"opcao_{self.escolha.pk}": self.doutorado.pk,
            "declara_disponibilidade": "on",
            "declara_nao_redistribuicao": "on",
            "aceite_envio": "on",
            "comprovantes_pdf": pdf_novo(),
        }
        dados.update(extra)
        return self.client.post(
            reverse("inscricao_chamada", args=[self.chamada.pk]), dados
        )


class PontuacaoCalculadaTest(BaseChamada):
    """O candidato não digita pontos — quem calcula é o servidor."""

    def test_contagem_multiplica_pela_unidade(self):
        self.assertEqual(self.contagem.pontuar(quantidade=2), Decimal("80"))

    def test_contagem_respeita_o_maximo(self):
        # 10 projetos x 40 = 400, mas o teto do critério é 120.
        self.assertEqual(self.contagem.pontuar(quantidade=10), Decimal("120"))

    def test_contagem_zero_nao_pontua(self):
        self.assertEqual(self.contagem.pontuar(quantidade=0), Decimal("0"))

    def test_escolha_usa_os_pontos_da_opcao(self):
        self.assertEqual(self.escolha.pontuar(opcao=self.mestrado), Decimal("70"))

    def test_escolha_sem_resposta_nao_pontua(self):
        self.assertEqual(self.escolha.pontuar(opcao=None), Decimal("0"))

    def test_total_do_envio_e_calculado_no_servidor(self):
        # O POST não manda pontuação nenhuma: 2 projetos (80) + Doutorado (100).
        self._post()
        inscricao = Inscricao.objects.get(usuario=self.usuario, chamada=self.chamada)
        self.assertEqual(inscricao.total, Decimal("180"))

    def test_quantidade_negativa_vira_zero(self):
        self._post(**{f"qtd_{self.contagem.pk}": "-5"})
        inscricao = Inscricao.objects.get(usuario=self.usuario, chamada=self.chamada)
        item = inscricao.itens.get(criterio=self.contagem)
        self.assertEqual(item.quantidade, 0)
        self.assertEqual(item.pontuacao, Decimal("0"))

    def test_opcao_de_outro_criterio_nao_pontua(self):
        outro = OpcaoCriterio.objects.create(
            criterio=self.contagem, rotulo="Intruso", pontos=Decimal("999")
        )
        self._post(**{f"opcao_{self.escolha.pk}": outro.pk})
        inscricao = Inscricao.objects.get(usuario=self.usuario, chamada=self.chamada)
        self.assertEqual(inscricao.itens.get(criterio=self.escolha).pontuacao, Decimal("0"))


class EnvioDaInscricaoTest(BaseChamada):
    def test_envio_grava_itens_e_status(self):
        self._post()
        inscricao = Inscricao.objects.get(usuario=self.usuario, chamada=self.chamada)
        self.assertEqual(inscricao.status, StatusInscricao.EM_ANALISE)
        self.assertIsNotNone(inscricao.enviada_em)
        self.assertEqual(inscricao.vaga, self.vaga)
        self.assertEqual(inscricao.itens.count(), 2)

    def test_rascunho_nao_exige_declaracoes(self):
        resposta = self.client.post(
            reverse("inscricao_chamada", args=[self.chamada.pk]),
            {"action": "rascunho", f"qtd_{self.contagem.pk}": "1"},
        )
        self.assertEqual(resposta.status_code, 302)
        inscricao = Inscricao.objects.get(usuario=self.usuario, chamada=self.chamada)
        self.assertEqual(inscricao.status, StatusInscricao.PENDENTE)
        self.assertIsNone(inscricao.enviada_em)

    def test_envio_sem_declaracoes_e_recusado(self):
        self._post(declara_disponibilidade="", declara_nao_redistribuicao="", aceite_envio="")
        self.assertFalse(Inscricao.objects.filter(usuario=self.usuario).exists())

    def test_envio_sem_pdf_e_recusado(self):
        self._post(comprovantes_pdf="")
        self.assertFalse(Inscricao.objects.filter(usuario=self.usuario).exists())

    def test_licencas_maternidade_sao_registradas(self):
        self._post(licencas_maternidade="2")
        inscricao = Inscricao.objects.get(usuario=self.usuario, chamada=self.chamada)
        self.assertEqual(inscricao.licencas_maternidade, 2)

    def test_pdf_vai_para_a_pasta_da_chamada(self):
        self._post()
        inscricao = Inscricao.objects.get(usuario=self.usuario, chamada=self.chamada)
        self.assertIn(f"chamada-{self.chamada.pk}", inscricao.comprovantes_pdf.name)

    def test_reenvio_nao_duplica_itens(self):
        self._post()
        self._post(**{f"qtd_{self.contagem.pk}": "1"})
        inscricao = Inscricao.objects.get(usuario=self.usuario, chamada=self.chamada)
        self.assertEqual(inscricao.itens.count(), 2)

    def test_criterio_removido_do_quadro_some_da_inscricao(self):
        self._post()
        self.escolha.ativo = False
        self.escolha.save(update_fields=["ativo"])
        # Reabre para o candidato poder reenviar.
        Inscricao.objects.filter(usuario=self.usuario).update(status=StatusInscricao.PENDENTE)
        self._post()
        inscricao = Inscricao.objects.get(usuario=self.usuario, chamada=self.chamada)
        self.assertEqual(inscricao.itens.count(), 1)


class PrazoDaChamadaTest(BaseChamada):
    """O prazo é o da chamada — não existe mais uma flag global."""

    def _fechar(self):
        self.chamada.encerramento = timezone.now() - timedelta(days=1)
        self.chamada.save(update_fields=["encerramento"])

    def test_get_fora_do_prazo_e_bloqueado(self):
        self._fechar()
        resposta = self.client.get(reverse("inscricao_chamada", args=[self.chamada.pk]))
        self.assertTemplateUsed(resposta, "inscricoes/chamada_fora_do_prazo.html")

    def test_post_fora_do_prazo_nao_grava_nada(self):
        self._fechar()
        self._post()
        self.assertFalse(Inscricao.objects.filter(usuario=self.usuario).exists())

    def test_chamada_nao_publicada_da_404(self):
        self.chamada.publicada = False
        self.chamada.save(update_fields=["publicada"])
        resposta = self.client.get(reverse("inscricao_chamada", args=[self.chamada.pk]))
        self.assertEqual(resposta.status_code, 404)

    def test_aberta_depende_de_publicada_e_das_datas(self):
        self.assertTrue(self.chamada.aberta)
        self._fechar()
        self.assertFalse(self.chamada.aberta)
        self.assertTrue(self.chamada.encerrada)


class UmaInscricaoPorChamadaTest(BaseChamada):
    def test_mesma_chamada_duas_vezes_e_bloqueado_no_banco(self):
        Inscricao.objects.create(
            usuario=self.usuario, chamada=self.chamada, modalidade=Vinculo.ESTUDANTE
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Inscricao.objects.create(
                    usuario=self.usuario, chamada=self.chamada, modalidade=Vinculo.ESTUDANTE
                )

    def test_duas_chamadas_diferentes_sao_permitidas(self):
        outra = ChamadaInterna.objects.create(
            numero=2,
            ano=2027,
            titulo="Outro projeto",
            abertura=timezone.now() - timedelta(days=1),
            encerramento=timezone.now() + timedelta(days=5),
            publicada=True,
        )
        Inscricao.objects.create(
            usuario=self.usuario, chamada=self.chamada, modalidade=Vinculo.ESTUDANTE
        )
        Inscricao.objects.create(
            usuario=self.usuario, chamada=outra, modalidade=Vinculo.ESTUDANTE
        )
        self.assertEqual(Inscricao.objects.filter(usuario=self.usuario).count(), 2)


class ElegibilidadeTest(BaseChamada):
    """A elegibilidade sai das vagas, não de um campo na chamada."""

    def test_chamada_aparece_para_o_vinculo_com_vaga(self):
        resposta = self.client.get(reverse("chamadas"))
        self.assertContains(resposta, "Rota do Pescado")

    def test_chamada_nao_aparece_para_outro_vinculo(self):
        servidor = Usuario.objects.create_user(
            cpf="11144477735",
            email="servidor@test.com",
            nome_completo="Servidor",
            vinculo=Vinculo.SERVIDOR,
            password="senha123",
        )
        self.client.force_login(servidor)
        resposta = self.client.get(reverse("chamadas"))
        self.assertNotContains(resposta, "Rota do Pescado")

    def test_home_lista_a_chamada_aberta(self):
        resposta = self.client.get(reverse("home"))
        self.assertContains(resposta, "Chamada Interna 01 &mdash; Rota do Pescado")

    def test_chamada_de_legado_nunca_aparece(self):
        resposta = self.client.get(reverse("chamadas"))
        self.assertNotContains(resposta, "Credenciamento (legado)")


class QuadroSemVazamentoTest(BaseChamada):
    def test_criterio_de_outra_chamada_nao_entra_no_formulario(self):
        outra = ChamadaInterna.objects.create(
            numero=3,
            ano=2027,
            titulo="Chamada vizinha",
            abertura=timezone.now() - timedelta(days=1),
            encerramento=timezone.now() + timedelta(days=5),
            publicada=True,
        )
        CriterioEdital.objects.create(
            chamada=outra,
            modalidade=Vinculo.ESTUDANTE,
            item_id="intruso",
            ordem=1,
            criterio="Critério da chamada vizinha",
            regra="não deve aparecer",
            maximo=Decimal("10"),
        )
        resposta = self.client.get(reverse("inscricao_chamada", args=[self.chamada.pk]))
        self.assertContains(resposta, "Participação em projeto de PD&amp;I")
        self.assertNotContains(resposta, "Critério da chamada vizinha")

    def test_mesmo_item_id_pode_existir_em_duas_chamadas(self):
        # É o ganho da constraint nova: "titulacao" repete a cada chamada.
        outra = ChamadaInterna.objects.create(
            numero=4,
            ano=2027,
            titulo="Terceira",
            abertura=timezone.now(),
            encerramento=timezone.now() + timedelta(days=1),
        )
        CriterioEdital.objects.create(
            chamada=outra,
            modalidade=Vinculo.ESTUDANTE,
            item_id="titulacao",
            ordem=1,
            criterio="Titulação",
            regra="idem",
            maximo=Decimal("100"),
        )
        self.assertEqual(
            CriterioEdital.objects.filter(item_id="titulacao", modalidade=Vinculo.ESTUDANTE).count(),
            2,
        )


class LegadoSomenteLeituraTest(TestCase):
    def test_inscricao_de_legado_nao_e_editavel(self):
        legado = ChamadaInterna.objects.get(numero=31, ano=2026)
        usuario = Usuario.objects.create_user(
            cpf="52998224725",
            email="legado@test.com",
            nome_completo="Legado",
            vinculo=Vinculo.ESTUDANTE,
            password="senha123",
        )
        inscricao = Inscricao.objects.create(
            usuario=usuario, chamada=legado, modalidade=Vinculo.ESTUDANTE
        )
        self.assertTrue(inscricao.e_legado)
        self.assertFalse(inscricao.editavel)

    def test_chamadas_de_legado_existem_e_estao_despublicadas(self):
        legado = ChamadaInterna.objects.filter(legado=True)
        self.assertEqual(legado.count(), 3)
        self.assertFalse(legado.filter(publicada=True).exists())
