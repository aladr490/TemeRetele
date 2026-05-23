from __future__ import annotations

import argparse
import socket
import sys
import threading
from typing import Optional

from protocol import ProtocolError, parse_json_line, send_json


def print_message(message: dict) -> None:
    msg_type = message.get("type")

    if msg_type == "hello_ok":
        print(f"[OK] {message.get('message')}")
        print(f"[INFO] Runda {message.get('round')}, configuratie: {message.get('config_id')}")
        print("[HELP] Scrie: trage <linie> <coloana>  sau direct: <linie> <coloana>")
    elif msg_type == "shot_result":
        print(
            f"[REZULTAT] ({message.get('row')}, {message.get('col')}) => {message.get('result')} | "
            f"{message.get('message')} | doborate de tine: {message.get('downed_by_you')}/3"
        )
    elif msg_type == "game_won":
        print(f"\n[CASTIGATOR] {message.get('message')}\n> ", end="", flush=True)
    elif msg_type == "game_reset":
        print(f"\n[RESET] {message.get('message')} Runda {message.get('round')}, configuratie: {message.get('config_id')}\n> ", end="", flush=True)
    elif msg_type == "player_joined":
        print(f"\n[INFO] {message.get('name')} s-a conectat.\n> ", end="", flush=True)
    elif msg_type == "player_left":
        print(f"\n[INFO] {message.get('name')} s-a deconectat.\n> ", end="", flush=True)
    elif msg_type == "error":
        print(f"[EROARE] {message.get('code')}: {message.get('message')}")
    elif msg_type == "bye":
        print(f"[BYE] {message.get('message')}")
    else:
        print(f"[MESAJ] {message}")


def receiver(sock: socket.socket, stop_event: threading.Event) -> None:
    try:
        file_in = sock.makefile("r", encoding="utf-8", newline="\n")
        for line in file_in:
            try:
                message = parse_json_line(line)
            except ProtocolError as exc:
                print(f"[EROARE] Mesaj invalid de la server: {exc}")
                continue
            print_message(message)
    except OSError:
        pass
    finally:
        stop_event.set()
        print("\n[INFO] Conexiunea cu serverul s-a inchis.")


def parse_command(text: str) -> Optional[dict]:
    text = text.strip()
    if not text:
        return None
    if text.lower() in {"quit", "exit", "q"}:
        return {"type": "quit"}
    if text.lower() in {"help", "?"}:
        print("Comenzi: trage <linie> <coloana> | <linie> <coloana> | quit")
        return None

    parts = text.split()
    if parts and parts[0].lower() in {"trage", "shot", "fire"}:
        parts = parts[1:]

    if len(parts) != 2:
        print("Comanda invalida. Exemplu: trage 2 3")
        return None

    try:
        row = int(parts[0])
        col = int(parts[1])
    except ValueError:
        print("Coordonatele trebuie sa fie numere intregi.")
        return None

    return {"type": "shot", "row": row, "col": col}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Client CLI pentru jocul Avionasele")
    parser.add_argument("--host", default="127.0.0.1", help="Adresa serverului")
    parser.add_argument("--port", type=int, default=5000, help="Port TCP")
    parser.add_argument("--name", default=None, help="Nume unic de jucator")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    name = args.name or input("Nume jucator: ").strip()

    stop_event = threading.Event()
    try:
        with socket.create_connection((args.host, args.port), timeout=10) as sock:
            sock.settimeout(None)
            send_json(sock, {"type": "hello", "name": name})

            recv_thread = threading.Thread(target=receiver, args=(sock, stop_event), daemon=True)
            recv_thread.start()

            while not stop_event.is_set():
                try:
                    text = input("> ")
                except (EOFError, KeyboardInterrupt):
                    text = "quit"

                message = parse_command(text)
                if message is None:
                    continue
                try:
                    send_json(sock, message)
                except OSError:
                    print("[EROARE] Nu mai pot trimite catre server.")
                    break
                if message.get("type") == "quit":
                    break

    except ConnectionRefusedError:
        print("[EROARE] Serverul nu accepta conexiuni. Verifica host/port si daca Docker/serverul ruleaza.")
        return 1
    except socket.timeout:
        print("[EROARE] Timeout la conectare.")
        return 1
    except OSError as exc:
        print(f"[EROARE] Conexiune esuata: {exc}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())