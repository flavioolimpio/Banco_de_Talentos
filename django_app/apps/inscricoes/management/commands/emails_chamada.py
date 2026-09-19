# apps/inscricoes/management/commands/emails_chamada.py
# Banco de Talentos — Polo de Inovação IFG
#
# Gera a lista de e-mails para a divulgação de uma Chamada Interna, junto com
# um rascunho do texto do aviso.
#
# Base normativa (Edital PROPPG 29/2026, na redação da Retificação 4):
#   5.2.2 — publicada a chamada, o Polo envia comunicação "ao endereço de
#           e-mail informado a todos os servidores(as) cadastrados no Banco de
#           Especialistas, a título de aviso complementar";
#   5.2.3 — falha no recebimento não suspende nem prorroga o prazo;
#   5.2.4 — manter o e-mail atualizado é responsabilidade de quem se cadastrou.
#
# POR QUE O SISTEMA NÃO ENVIA: o e-mail é aviso COMPLEMENTAR — o ato que abre o
# prazo é a publicação na página da PROPPG. Mandar por fora, colando a lista no
# Cco de rh.embrapii@ifg.edu.br, é juridicamente suficiente, e evita depender de
# SMTP institucional (que hoje sequer está configurado em produção).
#
# QUEM ENTRA: só quem tem vínculo compatível com alguma VAGA da chamada. Se a
# chamada só oferta vaga de servidor, estudante não recebe. Avisar quem não pode
# se inscrever foi exatamente a reclamação que originou toda esta mudança.
#
# Uso:
#   python manage.py emails_chamada --chamada 4
#   python manage.py emails_chamada --chamada 4 --saida aviso.txt
#   python manage.py emails_chamada --chamada 4 --csv lista.csv
#
# Apenas consulta + exportação. NUNCA altera dados do banco.

import csv

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.auditoria.models import AuditAction, AuditLog
from apps.inscricoes.models import ChamadaInterna
from apps.usuarios.models import Usuario, Vinculo

CONTATO = "rh.embrapii@ifg.edu.br"
PAGINA_PROPPG = "https://www.ifg.edu.br/editais-pesquisa-e-pos-graduacao"


def destinatarios(chamada):
    """Cadastrados ativos cujo vínculo tem vaga nesta chamada."""
    modalidades = sorted(chamada.modalidades())
    if not modalidades:
        return Usuario.objects.none()
    return (
        Usuario.objects.filter(is_active=True, vinculo__in=modalidades)
        .exclude(email="")
        .order_by("nome_completo")
    )


def _frase_publico(chamada):
    """'servidores(as) do IFG e colaboradores(as) externos(as)' etc.

    O público varia a cada chamada — ora só servidor, ora só estudante, ora
    todos —, então o texto é montado a partir das vagas de fato ofertadas.
    """
    rotulos = {
        Vinculo.SERVIDOR: "servidores(as) do IFG",
        Vinculo.COLABORADOR_EXTERNO: "colaboradores(as) externos(as)",
        Vinculo.ESTUDANTE: "estudantes do IFG",
    }
    ordem = [Vinculo.SERVIDOR, Vinculo.COLABORADOR_EXTERNO, Vinculo.ESTUDANTE]
    presentes = [rotulos[v] for v in ordem if v in chamada.modalidades()]
    if not presentes:
        return "candidatos(as) credenciados(as) no Banco de Especialistas"
    if len(presentes) == 1:
        return presentes[0]
    return ", ".join(presentes[:-1]) + " e " + presentes[-1]


