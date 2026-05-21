# apps/inscricoes/urls.py
# Banco de Talentos — Polo de Inovação IFG
# URL patterns da área de inscrição do candidato e revisão do RH.

from django.urls import path

from apps.inscricoes import views, views_rh

urlpatterns = [
    path("inscricao/", views.inscricao_view, name="inscricao"),
    path("inscricao/confirmacao/", views.confirmacao_view, name="inscricao_confirmacao"),
    path("inscricoes/<int:pk>/comprovante/", views.download_comprovante, name="download_comprovante"),
    path("rh/inscricoes/<int:pk>/revisar/", views_rh.revisao_view, name="revisao_rh"),
    path("rh/inscricoes/<int:pk>/pdf/", views_rh.view_comprovante, name="view_comprovante"),
]
