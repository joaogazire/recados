"""Aplicativo Recados: abre uma janela por nota."""
from __future__ import annotations

import json
import threading
from datetime import date, datetime
import os
import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk  # noqa: E402

from recados.janela import JanelaNota  # noqa: E402
from recados.notas import FONTES, TAMANHOS, Repositorio, rascunho  # noqa: E402
from recados import fixadas, preferencias  # noqa: E402
from recados.captura import achar_inbox, acrescentar_item, capturar  # noqa: E402
from recados.captura_janela import JanelaCaptura  # noqa: E402
from recados.dia import nota_de_hoje, titulo_do_dia  # noqa: E402
from recados.resumo import resumo  # noqa: E402
from recados import gagenda, resumir, voz  # noqa: E402
from recados.lembretes import Avisador  # noqa: E402

APP_ID = "io.github.joaowgf.Recados"


def caminho_banco() -> Path:
    base = os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share"
    return Path(os.environ.get("RECADOS_BANCO") or Path(base) / "recados" / "recados.db")


class App(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        self.repo: Repositorio | None = None
        self._rascunho_dia = None  # janela da nota do dia ainda não salva (evita abrir duas)
        self._voz = None
        self._voz_limite = 0  # timer que para a gravação depois de MAX_GRAVACAO_S
        self.add_main_option("nova", ord("n"), 0, 0, "Criar uma nota nova", None)
        self.add_main_option("abrir", ord("a"), 0, GLib.OptionArg.INT, "Abrir a nota pelo id", "ID")
        self.add_main_option("sessao", 0, 0, 0, "Início de sessão: abre as notas só se a preferência mandar", None)
        self.add_main_option("capturar", ord("c"), 0, 0, "Captura rápida: uma linha para a Inbox", None)
        self.add_main_option("reabrir", 0, 0, GLib.OptionArg.INT, "Reabrir nota concluída/cancelada/arquivada", "ID")
        self.add_main_option("voz", ord("v"), 0, 0, "Gravar uma ideia falada (de novo para parar)", None)
        self.add_main_option("hoje", ord("d"), 0, 0, "Abrir (ou criar) a nota do dia", None)
        self.add_main_option("preferencias", ord("p"), 0, 0, "Abrir as preferências", None)
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
        fixadas.gravar(self.repo)
        voz.limpar_flag(caminho_banco().parent / "voz")  # sobra de um app que fechou gravando
        self._resumindo = False
        self._resumir()
        GLib.timeout_add_seconds(60, self._resumir)
        dados = caminho_banco().parent
        self._avisador = Avisador(dados / "avisados.json", self._avisar)
        self._agenda_estado = dados / "agenda.json"
        self._sincronizando = False
        GLib.timeout_add_seconds(30, self._checar_lembretes)
        self._checar_lembretes()
        acao = Gio.SimpleAction.new("abrir", GLib.VariantType.new("i"))
        acao.connect("activate", lambda _a, p: self.abrir_nota(p.get_int32()))
        self.add_action(acao)
        acao = Gio.SimpleAction.new("nova", None)
        acao.connect("activate", lambda *_: self.nova_nota())
        self.add_action(acao)
        acao = Gio.SimpleAction.new("hoje", None)
        acao.connect("activate", lambda *_: self.nota_do_dia())
        self.add_action(acao)
        self.set_accels_for_action("app.hoje", ["<Control>d"])
        acao = Gio.SimpleAction.new("preferencias", None)
        acao.connect("activate", lambda *_: self.mostrar_preferencias())
        self.add_action(acao)
        self.set_accels_for_action("app.nova", ["<Control>n"])

    def do_command_line(self, linha):
        opcoes = linha.get_options_dict().end().unpack()
        if opcoes.get("voz"):
            self.alternar_voz()
        elif opcoes.get("capturar"):
            self.mostrar_captura()
        elif opcoes.get("hoje"):
            self.nota_do_dia()
        elif opcoes.get("preferencias"):
            self.mostrar_preferencias()
        elif opcoes.get("sessao"):
            if preferencias.carregar()["abrir_na_sessao"]:
                self.activate()
        elif opcoes.get("nova"):
            self.nova_nota()
        elif "reabrir" in opcoes:
            if not self.reabrir_nota(opcoes["reabrir"]):
                self.activate()
        elif "abrir" in opcoes:
            if not self.abrir_nota(opcoes["abrir"]):
                self.activate()
        else:
            self.activate()
        return 0

    def _notas_abertas(self) -> dict:
        return {j.nota.id: j for j in self.get_windows() if isinstance(j, JanelaNota) and j.nota.id is not None}

    def do_activate(self):
        """Mostra todas as notas: traz as abertas para a frente e reabre as fechadas."""
        abertas = self._notas_abertas()
        notas = self.repo.listar()
        if not notas and not abertas:
            self.nova_nota()
        for n in notas:
            (abertas.get(n.id) or self._janela(n)).present()

    def abrir_nota(self, id_: int) -> bool:
        """Traz a nota para a frente (reabre se estiver fechada). Devolve se achou."""
        if (j := self._notas_abertas().get(id_)):
            j.present()
            return True
        nota = self.repo.obter(id_)
        if nota is None:
            return False
        self._janela(nota).present()
        return True

    def reabrir_nota(self, id_: int) -> bool:
        """Volta a nota para ativa e mostra."""
        try:
            self.repo.mudar_estado(id_, "ativa")
        except KeyError:
            return False
        return self.abrir_nota(id_)

    MAX_GRAVACAO_S = 300

    def alternar_voz(self):
        """1º toque grava; 2º para, transcreve (Whisper local) e resume (DeepSeek) numa nota verde."""
        if self._voz is None:
            self._voz = voz.Voz(voz.Gravador(), caminho_banco().parent / "voz")
        estado = self._voz.alternar()
        if estado == "gravando":
            self.hold()  # mantém o app vivo sem janela enquanto grava
            n = Gio.Notification.new("🎙 Gravando ideia…")
            n.set_body("Aperte Super+Alt+V de novo para parar (máx. 5 min).")
            self.send_notification("voz", n)
            self._voz_limite = GLib.timeout_add_seconds(self.MAX_GRAVACAO_S, self._voz_tempo_esgotado)
            return
        if self._voz_limite:
            GLib.source_remove(self._voz_limite)
            self._voz_limite = 0
        self.withdraw_notification("voz")
        audio = self._voz.ultimo_audio

        def trabalho():
            try:
                texto = voz.processar(str(audio))
            except Exception as e:
                print(f"recados: voz falhou: {e}", file=sys.stderr)
                texto = None
            finally:
                audio.unlink(missing_ok=True)
            GLib.idle_add(self._fim_voz, texto)

        threading.Thread(target=trabalho, daemon=True).start()

    def _voz_tempo_esgotado(self):
        self._voz_limite = 0
        if self._voz is not None and self._voz.gravando:
            self.alternar_voz()
        return GLib.SOURCE_REMOVE

    def _fim_voz(self, texto):
        try:
            if texto:
                self._nota_de_voz(texto)
            else:
                n = Gio.Notification.new("Não entendi a gravação")
                n.set_body("Nenhuma fala reconhecida. Tente de novo mais perto do microfone.")
                self.send_notification("voz", n)
        finally:
            self.release()
        return GLib.SOURCE_REMOVE

    def _nota_de_voz(self, texto: str):
        nota = self.repo.criar(texto, "verde")
        self.abrir_nota(nota.id)

    def mostrar_captura(self):
        JanelaCaptura(self.capturar, self).present()

    def capturar(self, item: str):
        """Acrescenta '- [ ] item' na Inbox; se a Inbox está aberta, passa pela janela para não perder edição."""
        inbox = achar_inbox(self.repo)
        j = self._notas_abertas().get(inbox.id) if inbox else None
        if j is None:
            capturar(self.repo, item)
            return
        j.salvar_agora()
        j._trocar_texto(acrescentar_item(j.texto(), item))
        j.salvar_agora()
        if j.em_leitura:
            j._montar_leitura()

    def nota_do_dia(self):
        """Traz a nota de hoje; se não existe, abre um rascunho com o título da data."""
        if (n := nota_de_hoje(self.repo)) is not None:
            self.abrir_nota(n.id)
            return
        if self._rascunho_dia is not None:
            self._rascunho_dia.present()
            return
        p = preferencias.carregar()
        largura, altura = TAMANHOS[p["tamanho"]]
        j = self._janela(rascunho(fonte=p["fonte"], largura=largura, altura=altura))
        self._rascunho_dia = j
        j.connect("destroy", lambda *_: setattr(self, "_rascunho_dia", None))
        j.modelo = titulo_do_dia(date.today()) + "\n- [ ] "
        j.buffer.set_text(j.modelo)
        j.buffer.place_cursor(j.buffer.get_end_iter())
        j.present()
        j.editor.grab_focus()

    def nova_nota(self):
        if not self._notas_abertas():
            for n in self.repo.listar():
                self._janela(n).present()
        p = preferencias.carregar()
        largura, altura = TAMANHOS[p["tamanho"]]
        nota = rascunho(fonte=p["fonte"], largura=largura, altura=altura)
        j = self._janela(nota)
        j.present()
        j.editor.grab_focus()

    def _avisar(self, nota, lembrete):
        n = Gio.Notification.new(f"⏰ {lembrete.titulo}")
        n.set_body(f"{lembrete.quando:%d/%m %H:%M} · Post-it {nota.id}")
        n.set_default_action_and_target_value("app.abrir", GLib.Variant.new_int32(nota.id))
        self.send_notification(f"lembrete-{nota.id}-{lembrete.linha}", n)

    def _checar_lembretes(self):
        """A cada 30 s: avisa lembretes vencidos e, numa thread, espelha no Google Agenda."""
        try:
            self._avisador.checar(self.repo, datetime.now())
        except Exception as e:
            print(f"recados: aviso falhou: {e}", file=sys.stderr)
        if getattr(self, "_cliente_google", None) is None:
            self._cliente_google = gagenda.cliente_do_token()  # guarda o access token entre rodadas
        cliente = self._cliente_google
        if not self._sincronizando and cliente is not None:
            self._sincronizando = True

            def trabalho():
                repo = None
                try:
                    repo = Repositorio(caminho_banco())
                    gagenda.sincronizar(repo, cliente, self._agenda_estado, datetime.now())
                except Exception as e:  # sem internet, token vencido: tenta de novo em 30 s
                    print(f"recados: Google Agenda falhou: {e}", file=sys.stderr)
                finally:
                    if repo is not None:
                        repo.fechar()
                    self._sincronizando = False

            threading.Thread(target=trabalho, daemon=True).start()
        return GLib.SOURCE_CONTINUE

    def _resumir(self):
        """Resume (DeepSeek) as notas que mudaram, numa thread com conexão própria ao banco."""
        if not self._resumindo:
            self._resumindo = True

            def trabalho():
                repo = None
                try:
                    repo = Repositorio(caminho_banco())
                    resumir.atualizar(repo)
                except Exception as e:  # banco ocupado etc.: tenta de novo daqui a 60 s
                    print(f"recados: resumo falhou: {e}", file=sys.stderr)
                finally:
                    if repo is not None:
                        repo.fechar()
                    self._resumindo = False

            threading.Thread(target=trabalho, daemon=True).start()
        return GLib.SOURCE_CONTINUE

    def _janela(self, nota):
        return JanelaNota(self.repo, nota, self, ler=preferencias.carregar()["abrir_em"] == "leitura")

    def mostrar_preferencias(self):
        p = preferencias.carregar()
        nomes_fonte = {"sans": "Sans", "serifa": "Serifa", "mono": "Mono"}
        tamanhos = list(TAMANHOS)
        modos = [("leitura", "Leitura (Markdown formatado)"), ("edicao", "Edição (texto Markdown)")]

        def combo(titulo, rotulos, atual):
            linha = Adw.ComboRow(title=titulo, model=Gtk.StringList.new(rotulos))
            linha.set_selected(atual)
            return linha

        fonte = combo("Fonte das notas novas", [nomes_fonte[f] for f in FONTES], FONTES.index(p["fonte"]))
        tamanho = combo("Tamanho das notas novas",
                        ["%s — %d × %d" % (t, *TAMANHOS[t]) for t in tamanhos], tamanhos.index(p["tamanho"]))
        modo = combo("Notas abrem em", [r for _, r in modos], [m for m, _ in modos].index(p["abrir_em"]))
        sessao = Adw.SwitchRow(title="Mostrar as notas ao iniciar a sessão", active=p["abrir_na_sessao"])

        def gravar(*_):
            preferencias.salvar(None, {
                "fonte": FONTES[fonte.get_selected()],
                "tamanho": tamanhos[tamanho.get_selected()],
                "abrir_em": modos[modo.get_selected()][0],
                "abrir_na_sessao": sessao.get_active(),
            })

        for linha in (fonte, tamanho, modo):
            linha.connect("notify::selected", gravar)
        sessao.connect("notify::active", gravar)

        grupo_novas = Adw.PreferencesGroup(title="Notas")
        for linha in (fonte, tamanho, modo):
            grupo_novas.add(linha)
        grupo_sessao = Adw.PreferencesGroup(title="Sessão")
        grupo_sessao.add(sessao)
        pagina = Adw.PreferencesPage()
        pagina.add(grupo_novas)
        pagina.add(grupo_sessao)
        janela = Adw.PreferencesWindow(application=self, title="Preferências do Post-it", modal=False)
        janela.add(pagina)
        janela.present()

    def do_shutdown(self):
        if self._voz is not None and self._voz.gravando:
            self._voz.alternar()  # para o pw-record e apaga a flag
        for j in self.get_windows():
            if isinstance(j, JanelaNota):
                j.salvar_agora()
        self.repo.fechar()
        Adw.Application.do_shutdown(self)


def main() -> int:
    return App().run(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