def montar_texto(chamada):
    linhas_vagas = []
    for vaga in chamada.vagas.all():
        detalhe = [f"{vaga.quantidade} vaga(s)"]
        if vaga.carga_horaria:
            detalhe.append(f"{vaga.carga_horaria}h semanais")
        if vaga.bolsa:
            detalhe.append(f"bolsa de R$ {vaga.bolsa:,.2f}".replace(",", "X")
                           .replace(".", ",").replace("X", "."))
        linhas_vagas.append(
            f"  - {vaga.codigo} — {vaga.funcao} "
            f"({vaga.get_modalidade_display()}): {', '.join(detalhe)}"
        )

    assunto = (
        f"Chamada Interna nº {chamada.numero:02d}/{chamada.ano} — {chamada.titulo} — "
        f"inscrições até {chamada.encerramento.strftime('%d/%m/%Y')}"
    )

    corpo = f"""Prezado(a) credenciado(a) no Banco de Especialistas,

Está publicada a Chamada Interna nº {chamada.numero:02d}/{chamada.ano} — {chamada.titulo}{
        f', referente ao projeto "{chamada.projeto}"' if chamada.projeto else ''
    }, destinada a {_frase_publico(chamada)} credenciados(as) no Banco de
Especialistas do Polo de Inovação/PROPPG.

Vagas ofertadas:
{chr(10).join(linhas_vagas) if linhas_vagas else '  (nenhuma vaga cadastrada)'}

As inscrições são feitas exclusivamente no Sistema do Banco de Especialistas,
em https://banco-de-especialistas.ifg.edu.br, entrando com o seu CPF e
clicando no botão da chamada na página inicial. O prazo encerra em
{chamada.encerramento.strftime('%d/%m/%Y às %Hh%M')}.

No formulário, você responde ao quadro de critérios desta chamada, anexa um
único PDF com os comprovantes e firma as declarações exigidas. A pontuação é
calculada pelo próprio sistema e só é consolidada após a conferência dos
documentos.

{f'Aviso na íntegra: {chamada.aviso_url}' if chamada.aviso_url else f'Aviso na íntegra: {PAGINA_PROPPG}'}

A não inscrição nesta chamada não gera nenhum prejuízo à sua permanência no
Banco de Especialistas nem à participação em chamadas futuras.

Esta mensagem é um aviso complementar: o ato que abre o prazo é a publicação
na página da PROPPG. Mantenha seu e-mail atualizado em "Meu Cadastro".

Atenciosamente,

Unidade Embrapii-IFG — Polo de Inovação / PROPPG
{CONTATO}"""

    return assunto, corpo


class Command(BaseCommand):
    help = (
        "Gera a lista de e-mails e o rascunho do aviso de divulgação de uma "
        "chamada interna. Exige --chamada."
    )

    def add_arguments(self, parser):
        parser.add_argument("--chamada", type=int, help="ID da chamada interna.")
        parser.add_argument("--saida", help="Arquivo .txt a gerar (padrão: nome automático).")
        parser.add_argument("--csv", help="Também gera um CSV com nome, e-mail, vínculo e área.")
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
                "Informe --chamada <id>. Use --listar-chamadas para ver os IDs."
            )
        try:
            chamada = ChamadaInterna.objects.get(pk=options["chamada"])
        except ChamadaInterna.DoesNotExist:
            raise CommandError(f"Não existe chamada com id {options['chamada']}.")

        pessoas = list(destinatarios(chamada))
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING(f"{chamada}"))
        self.stdout.write(f"Público: {_frase_publico(chamada)}")
        self.stdout.write(f"Destinatários: {len(pessoas)}")

        if not chamada.modalidades():
            self.stdout.write(self.style.WARNING(
                "A chamada não tem vaga cadastrada, então não há como saber quem avisar.\n"
                "Cadastre as vagas no admin antes de gerar a lista."
            ))
            return
        if not pessoas:
            self.stdout.write("Nenhum cadastrado com esse vínculo — nada a exportar.")
            return
        if not chamada.publicada:
            self.stdout.write(self.style.WARNING(
                "ATENÇÃO: esta chamada ainda não está publicada. O e-mail é aviso\n"
                "complementar à publicação (item 5.2.2) — publique antes de disparar."
            ))

        assunto, corpo = montar_texto(chamada)
        emails = "; ".join(p.email for p in pessoas)

        caminho = options["saida"] or (
            f"emails_chamada_{chamada.numero:02d}_{chamada.ano}_{timezone.localdate()}.txt"
        )
        with open(caminho, "w", encoding="utf-8") as arquivo:
            arquivo.write(emails + "\n\n\n")
            arquivo.write(f"Assunto: {assunto}\n\n\n")
            arquivo.write(corpo + "\n")

        if options["csv"]:
            with open(options["csv"], "w", newline="", encoding="utf-8-sig") as arquivo:
                writer = csv.writer(arquivo, delimiter=";")
                writer.writerow(["Nome", "E-mail", "Vínculo", "Categoria", "Área CNPq"])
                for p in pessoas:
                    writer.writerow([
                        p.nome_completo,
                        p.email,
                        p.get_vinculo_display(),
                        p.get_categoria_pretendida_display() or "—",
                        p.get_cnpq_area_display() or "—",
                    ])

        # Exportação de dado pessoal — fica registrada, conforme a regra 6 do
        # CLAUDE.md. Sem CPF: o e-mail já basta para o disparo.
        AuditLog.objects.create(
            acao=AuditAction.CSV_EXPORTADO,
            detalhes={
                "comando": "emails_chamada",
                "chamada": chamada.pk,
                "destinatarios": len(pessoas),
                "arquivo": caminho,
            },
        )

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"Arquivo gerado: {caminho}"))
        if options["csv"]:
            self.stdout.write(self.style.SUCCESS(f"CSV gerado: {options['csv']}"))
        self.stdout.write("")
        self.stdout.write(
            "Confira o texto antes de enviar. Dispare de "
            f"{CONTATO} com os endereços em Cco."
        )
