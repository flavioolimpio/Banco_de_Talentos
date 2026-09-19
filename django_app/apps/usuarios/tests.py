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


    def test_home_exibe_foto_do_polo(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, "imagens/polo.jpg")

    def test_home_nao_menciona_energia(self):
        # A home deixou de carregar o escopo antigo do Polo (energia) — decisão
        # da gestão em 18/09/2026.
        response = self.client.get(reverse("home"))
        self.assertNotContains(response, "Energ")
        self.assertNotContains(response, "energ")


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


class MeuCadastroFormTest(TestCase):
    def setUp(self):
        self.user = Usuario.objects.create_user(
            cpf="52998224725",
            email="formtest@test.com",
            nome_completo="Form Teste",
            vinculo=Vinculo.SERVIDOR,
            password="senha123",
        )

    def test_form_salva_nome_completo(self):
        from apps.usuarios.forms import MeuCadastroForm
        form = MeuCadastroForm(
            {"nome_completo": "Novo Nome", "email": self.user.email, "telefone": "", "resumo": ""},
            instance=self.user,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_nao_tem_campo_cpf(self):
        from apps.usuarios.forms import MeuCadastroForm
        form = MeuCadastroForm(instance=self.user)
        self.assertNotIn("cpf", form.fields)

    def test_form_tem_campo_email_obrigatorio(self):
        # O e-mail passou a ser editável pelo candidato (ele é o canal de
        # divulgação das chamadas). Continua obrigatório: salvar em branco
        # gravaria email="" e colidiria no unique com o próximo que fizesse
        # o mesmo, além de derrubar a recuperação de senha.
        from apps.usuarios.forms import MeuCadastroForm
        form = MeuCadastroForm(instance=self.user)
        self.assertIn("email", form.fields)
        self.assertTrue(form.fields["email"].required)

    def test_form_rejeita_email_em_branco(self):
        from apps.usuarios.forms import MeuCadastroForm
        form = MeuCadastroForm({"nome_completo": "X", "email": ""}, instance=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_form_rejeita_email_de_outro_usuario(self):
        from apps.usuarios.forms import MeuCadastroForm
        Usuario.objects.create_user(
            cpf="11144477735",
            email="ocupado@test.com",
            nome_completo="Outro",
            vinculo=Vinculo.SERVIDOR,
            password="senha123",
        )
        form = MeuCadastroForm(
            {"nome_completo": "X", "email": "OCUPADO@test.com"}, instance=self.user
        )
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_form_aceita_o_proprio_email_sem_alteracao(self):
        # Sem o exclude(pk=...) no clean_email, salvar sem mudar o e-mail
        # colidiria com o próprio registro.
        from apps.usuarios.forms import MeuCadastroForm
        form = MeuCadastroForm(
            {"nome_completo": "X", "email": self.user.email}, instance=self.user
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_valida_tamanho_do_resumo(self):
        from apps.usuarios.forms import MeuCadastroForm
        curto = MeuCadastroForm(
            {"nome_completo": "X", "email": self.user.email, "resumo": "palavra " * 10},
            instance=self.user,
        )
        self.assertFalse(curto.is_valid())
        self.assertIn("resumo", curto.errors)

        longo = MeuCadastroForm(
            {"nome_completo": "X", "email": self.user.email, "resumo": "palavra " * 300},
            instance=self.user,
        )
        self.assertFalse(longo.is_valid())

        ok = MeuCadastroForm(
            {"nome_completo": "X", "email": self.user.email, "resumo": "palavra " * 80},
            instance=self.user,
        )
        self.assertTrue(ok.is_valid(), ok.errors)

    def test_form_nao_tem_campo_vinculo(self):
        from apps.usuarios.forms import MeuCadastroForm
        form = MeuCadastroForm(instance=self.user)
        self.assertNotIn("vinculo", form.fields)


class MeuCadastroViewTest(TestCase):
    def setUp(self):
        self.user = Usuario.objects.create_user(
            cpf="52998224725",
            email="mcadastro@test.com",
            nome_completo="Cadastro Teste",
            vinculo=Vinculo.SERVIDOR,
            password="senha123",
        )
        self.client.force_login(self.user)

    def test_get_retorna_200(self):
        response = self.client.get(reverse("meu_cadastro"))
        self.assertEqual(response.status_code, 200)

    def test_get_exibe_nome_usuario(self):
        response = self.client.get(reverse("meu_cadastro"))
        self.assertContains(response, "Cadastro Teste")

    def test_get_exibe_cpf_formatado(self):
        response = self.client.get(reverse("meu_cadastro"))
        self.assertContains(response, "529.982.247-25")

    def test_get_aba_padrao_e_dados(self):
        response = self.client.get(reverse("meu_cadastro"))
        self.assertContains(response, "Dados Pessoais")

    def test_aba_dados_tem_uf_e_cidade(self):
        # A aba "Endereço" deixou de existir: UF e cidade subiram para "Dados".
        response = self.client.get(reverse("meu_cadastro") + "?aba=dados")
        self.assertContains(response, "UF")
        self.assertContains(response, "Cidade")

    def test_link_antigo_de_endereco_cai_em_dados(self):
        response = self.client.get(reverse("meu_cadastro") + "?aba=endereco")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dados Pessoais")

    def test_get_aba_formacao(self):
        response = self.client.get(reverse("meu_cadastro") + "?aba=formacao")
        self.assertContains(response, "Lattes")

    def test_post_salva_nome_completo(self):
        self.client.post(
            reverse("meu_cadastro") + "?aba=dados",
            {"nome_completo": "Nome Atualizado", "email": self.user.email, "telefone": ""},
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.nome_completo, "Nome Atualizado")

    def test_post_altera_email(self):
        from apps.auditoria.models import AuditAction, AuditLog
        email_original = self.user.email
        self.client.post(
            reverse("meu_cadastro") + "?aba=dados",
            {"nome_completo": "X", "email": "Novo.Email@IFG.edu.br"},
        )
        self.user.refresh_from_db()
        # normalizado para minúsculas, igual ao cadastro inicial
        self.assertEqual(self.user.email, "novo.email@ifg.edu.br")
        log = AuditLog.objects.filter(
            ator=self.user, acao=AuditAction.CADASTRO_ATUALIZADO
        ).latest("id")
        self.assertEqual(log.detalhes["email_anterior"], email_original)
        self.assertEqual(log.detalhes["email_novo"], "novo.email@ifg.edu.br")

    def test_post_nao_altera_email_para_o_de_outro_usuario(self):
        Usuario.objects.create_user(
            cpf="11144477735",
            email="ocupado@test.com",
            nome_completo="Outro",
            vinculo=Vinculo.SERVIDOR,
            password="senha123",
        )
        email_original = self.user.email
        self.client.post(
            reverse("meu_cadastro") + "?aba=dados",
            {"nome_completo": "X", "email": "ocupado@test.com"},
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, email_original)

    def test_post_nao_altera_vinculo(self):
        vinculo_original = self.user.vinculo
        self.client.post(
            reverse("meu_cadastro") + "?aba=dados",
            {"nome_completo": "X", "email": self.user.email, "vinculo": "estudante"},
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.vinculo, vinculo_original)

    def test_post_salva_apenas_aba_dados_sem_sobrescrever_endereco(self):
        self.user.cep = "75000000"
        self.user.save(update_fields=["cep"])
        self.client.post(
            reverse("meu_cadastro") + "?aba=dados",
            {"nome_completo": "Novo Nome", "email": self.user.email},
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.cep, "75000000")

    def test_get_sem_login_redireciona(self):
        self.client.logout()
        response = self.client.get(reverse("meu_cadastro"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('meu_cadastro')}")

    def test_post_cross_tab_nao_salva_campo_de_outra_aba(self):
        """POST com cep para ?aba=dados NÃO deve persistir o cep."""
        self.user.cep = "75000000"
        self.user.save(update_fields=["cep"])
        self.client.post(
            reverse("meu_cadastro") + "?aba=dados",
            {"nome_completo": "Novo Nome", "email": self.user.email, "cep": "99999999"},
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.cep, "75000000")

    def test_post_nao_altera_cpf(self):
        """CPF nunca pode ser alterado via POST."""
        cpf_original = self.user.cpf
        self.client.post(
            reverse("meu_cadastro") + "?aba=dados",
            {"nome_completo": "X", "email": self.user.email, "cpf": "11144477735"},
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.cpf, cpf_original)

    def test_get_aba_invalida_usa_aba_dados(self):
        """?aba=hacker deve ser tratado como ?aba=dados."""
        response = self.client.get(reverse("meu_cadastro") + "?aba=hacker")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dados Pessoais")

    def test_post_registra_auditlog(self):
        """Salvar cadastro deve criar um AuditLog com CADASTRO_ATUALIZADO."""
        from apps.auditoria.models import AuditLog, AuditAction
        self.client.post(
            reverse("meu_cadastro") + "?aba=dados",
            {"nome_completo": "Log Teste", "email": self.user.email},
        )
        self.assertTrue(
            AuditLog.objects.filter(
                ator=self.user,
                acao=AuditAction.CADASTRO_ATUALIZADO,
            ).exists()
        )


from apps.usuarios.models import CategoriaPretendida, MaiorTitulacao


class PerfilProfissionalModelTest(TestCase):
    def setUp(self):
        self.servidor = Usuario.objects.create_user(
            cpf="11144477735",
            email="perfilservidor@test.com",
            nome_completo="Servidor Perfil",
            vinculo=Vinculo.SERVIDOR,
            password="senha123",
        )
        self.externo = Usuario.objects.create_user(
            cpf="52998224725",
            email="perfilexterno@test.com",
            nome_completo="Externo Perfil",
            vinculo=Vinculo.COLABORADOR_EXTERNO,
            password="senha123",
        )

    def _preencher_campos_base(self, usuario):
        usuario.categoria_pretendida = CategoriaPretendida.PESQUISADOR
        usuario.maior_titulacao = MaiorTitulacao.DOUTORADO
        usuario.cnpq_area = "3.04"
        usuario.disponibilidade_semanal = 20

    def _confirmar_todas_declaracoes(self, usuario):
        usuario.confirmar_declaracao("ciencia_credenciamento")
        usuario.confirmar_declaracao("declaracao_veracidade")
        usuario.confirmar_declaracao("consentimento_verificacao_bases")

    def test_perfil_incompleto_por_padrao(self):
        self.assertFalse(self.servidor.perfil_completo)
        self.assertFalse(self.externo.perfil_completo)

    def test_perfil_completo_para_colaborador_externo(self):
        self._preencher_campos_base(self.externo)
        self._confirmar_todas_declaracoes(self.externo)
        self.assertTrue(self.externo.perfil_completo)

    def test_servidor_ativo_exige_declaracao_de_nao_afastamento(self):
        self._preencher_campos_base(self.servidor)
        self._confirmar_todas_declaracoes(self.servidor)
        self.servidor.servidor_ativo = True
        self.assertFalse(self.servidor.perfil_completo)
        self.servidor.nao_afastado_licenciado = True
        self.assertTrue(self.servidor.perfil_completo)

    def test_servidor_inativo_nao_precisa_declarar_afastamento(self):
        self._preencher_campos_base(self.servidor)
        self._confirmar_todas_declaracoes(self.servidor)
        self.servidor.servidor_ativo = False
        self.assertTrue(self.servidor.perfil_completo)

    def test_confirmar_declaracao_grava_booleano_e_timestamp(self):
        self.assertFalse(self.externo.declaracao_veracidade)
        self.assertIsNone(self.externo.declaracao_veracidade_em)
        self.externo.confirmar_declaracao("declaracao_veracidade")
        self.assertTrue(self.externo.declaracao_veracidade)
        self.assertIsNotNone(self.externo.declaracao_veracidade_em)

    def test_confirmar_declaracao_nao_atualiza_timestamp_se_ja_confirmada(self):
        self.externo.confirmar_declaracao("declaracao_veracidade")
        primeira_data = self.externo.declaracao_veracidade_em
        self.externo.confirmar_declaracao("declaracao_veracidade")
        self.assertEqual(self.externo.declaracao_veracidade_em, primeira_data)


class MeuCadastroFormPerfilTest(TestCase):
    def setUp(self):
        self.servidor_ativo = Usuario.objects.create_user(
            cpf="11144477735",
            email="formservativo@test.com",
            nome_completo="Servidor Ativo",
            vinculo=Vinculo.SERVIDOR,
            password="senha123",
        )
        self.externo = Usuario.objects.create_user(
            cpf="52998224725",
            email="formexterno@test.com",
            nome_completo="Externo Form",
            vinculo=Vinculo.COLABORADOR_EXTERNO,
            password="senha123",
        )

    def test_form_aceita_disponibilidade_dentro_da_faixa_servidor_ativo(self):
        from apps.usuarios.forms import MeuCadastroForm
        form = MeuCadastroForm(
            {"nome_completo": "X", "email": self.servidor_ativo.email, "servidor_ativo": "true", "disponibilidade_semanal": "20"},
            instance=self.servidor_ativo,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_rejeita_disponibilidade_acima_da_faixa_servidor_ativo(self):
        from apps.usuarios.forms import MeuCadastroForm
        form = MeuCadastroForm(
            {"nome_completo": "X", "email": self.servidor_ativo.email, "servidor_ativo": "true", "disponibilidade_semanal": "30"},
            instance=self.servidor_ativo,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("disponibilidade_semanal", form.errors)

    def test_form_aceita_disponibilidade_ate_40h_para_colaborador_externo(self):
        from apps.usuarios.forms import MeuCadastroForm
        form = MeuCadastroForm(
            {"nome_completo": "X", "email": self.externo.email, "disponibilidade_semanal": "40"},
            instance=self.externo,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_rejeita_disponibilidade_abaixo_de_5h(self):
        from apps.usuarios.forms import MeuCadastroForm
        form = MeuCadastroForm(
            {"nome_completo": "X", "email": self.externo.email, "disponibilidade_semanal": "3"},
            instance=self.externo,
        )
        self.assertFalse(form.is_valid())

    def test_form_aceita_nao_afastado_licenciado_como_verdadeiro(self):
        """Testa que checkbox 'nao_afastado_licenciado' com valor "on" é convertido para True."""
        from apps.usuarios.forms import MeuCadastroForm
        form = MeuCadastroForm(
            {"nome_completo": "X", "email": self.servidor_ativo.email, "nao_afastado_licenciado": "on"},
            instance=self.servidor_ativo,
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertTrue(form.cleaned_data["nao_afastado_licenciado"])

    def test_form_nao_afastado_licenciado_opcional_para_servidor_inativo(self):
        """Campo 'nao_afastado_licenciado' é opcional e valida sem ser preenchido."""
        from apps.usuarios.forms import MeuCadastroForm
        form = MeuCadastroForm(
            {"nome_completo": "X", "email": self.servidor_ativo.email, "servidor_ativo": ""},
            instance=self.servidor_ativo,
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertFalse(form.cleaned_data["nao_afastado_licenciado"])


class MeuCadastroPerfilViewTest(TestCase):
    def setUp(self):
        self.servidor = Usuario.objects.create_user(
            cpf="11144477735",
            email="viewservidor@test.com",
            nome_completo="Servidor View",
            vinculo=Vinculo.SERVIDOR,
            password="senha123",
        )
        self.externo = Usuario.objects.create_user(
            cpf="52998224725",
            email="viewexterno@test.com",
            nome_completo="Externo View",
            vinculo=Vinculo.COLABORADOR_EXTERNO,
            password="senha123",
        )

    def test_aba_dados_para_servidor_mostra_campo_servidor_ativo(self):
        # servidor_ativo e categoria_pretendida subiram da aba "perfil" para
        # "dados" — são identificação/vínculo (Bloco A da especificação).
        self.client.force_login(self.servidor)
        response = self.client.get(reverse("meu_cadastro") + "?aba=dados")
        self.assertContains(response, "name=\"servidor_ativo\"")

    def test_aba_dados_para_externo_esconde_campo_servidor_ativo(self):
        self.client.force_login(self.externo)
        response = self.client.get(reverse("meu_cadastro") + "?aba=dados")
        self.assertNotContains(response, "name=\"servidor_ativo\"")

    def test_post_dados_salva_categoria(self):
        self.client.force_login(self.externo)
        self.client.post(
            reverse("meu_cadastro") + "?aba=dados",
            {"nome_completo": "X", "email": self.externo.email,
             "categoria_pretendida": "pesquisador"},
        )
        self.externo.refresh_from_db()
        self.assertEqual(self.externo.categoria_pretendida, "pesquisador")

    def test_maior_titulacao_fica_na_aba_formacao(self):
        # Voltou ao formulário (lista fechada), na aba Formação — não na Perfil.
        self.client.force_login(self.externo)
        perfil = self.client.get(reverse("meu_cadastro") + "?aba=perfil")
        self.assertNotContains(perfil, "name=\"maior_titulacao\"")
        formacao = self.client.get(reverse("meu_cadastro") + "?aba=formacao")
        self.assertContains(formacao, "name=\"maior_titulacao\"")
        self.assertContains(formacao, "name=\"cnpq_area\"")

    def test_post_perfil_grava_declaracao_com_timestamp(self):
        self.client.force_login(self.externo)
        self.client.post(
            reverse("meu_cadastro") + "?aba=perfil",
            {"nome_completo": "X", "email": self.externo.email, "declaracao_veracidade": "on"},
        )
        self.externo.refresh_from_db()
        self.assertTrue(self.externo.declaracao_veracidade)
        self.assertIsNotNone(self.externo.declaracao_veracidade_em)

    def test_post_perfil_nao_desmarca_declaracao_ja_confirmada(self):
        self.externo.confirmar_declaracao("declaracao_veracidade")
        self.externo.save(update_fields=["declaracao_veracidade", "declaracao_veracidade_em"])
        primeira_data = self.externo.declaracao_veracidade_em
        self.client.force_login(self.externo)
        self.client.post(
            reverse("meu_cadastro") + "?aba=perfil",
            {"nome_completo": "X", "email": self.externo.email},
        )
        self.externo.refresh_from_db()
        self.assertTrue(self.externo.declaracao_veracidade)
        self.assertEqual(self.externo.declaracao_veracidade_em, primeira_data)

    def test_post_perfil_servidor_nao_persiste_servidor_ativo_de_externo(self):
        """Colaborador externo postando a aba perfil não grava servidor_ativo (nem existe no form pra ele)."""
        self.client.force_login(self.externo)
        self.client.post(
            reverse("meu_cadastro") + "?aba=perfil",
            {"nome_completo": "X", "email": self.externo.email, "servidor_ativo": "true"},
        )
        self.externo.refresh_from_db()
        self.assertIsNone(self.externo.servidor_ativo)

    def test_servidor_ativo_sem_declaracao_afastamento_mantem_perfil_incompleto(self):
        """POST via view com servidor_ativo=true mas sem confirmar nao_afastado_licenciado: perfil continua incompleto."""
        self.servidor.area_atuacao = "Engenharia"
        self.servidor.save(update_fields=["area_atuacao"])
        self.client.force_login(self.servidor)
        self.client.post(
            reverse("meu_cadastro") + "?aba=perfil",
            {
                "nome_completo": "X",
                "categoria_pretendida": "pesquisador",
                "disponibilidade_semanal": "20",
                "servidor_ativo": "true",
                "ciencia_credenciamento": "on",
                "declaracao_veracidade": "on",
                "consentimento_verificacao_bases": "on",
            },
        )
        self.servidor.refresh_from_db()
        self.assertFalse(self.servidor.perfil_completo)

    def test_servidor_ativo_mantem_teto_de_20h_via_view(self):
        """Servidor com servidor_ativo=true postando 40h pela view continua rejeitado (teto de 20h)."""
        self.client.force_login(self.servidor)
        response = self.client.post(
            reverse("meu_cadastro") + "?aba=perfil",
            {
                "nome_completo": "X",
                "servidor_ativo": "true",
                "disponibilidade_semanal": "40",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context["form"], "disponibilidade_semanal", "Disponibilidade deve estar entre 5 e 20 horas semanais.")
        self.servidor.refresh_from_db()
        self.assertIsNone(self.servidor.disponibilidade_semanal)


class HomeBannerPerfilTest(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            cpf="11144477735",
            email="bannerhome@test.com",
            nome_completo="Banner Teste",
            vinculo=Vinculo.COLABORADOR_EXTERNO,
            password="senha123",
        )
        self.client.force_login(self.usuario)

    def test_banner_aparece_quando_perfil_incompleto(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Complete seu perfil")

    def test_banner_some_quando_perfil_completo(self):
        self.usuario.categoria_pretendida = CategoriaPretendida.PESQUISADOR
        self.usuario.maior_titulacao = MaiorTitulacao.DOUTORADO
        self.usuario.cnpq_area = "3.04"
        self.usuario.disponibilidade_semanal = 20
        self.usuario.confirmar_declaracao("ciencia_credenciamento")
        self.usuario.confirmar_declaracao("declaracao_veracidade")
        self.usuario.confirmar_declaracao("consentimento_verificacao_bases")
        self.usuario.save()
        response = self.client.get(reverse("home"))
        self.assertNotContains(response, "Complete seu perfil")


class AceiteComunicacoesTest(TestCase):
    """Consentimento de receber e-mail sobre novas chamadas.

    Ao contrário das declarações (veracidade, ciência, LGPD), este é
    REVOGÁVEL a qualquer tempo — LGPD, art. 8º, §5º. Por isso não passa por
    confirmar_declaracao(), que é de via única.
    """

    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            cpf="11144477735",
            email="comunicacoes@test.com",
            nome_completo="Comunicações Teste",
            vinculo=Vinculo.COLABORADOR_EXTERNO,
            password="senha123",
        )
        self.client.force_login(self.usuario)

    def _post_perfil(self, **extra):
        dados = {"nome_completo": "X", "email": self.usuario.email}
        dados.update(extra)
        return self.client.post(reverse("meu_cadastro") + "?aba=perfil", dados)

    def test_comeca_desmarcado(self):
        self.assertFalse(self.usuario.aceite_comunicacoes)
        self.assertIsNone(self.usuario.aceite_comunicacoes_em)

    def test_marcar_grava_timestamp(self):
        self._post_perfil(aceite_comunicacoes="on")
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.aceite_comunicacoes)
        self.assertIsNotNone(self.usuario.aceite_comunicacoes_em)

    def test_pode_ser_revogado(self):
        self._post_perfil(aceite_comunicacoes="on")
        self.usuario.refresh_from_db()
        marcado_em = self.usuario.aceite_comunicacoes_em

        self._post_perfil()  # checkbox ausente = desmarcado
        self.usuario.refresh_from_db()
        self.assertFalse(self.usuario.aceite_comunicacoes)
        # a revogação também é datada — não fica com a data da concessão
        self.assertNotEqual(self.usuario.aceite_comunicacoes_em, marcado_em)

    def test_salvar_sem_mudar_nao_redata(self):
        self._post_perfil(aceite_comunicacoes="on")
        self.usuario.refresh_from_db()
        primeira_data = self.usuario.aceite_comunicacoes_em

        self._post_perfil(aceite_comunicacoes="on")
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.aceite_comunicacoes_em, primeira_data)


class GrandeAreaCnpqTest(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            cpf="52998224725",
            email="cnpq@test.com",
            nome_completo="CNPq Teste",
            vinculo=Vinculo.SERVIDOR,
            password="senha123",
        )

    def test_vazio_quando_area_nao_informada(self):
        self.assertEqual(self.usuario.grande_area_cnpq, "")

    def test_derivada_do_prefixo_do_codigo(self):
        self.usuario.cnpq_area = "3.04"
        self.assertEqual(self.usuario.grande_area_cnpq, "3. Engenharias")
        self.usuario.cnpq_area = "1.06"
        self.assertEqual(self.usuario.grande_area_cnpq, "1. Ciências Exatas e da Terra")
