# Checklist Operacional - Banco de Talentos IFG

Este documento resume o que sera necessario na VM institucional para operar o Banco de Talentos em Django.

## Infraestrutura

- [TI-IFG] VM Linux com acesso SSH para o usuario de operacao.
- [TI-IFG] Python 3.12+ instalado.
- [TI-IFG] PostgreSQL 15+ disponivel localmente ou em servidor institucional.
- [TI-IFG] Portas 80 e 443 liberadas para HTTP/HTTPS.
- [TI-IFG] Dominio institucional apontando para a VM.

## Seguranca

- [TI-IFG] HTTPS obrigatorio.
- [TI-IFG] `DEBUG=False` em producao.
- [TI-IFG] Segredos somente por variaveis de ambiente ou arquivo `.env` protegido.
- [RH] Definir quem tera permissao administrativa.
- [RH] Trocar qualquer usuario de teste antes de abrir edital real.

## Dados e LGPD

- [RH] Validar texto do termo de aceite LGPD.
- [RH] Definir versao do termo e prazo de retencao de dados.
- [TI-IFG] Backup diario do PostgreSQL.
- [TI-IFG] Backup diario da pasta de uploads/comprovantes.
- [EMBRAPII/Fundacao] Definir politica de guarda documental apos encerramento do edital.

## Deploy

- [TI-IFG] Configurar Gunicorn como servico `systemd`.
- [TI-IFG] Configurar Nginx como proxy reverso.
- [TI-IFG] Configurar log rotation.
- [TI-IFG] Documentar procedimento de restore.

