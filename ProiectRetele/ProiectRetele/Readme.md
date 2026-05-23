# Avionase - Joc Client-Server

Această aplicație implementează un joc distribuit de tip client-server, inspirat din jocul „Avioane”. Serverul încarcă mai multe configurații de joc din directorul `configs/`, alege aleator una dintre ele și permite conectarea mai multor clienți simultan. Fiecare client se identifică printr-un nume unic și poate trage la coordonate de forma linie-coloană.

Proiectul conține fișierele principale `server.py`, `Client.py`, `protocol.py`, `Dockerfile`, `docker-compose.yml` și directorul `configs/`, unde se află fișierele de configurare ale jocului.

Fiecare fișier de configurare reprezintă o matrice de dimensiune `10 x 10`. Caracterul `.` reprezintă o poziție goală, cifrele reprezintă părți ale avioanelor, iar literele reprezintă capetele avioanelor. O configurație validă trebuie să conțină exact 3 capete de avion.

Aplicația folosește un protocol simplu bazat pe JSON Lines, unde fiecare mesaj transmis între client și server este un obiect JSON trimis pe o singură linie.

Pentru pornirea serverului cu Docker se folosește comanda:

docker compose up --build

Serverul ascultă implicit pe portul `5000`.

Pentru pornirea unui client se folosește comanda:

python Client.py --host 127.0.0.1 --port 5000 --name Ion

Pentru mai mulți clienți, comanda se rulează în terminale diferite, folosind nume diferite pentru fiecare jucător:

python Client.py --name Ana

python Client.py --name Mihai

În client, o tragere se face folosind comanda:

trage <linie> <coloana>

sau direct:

<linie> <coloana>

Exemplu:

trage 3 4

Serverul răspunde cu unul dintre următoarele rezultate: `0` dacă nu a fost atins niciun avion, `1` dacă a fost atinsă o parte a unui avion, dar nu capul, și `X` dacă a fost lovit capul unui avion.

Când un client doboară toate cele 3 avioane, serverul notifică toți clienții cu numele câștigătorului, alege o nouă configurație, resetează scorurile și începe o rundă nouă.

Aplicația implementează un server concurent, capabil să gestioneze mai mulți clienți simultan. Accesul la starea jocului este sincronizat pentru a evita condițiile de cursă în cazul tragerilor simultane. Serverul ține evidența avioanelor doborâte pentru fiecare client, validează coordonatele primite și tratează deconectările fără să afecteze jocul global.

Funcționalitățile principale implementate sunt: încărcarea configurațiilor din fișiere, alegerea aleatoare a unei configurații, conectarea clienților cu nume unic, procesarea tragerilor, notificarea rezultatului, detectarea câștigătorului, resetarea automată a jocului și gestionarea deconectărilor.