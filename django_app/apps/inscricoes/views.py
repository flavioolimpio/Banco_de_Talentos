# apps/inscricoes/views.py
# Banco de Talentos — Polo de Inovação IFG
# Views da área de inscrição do candidato.

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse


@login_required
def inscricao_view(request):
    return HttpResponse("stub")


@login_required
def confirmacao_view(request):
    return HttpResponse("stub")
