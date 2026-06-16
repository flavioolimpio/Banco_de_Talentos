// static/js/revisao.js
// Banco de Talentos — Polo de Inovação IFG
// Recalcula o "Total validado" da tela de revisão do RH em tempo real.
// Para servidor aplica a mesma fórmula do candidato:
//   (min(IFGProduz, 100) + min(critérios, 100)) / 2
// Para as demais modalidades, soma simples.
//
// Carregado como arquivo externo (não inline) por causa da CSP do site,
// que só permite scripts servidos pelo próprio domínio (script-src 'self').
(function () {
    "use strict";

    var inputs      = document.querySelectorAll('[id^="validado_"]');
    var spanTotal   = document.getElementById("total-validado");
    var dados       = document.getElementById("revisao-dados");
    var isServidor  = dados && dados.dataset.servidor === "true";
    var formulaApi  = document.getElementById("formula-validado-api");
    var formulaCrit = document.getElementById("formula-validado-crit");

    function fmt(n) {
        return n.toFixed(1).replace('.', ',');
    }

    // valor considerado de um input: o digitado pelo RH ou, se vazio,
    // a pontuação declarada pelo candidato (data-candidato)
    function valorDe(inp) {
        var raw = inp.value.trim();
        if (raw !== "") {
            var v = parseFloat(raw);
            return isNaN(v) ? 0 : v;
        }
        var cand = parseFloat(inp.dataset.candidato);
        return isNaN(cand) ? 0 : cand;
    }

    function calcularTotal() {
        var totalManual = 0;
        var totalApi = 0;
        inputs.forEach(function (inp) {
            var v = valorDe(inp);
            if (inp.dataset.api === "true") {
                totalApi += v;
            } else {
                totalManual += v;
            }
        });

        var total;
        if (isServidor) {
            // mesma fórmula do candidato: (min(IFGProduz,100) + min(critérios,100)) / 2
            var apiCap  = Math.min(totalApi, 100);
            var critCap = Math.min(totalManual, 100);
            total = (apiCap + critCap) / 2;
            if (formulaApi)  { formulaApi.textContent  = fmt(apiCap); }
            if (formulaCrit) { formulaCrit.textContent = fmt(critCap); }
        } else {
            total = totalManual + totalApi;
        }

        if (spanTotal) {
            spanTotal.textContent = fmt(total);
        }
    }

    // calcular ao carregar a página
    calcularTotal();

    // recalcular a cada alteração
    inputs.forEach(function (inp) {
        inp.addEventListener("input", calcularTotal);
    });
}());
