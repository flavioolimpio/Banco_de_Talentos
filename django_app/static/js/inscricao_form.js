(function () {
    function fmt(n) {
        return n.toFixed(1).replace('.', ',');
    }

    function updateTotal() {
        var apiEls     = document.querySelectorAll('[data-score][data-api]');
        var manualEls  = document.querySelectorAll('[data-score]:not([data-api])');
        var formulaEl  = document.getElementById('formula-ifgproduz');

        var totalApi    = 0;
        var totalManual = 0;

        apiEls.forEach(function (el) {
            var val = parseFloat(el.dataset.value) || 0;
            var max = parseFloat(el.dataset.max)   || 0;
            totalApi += Math.min(Math.max(val, 0), max);
        });

        manualEls.forEach(function (el) {
            var val = parseFloat(el.value) || 0;
            var max = parseFloat(el.dataset.max) || 0;
            totalManual += Math.min(Math.max(val, 0), max);
        });

        var display = document.getElementById('total-display');
        if (!display) return;

        // Servidor: fórmula (min(IFGProduz,100) + min(critérios,100)) / 2
        if (formulaEl) {
            var apiCapped    = Math.min(totalApi,    100);
            var manualCapped = Math.min(totalManual, 100);
            var total        = (apiCapped + manualCapped) / 2;

            formulaEl.textContent = fmt(apiCapped);
            var critEl = document.getElementById('formula-criterios');
            if (critEl) critEl.textContent = fmt(manualCapped);

            display.textContent = fmt(total);
        } else {
            display.textContent = fmt(totalApi + totalManual);
        }
    }

    document.querySelectorAll('[data-score]:not([data-api])').forEach(function (el) {
        el.addEventListener('input', updateTotal);
    });

    updateTotal();

    // Ao trocar a categoria (tipo_servidor), recarrega o formulário com os
    // critérios do quadro correspondente. Necessário porque os critérios são
    // renderizados no servidor (ex.: Colaborador Externo Pesquisador x Apoio
    // Técnico têm quadros diferentes).
    var tipoSelect = document.getElementById('id_tipo_servidor');
    if (tipoSelect) {
        tipoSelect.addEventListener('change', function () {
            var url = new URL(window.location.href);
            url.searchParams.set('tipo', tipoSelect.value);
            window.location.href = url.toString();
        });
    }
}());
