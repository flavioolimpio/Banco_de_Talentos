from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordResetConfirmView, PasswordResetDoneView, PasswordResetView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_http_methods

from apps.auditoria.models import AuditAction, AuditLog
from apps.usuarios.forms import CadastroUsuarioForm, LoginForm, NovaSenhaForm, RecuperacaoSenhaForm


LGPD_TERMO_VERSAO_ATUAL = "2026-05-14"


def get_client_ip(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def audit(request, acao, alvo=None, detalhes=None):
    ator = request.user if request.user.is_authenticated else None
    AuditLog.objects.create(
        ator=ator,
        alvo=alvo,
        acao=acao,
        ip=get_client_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
        detalhes=detalhes or {},
    )


@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    form = LoginForm(request=request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        login(request, user)
        if not form.cleaned_data.get("lembrar"):
            request.session.set_expiry(0)
        audit(request, AuditAction.LOGIN, alvo=user)
        messages.success(request, "Login realizado com sucesso.")
        return redirect("home")

    return render(request, "usuarios/login.html", {"form": form})


@require_http_methods(["POST"])
def logout_view(request):
    if request.user.is_authenticated:
        audit(request, AuditAction.LOGOUT, alvo=request.user)
    logout(request)
    messages.info(request, "Você saiu da plataforma.")
    return redirect("login")


@require_http_methods(["GET", "POST"])
def cadastro_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    form = CadastroUsuarioForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save(commit=False)
        user.registrar_aceite_lgpd(LGPD_TERMO_VERSAO_ATUAL, get_client_ip(request))
        user.save()
        audit(request, AuditAction.CADASTRO_CRIADO, alvo=user, detalhes={"vinculo": user.vinculo})
        messages.success(request, "Cadastro realizado com sucesso. Faça login para continuar.")
        return redirect("login")

    return render(request, "usuarios/cadastro.html", {"form": form, "termo_versao": LGPD_TERMO_VERSAO_ATUAL})


@login_required
def home_view(request):
    from apps.inscricoes.models import Inscricao
    inscricao = None
    try:
        inscricao = Inscricao.objects.get(usuario=request.user)
    except Inscricao.DoesNotExist:
        pass
    return render(request, "usuarios/home.html", {"inscricao": inscricao})


@login_required
@require_http_methods(["GET", "POST"])
def meu_cadastro_view(request):
    return render(request, "usuarios/meu_cadastro.html", {})


class RecuperacaoSenhaView(PasswordResetView):
    form_class = RecuperacaoSenhaForm
    template_name = "usuarios/password_reset_form.html"
    email_template_name = "usuarios/password_reset_email.txt"
    subject_template_name = "usuarios/password_reset_subject.txt"
    success_url = reverse_lazy("password_reset_done")


class RecuperacaoSenhaEnviadaView(PasswordResetDoneView):
    template_name = "usuarios/password_reset_done.html"


class NovaSenhaConfirmView(PasswordResetConfirmView):
    form_class = NovaSenhaForm
    template_name = "usuarios/password_reset_confirm.html"
    success_url = reverse_lazy("login")

    def form_valid(self, form):
        messages.success(self.request, "Senha alterada com sucesso. Faça login com a nova senha.")
        return super().form_valid(form)
