# apps/inscricoes/test_chamadas.py
# Banco de Talentos — Polo de Inovação IFG
# Fluxo de inscrição por Chamada Interna (Retificação 4, itens 5.1 a 5.16).

from datetime import timedelta
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
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
from apps.usuarios.tests import completar_cadastro

def xml_novo(atualizado=None, nome="curriculo.xml", conteudo=None):
    """Um currículo Lattes mínimo, atualizado hoje (ou na data pedida)."""
    atualizado = atualizado or timezone.localdate()
    if conteudo is None:
        conteudo = (
            '<?xml version="1.0" encoding="ISO-8859-1"?>'
            f'<CURRICULO-VITAE NUMERO-IDENTIFICADOR="1234567890123456" '
            f'DATA-ATUALIZACAO="{atualizado:%d%m%Y}"><DADOS-GERAIS NOME-COMPLETO="Candidata"/>'
            "</CURRICULO-VITAE>"
        ).encode("latin-1")
    return SimpleUploadedFile(nome, conteudo, content_type="text/xml")


def pdf_novo(nome="matricula.pdf", conteudo=b"%PDF-1.4 declaracao de matricula"):
    """PDF mínimo: declaração de matrícula e histórico do estudante (Edital 31, 5.4, c)."""
    return SimpleUploadedFile(nome, conteudo, content_type="application/pdf")


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
        completar_cadastro(self.usuario)
        self.client.force_login(self.usuario)

    def _post(self, **extra):
        dados = {
            "action": "enviar",
            "vaga": self.vaga.pk,
            "declara_disponibilidade": "on",
            "lattes_xml": xml_novo(),
            "matricula_pdf": pdf_novo(),
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

    def test_envio_nao_pontua_ate_a_revisao(self):
        # O candidato não responde o quadro: cada critério vira um item
        # zerado, que o RH preenche com o que apurar do XML.
        self._post()
        inscricao = Inscricao.objects.get(usuario=self.usuario, chamada=self.chamada)
        self.assertEqual(inscricao.total, Decimal("0"))
        self.assertEqual(
            list(inscricao.itens.values_list("quantidade", "opcao", "pontuacao")),
            [(0, None, Decimal("0")), (0, None, Decimal("0"))],
        )


class EnvioDaInscricaoTest(BaseChamada):
    def test_envio_grava_itens_e_status(self):
        self._post()
        inscricao = Inscricao.objects.get(usuario=self.usuario, chamada=self.chamada)
        self.assertEqual(inscricao.status, StatusInscricao.EM_ANALISE)
        self.assertIsNotNone(inscricao.enviada_em)
        self.assertEqual(inscricao.vaga, self.vaga)
        self.assertEqual(inscricao.itens.count(), 2)
        self.assertTrue(inscricao.declara_disponibilidade)
        self.assertEqual(inscricao.lattes_xml_nome_original, "curriculo.xml")

    def test_formulario_so_tem_xml_e_disponibilidade(self):
        resposta = self.client.get(reverse("inscricao_chamada", args=[self.chamada.pk]))
        self.assertContains(resposta, 'name="lattes_xml"')
        self.assertContains(resposta, 'name="declara_disponibilidade"')
        self.assertContains(resposta, 'name="licencas_maternidade"')
        for fora in ("qtd_", "opcao_", "comprovantes_pdf", "declara_nao_redistribuicao",
                     "aceite_envio", "art. 299"):
            self.assertNotContains(resposta, fora)

    def test_rascunho_nao_exige_nada(self):
        resposta = self.client.post(
            reverse("inscricao_chamada", args=[self.chamada.pk]), {"action": "rascunho"}
        )
        self.assertEqual(resposta.status_code, 302)
        inscricao = Inscricao.objects.get(usuario=self.usuario, chamada=self.chamada)
        self.assertEqual(inscricao.status, StatusInscricao.PENDENTE)
        self.assertIsNone(inscricao.enviada_em)

    def test_envio_sem_declaracao_de_horas_e_recusado(self):
        self._post(declara_disponibilidade="")
        self.assertFalse(Inscricao.objects.filter(usuario=self.usuario).exists())

    def test_envio_sem_xml_e_recusado(self):
        self._post(lattes_xml="")
        self.assertFalse(Inscricao.objects.filter(usuario=self.usuario).exists())

    def test_xml_do_rascunho_vale_para_o_envio(self):
        self._post(action="rascunho")
        resposta = self._post(lattes_xml="")
        self.assertEqual(resposta.status_code, 302)
        inscricao = Inscricao.objects.get(usuario=self.usuario, chamada=self.chamada)
        self.assertEqual(inscricao.status, StatusInscricao.EM_ANALISE)

    def test_zip_e_recusado(self):
        resposta = self._post(lattes_xml=xml_novo(nome="CV_123.zip"))
        self.assertContains(resposta, "extraia o .xml")
        self.assertFalse(Inscricao.objects.filter(usuario=self.usuario).exists())

    def test_xml_que_nao_e_lattes_e_recusado(self):
        resposta = self._post(lattes_xml=xml_novo(conteudo=b"<planilha/>"))
        self.assertContains(resposta, "não é um currículo Lattes")

    def test_xml_com_entidade_e_recusado(self):
        # Defesa contra "billion laughs" / entidade externa.
        malicioso = (
            b'<?xml version="1.0"?><!DOCTYPE CURRICULO-VITAE [<!ENTITY x SYSTEM "file:///etc/passwd">]>'
            b'<CURRICULO-VITAE DATA-ATUALIZACAO="01012026">&x;</CURRICULO-VITAE>'
        )
        resposta = self._post(lattes_xml=xml_novo(conteudo=malicioso))
        self.assertContains(resposta, "não é um currículo Lattes")

    def test_xml_com_caractere_sujo_e_aceito(self):
        # Defeito comum de exportação do Lattes: "&" solto e caractere de controle.
        sujo = (
            f'<CURRICULO-VITAE DATA-ATUALIZACAO="{timezone.localdate():%d%m%Y}">'
            '<DADOS-GERAIS NOME-COMPLETO="P&D \x01"/></CURRICULO-VITAE>'
        ).encode("latin-1")
        self.assertEqual(self._post(lattes_xml=xml_novo(conteudo=sujo)).status_code, 302)

    def test_curriculo_desatualizado_e_recusado(self):
        antigo = timezone.localdate() - timedelta(days=200)
        resposta = self._post(lattes_xml=xml_novo(atualizado=antigo))
        self.assertContains(resposta, "há mais de 6 meses")
        self.assertFalse(Inscricao.objects.filter(usuario=self.usuario).exists())

    def test_licencas_maternidade_sao_registradas(self):
        self._post(licencas_maternidade="2")
        inscricao = Inscricao.objects.get(usuario=self.usuario, chamada=self.chamada)
        self.assertEqual(inscricao.licencas_maternidade, 2)

    def test_xml_vai_para_a_pasta_da_chamada(self):
        self._post()
        inscricao = Inscricao.objects.get(usuario=self.usuario, chamada=self.chamada)
        self.assertIn(f"lattes/chamada-{self.chamada.pk}/", inscricao.lattes_xml.name)

    def test_reenvio_nao_duplica_itens(self):
        self._post()
        Inscricao.objects.filter(usuario=self.usuario).update(status=StatusInscricao.PENDENTE)
        self._post()
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


class CadastroIncompletoTest(BaseChamada):
    """Item 5.3: só se inscreve quem tem o cadastro completo (item 4.4.2)."""

    def setUp(self):
        super().setUp()
        self.usuario.lattes = ""
        self.usuario.save()

    def test_tela_mostra_o_que_falta(self):
        resposta = self.client.get(reverse("inscricao_chamada", args=[self.chamada.pk]))
        self.assertContains(resposta, "Complete o seu cadastro")
        self.assertContains(resposta, "link do currículo Lattes")
        self.assertNotContains(resposta, 'name="lattes_xml"')

    def test_post_nao_cria_inscricao(self):
        self._post()
        self._post(action="rascunho")
        self.assertFalse(Inscricao.objects.filter(usuario=self.usuario).exists())


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
        self._post()
        inscricao = Inscricao.objects.get(usuario=self.usuario, chamada=self.chamada)
        self.assertEqual(
            set(inscricao.itens.values_list("criterio__chamada", flat=True)), {self.chamada.pk}
        )

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


class RevisaoRhTest(BaseChamada):
    """O RH lança as quantidades que apurou do XML; os pontos são calculados.

    Ninguém digita pontuação — vale o CriterioEdital.pontuar().
    """

    def setUp(self):
        super().setUp()
        self._post()  # inscrição enviada com o XML, itens zerados
        self.inscricao = Inscricao.objects.get(usuario=self.usuario, chamada=self.chamada)
        self.rh = Usuario.objects.create_superuser(
            cpf="11144477735",
            email="rh@ifg.edu.br",
            nome_completo="RH Teste",
            password="senha123",
        )
        self.client.force_login(self.rh)
        self.url = reverse("revisao_rh", args=[self.inscricao.pk])

    def _revisar(self, **extra):
        item_qtd = self.inscricao.itens.get(criterio=self.contagem)
        item_opc = self.inscricao.itens.get(criterio=self.escolha)
        dados = {
            "acao": "aprovar",
            "parecer_geral": "ok",
            f"validado_qtd_{item_qtd.pk}": "2",
            f"validado_opcao_{item_opc.pk}": str(self.doutorado.pk),
        }
        dados.update(extra)
        return self.client.post(self.url, dados)

    def test_confirmar_tudo_mantem_a_pontuacao(self):
        self._revisar()
        self.inscricao.refresh_from_db()
        self.assertEqual(self.inscricao.status, StatusInscricao.APROVADA)
        self.assertEqual(self.inscricao.total_validado, Decimal("180"))

    def test_quantidade_lancada_define_os_pontos(self):
        item_qtd = self.inscricao.itens.get(criterio=self.contagem)
        self._revisar(**{f"validado_qtd_{item_qtd.pk}": "1"})
        self.inscricao.refresh_from_db()
        self.assertEqual(self.inscricao.total_validado, Decimal("140"))  # 40 + 100
        item_qtd.refresh_from_db()
        self.assertEqual(item_qtd.pontuacao_validada, Decimal("40"))
        # a revisão grava no campo validado, não na resposta
        self.assertEqual(item_qtd.quantidade, 0)

    def test_admin_nao_expoe_o_caminho_do_xml(self):
        # O caminho em /media/ contém o CPF; o acesso é pela view auditada.
        self.assertIn(self.usuario.cpf, self.inscricao.lattes_xml.name)
        resposta = self.client.get(
            reverse("admin:inscricoes_inscricao_change", args=[self.inscricao.pk])
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertNotContains(resposta, "/media/")
        self.assertNotContains(resposta, self.inscricao.lattes_xml.name)
        self.assertNotContains(resposta, f"/{self.usuario.cpf}/")
        self.assertNotContains(resposta, 'name="lattes_xml"')
        self.assertContains(resposta, reverse("download_lattes_xml", args=[self.inscricao.pk]))

    def test_trocar_a_opcao_troca_os_pontos(self):
        item_opc = self.inscricao.itens.get(criterio=self.escolha)
        self._revisar(**{f"validado_opcao_{item_opc.pk}": str(self.mestrado.pk)})
        self.inscricao.refresh_from_db()
        self.assertEqual(self.inscricao.total_validado, Decimal("150"))  # 80 + 70

    def test_desmarcar_a_opcao_zera_o_item(self):
        item_opc = self.inscricao.itens.get(criterio=self.escolha)
        self._revisar(**{f"validado_opcao_{item_opc.pk}": ""})
        self.inscricao.refresh_from_db()
        self.assertEqual(self.inscricao.total_validado, Decimal("80"))

    def test_quantidade_acima_do_teto_respeita_o_maximo(self):
        item_qtd = self.inscricao.itens.get(criterio=self.contagem)
        self._revisar(**{f"validado_qtd_{item_qtd.pk}": "99"})
        self.inscricao.refresh_from_db()
        self.assertEqual(self.inscricao.total_validado, Decimal("220"))  # 120 (teto) + 100

    def test_observacao_do_avaliador_e_gravada(self):
        item_qtd = self.inscricao.itens.get(criterio=self.contagem)
        self._revisar(**{f"obs_{item_qtd.pk}": "Comprovante do projeto B ilegível."})
        item_qtd.refresh_from_db()
        self.assertEqual(item_qtd.observacao_avaliacao, "Comprovante do projeto B ilegível.")

    def test_tela_aponta_para_o_xml(self):
        resposta = self.client.get(self.url)
        self.assertContains(resposta, reverse("download_lattes_xml", args=[self.inscricao.pk]))
        self.assertContains(resposta, "Quantidade apurada no XML")
        self.assertNotContains(resposta, "Declarado")
        self.assertNotContains(resposta, "IFGProduz")

    def test_rh_baixa_o_xml_e_fica_no_auditlog(self):
        from apps.auditoria.models import AuditLog

        resposta = self.client.get(reverse("download_lattes_xml", args=[self.inscricao.pk]))
        self.assertEqual(resposta.status_code, 200)
        self.assertIn(b"CURRICULO-VITAE", b"".join(resposta.streaming_content))
        log = AuditLog.objects.latest("id")
        self.assertEqual(log.detalhes, {"inscricao_id": self.inscricao.pk, "arquivo": "lattes_xml"})

    def test_candidato_nao_baixa_o_xml(self):
        self.client.force_login(self.usuario)
        resposta = self.client.get(reverse("download_lattes_xml", args=[self.inscricao.pk]))
        self.assertEqual(resposta.status_code, 403)

    def test_exportar_lattes_xml_copia_os_enviados(self):
        import tempfile
        from pathlib import Path

        pasta = Path(tempfile.mkdtemp()) / "xmls"
        call_command("exportar_lattes_xml", chamada=self.chamada.pk, saida=str(pasta), verbosity=0)
        arquivos = [a.name for a in pasta.iterdir()]
        self.assertEqual(arquivos, [f"insc{self.inscricao.pk}_candidata-teste.xml"])
        self.assertNotIn(self.usuario.cpf, arquivos[0])
        planilha = (pasta.parent / "xmls_inscricoes.csv").read_text(encoding="utf-8-sig")
        self.assertIn(f"{arquivos[0]};{self.inscricao.pk};Candidata Teste;Pq 12;", planilha)
        self.assertTrue(planilha.strip().endswith(";0"))  # licenças


class RevisaoLegadoTest(TestCase):
    """Inscrição do credenciamento antigo continua com pontuação digitada.

    Recalcular pelos pontos-por-unidade zeraria a pontuação histórica, porque
    aqueles critérios não têm pontos por unidade nem opções.
    """

    def setUp(self):
        from apps.inscricoes.models import InscricaoItem

        self.legado = ChamadaInterna.objects.get(numero=31, ano=2026)
        self.criterio = CriterioEdital.objects.filter(chamada=self.legado).first()
        self.usuario = Usuario.objects.create_user(
            cpf="52998224725", email="leg@test.com", nome_completo="Legado",
            vinculo=Vinculo.ESTUDANTE, password="senha123",
        )
        self.inscricao = Inscricao.objects.create(
            usuario=self.usuario, chamada=self.legado, modalidade=Vinculo.ESTUDANTE,
            status=StatusInscricao.EM_ANALISE, total=Decimal("60"),
        )
        self.item = InscricaoItem.objects.create(
            inscricao=self.inscricao, criterio=self.criterio, pontuacao=Decimal("60")
        )
        rh = Usuario.objects.create_superuser(
            cpf="11144477735", email="rh2@ifg.edu.br", nome_completo="RH", password="senha123",
        )
        self.client.force_login(rh)
        self.url = reverse("revisao_rh", args=[self.inscricao.pk])

    def test_campo_em_branco_mantem_a_pontuacao_declarada(self):
        self.client.post(self.url, {"acao": "aprovar", "parecer_geral": "ok",
                                    f"validado_{self.item.pk}": ""})
        self.inscricao.refresh_from_db()
        self.assertEqual(self.inscricao.total_validado, Decimal("60"))

    def test_rh_pode_digitar_a_pontuacao(self):
        self.client.post(self.url, {"acao": "aprovar", "parecer_geral": "ok",
                                    f"validado_{self.item.pk}": "45"})
        self.inscricao.refresh_from_db()
        self.assertEqual(self.inscricao.total_validado, Decimal("45"))


class ExportarConvocadosTest(BaseChamada):
    """A convocação é sempre por chamada — nunca todas misturadas."""

    def setUp(self):
        super().setUp()
        self._post()
        self.inscricao = Inscricao.objects.get(usuario=self.usuario, chamada=self.chamada)
        self.inscricao.status = StatusInscricao.APROVADA
        self.inscricao.total_validado = Decimal("180")
        self.inscricao.save(update_fields=["status", "total_validado"])

    def _exportar(self, **kwargs):
        import tempfile
        from pathlib import Path

        from openpyxl import load_workbook

        destino = Path(tempfile.mkdtemp()) / "convocados.xlsx"
        call_command("exportar_convocados", saida=str(destino), verbosity=0, **kwargs)
        if not destino.exists():
            return None
        return list(load_workbook(destino).active.iter_rows(values_only=True))

    def test_exige_chamada(self):
        with self.assertRaises(CommandError):
            call_command("exportar_convocados", verbosity=0)

    def test_empate_traz_o_mais_velho_primeiro(self):
        from datetime import date

        mais_velho = Usuario.objects.create_user(
            cpf="11144477735", email="velho@test.com", nome_completo="Mais Velho",
            vinculo=Vinculo.ESTUDANTE, password="senha123",
        )
        completar_cadastro(mais_velho)
        mais_velho.data_nascimento = date(1960, 1, 1)
        mais_velho.save(update_fields=["data_nascimento"])
        Inscricao.objects.create(
            usuario=mais_velho, chamada=self.chamada, modalidade=Vinculo.ESTUDANTE,
            status=StatusInscricao.APROVADA, total_validado=Decimal("180"),
        )
        linhas = self._exportar(chamada=self.chamada.pk)
        self.assertEqual(linhas[0][2], "Data de nascimento")
        self.assertEqual([linha[0] for linha in linhas[1:]], ["Mais Velho", "Candidata Teste"])

    def test_chamada_inexistente_recusa(self):
        with self.assertRaises(CommandError):
            call_command("exportar_convocados", chamada=99999, verbosity=0)

    def test_traz_somente_a_chamada_pedida(self):
        outra = ChamadaInterna.objects.create(
            numero=9, ano=2027, titulo="Outra",
            abertura=timezone.now(), encerramento=timezone.now() + timedelta(days=1),
        )
        outro_usuario = Usuario.objects.create_user(
            cpf="11144477735", email="outro@test.com", nome_completo="Outro Aprovado",
            vinculo=Vinculo.ESTUDANTE, password="senha123",
        )
        Inscricao.objects.create(
            usuario=outro_usuario, chamada=outra, modalidade=Vinculo.ESTUDANTE,
            status=StatusInscricao.APROVADA, total_validado=Decimal("999"),
        )
        linhas = self._exportar(chamada=self.chamada.pk)
        nomes = [linha[0] for linha in linhas[1:]]
        self.assertIn("Candidata Teste", nomes)
        self.assertNotIn("Outro Aprovado", nomes)

    def test_sem_aprovados_nao_gera_arquivo(self):
        self.inscricao.status = StatusInscricao.EM_ANALISE
        self.inscricao.save(update_fields=["status"])
        self.assertIsNone(self._exportar(chamada=self.chamada.pk))

    def test_filtro_por_vaga(self):
        self.assertIsNone(self._exportar(chamada=self.chamada.pk, vaga="XX-99"))

    def test_registra_auditlog(self):
        from apps.auditoria.models import AuditAction, AuditLog

        self._exportar(chamada=self.chamada.pk)
        log = AuditLog.objects.filter(acao=AuditAction.CSV_EXPORTADO).latest("id")
        self.assertEqual(log.detalhes["comando"], "exportar_convocados")
        self.assertEqual(log.detalhes["chamada"], self.chamada.pk)


class EmailsChamadaTest(BaseChamada):
    """Lista de divulgação: só quem pode se inscrever é avisado.

    Avisar quem não tem vaga na chamada foi a reclamação que originou toda
    esta mudança — item 5.2.2 do Edital combinado com as vagas de fato
    ofertadas.
    """

    def setUp(self):
        super().setUp()
        # A chamada base só tem vaga de ESTUDANTE.
        self.servidor = Usuario.objects.create_user(
            cpf="11144477735", email="servidor@test.com", nome_completo="Servidor",
            vinculo=Vinculo.SERVIDOR, password="senha123",
        )
        self.inativo = Usuario.objects.create_user(
            cpf="15350946056", email="inativo@test.com", nome_completo="Inativo",
            vinculo=Vinculo.ESTUDANTE, password="senha123", is_active=False,
        )

    def _gerar(self, **kwargs):
        import tempfile
        from pathlib import Path

        destino = Path(tempfile.mkdtemp()) / "aviso.txt"
        call_command("emails_chamada", saida=str(destino), verbosity=0, **kwargs)
        return destino.read_text(encoding="utf-8") if destino.exists() else None

    def test_exige_chamada(self):
        with self.assertRaises(CommandError):
            call_command("emails_chamada", verbosity=0)

    def test_so_avisa_quem_tem_vaga_no_seu_vinculo(self):
        conteudo = self._gerar(chamada=self.chamada.pk)
        self.assertIn("candidato@test.com", conteudo)      # estudante
        self.assertNotIn("servidor@test.com", conteudo)    # sem vaga de servidor

    def test_inativo_fica_de_fora(self):
        conteudo = self._gerar(chamada=self.chamada.pk)
        self.assertNotIn("inativo@test.com", conteudo)

    def test_publico_muda_com_as_vagas(self):
        Vaga.objects.create(
            chamada=self.chamada, codigo="Pq 99", funcao="Pesquisador(a)",
            modalidade=Vinculo.SERVIDOR, quantidade=1,
        )
        conteudo = self._gerar(chamada=self.chamada.pk)
        self.assertIn("servidor@test.com", conteudo)
        self.assertIn("servidores(as) do IFG", conteudo)
        self.assertIn("estudantes do IFG", conteudo)

    def test_texto_traz_prazo_vagas_e_ressalvas(self):
        conteudo = self._gerar(chamada=self.chamada.pk)
        self.assertIn("Chamada Interna nº 01/2027", conteudo)
        self.assertIn("Rota do Pescado", conteudo)
        self.assertIn("Pq 12", conteudo)
        self.assertIn(self.chamada.encerramento.strftime("%d/%m/%Y"), conteudo)
        # ressalvas dos itens 5.16 e 5.2.2
        self.assertIn("não gera nenhum prejuízo", conteudo)
        self.assertIn("aviso complementar", conteudo)

    def test_emails_saem_colados_para_o_cco(self):
        conteudo = self._gerar(chamada=self.chamada.pk)
        primeira_linha = conteudo.splitlines()[0]
        self.assertIn("@", primeira_linha)
        self.assertNotIn("Assunto", primeira_linha)

    def test_chamada_sem_vagas_nao_gera_arquivo(self):
        vazia = ChamadaInterna.objects.create(
            numero=8, ano=2027, titulo="Sem vagas",
            abertura=timezone.now(), encerramento=timezone.now() + timedelta(days=1),
        )
        self.assertIsNone(self._gerar(chamada=vazia.pk))

    def test_registra_auditlog(self):
        from apps.auditoria.models import AuditAction, AuditLog

        self._gerar(chamada=self.chamada.pk)
        log = AuditLog.objects.filter(acao=AuditAction.CSV_EXPORTADO).latest("id")
        self.assertEqual(log.detalhes["comando"], "emails_chamada")
        self.assertEqual(log.detalhes["chamada"], self.chamada.pk)

class QuadroAteCemPontosTest(TestCase):
    """Anexo I, item 7.1: o quadro de cada Chamada soma no máximo 100 pontos."""

    def setUp(self):
        self.chamada = ChamadaInterna.objects.create(
            numero=9, ano=2027, titulo="Quadro", abertura=timezone.now(),
            encerramento=timezone.now() + timedelta(days=5),
        )

    def _formset(self, *maximos, chamada=None):
        from django.forms import inlineformset_factory

        from apps.inscricoes.admin import QuadroCriteriosFormSet

        FormSet = inlineformset_factory(
            ChamadaInterna, CriterioEdital, formset=QuadroCriteriosFormSet, extra=0,
            fields=("ordem", "modalidade", "tipo_servidor", "item_id", "criterio", "regra", "maximo", "ativo"),
        )
        dados = {"criterios-TOTAL_FORMS": len(maximos), "criterios-INITIAL_FORMS": 0}
        for i, maximo in enumerate(maximos):
            dados.update({
                f"criterios-{i}-ordem": i + 1, f"criterios-{i}-modalidade": Vinculo.ESTUDANTE,
                f"criterios-{i}-item_id": f"item{i}", f"criterios-{i}-criterio": "Critério",
                f"criterios-{i}-regra": "Regra", f"criterios-{i}-maximo": maximo,
                f"criterios-{i}-ativo": "on",
            })
        return FormSet(dados, instance=chamada or self.chamada, prefix="criterios")

    def test_aceita_ate_100(self):
        self.assertTrue(self._formset("60", "40").is_valid())

    def test_recusa_acima_de_100(self):
        formset = self._formset("60", "50")
        self.assertFalse(formset.is_valid())
        self.assertIn("soma 110 pontos", formset.non_form_errors()[0])

    def test_legado_fica_de_fora(self):
        self.chamada.legado = True
        self.chamada.save()
        self.assertTrue(self._formset("200").is_valid())

    def test_edicao_avulsa_conta_os_outros_criterios(self):
        from apps.inscricoes.admin import CriterioEditalForm

        CriterioEdital.objects.create(
            chamada=self.chamada, modalidade=Vinculo.ESTUDANTE, item_id="a", ordem=1,
            criterio="A", regra="A", maximo=Decimal("70"),
        )
        dados = {"chamada": self.chamada.pk, "modalidade": Vinculo.ESTUDANTE, "item_id": "b",
                 "ordem": 2, "criterio": "B", "regra": "B", "tipo": TipoCriterio.CONTAGEM,
                 "maximo": "40", "ativo": "on"}
        self.assertFalse(CriterioEditalForm(dados).is_valid())
        dados["maximo"] = "30"
        self.assertTrue(CriterioEditalForm(dados).is_valid())


class MatriculaEstudanteTest(BaseChamada):
    """Edital 31, item 5.4, c: o estudante anexa a declaração de matrícula e o histórico."""

    def test_envio_grava_o_pdf(self):
        self._post()
        inscricao = Inscricao.objects.get(usuario=self.usuario)
        self.assertTrue(inscricao.comprovantes_pdf)
        self.assertEqual(inscricao.comprovantes_pdf_nome_original, "matricula.pdf")

    def test_estudante_nao_envia_sem_o_pdf(self):
        dados = {"action": "enviar", "vaga": self.vaga.pk, "declara_disponibilidade": "on", "lattes_xml": xml_novo()}
        resposta = self.client.post(reverse("inscricao_chamada", args=[self.chamada.pk]), dados)
        self.assertContains(resposta, "Envie a declaração de matrícula")
        self.assertFalse(Inscricao.objects.filter(usuario=self.usuario, enviada_em__isnull=False).exists())

    def test_recusa_arquivo_que_nao_e_pdf(self):
        resposta = self._post(matricula_pdf=pdf_novo(conteudo=b"nao sou pdf"))
        self.assertContains(resposta, "não é um PDF válido")

    def test_servidor_nao_ve_o_campo(self):
        self.usuario.vinculo = Vinculo.SERVIDOR
        completar_cadastro(self.usuario)  # o servidor exige campos que o estudante não tem
        resposta = self.client.get(reverse("inscricao_chamada", args=[self.chamada.pk]))
        self.assertContains(resposta, 'name="lattes_xml"')
        self.assertNotContains(resposta, 'name="matricula_pdf"')
