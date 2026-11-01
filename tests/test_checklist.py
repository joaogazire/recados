from recados.markdown import alternar_item, blocos, para_pango, realces


def test_alternar_item_marca_e_desmarca():
    t = "x\n- [ ] pão\n- [x] leite"
    t2 = alternar_item(t, 1)
    assert t2 == "x\n- [x] pão\n- [x] leite"
    assert alternar_item(t2, 2) == "x\n- [x] pão\n- [ ] leite"


def test_alternar_aceita_X_maiusculo_e_asterisco_e_indentacao():
    assert alternar_item("  * [X] a", 0) == "  * [ ] a"


def test_alternar_linha_sem_item_nao_muda():
    assert alternar_item("- a\n[ ] b", 0) == "- a\n[ ] b"
    assert alternar_item("- a", 5) == "- a"


def test_realce_da_caixa():
    t = "- [ ] a\n- [x] b"
    caixas = [(t[i:f], tag) for i, f, tag in realces(t) if tag.startswith("caixa")]
    assert caixas == [("[ ]", "caixa"), ("[x]", "caixa-marcada")]


def test_blocos_para_modo_leitura():
    t = "# Lista\n- [ ] pão\n- [x] leite\ntexto **forte**\n\n- solto"
    assert blocos(t) == [
        ("titulo", 1, "Lista", 0),
        ("item", False, "pão", 1),
        ("item", True, "leite", 2),
        ("paragrafo", 0, "texto **forte**", 3),
        ("vazio", 0, "", 4),
        ("lista", 0, "solto", 5),
    ]


def test_para_pango_escapa_e_formata():
    assert para_pango("a <b> & **c** *d* `e`") == (
        "a &lt;b&gt; &amp; <b>c</b> <i>d</i> <tt>e</tt>"
    )


def test_para_pango_link():
    assert para_pango("[x](https://a.b?c=1&d=2)") == '<a href="https://a.b?c=1&amp;d=2">x</a>'


def test_para_pango_link_nao_http_vira_texto():
    assert para_pango("[x](javascript:alert(1))") == "[x](javascript:alert(1))"
