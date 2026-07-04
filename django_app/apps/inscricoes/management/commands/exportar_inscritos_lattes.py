# apps/inscricoes/management/commands/exportar_inscritos_lattes.py
# Banco de Talentos — Polo de Inovação IFG
# Exporta um .xlsx de TODAS as inscrições enviadas (completa, em análise ou
# aprovada) com Nome, Modalidade, Categoria, Titulação, Área de atuação,
# E-mail, URL do Lattes e as pontuações — planilha-mestre que organiza o
# trabalho manual do RH de baixar os currículos Lattes e montar shortlists
# de indicação de especialistas para projetos EMBRAPII.
#
# SEM CPF de propósito (minimização LGPD): é documento interno de trabalho,
# não publicação de convocados — nome + e-mail identificam o suficiente.
#
# Uso:
#   python manage.py exportar_inscritos_lattes
#   python manage.py exportar_inscritos_lattes --saida x.xlsx
#
# Apenas consulta + exportação. NUNCA altera dados do banco.

from openpyxl import Workbook
from openpyxl.styles import Font

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.inscricoes.models import Inscricao, StatusInscricao


class Command(BaseCommand):
    help = (
        "Gera um .xlsx de todas as inscrições enviadas (qualquer modalidade) "
        "com dados de perfil, URL do Lattes e pontuações, para apoiar a "
        "indicação de especialistas."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--saida",
            default=f"inscritos_lattes_{timezone.localdate()}.xlsx",
            help=(
                "Caminho do arquivo .xlsx a gerar "
                "(padrão: inscritos_lattes_<AAAA-MM-DD>.xlsx no diretório atual)."
            ),
        )

    def handle(self, *args, **options):
        # PENDENTE fica de fora (rascunho não enviado); INDEFERIDA idem.
        inscritos = (
            Inscricao.objects.filter(
                status__in=[
                    StatusInscricao.COMPLETA,
                    StatusInscricao.EM_ANALISE,
                    StatusInscricao.APROVADA,
                ]
            )
            .select_related("usuario")
            .order_by("-total")
        )

        total = inscritos.count()
        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_HEADING(f"Inscrições enviadas: {total}")
        )

        if total == 0:
            self.stdout.write("Nenhuma inscrição enviada — nada a exportar.")
            return

        caminho = options["saida"]

        wb = Workbook()
        ws = wb.active
        ws.title = "Inscritos"

        cabecalho = [
            "Nome",
            "Modalidade",
            "Categoria",
            "Titulação",
            "Área de atuação",
            "E-mail",
            "URL Lattes",
            "Total autodeclarado",
            "Total validado",
            "Status",
        ]
        ws.append(cabecalho)
        for celula in ws[1]:
            celula.font = Font(bold=True)

        sem_lattes = 0
        for ins in inscritos:
            usuario = ins.usuario
            if not usuario.lattes:
                sem_lattes += 1
            ws.append(
                [
                    usuario.nome_completo,
                    ins.get_modalidade_display(),
                    ins.get_tipo_servidor_display() or "—",
                    usuario.nivel_formacao or "—",
                    usuario.area_atuacao or "—",
                    usuario.email,
                    usuario.lattes or "SEM LATTES",
                    float(ins.total) if ins.total is not None else None,
                    float(ins.total_validado) if ins.total_validado is not None else None,
                    ins.get_status_display(),
                ]
            )

        larguras = [40, 20, 18, 28, 30, 32, 42, 18, 16, 14]
        for coluna, largura in zip("ABCDEFGHIJ", larguras):
            ws.column_dimensions[coluna].width = largura

        wb.save(caminho)

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Planilha gerada: {caminho} ({total} inscrição(ões), "
                f"{sem_lattes} sem URL do Lattes)."
            )
        )
