from turtle import Turtle, Screen, color
import time
import turtle
import random
import keyboard
import socket
import threading
import re
import os

FORMAT = 'utf-8'
SERVER_IP = '127.0.0.1'
SERVER_PORT = 2021
CLIENT_PORT = 25565

RE_COMANDO_OK = '^OK$'

TURTLE_SIZE = 20  #tamaño del jugador
WORLD_SIZE = 100  #cuadrado de 100 x 100
angleMap = {'N':90,'E':0,'S':270,'W':180}  #Map para traducir direcciones en angulos de turtle
colorList = ["red", 'blue', 'yellow', 'green', 'orange', 'black']

#players es una lista donde cada elemento es una terna de [x,y,dir]
#la coordenada (0,0) está en el centro de la pantalla, por lo que x e y van de -WORLD_SIZE/2 hasta WORLD_SIZE/2
#si las coordenadas a dibujar son de 0 a WORLD_SIZE, se deberá hacer la transformación correspondiente.
#screen es la pantalla donde se dibuja
#extraigo timestamp

def coordenadasJugador(players):
    global recibidoMundo
    print(recibidoMundo)
    if recibidoMundo != '':
        index = recibidoMundo.index('\n')
        recibidoMundo = recibidoMundo[index+1 : ]
        #extraigo coordenadas del jugador
        while('\n' in recibidoMundo):
            index = recibidoMundo.index(' ')
            recibidoMundo = recibidoMundo[index+1 : ]
            index = recibidoMundo.index(' ')
            posX = recibidoMundo[ : index]
            recibidoMundo = recibidoMundo[index+1 : ]
            index = recibidoMundo.index(' ')
            posY = recibidoMundo[ : index]
            recibidoMundo = recibidoMundo[index+1 : ]
            index = recibidoMundo.index('\n')
            dir = recibidoMundo[ : index]
            recibidoMundo = recibidoMundo[index+1 : ]

            #ajusto coordenadas
            player = [float(posX)-50, float(posY)-50, dir]
            
            players.append(player)
        print (players)

def updateWorld (screen):
    screen.clear()    #Se puede comentar para ver la traza de cada tortuga
    i = 0
    players = []
    coordenadasJugador(players)
    for p in players:
        #creo a la tortuga pepe
        pepe = Turtle(shape="turtle", visible=False)
        pepe.color (colorList[i])

        #para dibujar la tortuga en una pos inicial, se inicia oculta y se mueve a la pos deseada, luego se muestra
        pepe.speed(0)
        pepe.penup()
        pepe.goto((p[0]/(WORLD_SIZE/2))*(screen.window_width()/2-TURTLE_SIZE/2), (p[1]/(WORLD_SIZE/2))*(screen.window_height()/2-TURTLE_SIZE/2))
        pepe.tiltangle(angleMap.get(p[2]))
        pepe.showturtle()

        i = (i+1) % 6 #no acepta mas de 6 colores distintos, se puede extender la lista
        
    

def controlMovimiento(client):
    actual = ''
    dir = ''
    while True:
        tecla = keyboard.read_key()
        if tecla == 'w':
            dir = 'N'
        elif tecla == 'a':
            dir = 'W'
        elif tecla == 's':
            dir = 'S'
        elif tecla == 'd':
            dir = 'E'
        else:
            dir = ''
        if dir != '' and dir != actual:
            actual = dir
            data = 'GO ' + dir + '\n'
            client.send(data.encode(FORMAT))

def reciboInfo():
    global recibidoMundo
    sck_mundo = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sck_mundo.bind(('', CLIENT_PORT))

    while True:
        recibidoMundo, client_address = sck_mundo.recvfrom(4096)
        recibidoMundo = recibidoMundo.decode(FORMAT)
        
        print(recibidoMundo)


def actualizadorUbicaciones(screen):
    thread = threading.Thread(target = reciboInfo, args = ())
    thread.start()
    while True:  
        updateWorld(screen)
        time.sleep(0.1) 



#ejemplo de uso
recibidoMundo= ''
screen = turtle.Screen()
screen.setup(1000,1000)
players = []  #ver que las coordenadas van de -50 a 50 en este caso.
#llamo a la función que dibuja la posición inicial de cada jugador
updateWorld (screen)

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((SERVER_IP, SERVER_PORT))

print('Ingrese puerto: ')
CLIENT_PORT = int(input())
print('Ingrese nombre de usuario: ')
username = input()
data = 'PLAYER ' + username + '\n'
client.send(data.encode(FORMAT))
recibido = ''
LockPlayers = threading.Lock()

while('\n' not in recibido):
    recibido += client.recv(4096).decode(FORMAT)

index = recibido.index('\n')
mensaje = recibido[0 : index]
recibido = recibido[index+1 : ]

if(re.match(RE_COMANDO_OK, mensaje)):
    data = 'LISTEN ' + str(CLIENT_PORT) + '\n'
    client.send(data.encode(FORMAT))

    recibido = ''
    while('\n' not in recibido):
        recibido += client.recv(4096).decode(FORMAT)

    index = recibido.index('\n')
    mensaje = recibido[0 : index]
    recibido = recibido[index+1 : ]

    if(re.match(RE_COMANDO_OK, mensaje)):
        thread = threading.Thread(target = controlMovimiento, args = (client, ))
        thread.start()

        actualizadorUbicaciones(screen)

    else:
        print(mensaje)
        client.close()

else:
    print(mensaje)
    client.close()
