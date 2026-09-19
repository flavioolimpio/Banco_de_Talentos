# apps/inscricoes/migrations/0011_corrige_is_api_ifgproduz.py
# Banco de Talentos — Polo de Inovação IFG
#
# Garante que o critério "ifgproduz" esteja marcado como preenchido via API.
#
# Contexto do bug: a migration 0004 popula CriterioEdital importando
# `apps/inscricoes/quadros.py` em tempo de execução — ou seja, ela lê o arquivo
# como ele está HOJE, não como estava quando foi escrita. Quando o "ifgproduz"
# entrou no quadro do Servidor, a 0004 passou a criá-lo; só que nesse momento a
# coluna `is_api` ainda nem existe (ela é adicionada na 0005), então o critério
# nasce com o padrão False. A 0005, que criaria o critério com is_api=True, faz
# `if not ... exists()` e pula, porque a linha já está lá.
#
# Efeito: em PRODUÇÃO está correto (lá a 0004 rodou com o quadros.py antigo,
# que não tinha o ifgproduz, e a 0005 criou a linha com is_api=True). Mas todo
# banco criado do zero depois da revisão dos quadros — máquina de dev nova, CI,
# banco de teste — nasce com is_api=False, e o critério aparece para o
# candidato como campo digitável em vez de vir da API do IFGProduz.
#
# Correção: um UPDATE idempotente. É no-op em produção e conserta os bancos
# novos. O `popular_criterios` também passou a gravar `is_api` (mesma entrega),
# para não reintroduzir o problema ao repovoar.

from django.db import migrations


def corrigir_is_api(apps, schema_editor):
    CriterioEdital = apps.get_model("inscricoes", "CriterioEdital")
    CriterioEdital.objects.filter(item_id="ifgproduz").update(is_api=True)


class Migration(migrations.Migration):

    dependencies = [
        ("inscricoes", "0010_alter_criterioedital_modalidade_and_more"),
    ]

    operations = [
        # Sem reverse: voltar is_api para False recriaria o bug. A migration
        # apenas afirma o estado correto, então reverter é não fazer nada.
        migrations.RunPython(corrigir_is_api, migrations.RunPython.noop),
    ]
