# apps/inscricoes/context_processors.py
# Banco de Talentos — Polo de Inovação IFG
# Expõe a flag INSCRICOES_ABERTAS a todos os templates (home, sidebar etc.)
# sem precisar passar por cada view. Templates não enxergam settings
# diretamente — este é o mecanismo padrão do Django para isso.

from django.conf import settings


def inscricoes_abertas(request):
    """Disponibiliza {{ inscricoes_abertas }} em qualquer template."""
    return {"inscricoes_abertas": settings.INSCRICOES_ABERTAS}
