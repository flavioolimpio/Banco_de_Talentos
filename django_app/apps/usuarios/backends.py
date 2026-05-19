from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

from apps.usuarios.models import Usuario
from apps.usuarios.validators import somente_digitos


class CpfEmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        identifier = username or kwargs.get("cpf") or kwargs.get("email")
        if not identifier or password is None:
            return None

        identifier = identifier.strip()
        cpf = somente_digitos(identifier)

        query = Q(email__iexact=identifier)
        if cpf:
            query |= Q(cpf=cpf)

        try:
            user = Usuario.objects.get(query)
        except Usuario.DoesNotExist:
            Usuario().set_password(password)
            return None
        except Usuario.MultipleObjectsReturned:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
