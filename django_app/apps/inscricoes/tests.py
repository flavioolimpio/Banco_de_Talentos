from decimal import Decimal

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.management import call_command
from django.test import RequestFactory, TestCase
from django.utils import timezone

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

    def test_export_csv_registra_auditlog(self):
        from apps.auditoria.models import AuditAction, AuditLog
        self.client.force_login(self.admin_user)
        self.client.post(
            "/admin/inscricoes/inscricao/",
            {
                "action": "exportar_csv",
                "_selected_action": [str(self.inscricao.pk)],
            },
        )
        self.assertTrue(
            AuditLog.objects.filter(acao=AuditAction.CSV_EXPORTADO).exists()
        )


from django.urls import reverse


class InscricaoUrlsTest(TestCase):
    def test_url_inscricao_resolve(self):
        url = reverse("inscricao")
        self.assertEqual(url, "/inscricao/")

    def test_url_confirmacao_resolve(self):
        url = reverse("inscricao_confirmacao")
        self.assertEqual(url, "/inscricao/confirmacao/")


from django.core.files.uploadedfile import SimpleUploadedFile

from apps.inscricoes.forms import InscricaoForm
from apps.usuarios.models import Usuario, Vinculo


class InscricaoFormTest(TestCase):
    def _usuario(self, vinculo=Vinculo.ESTUDANTE):
        return Usuario(vinculo=vinculo)

    def _pdf(self, content=b"%PDF-1.4 ok", name="test.pdf", size=None):
        if size:
            content = b"%PDF-" + b"x" * (size - 5)
        return SimpleUploadedFile(name, content, content_type="application/pdf")

    def test_pdf_com_bytes_invalidos_e_rejeitado(self):
        pdf = SimpleUploadedFile("test.pdf", b"not a pdf", content_type="application/pdf")
        form = InscricaoForm(
            {"tipo_servidor": "", "aceite_envio": False},
            files={"comprovantes_pdf": pdf},
            usuario=self._usuario(),
            acao="rascunho",
        )
        self.assertFalse(form.is_valid())
        self.assertIn("comprovantes_pdf", form.errors)

    def test_pdf_maior_que_10mb_e_rejeitado(self):
        pdf = self._pdf(size=10 * 1024 * 1024 + 1)
        form = InscricaoForm(
            {"tipo_servidor": "", "aceite_envio": False},
            files={"comprovantes_pdf": pdf},
            usuario=self._usuario(),
            acao="rascunho",
        )
        self.assertFalse(form.is_valid())
        self.assertIn("comprovantes_pdf", form.errors)

    def test_pdf_valido_passa(self):
        pdf = self._pdf()
        form = InscricaoForm(
            {"tipo_servidor": "", "aceite_envio": False},
            files={"comprovantes_pdf": pdf},
            usuario=self._usuario(),
            acao="rascunho",
        )
        self.assertTrue(form.is_valid())

    def test_sem_pdf_e_valido_para_rascunho(self):
        form = InscricaoForm(
            {"tipo_servidor": "", "aceite_envio": False},
            usuario=self._usuario(),
            acao="rascunho",
        )
        self.assertTrue(form.is_valid())

    def test_tipo_servidor_obrigatorio_para_servidor(self):
        form = InscricaoForm(
            {"tipo_servidor": "", "aceite_envio": False},
            usuario=self._usuario(Vinculo.SERVIDOR),
            acao="rascunho",
        )
        self.assertFalse(form.is_valid())
        self.assertIn("tipo_servidor", form.errors)

    def test_aceite_envio_obrigatorio_para_enviar(self):
        form = InscricaoForm(
            {"tipo_servidor": "", "aceite_envio": False},
            usuario=self._usuario(),
            acao="enviar",
        )
        self.assertFalse(form.is_valid())
        self.assertIn("aceite_envio", form.errors)

    def test_tipo_servidor_valido_aceito_para_servidor(self):
        from apps.inscricoes.models import TipoServidor
        form = InscricaoForm(
            {"tipo_servidor": TipoServidor.PESQUISADOR, "aceite_envio": False},
            usuario=self._usuario(Vinculo.SERVIDOR),
            acao="rascunho",
        )
        self.assertTrue(form.is_valid())

    def test_aceite_envio_true_com_enviar_valido(self):
        form = InscricaoForm(
            {"tipo_servidor": "", "aceite_envio": True},
            usuario=self._usuario(),
            acao="enviar",
        )
        self.assertTrue(form.is_valid())

    def test_extensao_errada_com_magic_bytes_pdf_rejeitada(self):
        exe = SimpleUploadedFile("malware.exe", b"%PDF-1.4 content", content_type="application/pdf")
        form = InscricaoForm(
            {"tipo_servidor": "", "aceite_envio": False},
            files={"comprovantes_pdf": exe},
            usuario=self._usuario(),
            acao="rascunho",
        )
        self.assertFalse(form.is_valid())
        self.assertIn("comprovantes_pdf", form.errors)


