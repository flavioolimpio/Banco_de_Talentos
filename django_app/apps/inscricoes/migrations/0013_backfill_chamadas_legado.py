# apps/inscricoes/migrations/0013_backfill_chamadas_legado.py
# Banco de Talentos — Polo de Inovação IFG
#
# Passo 2 de 3 da mudança para inscrição por chamada interna.
#
# Cria três chamadas SINTÉTICAS — uma por modalidade, correspondendo aos
# Editais 29, 30 e 31/2026 — e liga a elas tudo o que já existe: os critérios
# e as inscrições do credenciamento antigo.
#
# Por que chamadas sintéticas em vez de deixar `chamada` nulo para sempre:
# paga-se esta migration curta uma vez e, daí em diante, TODA inscrição tem
# chamada. A alternativa seria carregar um `if inscricao.chamada is None:` em
# cada view, cada exportação e cada template, para sempre.
#
# As três nascem com publicada=False, legado=True e encerramento no passado:
# elas nunca aparecem para o candidato nem recebem inscrição nova; existem só
# para o histórico não ficar solto.
#
# CUIDADOS:
#   - Os vínculos são feitos com UPDATE, jamais delete+insert. InscricaoItem
#     aponta para CriterioEdital com PROTECT: apagar e recriar critérios "para
#     organizar" ou trava, ou desliga a pontuação histórica do critério que a
#     originou. Os item_id legados também não são tocados.
#   - HistoricalInscricao (django-simple-history) TAMBÉM é preenchido. Ele tem
#     `modalidade` próprio, então dá para atualizar direto. Se ficasse de fora,
#     a 0014 falharia ao tornar a coluna obrigatória — ou, pior, um
#     makemigrations posterior carimbaria o histórico inteiro com uma chamada
#     única, corrompendo a auditoria.
#   - No fim, se sobrar QUALQUER linha sem chamada, a migration aborta. É
#     melhor parar aqui do que deixar a 0014 estourar no meio de um deploy.

from django.db import migrations
from django.utils import timezone

# modalidade -> (numero, ano, titulo, edital)
LEGADO = {
    "servidor": (29, 2026, "Credenciamento (legado) — Servidores do IFG",
                 "Edital PROPPG nº 29/2026"),
    "colaborador_externo": (30, 2026, "Credenciamento (legado) — Colaboradores Externos",
                            "Edital PROPPG nº 30/2026"),
    "estudante": (31, 2026, "Credenciamento (legado) — Estudantes do IFG",
                  "Edital PROPPG nº 31/2026"),
}

TEXTO = (
    "Registro histórico das inscrições feitas no credenciamento ao Banco de "
    "Especialistas, antes de a Análise Curricular passar a ocorrer dentro de "
    "cada Chamada Interna. Não recebe inscrições novas."
)


def criar_e_vincular(apps, schema_editor):
    ChamadaInterna = apps.get_model("inscricoes", "ChamadaInterna")
    CriterioEdital = apps.get_model("inscricoes", "CriterioEdital")
    Inscricao = apps.get_model("inscricoes", "Inscricao")
    HistoricalInscricao = apps.get_model("inscricoes", "HistoricalInscricao")

    agora = timezone.now()

    for modalidade, (numero, ano, titulo, edital) in LEGADO.items():
        chamada, _ = ChamadaInterna.objects.get_or_create(
            numero=numero,
            ano=ano,
            defaults={
                "titulo": titulo,
                "edital": edital,
                "texto": TEXTO,
                "abertura": agora,
                "encerramento": agora,
                "publicada": False,
                "legado": True,
            },
        )
        CriterioEdital.objects.filter(modalidade=modalidade, chamada__isnull=True).update(
            chamada=chamada
        )
        Inscricao.objects.filter(modalidade=modalidade, chamada__isnull=True).update(
            chamada=chamada
        )
        HistoricalInscricao.objects.filter(
            modalidade=modalidade, chamada__isnull=True
        ).update(chamada_id=chamada.pk)

    sobras = {
        "CriterioEdital": CriterioEdital.objects.filter(chamada__isnull=True).count(),
        "Inscricao": Inscricao.objects.filter(chamada__isnull=True).count(),
        "HistoricalInscricao": HistoricalInscricao.objects.filter(
            chamada__isnull=True
        ).count(),
    }
    if any(sobras.values()):
        raise RuntimeError(
            "Backfill incompleto — linhas sem chamada: "
            f"{ {k: v for k, v in sobras.items() if v} }. "
            "Provável modalidade fora de LEGADO. Corrija antes de aplicar a 0014."
        )


def desvincular(apps, schema_editor):
    ChamadaInterna = apps.get_model("inscricoes", "ChamadaInterna")
    CriterioEdital = apps.get_model("inscricoes", "CriterioEdital")
    Inscricao = apps.get_model("inscricoes", "Inscricao")
    HistoricalInscricao = apps.get_model("inscricoes", "HistoricalInscricao")

    legado = ChamadaInterna.objects.filter(legado=True)
    CriterioEdital.objects.filter(chamada__in=legado).update(chamada=None)
    Inscricao.objects.filter(chamada__in=legado).update(chamada=None)
    HistoricalInscricao.objects.filter(chamada__in=legado).update(chamada_id=None)
    # Só agora dá para apagar: as FKs são PROTECT e os filhos voltaram a nulo.
    legado.delete()


class Migration(migrations.Migration):

    dependencies = [
        ("inscricoes", "0012_chamadas_internas"),
    ]

    operations = [
        migrations.RunPython(criar_e_vincular, desvincular),
    ]
