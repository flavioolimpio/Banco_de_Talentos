# limpar_dados_teste.py
# Banco de Talentos — Polo de Inovação IFG
# Apaga dados de teste preservando CriterioEdital e superusuário.
# Uso (dentro de django_app/):
#   source .venv/bin/activate
#   python manage.py shell < limpar_dados_teste.py

from apps.inscricoes.models import Inscricao
from apps.auditoria.models import AuditLog
from apps.usuarios.models import Usuario
from django.contrib.sessions.models import Session

print("=== ANTES ===")
print(f"  Inscrições:          {Inscricao.objects.count()}")
print(f"  Usuários candidatos: {Usuario.objects.filter(is_staff=False).count()}")
print(f"  Logs de auditoria:   {AuditLog.objects.count()}")
print(f"  Sessões:             {Session.objects.count()}")
print()

Inscricao.objects.all().delete()
AuditLog.objects.all().delete()
Usuario.objects.filter(is_staff=False).delete()
Session.objects.all().delete()

print("=== DEPOIS ===")
print(f"  Inscrições:          {Inscricao.objects.count()}")
print(f"  Usuários candidatos: {Usuario.objects.filter(is_staff=False).count()}")
print(f"  Logs de auditoria:   {AuditLog.objects.count()}")
print(f"  Sessões:             {Session.objects.count()}")
print()
print("Critérios do edital preservados:", end=" ")

from apps.inscricoes.models import CriterioEdital
print(CriterioEdital.objects.count())
print()
print("Feito. Banco limpo e pronto para uso real.")
