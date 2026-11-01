"""Transcrição ao vivo enquanto grava.

Roda como processo próprio no venv da voz (o modelo carrega uma vez só):
    voz-venv/bin/python -m recados.ao_vivo gravacao.wav
A cada ~2 s lê o .wav que o pw-record está escrevendo e imprime uma linha JSON
{"tipo": "parcial", "texto": ...}. Quando o stdin fecha (gravação parou), faz a última
passada e imprime {"tipo": "final", ...}.

O áudio é cortado em blocos de 10 s: bloco fechado é transcrito uma vez; só a cauda
(o trecho que ainda está crescendo) é refeita a cada passada.
"""
from __future__ import annotations

import json
import select
import sys
from pathlib import Path
from typing import Callable

import numpy as np

TAXA = 16000
CABECALHO_WAV = 44
CAUDA_MINIMA_S = 0.5
INTERVALO_S = 2.0


def ler_pcm(caminho: Path) -> np.ndarray:
    """Áudio mono s16 de um .wav que ainda pode estar sendo gravado (tamanho no cabeçalho ainda 0)."""
    try:
        bruto = Path(caminho).read_bytes()[CABECALHO_WAV:]
    except OSError:
        return np.zeros(0, dtype=np.float32)
    bruto = bruto[: len(bruto) - len(bruto) % 2]
    return np.frombuffer(bruto, dtype=np.int16).astype(np.float32) / 32768.0


class Blocos:
    def __init__(self, transcrever: Callable[[np.ndarray], str], segundos: int = 10):
        self.transcrever = transcrever
        self.tam = segundos * TAXA
        self.feitos: list[str] = []
        self._cauda_len = -1
        self._cauda_txt = ""

    def texto(self, audio: np.ndarray) -> str:
        cheios = len(audio) // self.tam
        for i in range(len(self.feitos), cheios):
            self.feitos.append(self.transcrever(audio[i * self.tam:(i + 1) * self.tam]).strip())
        cauda = audio[cheios * self.tam:] if cheios >= len(self.feitos) else audio[:0]
        if len(cauda) < CAUDA_MINIMA_S * TAXA:
            self._cauda_len, self._cauda_txt = len(cauda), ""
        elif len(cauda) != self._cauda_len:
            self._cauda_len, self._cauda_txt = len(cauda), self.transcrever(cauda).strip()
        return " ".join(t for t in [*self.feitos, self._cauda_txt] if t)


def linha_evento(tipo: str, texto: str) -> str:
    return json.dumps({"tipo": tipo, "texto": texto}, ensure_ascii=False)


def ler_evento(linha: str) -> tuple[str, str] | None:
    try:
        d = json.loads(linha)
    except ValueError:
        return None
    if not isinstance(d, dict) or d.get("tipo") not in ("parcial", "final") or not isinstance(d.get("texto"), str):
        return None
    return d["tipo"], d["texto"]


def main() -> int:
    from faster_whisper import WhisperModel

    modelo = WhisperModel("small", device="cpu", compute_type="int8")

    def transcrever(audio: np.ndarray) -> str:
        segmentos, _ = modelo.transcribe(audio, language="pt", vad_filter=True)
        return " ".join(s.text.strip() for s in segmentos)

    caminho, blocos, ultimo = Path(sys.argv[1]), Blocos(transcrever), None
    while True:
        pronto, _, _ = select.select([sys.stdin], [], [], INTERVALO_S)
        acabou = bool(pronto) and sys.stdin.readline() == ""  # EOF: o app parou a gravação
        texto = blocos.texto(ler_pcm(caminho))
        if acabou:
            print(linha_evento("final", texto), flush=True)
            return 0
        if texto != ultimo:
            print(linha_evento("parcial", texto), flush=True)
            ultimo = texto


if __name__ == "__main__":
    raise SystemExit(main())
