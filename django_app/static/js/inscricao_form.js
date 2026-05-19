(function () {
    function updateTotal() {
        var inputs = document.querySelectorAll('[data-score]');
        var total = 0;
        inputs.forEach(function (el) {
            var val = parseFloat(el.value) || 0;
            var max = parseFloat(el.dataset.max) || 0;
            total += Math.min(Math.max(val, 0), max);
        });
        var display = document.getElementById('total-display');
        if (display) {
            display.textContent = total.toFixed(1).replace('.', ',');
        }
    }
    document.querySelectorAll('[data-score]').forEach(function (el) {
        el.addEventListener('input', updateTotal);
    });
    updateTotal();
}());
