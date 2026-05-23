from __future__ import annotations

import argparse
import random
import socket
import string
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from protocol import ProtocolError, parse_json_line, send_json

Coord = Tuple[int, int] 


@dataclass(frozen=True)
class GameConfig:
    name: str
    grid: List[List[str]]
    heads: Dict[Coord, str]
    parts: Set[Coord]


@dataclass
class ClientSession:
    name: str
    sock: socket.socket
    address: Tuple[str, int]
    send_lock: threading.Lock = field(default_factory=threading.Lock)
    downed_heads: Set[str] = field(default_factory=set)

    def send(self, message: dict) -> bool:
        """Trimite sigur catre client. Returneaza False daca socket-ul a picat."""
        try:
            with self.send_lock:
                send_json(self.sock, message)
            return True
        except OSError:
            return False


class AvionaseServer:
    def __init__(self, host: str, port: int, config_dir: Path) -> None:
        self.host = host
        self.port = port
        self.config_dir = config_dir
        self.configs = self._load_configs(config_dir)
        if not self.configs:
            raise RuntimeError(f"Nu exista configuratii valide in {config_dir}")

        self.state_lock = threading.RLock()
        self.clients: Dict[str, ClientSession] = {}
        self.current_config: GameConfig = random.choice(self.configs)
        self.round_no = 1
        self.server_sock: Optional[socket.socket] = None

    @staticmethod
    def _load_configs(config_dir: Path) -> List[GameConfig]:
        configs: List[GameConfig] = []
        for path in sorted(config_dir.glob("*.txt")):
            try:
                configs.append(AvionaseServer._parse_config(path))
            except ValueError as exc:
                print(f"[WARN] Ignor {path.name}: {exc}")
        return configs

    @staticmethod
    def _parse_config(path: Path) -> GameConfig:
        raw_lines = path.read_text(encoding="utf-8").splitlines()
        lines = [line.strip().replace(" ", "") for line in raw_lines if line.strip() and not line.strip().startswith("#")]

        if len(lines) != 10:
            raise ValueError("configuratia trebuie sa aiba exact 10 linii utile")

        grid: List[List[str]] = []
        heads: Dict[Coord, str] = {}
        parts: Set[Coord] = set()
        seen_head_letters: Set[str] = set()

        for r, line in enumerate(lines):
            if len(line) != 10:
                raise ValueError(f"linia {r + 1} trebuie sa aiba exact 10 caractere")
            row: List[str] = []
            for c, ch in enumerate(line):
                row.append(ch)
                if ch == ".":
                    continue
                if ch.isdigit():
                    parts.add((r, c))
                elif ch in string.ascii_letters:
                    if ch in seen_head_letters:
                        raise ValueError(f"capul {ch!r} apare de mai multe ori")
                    seen_head_letters.add(ch)
                    heads[(r, c)] = ch
                else:
                    raise ValueError(f"caracter invalid {ch!r} la ({r + 1}, {c + 1})")
            grid.append(row)

        if len(heads) != 3:
            raise ValueError("configuratia trebuie sa contina exact 3 capete de avion (litere)")
        if not parts:
            raise ValueError("configuratia trebuie sa contina cel putin o parte de avion (cifra)")

        return GameConfig(name=path.name, grid=grid, heads=heads, parts=parts)

    def start(self) -> None:
        print(f"[SERVER] Configuratii incarcate: {', '.join(c.name for c in self.configs)}")
        print(f"[SERVER] Runda {self.round_no}, configuratie curenta: {self.current_config.name}")
        print(f"[SERVER] Ascult pe {self.host}:{self.port}")

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((self.host, self.port))
            sock.listen()
            self.server_sock = sock

            while True:
                client_sock, address = sock.accept()
                thread = threading.Thread(
                    target=self._handle_connection,
                    args=(client_sock, address),
                    daemon=True,
                )
                thread.start()

    def _handle_connection(self, client_sock: socket.socket, address: Tuple[str, int]) -> None:
        session: Optional[ClientSession] = None
        try:
            with client_sock:
                file_in = client_sock.makefile("r", encoding="utf-8", newline="\n")

                first_line = file_in.readline()
                if not first_line:
                    return
                try:
                    hello = parse_json_line(first_line)
                except ProtocolError as exc:
                    send_json(client_sock, {"type": "error", "code": "bad_json", "message": str(exc)})
                    return

                if hello.get("type") != "hello":
                    send_json(client_sock, {"type": "error", "code": "bad_hello", "message": "Primul mesaj trebuie sa fie hello."})
                    return

                name = str(hello.get("name", "")).strip()
                if not self._valid_name(name):
                    send_json(client_sock, {"type": "error", "code": "invalid_name", "message": "Numele trebuie sa fie unic, nevid si max. 32 caractere."})
                    return

                with self.state_lock:
                    if name in self.clients:
                        send_json(client_sock, {"type": "error", "code": "name_taken", "message": "Numele este deja folosit."})
                        return
                    session = ClientSession(name=name, sock=client_sock, address=address)
                    self.clients[name] = session
                    current_config_name = self.current_config.name
                    current_round = self.round_no

                session.send({
                    "type": "hello_ok",
                    "message": f"Salut, {name}! Esti conectat.",
                    "round": current_round,
                    "config_id": current_config_name,
                    "rules": "Trimite {type:'shot', row:1..10, col:1..10}.",
                })
                self._broadcast({"type": "player_joined", "name": name}, exclude=name)
                print(f"[SERVER] {name} conectat de la {address}")

                for line in file_in:
                    try:
                        request = parse_json_line(line)
                    except ProtocolError as exc:
                        session.send({"type": "error", "code": "bad_json", "message": str(exc)})
                        continue

                    msg_type = request.get("type")
                    if msg_type == "shot":
                        self._handle_shot(session, request)
                    elif msg_type == "quit":
                        session.send({"type": "bye", "message": "Deconectare ceruta de client."})
                        return
                    else:
                        session.send({"type": "error", "code": "unknown_type", "message": f"Tip necunoscut: {msg_type!r}"})

        except ConnectionResetError:
            pass
        except OSError as exc:
            print(f"[WARN] Eroare socket pentru {address}: {exc}")
        finally:
            if session is not None:
                self._remove_client(session.name)

    @staticmethod
    def _valid_name(name: str) -> bool:
        if not name or len(name) > 32:
            return False
        return all(ch.isalnum() or ch in "_-" for ch in name)

    def _handle_shot(self, session: ClientSession, request: dict) -> None:
        try:
            row = int(request.get("row"))
            col = int(request.get("col"))
        except (TypeError, ValueError):
            session.send({"type": "error", "code": "invalid_coordinates", "message": "Coordonatele trebuie sa fie numere intregi intre 1 si 10."})
            return

        if not (1 <= row <= 10 and 1 <= col <= 10):
            session.send({"type": "error", "code": "out_of_bounds", "message": "Linia si coloana trebuie sa fie in intervalul 1..10."})
            return

        coord = (row - 1, col - 1)
        messages_after: List[dict] = []
        reset_message: Optional[dict] = None

        with self.state_lock:
            config = self.current_config
            result = "0"
            counted = False
            won = False
            head_letter: Optional[str] = None

            if coord in config.heads:
                result = "X"
                head_letter = config.heads[coord]
                if head_letter not in session.downed_heads:
                    session.downed_heads.add(head_letter)
                    counted = True
            elif coord in config.parts:
                result = "1"

            downed_by_client = len(session.downed_heads)
            if downed_by_client == 3:
                won = True
                messages_after.append({
                    "type": "game_won",
                    "winner": session.name,
                    "message": f"{session.name} a doborat toate cele 3 avioane!",
                    "finished_round": self.round_no,
                })
                self._choose_new_config_locked()
                reset_message = {
                    "type": "game_reset",
                    "message": "Joc resetat automat cu o noua configuratie.",
                    "round": self.round_no,
                    "config_id": self.current_config.name,
                }

            response = {
                "type": "shot_result",
                "row": row,
                "col": col,
                "result": result,
                "downed_by_you": downed_by_client,
                "counted": counted,
                "round": self.round_no if not won else self.round_no - 1,
            }
            if result == "0":
                response["message"] = "Niciun avion atins."
            elif result == "1":
                response["message"] = "Parte de avion atinsa, dar nu cap."
            else:
                response[
                    "message"] = "Cap de avion lovit!" if counted else "Cap de avion deja doborat de tine anterior."
            clients_snapshot = list(self.clients.values())

        session.send(response)
        if messages_after:
            for msg in messages_after:
                self._send_to_snapshot(clients_snapshot, msg)
        if reset_message:
            self._send_to_snapshot(clients_snapshot, reset_message)
            print(f"[SERVER] Runda {self.round_no}, configuratie curenta: {self.current_config.name}")

    def _choose_new_config_locked(self) -> None:
        """Alege o configuratie noua si reseteaza scorurile. Se apeleaza sub state_lock."""
        old_name = self.current_config.name
        if len(self.configs) == 1:
            self.current_config = self.configs[0]
        else:
            choices = [cfg for cfg in self.configs if cfg.name != old_name]
            self.current_config = random.choice(choices)

        self.round_no += 1
        for session in self.clients.values():
            session.downed_heads.clear()

    def _broadcast(self, message: dict, exclude: Optional[str] = None) -> None:
        with self.state_lock:
            snapshot = [s for name, s in self.clients.items() if name != exclude]
        self._send_to_snapshot(snapshot, message)

    @staticmethod
    def _send_to_snapshot(sessions: List[ClientSession], message: dict) -> None:
        for session in sessions:
            session.send(message)

    def _remove_client(self, name: str) -> None:
        removed = False
        with self.state_lock:
            if name in self.clients:
                del self.clients[name]
                removed = True
        if removed:
            self._broadcast({"type": "player_left", "name": name}, exclude=name)
            print(f"[SERVER] {name} deconectat")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Server concurent pentru jocul Avionasele")
    parser.add_argument("--host", default="0.0.0.0", help="Interfata pe care asculta serverul")
    parser.add_argument("--port", type=int, default=5000, help="Port TCP")
    parser.add_argument("--config-dir", default="configs", help="Director cu fisiere .txt de configurare")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    server = AvionaseServer(args.host, args.port, Path(args.config_dir))
    server.start()
