from recados.markdown import realces


def tags(texto):
    return [(texto[i:f], t) for i, f, t in realces(texto)]


def test_titulos_por_nivel():
    assert tags("# Um") == [("# Um", "titulo1")]
    assert tags("## Dois") == [("## Dois", "titulo2")]
    assert tags("### Três") == [("### Três", "titulo3")]


def test_hashtag_sem_espaco_nao_e_titulo():
    assert tags("#tag") == []


def test_negrito_italico_codigo():
    t = "a **b** c *d* e _f_ g `h`"
    assert ("**b**", "negrito") in tags(t)
    assert ("*d*", "italico") in tags(t)
    assert ("_f_", "italico") in tags(t)
    assert ("`h`", "codigo") in tags(t)


def test_negrito_nao_vira_italico():
    assert tags("**x**") == [("**x**", "negrito")]


def test_codigo_protege_conteudo():
    assert tags("`**x**`") == [("`**x**`", "codigo")]


def test_marcadores_de_lista():
    t = "- a\n* b\n1. c"
    assert [x for x in tags(t) if x[1] == "marcador"] == [("-", "marcador"), ("*", "marcador"), ("1.", "marcador")]


def test_link():
    assert ("[site](https://x.y)", "link") in tags("ver [site](https://x.y) já")


def test_offsets_em_caracteres_com_acento():
    t = "ção **sim**"
    ((i, f, tag),) = realces(t)
    assert t[i:f] == "**sim**" and tag == "negrito"


def test_titulo_em_linha_do_meio():
    t = "a\n## b\nc"
    assert tags(t) == [("## b", "titulo2")]


def test_realce_de_data():
    from recados.markdown import realces
    assert (6, 15, "data") in realces("ligar @02/11 9h")
