"""Transcreve um .wav em pt-BR com faster-whisper (roda no venv da voz: ~/.local/share/recados/voz-venv).

Lê o .wav com a biblioteca padrão e entrega o áudio pronto ao Whisper: o PyAV que o
faster-whisper usaria não é compatível com esta versão.
"""
import sys
import wave

import numpy as np
from faster_whisper import WhisperModel

TAXA = 16000


def ler_wav(caminho: str) -> np.ndarray:
    with wave.open(caminho, "rb") as w:
        canais, largura, taxa = w.getnchannels(), w.getsampwidth(), w.getframerate()
        bruto = w.readframes(w.getnframes())
    if largura != 2:
        raise ValueError("esperava áudio de 16 bits")
    audio = np.frombuffer(bruto, dtype=np.int16).astype(np.float32) / 32768.0
    if canais > 1:
        audio = audio[: len(audio) - len(audio) % canais].reshape(-1, canais).mean(axis=1)
    if taxa != TAXA:  # reamostragem linear simples (a gravação já sai em 16 kHz)
        n = int(len(audio) * TAXA / taxa)
        audio = np.interp(np.linspace(0, len(audio) - 1, n), np.arange(len(audio)), audio).astype(np.float32)
    return audio


def main() -> int:
    modelo = WhisperModel("small", device="cpu", compute_type="int8")
    segmentos, _ = modelo.transcribe(ler_wav(sys.argv[1]), language="pt", vad_filter=True)
    print(" ".join(s.text.strip() for s in segmentos))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
