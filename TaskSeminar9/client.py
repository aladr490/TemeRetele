import socket

SERVER_HOST = '127.0.0.1'
SERVER_PORT = 9999
BUFFER_SIZE = 4096
TIMEOUT     = 5

client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client_socket.settimeout(TIMEOUT)

este_conectat = False


def trimite_comanda(mesaj: str) -> str:
    try:
        client_socket.sendto(mesaj.encode('utf-8'), (SERVER_HOST, SERVER_PORT))
        date_brute, _ = client_socket.recvfrom(BUFFER_SIZE)
        return date_brute.decode('utf-8')
    except socket.timeout:
        return "EROARE: Serverul nu raspunde (timeout)."
    except Exception as e:
        return f"EROARE: {e}"


print("=" * 55)
print("  CLIENT UDP - Seminar 9")
print("=" * 55)
print("  Comenzi disponibile:")
print("    CONNECT              - conectare la server")
print("    DISCONNECT           - deconectare de la server")
print("    PUBLISH <mesaj>      - publicare mesaj")
print("    DELETE <id>          - stergere mesaj dupa ID")
print("    LIST                 - afisare toate mesajele")
print("    EXIT                 - inchidere client")
print("=" * 55)
print()

while True:
    try:
        intrare = input(">> ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\nInchidere client...")
        break

    if not intrare:
        continue

    parti = intrare.split(' ', 1)
    comanda = parti[0].upper()
    argumente = parti[1] if len(parti) > 1 else ''

    if comanda == 'EXIT':
        print("Inchidere client...")
        break

    elif comanda == 'CONNECT':
        raspuns = trimite_comanda(intrare)
        print(raspuns)

        if raspuns.startswith("OK"):
            este_conectat = True

    elif comanda == 'DISCONNECT':
        raspuns = trimite_comanda(intrare)
        print(raspuns)

        if raspuns.startswith("OK"):
            este_conectat = False

    elif comanda == 'PUBLISH':
        if not este_conectat:
            print("EROARE: Nu esti conectat. Foloseste mai intai comanda CONNECT.")
            continue

        if not argumente.strip():
            print("EROARE: Pentru PUBLISH trebuie sa introduci un mesaj.")
            print("Exemplu: PUBLISH Salut, acesta este un mesaj.")
            continue

        raspuns = trimite_comanda(intrare)
        print(raspuns)

    elif comanda == 'DELETE':
        if not este_conectat:
            print("EROARE: Nu esti conectat. Foloseste mai intai comanda CONNECT.")
            continue

        if not argumente.strip():
            print("EROARE: Pentru DELETE trebuie sa introduci un ID.")
            print("Exemplu: DELETE 1")
            continue

        try:
            id_mesaj = int(argumente.strip())
            if id_mesaj <= 0:
                print("EROARE: ID-ul trebuie sa fie un numar intreg pozitiv.")
                continue
        except ValueError:
            print("EROARE: ID-ul trebuie sa fie un numar intreg valid.")
            print("Exemplu: DELETE 1")
            continue

        raspuns = trimite_comanda(f"DELETE {id_mesaj}")
        print(raspuns)

    elif comanda == 'LIST':
        if not este_conectat:
            print("EROARE: Nu esti conectat. Foloseste mai intai comanda CONNECT.")
            continue

        raspuns = trimite_comanda(intrare)
        print(raspuns)

    else:
        print(f"Comanda '{comanda}' nu este recunoscuta de client.")
        print("Comenzi valide: CONNECT, DISCONNECT, PUBLISH, DELETE, LIST, EXIT")

client_socket.close()
print("Socket inchis. La revedere!")