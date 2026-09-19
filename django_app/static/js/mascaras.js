// static/js/mascaras.js
// Banco de Talentos — Polo de Inovação IFG
//
// Máscara de telefone no formulário de Meu Cadastro.
//
// Diferença para o `placeholder`: o placeholder é só o exemplo cinza dentro
// do campo vazio, que some quando a pessoa digita. A máscara formata o que
// está sendo digitado — o candidato digita 62999998888 e vê
// (62) 99999-8888.
//
// Aplica-se a qualquer campo com data-mascara="telefone". Arquivo externo por
// causa da CSP de produção (script-src 'self').
//
// Sem JavaScript o campo continua funcionando como texto livre, exatamente
// como era antes — a máscara é conforto, não validação.
(function () {
    function formatarTelefone(valor) {
        var d = valor.replace(/\D/g, "").slice(0, 11);
        if (d.length === 0) return "";
        if (d.length <= 2) return "(" + d;
        // 8 dígitos = fixo ((62) 3232-3232); 9 = celular ((62) 99999-8888).
        var corte = d.length > 10 ? 7 : 6;
        if (d.length <= corte) return "(" + d.slice(0, 2) + ") " + d.slice(2);
        return "(" + d.slice(0, 2) + ") " + d.slice(2, corte) + "-" + d.slice(corte);
    }

    document.querySelectorAll('[data-mascara="telefone"]').forEach(function (campo) {
        function aplicar() {
            // Guarda se o cursor estava no fim: só nesse caso é seguro
            // devolvê-lo ao fim depois de reformatar. Mexer no meio do texto
            // com máscara e cursor é fonte clássica de campo que "pula".
            var noFim = campo.selectionStart === campo.value.length;
            campo.value = formatarTelefone(campo.value);
            if (noFim) {
                campo.selectionStart = campo.selectionEnd = campo.value.length;
            }
        }

        campo.addEventListener("input", aplicar);
        if (campo.value) aplicar();  // formata o que já estava salvo
    });
}());
