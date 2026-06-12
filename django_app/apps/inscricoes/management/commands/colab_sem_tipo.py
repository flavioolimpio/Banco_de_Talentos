# apps/inscricoes/management/commands/colab_sem_tipo.py
# Banco de Talentos — Polo de Inovação IFG
# Lista (e opcionalmente exporta em CSV) os Colaboradores Externos cuja
# inscrição ainda não tem a categoria (tipo_servidor) definida —
# isto é, inscrições feitas antes de existirem os subtipos
# "Pesquisador" e "Apoio técnico" para essa modalidade.
#
# Uso:
#   python manage.py colab_sem_tipo            # só lista (não cria arquivo)
#   python manage.py colab_sem_tipo --csv      # lista E gera o CSV
#
# Apenas consulta + exportação. NUNCA altera dados do banco.

import csv

from django.core.management.base import BaseCommand

from apps.inscricoes.models import Inscricao
from apps.usuarios.models import Vinculo

# Caminho do CSV gerado, relativo à pasta onde o manage.py é executado
CSV_PATH = "pendentes_classificacao.csv"


class Command(BaseCommand):
    help = (
        "Lista Colaboradores Externos com inscrição sem tipo_servidor definido. "
        "Use --csv para também exportar nome e e-mail para um arquivo."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv",
            action="store_true",
            help=f"Gera o arquivo {CSV_PATH} com nome e e-mail dos pendentes.",
        )

    def handle(self, *args, **options):
        # tipo_servidor é CharField(blank=True): vazio fica como "".
        # Incluímos None por segurança, caso algum registro antigo seja nulo.
        inscricoes = (
            Inscricao.objects.filter(modalidade=Vinculo.COLABORADOR_EXTERNO)
            .filter(tipo_servidor__in=["", None])
            .select_related("usuario")
            .order_by("usuario__nome_completo")
        )

        total = inscricoes.count()
        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"Colaboradores Externos sem categoria definida: {total}"
            )
        )
        self.stdout.write("-" * 78)

        if total == 0:
            self.stdout.write("Nenhuma inscrição pendente de classificação.")
            return

        for ins in inscricoes:
            usuario = ins.usuario
            self.stdout.write(
                f"{usuario.nome_completo}  |  {usuario.email}  "
                f"|  status: {ins.get_status_display()}"
            )

        self.stdout.write("-" * 78)

        if not options["csv"]:
            self.stdout.write("")
            self.stdout.write(
                "Para exportar nome e e-mail em CSV, rode novamente com --csv"
            )
            return

        # --csv: gera o arquivo apenas com nome e e-mail (sem CPF — dado sensível)
        with open(CSV_PATH, "w", newline="", encoding="utf-8") as arquivo:
            writer = csv.writer(arquivo)
            writer.writerow(["nome", "email"])
            for ins in inscricoes:
                writer.writerow([ins.usuario.nome_completo, ins.usuario.email])

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(f"CSV gerado: {CSV_PATH} ({total} candidato(s)).")
        )
