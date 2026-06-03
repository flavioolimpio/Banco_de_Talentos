# apps/inscricoes/management/commands/recalcular_totais_servidores.py
# Banco de Talentos — Polo de Inovação IFG
# Recalcula os totais de todas as inscrições de servidores com a fórmula:
#   total = (min(manual, 100) + min(IFGProduz, 100)) / 2
# Para inscrições sem item IFGProduz armazenado, tenta buscar da API.

from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.inscricoes.models import CriterioEdital, Inscricao, InscricaoItem
from apps.inscricoes.services import buscar_pontuacao_ifgproduz
from apps.usuarios.models import Vinculo


class Command(BaseCommand):
    help = "Recalcula totais de inscrições de servidores: (IFGProduz + critérios) / 2"

    def handle(self, *args, **options):
        inscricoes = (
            Inscricao.objects.filter(modalidade=Vinculo.SERVIDOR)
            .select_related("usuario")
            .prefetch_related("itens__criterio")
        )

        atualizadas = 0
        erros = 0

        for inscricao in inscricoes:
            itens = list(inscricao.itens.all())
            total_manual = Decimal("0")
            total_api = Decimal("0")
            tem_item_api = False

            for item in itens:
                if item.criterio.is_api:
                    total_api += item.pontuacao
                    tem_item_api = True
                else:
                    total_manual += item.pontuacao

            # Se não há item API armazenado, tenta buscar IFGProduz da API
            if not tem_item_api:
                criterio_api = CriterioEdital.objects.filter(
                    modalidade="servidor",
                    tipo_servidor=inscricao.tipo_servidor,
                    is_api=True,
                    ativo=True,
                ).first()

                if criterio_api and inscricao.usuario.lattes:
                    valor = buscar_pontuacao_ifgproduz(inscricao.usuario.lattes)
                    if valor is not None:
                        valor_capped = min(Decimal(str(valor)), criterio_api.maximo)
                        InscricaoItem.objects.update_or_create(
                            inscricao=inscricao,
                            criterio=criterio_api,
                            defaults={"pontuacao": valor_capped},
                        )
                        total_api = valor_capped
                        self.stdout.write(f"  IFGProduz buscado: {valor_capped} pts")
                    else:
                        self.stdout.write(
                            self.style.WARNING(f"  IFGProduz indisponível para {inscricao.usuario.nome_completo}")
                        )
                        erros += 1

            manual_capped = min(total_manual, Decimal("100"))
            api_capped = min(total_api, Decimal("100"))
            novo_total = (manual_capped + api_capped) / 2

            antigo_total = inscricao.total
            Inscricao.objects.filter(pk=inscricao.pk).update(total=novo_total)

            self.stdout.write(
                f"#{inscricao.pk} {inscricao.usuario.nome_completo} "
                f"[{inscricao.get_tipo_servidor_display() or 'Pesquisador'}]: "
                f"manual={manual_capped} ifgproduz={api_capped} "
                f"| {antigo_total} → {novo_total}"
            )
            atualizadas += 1

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"Recalculadas: {atualizadas} inscrições de servidores."))
        if erros:
            self.stdout.write(self.style.WARNING(f"IFGProduz indisponível em: {erros} inscrição(ões)."))
