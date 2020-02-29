import sys

import pygame
import gamestate
import render

import server
import threading

import socket
import select

import queue

import core

RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

roomarea_width  = 512
roomarea_height = 512

pygame.init()

currentcontrolled = -1

class AticAtacClient(threading.Thread):
    def __init__(self, ip, port):
        super().__init__(name='AticAtacClient')
        self.active = True

        self.ip = ip # 13225
        self.port = port

        self.incomingqueue = queue.Queue()
        self.outgoingqueue = queue.Queue()

    def run(self):

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.ip, self.port))
        self.sock.setblocking(False)
        self.peer = server.ConnectedPeer(self.sock)
        self.failure = False # This will be set to True when a fatal network error is detected

        while self.active:

            while True:
                try:
                    pack = self.outgoingqueue.get_nowait()
                    self.peer.sendPacket(pack)

                except queue.Empty:
                    break

            readable, writable, exceptional = select.select([self.sock], [self.sock], [self.sock])
            for s in readable:
                packet = None

                try:
                    packet = server.handleRead(s, self.peer)

                    if packet is not None:
                        self.peer.incoming.append(packet)

                except server.CloseConnectionException:
                    print('Invalid packet :( (Client-Side)')
                    self.failure = True
                    self.active = False

            for s in writable:
                if len(self.peer.tosend) > 0:
                    self.peer.tosend = self.peer.tosend[s.send(self.peer.tosend):]

            for pack in self.peer.incoming:
                self.incomingqueue.put(pack)

            self.peer.incoming.clear()

screen = pygame.display.set_mode((roomarea_width, roomarea_height))


# Room: (colour, vertices, connections)

leveltypes = [
    (BLACK,)
]

currentstate = gamestate.PLAYING

clock = pygame.time.Clock()

currentroom = 0

currentobjs = []

currentcontrols = set()

client = AticAtacClient('127.0.0.1', 13225)
client.start()

while True:
    if client.active is False and client.failure:
        client.join()
        sys.exit()

    currentcontrols.clear()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            client.active = False
            client.join()
            sys.exit()

    if currentstate == gamestate.MENU:
        screen.fill(RED)

    elif currentstate == gamestate.PLAYING:
        pass

    else:
        pass

    keys = pygame.key.get_pressed()

    if keys[pygame.K_LEFT]:
        currentcontrols.add((-2, 0))

    if keys[pygame.K_RIGHT]:
        currentcontrols.add((2, 0))

    if keys[pygame.K_UP]:
        currentcontrols.add((0, -2))

    if keys[pygame.K_DOWN]:
        currentcontrols.add((0, 2))

    for obj in currentobjs:
        if obj.id == currentcontrolled:
            changed = False
            for v in currentcontrols:
                changed = True
                obj.x += v[0]
                obj.y += v[1]

            if changed: client.outgoingqueue.put(server.PlayerChangePos(obj.x, obj.y))
            break


    while True:
        try:
            pack = client.incomingqueue.get_nowait()
            if isinstance(pack, server.SendObjectPacket):
                obj = core.PlayerObj(pack.x, pack.y)
                obj.id = pack.uid
                currentobjs.append(obj)

            elif isinstance(pack, server.SendControlledUpdate):
                currentcontrolled = pack.objectid
                print(str(currentcontrolled))

            elif isinstance(pack, server.UpdateObjectPosition):
                for obj in currentobjs:
                    if obj.id == pack.uid:
                        obj.x = pack.x
                        obj.y = pack.y


        except queue.Empty:
            break



    screen.fill(WHITE)

    for obj in currentobjs:

        render.renderdict[obj.__class__](screen, obj)


    pygame.display.flip()

    fps = clock.tick(30)