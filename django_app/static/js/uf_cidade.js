// static/js/uf_cidade.js
// Banco de Talentos — Polo de Inovação IFG
//
// Troca a lista de cidades quando o usuário muda o estado, no formulário de
// Meu Cadastro. Os municípios vêm de /static/js/municipios.json — o MESMO
// arquivo que o Python lê para montar as opções do HTML (ver
// apps/usuarios/municipios.py), para as duas listas nunca discordarem.
//
// O arquivo é externo porque a CSP de produção é script-src 'self': <script>
// inline é bloqueado.
//
// Sem JavaScript o formulário continua funcionando: o servidor já renderiza as
// cidades do estado que está salvo no cadastro. O usuário só precisa de dois
// passos (escolher o estado, salvar, escolher a cidade).
(function () {
    var selectUf = document.getElementById('id_uf');
    var selectCidade = document.getElementById('id_cidade');
    if (!selectUf || !selectCidade) return;

    // Guarda a cidade que veio do servidor para reselecionar, se ela existir
    // na lista do estado escolhido (caso o usuário volte ao estado original).
    var cidadeSalva = selectCidade.value;
    var municipios = null;

    function preencher(uf) {
        var lista = (municipios && municipios[uf]) || [];
        selectCidade.innerHTML = '';

        var vazio = document.createElement('option');
        vazio.value = '';
        vazio.textContent = lista.length ? 'Selecione a cidade' : 'Selecione primeiro o estado';
        selectCidade.appendChild(vazio);

        lista.forEach(function (nome) {
            var opcao = document.createElement('option');
            opcao.value = nome;
            opcao.textContent = nome;
            if (nome === cidadeSalva) opcao.selected = true;
            selectCidade.appendChild(opcao);
        });
    }

    selectUf.addEventListener('change', function () {
        var uf = selectUf.value;
        if (municipios) {
            preencher(uf);
            return;
        }
        // Busca uma única vez, no primeiro uso.
        fetch(selectCidade.dataset.municipiosUrl)
            .then(function (resposta) { return resposta.json(); })
            .then(function (dados) {
                municipios = dados;
                preencher(uf);
            })
            .catch(function () {
                // Falhou o download: deixa o select como o servidor mandou, em
                // vez de esvaziar a lista e impedir o usuário de salvar.
            });
    });
}());
