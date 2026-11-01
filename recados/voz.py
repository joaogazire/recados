"""Ideia por voz: grava (pw-record), transcreve (Whisper local) e resume (DeepSeek) numa nota."""
from __future__ import annotations

import os
import signal
import subprocess
import time
from pathlib import Path
from typing import Callable

from recados import resumir

VENV_PY = Path.home() / ".local/share/recados/voz-venv/bin/python"
RAIZ = Path(__file__).resolve().parent.parent
MAX_LINHAS = 15
_PROMPT = (
    "Você recebe a transcrição de uma ideia falada em português. Escreva uma nota curta em Markdown: "
    "a primeira linha é '# ' + um título de até 6 palavras; depois de 1 a 5 tópicos com '- ', "
    "usando '- [ ] ' quando for uma tarefa a fazer. Use só o que foi dito, sem inventar nada. "
    "Responda só com o Markdown."
)


def limpar_md(resposta: str) -> str | None:
    linhas = [l.rstrip() for l in resposta.strip().splitlines() if not l.strip().startswith("```")]
    linhas = [l for l in linhas if l.strip()][:MAX_LINHAS]
    if not linhas:
        return None
    if not linhas[0].startswith("# "):
        linhas[0] = "# " + linhas[0].lstrip("# ").strip()
    return "\n".join(linhas)


def pedir_deepseek(transcricao: str) -> str:
    return resumir.conversar(_PROMPT, transcricao, max_tokens=300, limite=12000)


def transcrever_local(wav: str) -> str:
    env = {**os.environ, "PYTHONPATH": str(RAIZ)}
    r = subprocess.run([str(VENV_PY), "-m", "recados.transcrever", wav], capture_output=True,
                       text=True, timeout=600, env=env)
    if r.returncode != 0:
        raise RuntimeError(f"transcrição falhou: {r.stderr[-300:]}")
    return r.stdout.strip()


def iniciar_ao_vivo(wav: Path) -> subprocess.Popen:
    """Processo do Whisper que vai transcrevendo o .wav enquanto ele cresce (ver recados/ao_vivo.py)."""
    env = {**os.environ, "PYTHONPATH": str(RAIZ)}
    return subprocess.Popen([str(VENV_PY), "-m", "recados.ao_vivo", str(wav)], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, env=env)


def processar(wav: str, transcrever: Callable[[str], str] = transcrever_local,
              pedir: Callable[[str], str] = pedir_deepseek) -> str | None:
    """Texto da nota (resumo + transcrição), ou None se não houve fala."""
    return montar_nota(transcrever(wav), pedir)


def montar_nota(fala: str, pedir: Callable[[str], str] = pedir_deepseek) -> str | None:
    fala = " ".join(fala.split())
    if not fala:
        return None
    try:
        resumo = limpar_md(pedir(fala))
    except Exception:  # sem internet/proxy: fica só a transcrição
        resumo = None
    return f"{resumo or '# Ideia por voz'}\n\n---\nTranscrição: {fala}"


class Gravador:
    """pw-record em mono 16 kHz (o que o Whisper usa)."""

    def __init__(self):
        self._proc: subprocess.Popen | None = None

    def iniciar(self, caminho: Path) -> None:
        self._proc = subprocess.Popen(["pw-record", "--rate", "16000", "--channels", "1", "--format", "s16", str(caminho)],
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def parar(self) -> None:
        if self._proc is None:
            return
        self._proc.send_signal(signal.SIGINT)  # SIGINT fecha o .wav direito
        try:
            self._proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self._proc.kill()
        self._proc = None


def limpar_flag(pasta: Path) -> None:
    (Path(pasta) / "gravando").unlink(missing_ok=True)


class Voz:
    """Liga/desliga a gravação. O arquivo 'gravando' avisa a extensão (ícone vermelho)."""

    def __init__(self, gravador, pasta: Path):
        self.gravador = gravador
        self.pasta = Path(pasta)
        self.ultimo_audio: Path | None = None
        self.gravando = False

    def alternar(self) -> str:
        flag = self.pasta / "gravando"
        if self.gravando:
            self.gravador.parar()
            flag.unlink(missing_ok=True)
            self.gravando = False
            return "parado"
        self.pasta.mkdir(parents=True, exist_ok=True)
        self.ultimo_audio = self.pasta / f"voz-{int(time.time())}.wav"
        self.gravador.iniciar(self.ultimo_audio)
        flag.touch()
        self.gravando = True
        return "gravando"


