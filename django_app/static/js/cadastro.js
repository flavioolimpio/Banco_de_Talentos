// static/js/cadastro.js
// Banco de Talentos — Polo de Inovação IFG
//
// Na tela de Cadastro, o vínculo é escolhido no mesmo formulário que traz o
// consentimento de verificação em bases internas do IFG — que não se aplica a
// colaborador(a) externo(a). Este script esconde (e desmarca) a caixa quando o
// vínculo escolhido está em data-oculta-para-vinculo, e a mostra de novo nos
// demais casos.
//
// Arquivo externo por causa da CSP de produção (script-src 'self').
//
// É só conforto: quem decide é o servidor (CadastroUsuarioForm.clean). Sem
// JavaScript a caixa aparece para todos e o externo pode deixá-la em branco.
(function () {
    var selectVinculo = document.getElementById('id_vinculo');
    var campo = document.getElementById('campo-consentimento-bases');
    if (!selectVinculo || !campo) return;

    var ocultaPara = (campo.dataset.ocultaParaVinculo || '').split(' ');
    var caixa = campo.querySelector('input[type="checkbox"]');

    function atualizar() {
        var ocultar = ocultaPara.indexOf(selectVinculo.value) !== -1;
        // style.display, e não o atributo hidden: .check-row tem display:flex
        // no CSS, que venceria o [hidden] do navegador.
        campo.style.display = ocultar ? 'none' : '';
        if (ocultar && caixa) caixa.checked = false;
    }

    selectVinculo.addEventListener('change', atualizar);
    atualizar();
}());
