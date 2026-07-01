# apps/inscricoes/management/commands/exportar_servidores_convocados.py
# Banco de Talentos — Polo de Inovação IFG
# Exporta um .xlsx com as inscrições de Servidor(a) aprovadas, contendo
# Nome, CPF, Titulação (nível de formação) e Pontuação validada pelo RH,
# ordenadas da maior para a menor pontuação — ordem de convocação.
#
# ATENÇÃO — dado sensível: o CPF sai completo neste arquivo porque o
# Prof. Flávio confirmou que é para publicação de convocados (decisão
# institucional, não técnica). Se o uso mudar, revisar antes de reusar
# este comando.
#
# Uso:
#   python manage.py exportar_servidores_convocados
#   python manage.py exportar_servidores_convocados --saida x.xlsx
#
# Apenas consulta + exportação. NUNCA altera dados do banco.

from openpyxl import Workbook
from openpyxl.styles import Font

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.inscricoes.models import Inscricao, StatusInscricao
from apps.usuarios.models import Vinculo


class Command(BaseCommand):
    help = (
        "Gera um .xlsx das inscrições de Servidor(a) aprovadas com Nome, CPF, "
        "Titulação e Pontuação validada, ordenadas por pontuação (convocação)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--saida",
            default=f"servidores_convocados_{timezone.localdate()}.xlsx",
            help=(
                "Caminho do arquivo .xlsx a gerar "
                "(padrão: servidores_convocados_<AAAA-MM-DD>.xlsx no diretório atual)."
            ),
        )

    def handle(self, *args, **options):
        aprovadas = (
            Inscricao.objects.filter(
                modalidade=Vinculo.SERVIDOR, status=StatusInscricao.APROVADA
            )
            .select_related("usuario")
            .order_by("-total_validado")
        )

        total = aprovadas.count()
        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_HEADING(f"Servidores aprovados: {total}")
        )

        if total == 0:
            self.stdout.write("Nenhum servidor aprovado — nada a exportar.")
            return

        caminho = options["saida"]

        wb = Workbook()
        ws = wb.active
        ws.title = "Convocados"

        cabecalho = ["Nome", "CPF", "Titulação", "Pontuação Validada"]
        ws.append(cabecalho)
        for celula in ws[1]:
            celula.font = Font(bold=True)

        for ins in aprovadas:
            usuario = ins.usuario
            ws.append(
                [
                    usuario.nome_completo,
                    usuario.cpf,
                    usuario.nivel_formacao or "—",
                    float(ins.total_validado),
                ]
            )

        for coluna, largura in zip("ABCD", [40, 16, 28, 20]):
            ws.column_dimensions[coluna].width = largura

        wb.save(caminho)

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Planilha gerada: {caminho} ({total} servidor(es) aprovado(s))."
            )
        )
