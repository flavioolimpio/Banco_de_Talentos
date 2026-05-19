import re

from django.core.exceptions import ValidationError


def somente_digitos(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def validar_cpf(value: str) -> str:
    cpf = somente_digitos(value)
    if len(cpf) != 11:
        raise ValidationError("Informe um CPF com 11 dígitos.")
    if cpf == cpf[0] * 11:
        raise ValidationError("Informe um CPF válido.")

    for tamanho in (9, 10):
        soma = sum(int(cpf[i]) * (tamanho + 1 - i) for i in range(tamanho))
        digito = (soma * 10) % 11
        digito = 0 if digito == 10 else digito
        if digito != int(cpf[tamanho]):
            raise ValidationError("Informe um CPF válido.")

    return cpf
