"""Lembretes do Post-it no Google Agenda (calendário próprio "Post-it").

Reaproveita o OAuth do Agenda Esportiva (~/.config/agenda-esportiva/token.json, escopo calendar),
só lendo: o access token renovado fica na memória, o arquivo não é alterado.
Só mexe em eventos que ele mesmo criou, no calendário dele.
"""
from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

from recados.lembretes import lembretes_do_repo
from recados.notas import Repositorio

NOME_CALENDARIO = "Post-it"
DURACAO = timedelta(minutes=30)
API = "https://www.googleapis.com/calendar/v3"
TOKEN_PADRAO = Path.home() / ".config/agenda-esportiva/token.json"
_TOKEN_URI = "https://oauth2.googleapis.com/token"


class ClienteGoogle:
    def __init__(self, token: dict):
        self._t = token
        self._acesso, self._expira = None, 0.0

    def _token(self) -> str:
        if self._acesso and time.time() < self._expira - 60:
            return self._acesso
        corpo = urllib.parse.urlencode({
            "client_id": self._t["client_id"], "client_secret": self._t["client_secret"],
            "refresh_token": self._t["refresh_token"], "grant_type": "refresh_token"}).encode()
        with urllib.request.urlopen(urllib.request.Request(_TOKEN_URI, data=corpo), timeout=20) as r:
            d = json.loads(r.read(64 * 1024))
        self._acesso, self._expira = d["access_token"], time.time() + float(d.get("expires_in", 3600))
        return self._acesso

    def _req(self, metodo: str, caminho: str, corpo: dict | None = None) -> dict:
        dados = json.dumps(corpo).encode() if corpo is not None else None
        req = urllib.request.Request(API + caminho, data=dados, method=metodo, headers={
            "Authorization": f"Bearer {self._token()}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as r:
            txt = r.read(1024 * 1024)
        return json.loads(txt) if txt else {}

    def criar_calendario(self, nome: str) -> str:
        return self._req("POST", "/calendars", {"summary": nome})["id"]

    def inserir(self, cal: str, evento: dict) -> str:
        return self._req("POST", f"/calendars/{urllib.parse.quote(cal)}/events", evento)["id"]

    def atualizar(self, cal: str, eid: str, evento: dict) -> None:
        self._req("PATCH", f"/calendars/{urllib.parse.quote(cal)}/events/{urllib.parse.quote(eid)}", evento)

    def apagar(self, cal: str, eid: str) -> None:
        try:
            self._req("DELETE", f"/calendars/{urllib.parse.quote(cal)}/events/{urllib.parse.quote(eid)}")
        except urllib.error.HTTPError as e:
            if e.code not in (404, 410):  # já apagado no Google: tudo bem
                raise


def cliente_do_token(caminho: Path = TOKEN_PADRAO) -> ClienteGoogle | None:
    try:
        t = json.loads(Path(caminho).read_text())
    except (OSError, ValueError):
        return None
    if not all(isinstance(t.get(k), str) for k in ("client_id", "client_secret", "refresh_token")):
        return None
    return ClienteGoogle(t)


def _ler_estado(caminho: Path) -> dict:
    try:
        d = json.loads(Path(caminho).read_text())
        if isinstance(d, dict) and isinstance(d.get("eventos", {}), dict):
            return {"calendario": d.get("calendario"), "eventos": d.get("eventos", {})}
    except (OSError, ValueError):
        pass
    return {"calendario": None, "eventos": {}}


def _gravar_estado(caminho: Path, estado: dict) -> None:
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    tmp = caminho.with_suffix(".tmp")
    tmp.write_text(json.dumps(estado, ensure_ascii=False))
    tmp.replace(caminho)


def desejados(repo: Repositorio, agora: datetime) -> dict[str, dict]:
    fuso = datetime.now().astimezone().tzinfo
    saida, vistos = {}, {}
    for nota, l in lembretes_do_repo(repo, agora):
        base = f"{nota.id}:{hashlib.sha256(l.titulo.encode()).hexdigest()[:10]}"
        vistos[base] = vistos.get(base, 0) + 1  # mesmo título 2x na nota: chaves diferentes
        if l.feito or l.quando < agora - timedelta(hours=1):
            continue
        k = base if vistos[base] == 1 else f"{base}:{vistos[base]}"
        ini = l.quando.replace(tzinfo=fuso)
        saida[k] = {
            "summary": l.titulo,
            "description": f"Lembrete do Post-it {nota.id}",
            "start": {"dateTime": ini.isoformat()},
            "end": {"dateTime": (ini + DURACAO).isoformat()},
        }
    return saida


def _assin(evento: dict) -> str:
    return hashlib.sha256(json.dumps(evento, sort_keys=True).encode()).hexdigest()[:16]


def sincronizar(repo: Repositorio, cliente, caminho_estado: Path, agora: datetime) -> None:
    """Deixa o calendário Post-it igual aos lembretes. Grava o estado a cada passo (falha no meio não duplica)."""
    estado = _ler_estado(caminho_estado)
    querer = desejados(repo, agora)
    feitos = estado["eventos"]
    if not querer and not feitos:
        return
    if not estado["calendario"]:
        estado["calendario"] = cliente.criar_calendario(NOME_CALENDARIO)
        _gravar_estado(caminho_estado, estado)
    cal = estado["calendario"]
    for k, ev in querer.items():
        a = _assin(ev)
        if k not in feitos:
            feitos[k] = {"id": cliente.inserir(cal, ev), "assin": a, "inicio": ev["start"]["dateTime"]}
        elif feitos[k].get("assin") != a:
            cliente.atualizar(cal, feitos[k]["id"], ev)
            feitos[k].update(assin=a, inicio=ev["start"]["dateTime"])
        else:
            continue
        _gravar_estado(caminho_estado, estado)
    limite = (agora - timedelta(hours=1)).replace(tzinfo=datetime.now().astimezone().tzinfo)
    for k in [k for k in feitos if k not in querer]:
        try:
            passou = datetime.fromisoformat(feitos[k].get("inicio", "")) < limite
        except ValueError:
            passou = False
        if not passou:  # removido, marcado ou mudou: apaga; já aconteceu: fica no Google como histórico
            cliente.apagar(cal, feitos[k]["id"])
        del feitos[k]
        _gravar_estado(caminho_estado, estado)
