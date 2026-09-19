# apps/inscricoes/urls.py
# Banco de Talentos — Polo de Inovação IFG
# URL patterns da área de inscrição do candidato e revisão do RH.

from django.urls import path

from apps.inscricoes import views, views_chamadas, views_rh

urlpatterns = [
    # Fluxo por Chamada Interna (Retificação 4 do Edital 29/2026).
    path("chamadas/", views_chamadas.chamadas_lista, name="chamadas"),
    path("chamadas/<int:pk>/", views_chamadas.chamada_detalhe, name="chamada_detalhe"),
    path(
        "chamadas/<int:pk>/inscricao/",
        views_chamadas.inscricao_chamada,
        name="inscricao_chamada",
    ),
    path(
        "inscricoes/<int:pk>/",
        views_chamadas.inscricao_detalhe,
        name="inscricao_detalhe",
    ),
    # Rota antiga: mantida só para não quebrar link salvo ou favorito de
    # candidato. Leva para a lista de chamadas.
    path("inscricao/", views.inscricao_view, name="inscricao"),
    path("inscricao/confirmacao/", views.confirmacao_view, name="inscricao_confirmacao"),
    path("inscricoes/<int:pk>/comprovante/", views.download_comprovante, name="download_comprovante"),
    path("rh/inscricoes/<int:pk>/revisar/", views_rh.revisao_view, name="revisao_rh"),
    path("rh/inscricoes/<int:pk>/pdf/", views_rh.view_comprovante, name="view_comprovante"),
]
