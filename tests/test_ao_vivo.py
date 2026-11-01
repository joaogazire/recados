import json
import struct
import wave

import pytest

from recados.ao_vivo import Blocos, ler_pcm, linha_evento, ler_evento

TAXA = 16000


def _wav(caminho, segundos, cabecalho_completo=True):
    with wave.open(str(caminho), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(TAXA)
        w.writeframes(b"\x01\x00" * int(TAXA * segundos))


def test_ler_pcm_de_wav_ainda_sendo_gravado(tmp_path):
    p = tmp_path / "a.wav"
    _wav(p, 1.5)
    dados = bytearray(p.read_bytes())
    dados[40:44] = struct.pack("<I", 0)  # pw-record só preenche o tamanho no fim
    p.write_bytes(bytes(dados))
    audio = ler_pcm(p)
    assert len(audio) == int(TAXA * 1.5)


def test_ler_pcm_arquivo_ainda_vazio(tmp_path):
    p = tmp_path / "a.wav"
    p.write_bytes(b"RIFF")
    assert len(ler_pcm(p)) == 0
    assert len(ler_pcm(tmp_path / "nao-existe.wav")) == 0


def test_blocos_transcreve_cada_bloco_fechado_uma_vez():
    import numpy as np
    chamadas = []

    def falso(audio):
        chamadas.append(len(audio))
        return f"<{len(audio) // TAXA}s>"

    b = Blocos(falso, segundos=10)
    assert b.texto(np.zeros(TAXA * 4, dtype=np.float32)) == "<4s>"
    assert b.texto(np.zeros(TAXA * 13, dtype=np.float32)) == "<10s> <3s>"
    assert b.texto(np.zeros(TAXA * 15, dtype=np.float32)) == "<10s> <5s>"
    assert chamadas.count(TAXA * 10) == 1  # bloco fechado não é refeito
    assert b.texto(np.zeros(TAXA * 0, dtype=np.float32)) == "<10s>"  # nada novo: mantém


def test_blocos_ignora_cauda_curta_demais():
    import numpy as np
    b = Blocos(lambda a: "x", segundos=10)
    assert b.texto(np.zeros(TAXA // 4, dtype=np.float32)) == ""  # 0,25 s: nem tenta


def test_protocolo_de_eventos():
    assert json.loads(linha_evento("parcial", "oi")) == {"tipo": "parcial", "texto": "oi"}
    assert ler_evento(linha_evento("final", "tchau")) == ("final", "tchau")
    assert ler_evento("lixo") is None
    assert ler_evento('{"tipo": "outro", "texto": "x"}') is None
