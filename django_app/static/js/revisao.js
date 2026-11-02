// static/js/revisao.js
// Banco de Talentos — Polo de Inovação IFG
//
// Recalcula o "Total validado" da tela de revisão do RH em tempo real,
// enquanto a pessoa confirma a quantidade ou a opção de cada critério.
//
// Só conforto visual: quem vale é o servidor, em views_rh._validar_item, que
// usa exatamente o mesmo CriterioEdital.pontuar() do formulário do candidato.
//
// A antiga fórmula de média com o IFGProduz saiu junto com o quadro fixo do
// Servidor: no fluxo por chamada, o total é a soma simples dos critérios.
//
// Arquivo externo por causa da CSP (script-src 'self').
(function () {
    "use strict";

    var campos = document.querySelectorAll("[data-valida]");
    var spanTotal = document.getElementById("total-validado");
    // Critérios do credenciamento antigo continuam com pontuação digitada.
    var legados = document.querySelectorAll('input[id^="validado_"]');

    function fmt(n) {
        return n.toFixed(1).replace(".", ",");
    }

    function pontosDe(campo) {
        var pontos;
        if (campo.dataset.tipo === "escolha") {
            var opcao = campo.options[campo.selectedIndex];
            pontos = parseFloat((opcao && opcao.dataset.pontos) || 0) || 0;
        } else {
            var qtd = parseInt(campo.value, 10);
            if (isNaN(qtd) || qtd < 0) qtd = 0;
            pontos = qtd * (parseFloat(campo.dataset.porUnidade) || 0);
            var maximo = parseFloat(campo.dataset.maximo);
            if (!isNaN(maximo) && pontos > maximo) pontos = maximo;
        }
        return pontos;
    }

    function recalcular() {
        var total = 0;
        campos.forEach(function (campo) { total += pontosDe(campo); });
        legados.forEach(function (input) {
            var valor = parseFloat(String(input.value).replace(",", "."));
            if (isNaN(valor)) {
                // Campo em branco: vale o que o candidato declarou.
                valor = parseFloat(input.placeholder.replace(",", ".")) || 0;
            }
            total += valor;
        });
        if (spanTotal) spanTotal.textContent = fmt(total);
    }

    campos.forEach(function (campo) {
        campo.addEventListener("input", recalcular);
        campo.addEventListener("change", recalcular);
    });
    legados.forEach(function (input) {
        input.addEventListener("input", recalcular);
    });

    recalcular();
}());