class InscricaoViewGetTest(TestCase):
    def setUp(self):
        call_command("popular_criterios", verbosity=0)
        self.candidato = Usuario.objects.create_user(
            cpf="11144477735",
            email="candidato@test.com",
            nome_completo="Candidato Teste",
            vinculo=Vinculo.ESTUDANTE,
            password="senha123",
        )
        self.client.force_login(self.candidato)

    def test_get_retorna_200(self):
        response = self.client.get(reverse("inscricao"))
        self.assertEqual(response.status_code, 200)

    def test_get_exibe_criterios_da_modalidade(self):
        from django.utils.html import escape
        response = self.client.get(reverse("inscricao"))
        criterios = CriterioEdital.objects.filter(modalidade="estudante")
        for criterio in criterios:
            self.assertContains(response, escape(criterio.criterio))

    def test_get_redireciona_se_inscricao_enviada(self):
        Inscricao.objects.create(
            usuario=self.candidato,
            modalidade="estudante",
            status=StatusInscricao.EM_ANALISE,
            enviada_em=timezone.now(),
        )
        response = self.client.get(reverse("inscricao"))
        self.assertRedirects(response, reverse("inscricao_confirmacao"))

    def test_get_sem_criterios_exibe_aviso(self):
        CriterioEdital.objects.filter(modalidade="estudante").update(ativo=False)
        response = self.client.get(reverse("inscricao"))
        self.assertContains(response, "preparação")


