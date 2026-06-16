# apps/inscricoes/management/commands/itens_orfaos.py
# Banco de Talentos — Polo de Inovação IFG
# Lista (e opcionalmente exporta em CSV) as inscrições que possuem itens
# "órfãos": itens de pontuação amarrados a critérios que NÃO fazem mais
# parte do quadro atual daquela inscrição.
#
# Isso acontece quando os critérios mudam depois que a pessoa se inscreve
# (ex.: o Apoio Técnico ganhou quadro próprio com IFGProduz). O formulário
# do candidato passa a mostrar os critérios novos, mas os itens antigos
# continuam guardados na inscrição e aparecem na revisão do RH.
#
# Uso:
#   python manage.py itens_orfaos          # só lista (não cria arquivo)
#   python manage.py itens_orfaos --csv    # lista E gera o CSV
#
# Apenas consulta + exportação. NUNCA altera nem apaga dados do banco.

import csv

from django.core.management.base import BaseCommand

from apps.inscricoes.models import CriterioEdital, Inscricao, TipoServidor

# Caminho do CSV gerado, relativo à pasta onde o manage.py é executado
CSV_PATH = "itens_orfaos.csv"


def _criterio_ids_validos(modalidade, tipo_servidor):
    """
    Conjunto de IDs de critérios válidos HOJE para uma inscrição, usando a
    mesma regra do formulário do candidato (_get_criterios em views.py):
    critérios de Pesquisador ficam no quadro compartilhado (tipo_servidor="");
    apenas Apoio Técnico tem quadro próprio.
    """
    ts = tipo_servidor if tipo_servidor == TipoServidor.APOIO_TECNICO else ""
    return set(
        CriterioEdital.objects.filter(
            modalidade=modalidade,
            tipo_servidor=ts,
            ativo=True,
        ).values_list("pk", flat=True)
    )


class Command(BaseCommand):
    help = (
        "Lista inscrições com itens órfãos (apontando para critérios fora do "
        "quadro atual). Use --csv para também exportar a lista em arquivo."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv",
            action="store_true",
            help=f"Gera o arquivo {CSV_PATH} com a lista dos afetados.",
        )

    def handle(self, *args, **options):
        inscricoes = (
            Inscricao.objects.select_related("usuario")
            .prefetch_related("itens__criterio")
            .order_by("usuario__nome_completo")
        )

        # cache dos critérios válidos por (modalidade, tipo_servidor) para
        # não repetir a consulta a cada inscrição
        cache_validos = {}
        afetados = []  # lista de tuplas (inscricao, [itens_orfaos])

        for ins in inscricoes:
            chave = (ins.modalidade, ins.tipo_servidor or "")
            if chave not in cache_validos:
                cache_validos[chave] = _criterio_ids_validos(*chave)
            validos = cache_validos[chave]

            orfaos = [
                item for item in ins.itens.all()
                if item.criterio_id not in validos
            ]
            if orfaos:
                afetados.append((ins, orfaos))

        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"Inscrições com itens órfãos: {len(afetados)}"
            )
        )
        self.stdout.write("-" * 78)

        if not afetados:
            self.stdout.write("Nenhuma inscrição com itens órfãos.")
            return

        for ins, orfaos in afetados:
            usuario = ins.usuario
            tipo = ins.get_tipo_servidor_display() if ins.tipo_servidor else "-"
            self.stdout.write(
                f"{usuario.nome_completo}  |  {usuario.email}  "
                f"|  {ins.get_modalidade_display()} / {tipo}  "
                f"|  status: {ins.get_status_display()}"
            )
            for item in orfaos:
                self.stdout.write(
                    f"    - item órfão: {item.criterio.criterio} "
                    f"(pontuação: {item.pontuacao})"
                )

        self.stdout.write("-" * 78)

        if not options["csv"]:
            self.stdout.write("")
            self.stdout.write(
                "Para exportar a lista em CSV, rode novamente com --csv"
            )
            return

        # --csv: uma linha por item órfão (sem CPF — dado sensível)
        with open(CSV_PATH, "w", newline="", encoding="utf-8") as arquivo:
            writer = csv.writer(arquivo)
            writer.writerow([
                "nome", "email", "modalidade", "tipo_servidor", "status",
                "criterio_orfao", "pontuacao",
            ])
            for ins, orfaos in afetados:
                tipo = ins.get_tipo_servidor_display() if ins.tipo_servidor else ""
                for item in orfaos:
                    writer.writerow([
                        ins.usuario.nome_completo,
                        ins.usuario.email,
                        ins.get_modalidade_display(),
                        tipo,
                        ins.get_status_display(),
                        item.criterio.criterio,
                        item.pontuacao,
                    ])

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"CSV gerado: {CSV_PATH} "
                f"({len(afetados)} inscrição(ões) afetada(s))."
            )
        )
