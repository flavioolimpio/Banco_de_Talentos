# apps/inscricoes/management/commands/exportar_convocados.py
# Banco de Talentos — Polo de Inovação IFG
#
# Exporta um .xlsx com os aprovados de uma CHAMADA INTERNA, em ordem de
# convocação (maior pontuação validada primeiro).
#
# Substitui três comandos que eram clones — exportar_servidores_convocados,
# exportar_colaboradores_pesquisador_convocados e
# exportar_colaboradores_apoio_tecnico_convocados. Os três diferiam só no
# filtro e nos rótulos; manter três arquivos de ~100 linhas que divergiam em
# duas era dívida que a chegada das chamadas só pioraria.
#
# ATENÇÃO — dado sensível: o CPF sai completo, porque o Prof. Flávio confirmou
# que este arquivo é para a publicação de convocados (decisão institucional,
# não técnica). Se o uso mudar, revisar antes de reusar. A exportação fica
# registrada no AuditLog.
#
# Uso:
#   python manage.py exportar_convocados --chamada 4
#   python manage.py exportar_convocados --chamada 4 --modalidade servidor
#   python manage.py exportar_convocados --chamada 4 --vaga "Pq 12"
#   python manage.py exportar_convocados --listar-chamadas
#
# Apenas consulta + exportação. NUNCA altera dados do banco.

from django.core.management.base import BaseCommand, CommandError
from django.db.models import F
from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Font

from apps.auditoria.models import AuditAction, AuditLog
from apps.inscricoes.models import ChamadaInterna, Inscricao, StatusInscricao, TipoServidor
from apps.usuarios.models import Vinculo


class Command(BaseCommand):
    help = (
        "Gera um .xlsx dos aprovados de uma chamada, em ordem de convocação. "
        "Exige --chamada."
    )

    def add_arguments(self, parser):
        parser.add_argument("--chamada", type=int, help="ID da chamada interna.")
        parser.add_argument(
            "--modalidade",
            choices=[v for v, _ in Vinculo.choices],
            help="Filtra por vínculo (padrão: todos).",
        )
        parser.add_argument(
            "--tipo",
            choices=[v for v, _ in TipoServidor.choices],
            help="Filtra por categoria (padrão: todas).",
        )
        parser.add_argument("--vaga", help="Filtra pelo código da vaga. Ex.: \"Pq 12\".")
        parser.add_argument("--saida", help="Caminho do .xlsx (padrão: nome automático).")
        parser.add_argument(
            "--listar-chamadas", action="store_true", help="Lista as chamadas e seus IDs."
        )

    def handle(self, *args, **options):
        if options["listar_chamadas"]:
            self.stdout.write("")
            self.stdout.write(self.style.MIGRATE_HEADING("Chamadas cadastradas"))
            for chamada in ChamadaInterna.objects.all():
                marca = " (legado)" if chamada.legado else ""
                self.stdout.write(f"  {chamada.pk:>4}  {chamada}{marca}")
            return

        if not options["chamada"]:
            raise CommandError(
                "Informe --chamada <id>. A convocação é sempre por chamada.\n"
                "Use --listar-chamadas para ver os IDs disponíveis."
            )
        try:
            chamada = ChamadaInterna.objects.get(pk=options["chamada"])
        except ChamadaInterna.DoesNotExist:
            raise CommandError(f"Não existe chamada com id {options['chamada']}.")

        aprovadas = (
            Inscricao.objects.filter(chamada=chamada, status=StatusInscricao.APROVADA)
            .select_related("usuario", "vaga")
            # Empate na pontuação: mais velho(a) primeiro (maior idade, último
            # critério dos Anexos). É só a ordem da lista — o desempate oficial
            # vem depois da Entrevista, na planilha, e para estudante o CRE
            # entra antes da idade (Edital 31). nulls_last: SQLite e Postgres
            # discordam de onde vai a data em branco.
            .order_by("-total_validado", F("usuario__data_nascimento").asc(nulls_last=True))
        )
        if options["modalidade"]:
            aprovadas = aprovadas.filter(modalidade=options["modalidade"])
        if options["tipo"]:
            aprovadas = aprovadas.filter(tipo_servidor=options["tipo"])
        if options["vaga"]:
            aprovadas = aprovadas.filter(vaga__codigo=options["vaga"])

        total = aprovadas.count()
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING(f"{chamada}"))
        self.stdout.write(f"Aprovados: {total}")

        if total == 0:
            self.stdout.write("Nada a exportar.")
            return

        caminho = options["saida"] or (
            f"convocados_chamada_{chamada.numero:02d}_{chamada.ano}"
            f"_{timezone.localdate()}.xlsx"
        )

        wb = Workbook()
        ws = wb.active
        ws.title = "Convocados"
        ws.append(["Nome", "CPF", "Data de nascimento", "Vaga", "Vínculo", "Categoria", "Titulação", "Pontuação Validada"])
        for celula in ws[1]:
            celula.font = Font(bold=True)

        for ins in aprovadas:
            usuario = ins.usuario
            ws.append([
                usuario.nome_completo,
                usuario.cpf,
                usuario.data_nascimento,
                ins.vaga.codigo if ins.vaga else "—",
                ins.get_modalidade_display(),
                ins.get_tipo_servidor_display() or "—",
                usuario.get_maior_titulacao_display() or usuario.nivel_formacao or "—",
                float(ins.total_validado),
            ])

        for coluna, largura in zip("ABCDEFGH", [40, 16, 14, 12, 22, 18, 28, 20]):
            ws.column_dimensions[coluna].width = largura
        wb.save(caminho)

        AuditLog.objects.create(
            acao=AuditAction.CSV_EXPORTADO,
            detalhes={
                "comando": "exportar_convocados",
                "chamada": chamada.pk,
                "total": total,
                "arquivo": caminho,
            },
        )

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"Planilha gerada: {caminho} ({total} aprovado(s))."))
