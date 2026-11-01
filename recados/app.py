"""Aplicativo Recados: abre uma janela por nota."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk  # noqa: E402

from recados.janela import JanelaNota  # noqa: E402
from recados.notas import Repositorio  # noqa: E402
from recados.resumo import resumo  # noqa: E402

APP_ID = "io.github.joaowgf.Recados"


def caminho_banco() -> Path:
    base = os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share"
    return Path(os.environ.get("RECADOS_BANCO") or Path(base) / "recados" / "recados.db")


class App(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        self.repo: Repositorio | None = None
        self.add_main_option("nova", ord("n"), 0, 0, "Criar uma nota nova", None)
        self.add_main_option("abrir", ord("a"), 0, GLib.OptionArg.INT, "Abrir a nota pelo id", "ID")
        self.add_main_option("listar", ord("l"), 0, 0, "Imprimir as notas em JSON e sair", None)

    def do_handle_local_options(self, opcoes):
        if opcoes.contains("listar"):
            repo = Repositorio(caminho_banco())
            try:
                print(json.dumps(resumo(repo), ensure_ascii=False))
            finally:
                repo.fechar()
            return 0
        return -1

    def do_startup(self):
        Adw.Application.do_startup(self)
        Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
        css = Gtk.CssProvider()
        css.load_from_path(str(Path(__file__).with_name("estilo.css")))
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        self.repo = Repositorio(caminho_banco())
        self.repo.purgar_apagadas()  # o desfazer só vale enquanto o app está aberto
        acao = Gio.SimpleAction.new("nova", None)
        acao.connect("activate", lambda *_: self.nova_nota())
        self.add_action(acao)
        self.set_accels_for_action("app.nova", ["<Control>n"])

    def do_command_line(self, linha):
        opcoes = linha.get_options_dict().end().unpack()
        if opcoes.get("nova"):
            self.nova_nota()
        elif "abrir" in opcoes:
            if not self.abrir_nota(opcoes["abrir"]):
                self.activate()
        else:
            self.activate()
        return 0

    def do_activate(self):
        janelas = self.get_windows()
        if janelas:
            for j in janelas:
                j.present()
            return
        notas = self.repo.listar()
        if not notas:
            self.nova_nota()
        for n in notas:
            JanelaNota(self.repo, n, self).present()

    def abrir_nota(self, id_: int) -> bool:
        """Traz a nota para a frente (reabre se estiver fechada). Devolve se achou."""
        for j in self.get_windows():
            if getattr(j, "nota", None) and j.nota.id == id_:
                j.present()
                return True
        nota = self.repo.obter(id_)
        if nota is None:
            return False
        JanelaNota(self.repo, nota, self).present()
        return True

    def nova_nota(self):
        if not self.get_windows():
            for n in self.repo.listar():
                JanelaNota(self.repo, n, self).present()
        j = JanelaNota(self.repo, self.repo.criar(), self)
        j.present()
        j.editor.grab_focus()

    def do_shutdown(self):
        for j in self.get_windows():
            j.salvar_agora()
        self.repo.fechar()
        Adw.Application.do_shutdown(self)


def main() -> int:
    return App().run(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