class InscricaoViewPostTest(TestCase):
    def setUp(self):
        call_command("popular_criterios", verbosity=0)
        self.candidato = Usuario.objects.create_user(
            cpf="11144477735",
            email="candidato@test.com",
            nome_completo="Candidato Teste",
            vinculo=Vinculo.ESTUDANTE,
            password="senha123",
        )
        self.client.force_login(self.candidato)
        self.criterios = list(CriterioEdital.objects.filter(modalidade="estudante", ativo=True))

    def _scores(self, valor="0"):
        return {f"score_{c.pk}": valor for c in self.criterios}

    def test_rascunho_cria_inscricao(self):
        data = {"action": "rascunho", **self._scores("5")}
        self.client.post(reverse("inscricao"), data)
        self.assertTrue(Inscricao.objects.filter(usuario=self.candidato).exists())

    def test_rascunho_salva_itens(self):
        data = {"action": "rascunho", **self._scores("5")}
        self.client.post(reverse("inscricao"), data)
        inscricao = Inscricao.objects.get(usuario=self.candidato)
        self.assertEqual(inscricao.itens.count(), len(self.criterios))

    def test_rascunho_redireciona_para_formulario(self):
        data = {"action": "rascunho", **self._scores("0")}
        response = self.client.post(reverse("inscricao"), data)
        self.assertRedirects(response, reverse("inscricao"))

    def test_rascunho_idempotente_nao_duplica_itens(self):
        data = {"action": "rascunho", **self._scores("3")}
        self.client.post(reverse("inscricao"), data)
        self.client.post(reverse("inscricao"), data)
        inscricao = Inscricao.objects.get(usuario=self.candidato)
        self.assertEqual(inscricao.itens.count(), len(self.criterios))

    def test_rascunho_registra_auditlog(self):
        from apps.auditoria.models import AuditAction, AuditLog
        data = {"action": "rascunho", **self._scores("0")}
        self.client.post(reverse("inscricao"), data)
        self.assertTrue(AuditLog.objects.filter(acao=AuditAction.INSCRICAO_SALVA).exists())

    def test_enviar_define_enviada_em(self):
        data = {"action": "enviar", "aceite_envio": True, **self._scores("0")}
        self.client.post(reverse("inscricao"), data)
        inscricao = Inscricao.objects.get(usuario=self.candidato)
        self.assertIsNotNone(inscricao.enviada_em)

    def test_enviar_status_em_analise(self):
        data = {"action": "enviar", "aceite_envio": True, **self._scores("0")}
        self.client.post(reverse("inscricao"), data)
        inscricao = Inscricao.objects.get(usuario=self.candidato)
        self.assertEqual(inscricao.status, StatusInscricao.EM_ANALISE)

    def test_enviar_redireciona_para_confirmacao(self):
        data = {"action": "enviar", "aceite_envio": True, **self._scores("0")}
        response = self.client.post(reverse("inscricao"), data)
        self.assertRedirects(response, reverse("inscricao_confirmacao"))

    def test_enviar_sem_aceite_retorna_form_com_erro(self):
        data = {"action": "enviar", "aceite_envio": False, **self._scores("0")}
        response = self.client.post(reverse("inscricao"), data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "verdadeiros")

    def test_pontuacao_maxima_respeitada(self):
        criterio = self.criterios[0]
        data = {"action": "rascunho", **self._scores("0")}
        data[f"score_{criterio.pk}"] = str(float(criterio.maximo) + 999)
        self.client.post(reverse("inscricao"), data)
        inscricao = Inscricao.objects.get(usuario=self.candidato)
        item = inscricao.itens.get(criterio=criterio)
        self.assertLessEqual(item.pontuacao, criterio.maximo)

    def test_pdf_upload_salvo(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        pdf = SimpleUploadedFile("comp.pdf", b"%PDF-1.4 ok", content_type="application/pdf")
        data = {"action": "rascunho", **self._scores("0")}
        self.client.post(reverse("inscricao"), data, files={"comprovantes_pdf": pdf})
        # POST via client.post passa files no segundo dict
        data2 = {"action": "rascunho", **self._scores("0")}
        self.client.post(reverse("inscricao"), {**data2, "comprovantes_pdf": pdf})
        inscricao = Inscricao.objects.get(usuario=self.candidato)
        self.assertTrue(bool(inscricao.comprovantes_pdf))


class ConfirmacaoViewTest(TestCase):
    def setUp(self):
        call_command("popular_criterios", verbosity=0)
        self.candidato = Usuario.objects.create_user(
            cpf="11144477735",
            email="candidato@test.com",
            nome_completo="Candidato Teste",
            vinculo=Vinculo.ESTUDANTE,
            password="senha123",
        )
        self.client.force_login(self.candidato)

    def test_sem_inscricao_redireciona(self):
        response = self.client.get(reverse("inscricao_confirmacao"))
        self.assertRedirects(response, reverse("inscricao"))

    def test_com_inscricao_retorna_200(self):
        Inscricao.objects.create(
            usuario=self.candidato,
            modalidade="estudante",
            status=StatusInscricao.EM_ANALISE,
            enviada_em=timezone.now(),
            total=Decimal("20.00"),
        )
        response = self.client.get(reverse("inscricao_confirmacao"))
        self.assertEqual(response.status_code, 200)

    def test_exibe_nome_candidato(self):
        Inscricao.objects.create(
            usuario=self.candidato,
            modalidade="estudante",
            status=StatusInscricao.EM_ANALISE,
            enviada_em=timezone.now(),
            total=Decimal("20.00"),
        )
        response = self.client.get(reverse("inscricao_confirmacao"))
        self.assertContains(response, "Candidato Teste")

    def test_exibe_total(self):
        Inscricao.objects.create(
            usuario=self.candidato,
            modalidade="estudante",
            status=StatusInscricao.EM_ANALISE,
            enviada_em=timezone.now(),
            total=Decimal("42.50"),
        )
        response = self.client.get(reverse("inscricao_confirmacao"))
        self.assertContains(response, "42,5")


class InscricaoDownloadTest(TestCase):
    def setUp(self):
        self.staff_user = Usuario.objects.create_user(
            cpf="52998224725",
            email="rh@ifg.edu.br",
            nome_completo="RH Staff",
            password="senha123",
            is_staff=True,
        )
        self.candidato = Usuario.objects.create_user(
            cpf="11144477735",
            email="candidato@test.com",
            nome_completo="Candidato Teste",
            vinculo=Vinculo.ESTUDANTE,
            password="senha123",
        )
        self.inscricao = Inscricao.objects.create(
            usuario=self.candidato,
            modalidade="estudante",
            status=StatusInscricao.EM_ANALISE,
            enviada_em=timezone.now(),
        )

    def _url(self):
        return reverse("download_comprovante", args=[self.inscricao.pk])

    def _add_pdf(self):
        from django.core.files.base import ContentFile
        self.inscricao.comprovantes_pdf.save(
            "comp.pdf", ContentFile(b"%PDF-1.4 ok"), save=False
        )
        self.inscricao.comprovantes_pdf_nome_original = "comp.pdf"
        self.inscricao.save()

    def test_sem_login_redireciona(self):
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response["Location"])

    def test_nao_staff_retorna_403(self):
        self.client.force_login(self.candidato)
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 403)

    def test_sem_pdf_retorna_404(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 404)

    def test_com_pdf_retorna_200_e_content_disposition(self):
        self._add_pdf()
        self.client.force_login(self.staff_user)
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200)
        self.assertIn("comp.pdf", response.get("Content-Disposition", ""))

    def test_com_pdf_registra_auditlog(self):
        from apps.auditoria.models import AuditAction, AuditLog
        self._add_pdf()
        self.client.force_login(self.staff_user)
        self.client.get(self._url())
        self.assertTrue(
            AuditLog.objects.filter(acao=AuditAction.COMPROVANTE_DOWNLOAD).exists()
        )

    def test_media_direta_retorna_404(self):
        response = self.client.get("/media/comprovantes/estudante/11144477735/comp.pdf")
        self.assertEqual(response.status_code, 404)
