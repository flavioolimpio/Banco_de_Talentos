# Banco de Talentos — Polo de Inovação IFG
# Popula CriterioEdital a partir de quadros.py. Operação idempotente.

from django.core.management.base import BaseCommand

from apps.inscricoes.models import CriterioEdital
from apps.inscricoes.quadros import QUADROS_INSCRICAO


class Command(BaseCommand):
    help = "Popula ou atualiza os critérios do edital no banco de dados."

    def handle(self, *args, **options):
        criados = 0
        atualizados = 0

        for modalidade, itens in QUADROS_INSCRICAO.items():
            for ordem, item in enumerate(itens, start=1):
                _, created = CriterioEdital.objects.update_or_create(
                    modalidade=modalidade,
                    tipo_servidor="",
                    item_id=item["id"],
                    defaults={
                        "ordem": ordem,
                        "criterio": item["criterio"],
                        "regra": item["regra"],
                        "maximo": item["maximo"],
                        "ativo": True,
                    },
                )
                if created:
                    criados += 1
                else:
                    atualizados += 1

        if options["verbosity"] >= 1:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Concluído: {criados} criados, {atualizados} atualizados."
                )
            )
