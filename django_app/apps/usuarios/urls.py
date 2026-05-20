from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordResetCompleteView
from django.urls import path

from apps.usuarios import views


urlpatterns = [
    path("", login_required(views.home_view), name="home"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("cadastro/", views.cadastro_view, name="cadastro"),
    path("meu-cadastro/", views.meu_cadastro_view, name="meu_cadastro"),
    path("senha/recuperar/", views.RecuperacaoSenhaView.as_view(), name="password_reset"),
    path("senha/enviada/", views.RecuperacaoSenhaEnviadaView.as_view(), name="password_reset_done"),
    path("senha/nova/<uidb64>/<token>/", views.NovaSenhaConfirmView.as_view(), name="password_reset_confirm"),
    path(
        "senha/concluida/",
        PasswordResetCompleteView.as_view(template_name="usuarios/password_reset_complete.html"),
        name="password_reset_complete",
    ),
]
