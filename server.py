import socket
import threading
import re
import random
import time
import math
import os

FORMAT = 'utf-8'
RE_COMANDO_PLAYER = re.compile('^PLAYER \w+$')
RE_COMANDO_LISTEN = re.compile('^LISTEN \d{1,5}$')
RE_COMANDO_GO = re.compile('^GO (N|S|E|W)$')


LockPlayers = threading.Lock()

class Player:
    def __init__(self, name, x, y, dir, ip, port):
        self.name = name
        self.x = x
        self.y = y
        self.dir = dir
        self.ip = ip
        self.port = port

def escucharCambioDir(conn, user, recibido):
    while (True):
        while('\n' not in recibido):
            try:
                data = conn.recv(4096).decode(FORMAT)
            except ConnectionResetError:
                #se cerro la conexión
                LockPlayers.acquire()
                player = next((x for x in players if x.name == user), None)
                players.remove(player)
                LockPlayers.release()
                conn.close()
                print('Conexion cerrada con: ' + player.ip)
                return

            recibido += data
    
        index = recibido.index('\n')
        mensaje = recibido[0 : index]
        recibido = recibido[index+1 : ]

        if(re.match(RE_COMANDO_GO, mensaje)):
            player = next((x for x in players if x.name == user), None)
            if (player != None):
                LockPlayers.acquire()
                player.dir = mensaje[3 : ]
                LockPlayers.release()
       

def generarDir():
    num = math.floor(random.random()*4+1)
    return {
        1 : 'N',
        2 : 'S',
        3 : 'E',
        4 : 'W',
    }[num]

def nuevaConexion(conn, address):
    recibido = ''
    while('\n' not in recibido):
        recibido += conn.recv(4096).decode(FORMAT)
    
    index = recibido.index('\n')
    mensaje = recibido[0 : index]
    recibido = recibido[index+1 : ]

    if(re.match(RE_COMANDO_PLAYER, mensaje)):
        nombre = mensaje[7 : ]
        if(not any(x.name == nombre for x in players)):
            conn.send('OK\n'.encode(FORMAT))

            while('\n' not in recibido):
                recibido += conn.recv(4096).decode(FORMAT)

            index = recibido.index('\n')
            mensaje = recibido[0 : index]
            recibido = recibido[index+1 : ]

            if(re.match(RE_COMANDO_LISTEN, mensaje)):
                conn.send('OK\n'.encode(FORMAT))

                LockPlayers.acquire()
                players.append(Player(nombre, random.uniform(0, 100), random.uniform(0, 100), generarDir(), address[0], int(mensaje[7 : ])))
                LockPlayers.release()

                #escuchamos los comandos GO
                escucharCambioDir(conn, nombre, recibido)

            else:
                conn.send('FAIL comando incorrecto o número de puerto inválido\n'.encode(FORMAT))
                conn.close()
                print('Conexión con ' + address[0] + ':' + str(address[1]) + ' fallida.')

        else:
            conn.send('FAIL usuario ya existe\n'.encode(FORMAT))
            conn.close()
            print('Conexión con ' + address[0] + ':' + str(address[1]) + ' fallida. El usuario ya existe')

    else:
        conn.send('FAIL comando no reconocido\n'.encode(FORMAT))
        conn.close()
        print('Conexión con ' + address[0] + ':' + str(address[1]) + ' fallida.')


def findCloserThan(jugador, players, radio):
    devolver = []
    j1 = [jugador.x,jugador.y]
    
    for player in players:
        v1 = [player.x,player.y]
        dist = math.dist(j1, v1)
        if(player.name != jugador.name and dist <= radio):
            devolver.append(player)

    return devolver

def buildMessage(player, time, vecinos):
    mensaje = 'WORLD ' + str(time) + '\n'
    mensaje += 'PLAYER ' + str(player.x) + ' ' + str(player.y) + ' ' + player.dir + '\n'
    for vecino in vecinos:
        mensaje += vecino.name + ' ' + str(vecino.x) + ' ' + str(vecino.y) + ' ' + vecino.dir + '\n'
    
    return mensaje


def broadcastUbicacion():
    dt_send = 0.1
    global radio 
    world_skt = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    while (True):
        LockPlayers.acquire()
        for player in players:
            vecinos = findCloserThan(player, players, radio)
            mensaje = buildMessage(player, round((time.time()-tiempoInicio)*1000), vecinos)
            world_skt.sendto(mensaje.encode(FORMAT), (player.ip, player.port))
        LockPlayers.release()
        time.sleep(dt_send)

    #cerramos el socket file descriptor
    world_skt.close()

def actualizadorUbicaciones():
    v = 1
    dt_sim = 0.01

    while (True):
        LockPlayers.acquire()
        for p in players:
            dir = p.dir
            if dir == 'N':
                p.y += v*dt_sim
            elif dir == 'S':
                p.y -= v*dt_sim
            elif dir == 'E':
                p.x += v*dt_sim
            elif dir == 'W':
                p.x -= v*dt_sim
            #p.x = numpy.clip(p.x, 0, 100)
            #p.y = numpy.clip(p.y, 0, 100)
            if (p.x < 0):
                p.x= 0
            elif p.x>100:  
                p.x=100
            if (p.y < 0):
                p.y= 0
            elif p.y>100:  
                p.y=100
        LockPlayers.release()
        time.sleep(dt_sim)


players = []
print('Ingrese radio de vision')
radio = int(input())
control_skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
control_skt.bind(('', 2021))
control_skt.listen()

print('Escuchando conexiones en el puerto 2021')

tiempoInicio = time.time()

thread = threading.Thread(target = actualizadorUbicaciones, args = ())
thread.start()

thread = threading.Thread(target = broadcastUbicacion, args = ())
thread.start()

while True:
    conn, address = control_skt.accept()
    print('Nueva conexion desde: ' + address[0] + ':' + str(address[1]))
    thread = threading.Thread(target = nuevaConexion, args = (conn, address))
    thread.start()

