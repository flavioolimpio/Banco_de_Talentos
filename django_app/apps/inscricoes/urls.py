# apps/inscricoes/urls.py
# Banco de Talentos — Polo de Inovação IFG
# URL patterns da área de inscrição do candidato.

from django.urls import path

from apps.inscricoes import views

urlpatterns = [
    path("inscricao/", views.inscricao_view, name="inscricao"),
    path("inscricao/confirmacao/", views.confirmacao_view, name="inscricao_confirmacao"),
]
