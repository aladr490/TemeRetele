from __future__ import annotations

import json
import socket
from typing import Any, Dict


class ProtocolError(ValueError):
    pass


def send_json(sock: socket.socket, message: Dict[str, Any]) -> None:
    """
    Trimite un mesaj JSON terminat cu newline.

    Protocolul folosit este JSON Lines:
    fiecare mesaj este un obiect JSON pe o singura linie.
    """
    data = json.dumps(message, ensure_ascii=False) + "\n"
    sock.sendall(data.encode("utf-8"))


def parse_json_line(line: str) -> Dict[str, Any]:
    """
    Parseaza o linie JSON primita de pe socket.
    Ridica ProtocolError daca mesajul nu este valid.
    """
    try:
        obj = json.loads(line)
    except json.JSONDecodeError as exc:
        raise ProtocolError(f"JSON invalid: {exc.msg}") from exc

    if not isinstance(obj, dict):
        raise ProtocolError("Mesajul trebuie sa fie un obiect JSON.")

    return obj