# apps/inscricoes/management/commands/exportar_lattes_xml.py
# Banco de Talentos — Polo de Inovação IFG
# Copia para uma pasta os currículos Lattes (XML) das inscrições ENVIADAS de
# uma chamada, para rodar a skill lattes-xml-extrator de uma vez só.
#
# Pasta e não .zip: o script da skill lê só .xml e ignora .zip. Cada arquivo
# sai como "insc<id>_<nome-curto>.xml" — o id da inscrição volta na coluna
# arquivo_origem da planilha da skill, e é por ele que o RH acha a inscrição
# na tela de revisão. Sem CPF no nome do arquivo.
#
# Ao lado da pasta sai <pasta>_inscricoes.csv, com a vaga, a categoria e as
# licenças à gestante/adotante de cada arquivo. É o que o RH precisa para rodar
# a skill: o quadro de critérios muda conforme a vaga, e --licencas vale para
# todos os arquivos de uma rodada — quem declarou licença roda à parte.
#
# Uso:
#   python manage.py exportar_lattes_xml --chamada 4
#   python manage.py exportar_lattes_xml --chamada 4 --saida pasta/
#
# Apenas leitura. NUNCA altera dados do banco. A pasta gerada contém dados
# pessoais (o XML traz CPF, RG, filiação): apague depois da análise.

import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.auditoria.models import AuditAction, AuditLog
from apps.inscricoes.management.commands.exportar_pdfs_aprovados import _slug_nome
from apps.inscricoes.models import ChamadaInterna, Inscricao


class Command(BaseCommand):
    help = "Copia os XML do Lattes das inscrições enviadas de uma chamada para uma pasta."

    def add_arguments(self, parser):
        parser.add_argument("--chamada", type=int, required=True, help="ID da chamada interna.")
        parser.add_argument("--saida", help="Pasta de destino (padrão: lattes_chamada_<id>_<data>/).")

    def handle(self, *args, **options):
        try:
            chamada = ChamadaInterna.objects.get(pk=options["chamada"])
        except ChamadaInterna.DoesNotExist:
            raise CommandError(f"Não existe chamada com id {options['chamada']}.")

        inscricoes = (
            Inscricao.objects.filter(chamada=chamada, enviada_em__isnull=False)
            .exclude(lattes_xml="")
            .select_related("usuario")
            .order_by("pk")
        )
        if not inscricoes:
            self.stdout.write("Nenhuma inscrição enviada com XML nesta chamada — nada a exportar.")
            return

        pasta = Path(options["saida"] or f"lattes_chamada_{chamada.pk}_{timezone.localdate()}")
        if pasta.exists() and any(pasta.iterdir()):
            raise CommandError(f"A pasta {pasta} já existe e não está vazia. Escolha outra com --saida.")
        pasta.mkdir(parents=True, exist_ok=True)

        copiados, sem_arquivo, linhas = 0, [], []
        for ins in inscricoes.select_related("vaga"):
            if not ins.lattes_xml.storage.exists(ins.lattes_xml.name):
                sem_arquivo.append(f"inscrição {ins.pk}")
                continue
            destino = pasta / f"insc{ins.pk}_{_slug_nome(ins.usuario.nome_completo)}.xml"
            with ins.lattes_xml.open("rb") as f:
                destino.write_bytes(f.read())
            copiados += 1
            linhas.append({
                "arquivo": destino.name,
                "inscricao": ins.pk,
                "nome": ins.usuario.nome_completo,
                "vaga": ins.vaga.codigo if ins.vaga else "",
                "modalidade": ins.get_modalidade_display(),
                "categoria": ins.get_tipo_servidor_display(),
                "licencas": ins.licencas_maternidade,
            })

        planilha = pasta.with_name(f"{pasta.name}_inscricoes.csv")
        with open(planilha, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, list(linhas[0]) if linhas else ["arquivo"], delimiter=";")
            w.writeheader()
            w.writerows(linhas)

        AuditLog.objects.create(
            acao=AuditAction.CSV_EXPORTADO,
            detalhes={"comando": "exportar_lattes_xml", "chamada": chamada.pk, "arquivos": copiados},
        )
        self.stdout.write(self.style.SUCCESS(f"{copiados} XML copiado(s) para {pasta}/"))
        self.stdout.write(f"Vaga e licenças de cada arquivo: {planilha}")
        self.stdout.write(
            "Próximo passo: python <pasta-da-skill>/scripts/lattes_extract.py "
            f"{pasta} --criterios quadro.csv --data-chamada DD/MM/AAAA --xlsx pretriagem.xlsx"
        )
        if sem_arquivo:
            self.stdout.write(self.style.WARNING("Registro sem arquivo no disco: " + ", ".join(sem_arquivo)))
