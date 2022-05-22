import signal
signal.signal(signal.SIGINT, signal.SIG_DFL)

import socket
import struct
import threading
import random
from datetime import datetime


PORT = 1234
HEADER_LENGTH = 2
open("uporabniki.txt", "w").close()


def receive_fixed_length_msg(sock, msglen):
    message = b''
    while len(message) < msglen:
        chunk = sock.recv(msglen - len(message))  # preberi nekaj bajtov
        if chunk == b'':
            raise RuntimeError("socket connection broken")
        message = message + chunk  # pripni prebrane bajte sporocilu

    return message


def receive_message(sock):
    header = receive_fixed_length_msg(sock,
                                      HEADER_LENGTH)  # preberi glavo sporocila (v prvih 2 bytih je dolzina sporocila)
    message_length = struct.unpack("!H", header)[0]  # pretvori dolzino sporocila v int

    message = None
    if message_length > 0:  # ce je vse OK
        message = receive_fixed_length_msg(sock, message_length)  # preberi sporocilo
        message = message.decode("utf-8")

    return message


def send_message(sock, message):
    encoded_message = message.encode("utf-8")  # pretvori sporocilo v niz bajtov, uporabi UTF-8 kodno tabelo

    # ustvari glavo v prvih 2 bytih je dolzina sporocila (HEADER_LENGTH)
    # metoda pack "!H" : !=network byte order, H=unsigned short
    header = struct.pack("!H", len(encoded_message))

    message = header + encoded_message  # najprj posljemo dolzino sporocilo, slee nato sporocilo samo
    sock.sendall(message)


# funkcija za komunikacijo z odjemalcem (tece v loceni niti za vsakega odjemalca)
def client_thread(client_sock, client_addr):
    global clients
    uporabniki = preberi()
    posiljatelj = ""
    for uporabnik, addr in uporabniki.items():
        if addr == int(client_addr[1]):
            posiljatelj = uporabnik

    print("[system] connected with " + posiljatelj + ":" + str(client_addr[1]))
    print("[system] we now have " + str(len(clients)) + " clients")

    try:

        while True:  # neskoncna zanka
            msg_received = receive_message(client_sock)
            uporabniki = preberi()
            now = datetime.now()
            cajt = now.strftime("%H:%M:%S")

            if not msg_received:  # ce obstaja sporocilo
                break

            posiljatelj = ""
            for uporabnik, addr in uporabniki.items():
                if addr == int(client_addr[1]):
                    posiljatelj = uporabnik

            if msg_received == "!pomoc":
                for client in clients:
                    if client.getpeername()[1] == int(client_addr[1]):
                        send_message(client, "Za privatna sporocila napisite '!<naslovnik>' nato ' ' in potem sporocilo.")
                        send_message(client, "Za izpis uporabnikov uporabite ukaz '!uporabniki'")
                        send_message(client, "Za metanje kocke uporabite ukaz '!dice <številka od 1 do 6>'")

            elif msg_received == "!uporabniki":
                stevec = 1
                for client in clients:
                    if client.getpeername()[1] == int(client_addr[1]):
                        send_message(client, "--------------------")
                        send_message(client, "-----UPORABNIKI-----")
                        send_message(client, "--------------------")
                        for user, address in uporabniki.items():
                            send_message(client, str(stevec) + ".Uporabnik: [" + user + "]")
                            stevec += 1

            elif msg_received.split(" ")[0] == "!dice":
                cifra = random.randint(1, 6)
                for client in clients:
                    if client.getpeername()[1] == int(client_addr[1]):
                        if int(msg_received.split(" ")[1]) == cifra:
                            send_message(client, "Bravo! Številka je bila " + str(cifra))
                        else:
                            send_message(client, "Več sreče prihodnjič. Kocka je padla na " + str(cifra))

            elif msg_received.startswith("!") and msg_received != "!uporabniki":
                prijavljen = False
                vsebina = msg_received.split(" ")
                prejemnik = vsebina[0][1:].lower()
                for uporabnik, address in uporabniki.items():
                    if uporabnik.lower() == prejemnik:
                        prijavljen = True
                        naslov = int(address)
                if prijavljen:
                    for client in clients:
                        if client.getpeername()[1] == naslov:
                            print("[RKchat] [" + cajt + "] [" + posiljatelj + "] to [" + prejemnik.capitalize() +
                                  "] : " + " ".join(vsebina[1:]))
                            send_message(client, "[" + cajt + "] From [" + posiljatelj + "]: "
                                         + " ".join(vsebina[1:]))
                if not prijavljen:
                    for client in clients:
                        if client.getpeername()[1] == int(client_addr[1]):
                            send_message(client, "Uporabnik [" + prejemnik.capitalize() + "] trenutno ni dosegljiv.")

            else:
                print("[RKchat] [" + cajt + "] [" + posiljatelj + "] to [All] : " + msg_received)
                for client in clients:
                    send_message(client, "[" + cajt + "] From [" + posiljatelj + "] to [All]: " + msg_received)
    except:
        # tule bi lahko bolj elegantno reagirali, npr. na posamezne izjeme. Trenutno kar pozremo izjemo
        pass

    # prisli smo iz neskoncne zanke
    with clients_lock:
        clients.remove(client_sock)
    print("[system] we now have " + str(len(clients)) + " clients")
    client_sock.close()



def preberi():
    uporabniki = dict()
    f = open("uporabniki.txt", encoding="utf-8")
    for vrstica in f:
        vrstica = vrstica.strip()
        besede = vrstica.split(":")
        uporabniki[besede[0]] = int(besede[1])
    f.close()
    return uporabniki


# kreiraj socket
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind(("localhost", PORT))
server_socket.listen(1)

# cakaj na nove odjemalce
print("[system] listening ...")
clients = set()
clients_lock = threading.Lock()
while True:
    try:
        # pocakaj na novo povezavo - blokirajoc klic
        client_sock, client_addr = server_socket.accept()
        with clients_lock:
            clients.add(client_sock)

        thread = threading.Thread(target=client_thread, args=(client_sock, client_addr));
        thread.daemon = True
        thread.start()

    except KeyboardInterrupt or ConnectionError:
        open("uporabniki.txt", "w").close()
        break

print("[system] closing server socket ...")
server_socket.close()
