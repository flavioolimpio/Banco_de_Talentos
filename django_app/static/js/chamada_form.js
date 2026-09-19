// static/js/chamada_form.js
// Banco de Talentos — Polo de Inovação IFG
//
// Atualiza a pontuação de cada critério e o total enquanto o candidato
// responde o formulário da chamada. É só conforto visual: quem calcula de
// verdade é o servidor, em CriterioEdital.pontuar(). Nunca confiar no cliente.
//
// Arquivo externo porque a CSP de produção é script-src 'self'.
(function () {
    var campos = document.querySelectorAll('[data-pontua]');
    if (!campos.length) return;

    var totalEl = document.getElementById('ci-total');

    function formatar(n) {
        return n.toFixed(2).replace(/\.00$/, '').replace('.', ',');
    }

    function pontosDe(campo) {
        var maximo = 0;
        var pontos = 0;

        if (campo.dataset.tipo === 'escolha') {
            var opcao = campo.options[campo.selectedIndex];
            pontos = parseFloat((opcao && opcao.dataset.pontos) || 0) || 0;
        } else {
            var qtd = parseInt(campo.value, 10);
            if (isNaN(qtd) || qtd < 0) qtd = 0;
            pontos = qtd * (parseFloat(campo.dataset.porUnidade) || 0);
        }

        var badge = campo.closest('.ci-resposta').querySelector('[data-pontos-de]');
        if (badge) {
            maximo = parseFloat(badge.dataset.maximo) || 0;
            if (pontos > maximo) pontos = maximo;
            badge.textContent = formatar(pontos) + ' pontos';
        }
        return pontos;
    }

    function recalcular() {
        var total = 0;
        campos.forEach(function (campo) { total += pontosDe(campo); });
        if (totalEl) totalEl.textContent = formatar(total);
    }

    campos.forEach(function (campo) {
        campo.addEventListener('input', recalcular);
        campo.addEventListener('change', recalcular);
    });

    recalcular();
}());
