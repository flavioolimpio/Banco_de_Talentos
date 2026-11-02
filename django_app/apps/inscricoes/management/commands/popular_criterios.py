# apps/inscricoes/management/commands/popular_criterios.py
# Banco de Talentos — Polo de Inovação IFG
#
# Copia um quadro modelo de `quadros.py` para o quadro de critérios de uma
# CHAMADA INTERNA. Operação idempotente.
#
# O que mudou e por quê: desde a Retificação 4 do Edital 29/2026 não existe
# mais um quadro fixo por modalidade — cada chamada tem o seu, montado pela
# Coordenação do Projeto (item 5.1, VI). Então `quadros.py` deixou de ser "a
# verdade" e virou uma BIBLIOTECA DE MODELOS: serve para não começar uma
# chamada com a folha em branco.
#
# Por isso `--chamada` é obrigatório. Sem ele, o comando tentava criar critério
# sem chamada e estourava com
#     IntegrityError: NOT NULL constraint failed: criterioedital.chamada_id
#
# Uso:
#   python manage.py popular_criterios --chamada 4
#   python manage.py popular_criterios --chamada 4 --quadro servidor
#   python manage.py popular_criterios --listar-chamadas
#
# Os critérios copiados nascem como CONTAGEM sem pontos por unidade: os
# quadros modelo são do formato antigo, em que o candidato digitava a
# pontuação. Depois de copiar, ajuste cada linha no admin — defina o tipo
# (quantidade ou escolha), os pontos por unidade e o que é contado. O comando
# avisa disso ao terminar.

from django.core.management.base import BaseCommand, CommandError

from apps.inscricoes.models import ChamadaInterna, CriterioEdital
from apps.inscricoes.quadros import QUADROS_INSCRICAO


class Command(BaseCommand):
    help = (
        "Copia um quadro modelo de quadros.py para o quadro de critérios de uma "
        "chamada interna. Exige --chamada."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--chamada",
            type=int,
            help="ID da chamada interna que vai receber os critérios.",
        )
        parser.add_argument(
            "--quadro",
            action="append",
            choices=sorted(QUADROS_INSCRICAO),
            help=(
                "Quadro modelo a copiar (pode repetir). "
                "Padrão: todos os quadros de quadros.py."
            ),
        )
        parser.add_argument(
            "--listar-chamadas",
            action="store_true",
            help="Só lista as chamadas cadastradas, com os respectivos IDs.",
        )

    def handle(self, *args, **options):
        if options["listar_chamadas"]:
            self._listar_chamadas()
            return

        chamada_id = options["chamada"]
        if not chamada_id:
            raise CommandError(
                "Informe --chamada <id>. Cada chamada tem o seu próprio quadro de "
                "critérios (item 5.1, VI do Edital).\n"
                "Use --listar-chamadas para ver os IDs disponíveis."
            )

        try:
            chamada = ChamadaInterna.objects.get(pk=chamada_id)
        except ChamadaInterna.DoesNotExist:
            raise CommandError(f"Não existe chamada com id {chamada_id}.")

        if chamada.legado:
            raise CommandError(
                f"'{chamada}' é uma chamada de legado: ela guarda o histórico do "
                "credenciamento antigo e não deve receber critérios novos."
            )

        quadros = options["quadro"] or sorted(QUADROS_INSCRICAO)
        criados = atualizados = 0

        for quadro_key in quadros:
            for ordem, item in enumerate(QUADROS_INSCRICAO[quadro_key], start=1):
                _, created = CriterioEdital.objects.update_or_create(
                    chamada=chamada,
                    modalidade=quadro_key,
                    tipo_servidor="",
                    item_id=item["id"],
                    defaults={
                        "ordem": ordem,
                        "criterio": item["criterio"],
                        "regra": item["regra"],
                        "maximo": item["maximo"],
                        "is_api": item.get("is_api", False),
                        "ativo": True,
                    },
                )
                criados += int(created)
                atualizados += int(not created)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"{chamada}\n  {criados} critério(s) criado(s), {atualizados} atualizado(s)."
        ))
        if criados:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING(
                "Ajuste as linhas no admin antes de publicar a chamada: defina o tipo\n"
                "(quantidade ou escolha única), os pontos por unidade e o que é\n"
                "contado. Enquanto isso não for feito, os critérios de quantidade\n"
                "valem 0 ponto para o candidato. Cada quadro soma no máximo 100\n"
                "pontos — Anexo I (Edital 29: 7.1; 30: 6.1; 31: 8.1). O admin não salva a chamada acima disso."
            ))

    def _listar_chamadas(self):
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Chamadas cadastradas"))
        for chamada in ChamadaInterna.objects.all():
            marca = " (legado)" if chamada.legado else ""
            self.stdout.write(f"  {chamada.pk:>4}  {chamada}{marca}")
