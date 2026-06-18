# apps/inscricoes/management/commands/exportar_aprovadas.py
# Banco de Talentos — Polo de Inovação IFG
# Exporta um CSV com TODAS as inscrições com status "aprovada", contendo
# Nome, Modalidade, Categoria, E-mail e Pontuação (a nota validada pelo RH).
#
# Pensado para entregar uma planilha ao chefe. Abre direto no Excel pt-BR
# com os acentos corretos (ç, ã, é) porque grava o BOM de UTF-8.
#
# Uso:
#   python manage.py exportar_aprovadas                 # gera aprovadas_<data>.csv
#   python manage.py exportar_aprovadas --saida x.csv   # escolhe o nome/caminho
#
# Apenas consulta + exportação. NUNCA altera dados do banco.
# Não inclui CPF (dado sensível e não solicitado).

import csv

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.inscricoes.models import Inscricao, StatusInscricao


class Command(BaseCommand):
    help = (
        "Gera um CSV (UTF-8 com BOM, separador ';') das inscrições aprovadas "
        "com Nome, Modalidade, Categoria, E-mail e Pontuação validada."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--saida",
            default=f"aprovadas_{timezone.localdate()}.csv",
            help=(
                "Caminho do arquivo CSV a gerar "
                "(padrão: aprovadas_<AAAA-MM-DD>.csv no diretório atual)."
            ),
        )

    def handle(self, *args, **options):
        aprovadas = (
            Inscricao.objects.filter(status=StatusInscricao.APROVADA)
            .select_related("usuario")
            .order_by("modalidade", "-total_validado")
        )

        total = aprovadas.count()
        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_HEADING(f"Inscrições aprovadas: {total}")
        )

        if total == 0:
            self.stdout.write("Nenhuma inscrição aprovada — nada a exportar.")
            return

        caminho = options["saida"]

        # encoding="utf-8-sig" grava o BOM de UTF-8 no início do arquivo, que é o
        # que faz o Excel pt-BR reconhecer o texto como UTF-8 (sem o BOM ele tenta
        # ler como Windows-1252 e os acentos viram lixo). newline="" evita linhas
        # em branco entre os registros no Windows. delimiter=";" porque o Excel
        # pt-BR usa o ponto-e-vírgula como separador de colunas.
        with open(caminho, "w", newline="", encoding="utf-8-sig") as arquivo:
            writer = csv.writer(arquivo, delimiter=";")
            writer.writerow(
                ["Nome", "Modalidade", "Categoria", "Email", "Pontuação"]
            )
            for ins in aprovadas:
                usuario = ins.usuario
                categoria = (
                    ins.get_tipo_servidor_display() if ins.tipo_servidor else "—"
                )
                # Pontuação com vírgula decimal para o Excel pt-BR tratar como número.
                if ins.total_validado is None:
                    pontuacao = "—"
                else:
                    pontuacao = f"{ins.total_validado:.2f}".replace(".", ",")
                writer.writerow(
                    [
                        usuario.nome_completo,
                        ins.get_modalidade_display(),
                        categoria,
                        usuario.email,
                        pontuacao,
                    ]
                )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"CSV gerado: {caminho} ({total} inscrição(ões) aprovada(s))."
            )
        )
