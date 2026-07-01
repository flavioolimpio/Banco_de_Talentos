# apps/inscricoes/management/commands/exportar_pdfs_aprovados.py
# Banco de Talentos — Polo de Inovação IFG
# Junta os PDFs de comprovantes de TODAS as inscrições aprovadas (qualquer
# modalidade) num único .zip, pra baixar de uma vez só via scp em vez de
# clicar "Baixar" um por um no Admin.
#
# Cada PDF entra no zip nomeado "<cpf>_<nome-curto>.pdf" — mesmo padrão
# sugerido pro processo de indicação nos quadros de vagas.
#
# Uso:
#   python manage.py exportar_pdfs_aprovados
#   python manage.py exportar_pdfs_aprovados --saida x.zip
#
# Apenas leitura de arquivos já enviados. NUNCA altera dados do banco.

import re
import zipfile

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.inscricoes.models import Inscricao, StatusInscricao


def _slug_nome(nome: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", nome).strip().lower()
    slug = re.sub(r"[\s_-]+", "-", slug)
    return slug[:40]


class Command(BaseCommand):
    help = (
        "Gera um .zip com os PDFs de comprovantes de todas as inscrições "
        "aprovadas, nomeados <cpf>_<nome-curto>.pdf."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--saida",
            default=f"pdfs_aprovados_{timezone.localdate()}.zip",
            help=(
                "Caminho do .zip a gerar "
                "(padrão: pdfs_aprovados_<AAAA-MM-DD>.zip no diretório atual)."
            ),
        )

    def handle(self, *args, **options):
        aprovadas = (
            Inscricao.objects.filter(status=StatusInscricao.APROVADA)
            .exclude(comprovantes_pdf="")
            .select_related("usuario")
            .order_by("modalidade", "-total_validado")
        )

        total = aprovadas.count()
        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_HEADING(f"Inscrições aprovadas com PDF: {total}")
        )

        if total == 0:
            self.stdout.write("Nenhum PDF de aprovado encontrado — nada a exportar.")
            return

        caminho = options["saida"]
        sem_arquivo = []

        with zipfile.ZipFile(caminho, "w", zipfile.ZIP_DEFLATED) as zf:
            for ins in aprovadas:
                usuario = ins.usuario
                if not ins.comprovantes_pdf.storage.exists(ins.comprovantes_pdf.name):
                    sem_arquivo.append(usuario.nome_completo)
                    continue
                nome_zip = f"{usuario.cpf}_{_slug_nome(usuario.nome_completo)}.pdf"
                with ins.comprovantes_pdf.open("rb") as f:
                    zf.writestr(nome_zip, f.read())

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(f"Zip gerado: {caminho} ({total - len(sem_arquivo)} PDF(s)).")
        )
        if sem_arquivo:
            self.stdout.write(
                self.style.WARNING(
                    "Sem arquivo no storage (registro aponta PDF que sumiu do disco): "
                    + ", ".join(sem_arquivo)
                )
            )
