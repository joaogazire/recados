import pytest

from recados import voz


def test_limpar_markdown_do_modelo():
    md = "```markdown\n# Ideia: app de livros\n- [ ] tracking de leitura\n- catálogo\n```"
    assert voz.limpar_md(md) == "# Ideia: app de livros\n- [ ] tracking de leitura\n- catálogo"
    assert voz.limpar_md("Título solto\n- a").startswith("# Título solto")
    assert voz.limpar_md("   ") is None


def test_processar_monta_nota_com_resumo_e_transcricao():
    texto = voz.processar("a.wav", transcrever=lambda w: "quero um app de livros com estante",
                          pedir=lambda t: "# App de livros\n- [ ] estante")
    assert texto.startswith("# App de livros\n- [ ] estante")
    assert texto.rstrip().endswith("quero um app de livros com estante")


def test_processar_sem_deepseek_guarda_transcricao():
    def quebra(t):
        raise OSError("offline")
    texto = voz.processar("a.wav", transcrever=lambda w: "ligar pro banco", pedir=quebra)
    assert texto.startswith("# Ideia por voz") and "ligar pro banco" in texto


def test_processar_fala_vazia():
    assert voz.processar("a.wav", transcrever=lambda w: "  ", pedir=lambda t: "x") is None


class GravadorFalso:
    def __init__(self):
        self.eventos = []

    def iniciar(self, caminho):
        self.eventos.append("iniciar")

    def parar(self):
        self.eventos.append("parar")


def test_alternar_grava_e_para(tmp_path):
    g = GravadorFalso()
    v = voz.Voz(g, tmp_path)
    assert v.alternar() == "gravando" and (tmp_path / "gravando").exists()
    assert v.alternar() == "parado" and not (tmp_path / "gravando").exists()
    assert g.eventos == ["iniciar", "parar"]
    assert v.ultimo_audio.parent == tmp_path


def test_limpar_flag_orfa(tmp_path):
    (tmp_path / "gravando").touch()
    voz.limpar_flag(tmp_path)
    assert not (tmp_path / "gravando").exists()
