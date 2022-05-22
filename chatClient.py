import socket
import struct
import sys
import threading

PORT = 1234
HEADER_LENGTH = 2


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


# message_receiver funkcija tece v loceni niti
def message_receiver():
    while True:
        msg_received = receive_message(sock)
        if len(msg_received) > 0:  # ce obstaja sporocilo
            uporabniki = preberi()
            ime = ""
            for uporabnik, addr in uporabniki.items():
                if addr == sock.getsockname()[1]:
                    ime = uporabnik
            print(msg_received)  # izpisi


def zapisi():
    ime = input("Vpiši ime:")
    addres = sock.getsockname()[1]
    f = open("uporabniki.txt", "a", encoding="utf-8")
    f.write(ime + ":" + str(addres) + "\n")
    f.close()
    print("Prijavljeni ste kot: " + ime)


def preberi():
    uporabniki = dict()
    f = open("uporabniki.txt", encoding="utf-8")
    for vrstica in f:
        vrstica = vrstica.strip()
        besede = vrstica.split(":")
        uporabniki[besede[0]] = int(besede[1])
    f.close()
    return uporabniki


def izbrisi():
    with open("uporabniki.txt") as f:
        vrstice = f.read().splitlines()
    for vrstica in vrstice:
        if str(sock.getsockname()[1]) in vrstica:
            vrstice.remove(vrstica)
    f.close()
    new = open("uporabniki.txt", "w", encoding="utf-8")
    for vrstica in vrstice:
        new.write(vrstica + "\n")
    new.close()


ime = input("Vpisi ime: ")

# povezi se na streznik
print("[system] connecting to chat server ...")
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(("localhost", PORT))
print("[system] connected!")
addres = sock.getsockname()[1]
f = open("uporabniki.txt", "a", encoding="utf-8")
f.write(ime + ":" + str(addres) + "\n")
f.close()
print("Prijavljeni ste kot: " + ime)
print("Za pomoc uporabite ukaz '!pomoc'")



# zazeni message_receiver funkcijo v loceni niti
thread = threading.Thread(target=message_receiver)
thread.daemon = True
thread.start()

# pocakaj da uporabnik nekaj natipka in poslji na streznik

while True:
    try:
        msg_send = input("")
        send_message(sock, msg_send)
    except KeyboardInterrupt or ConnectionResetError or ConnectionError:
        izbrisi()
        sys.exit()
