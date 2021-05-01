import sys

import pygame
import gamestate
import render

import threading

import socket
import select

import queue

import core
import net

RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

roomarea_width  = 512
roomarea_height = 512

PLAYER_SPEED = 4

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
        self.peer = net.ConnectedPeer(self.sock)
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
                    packet = net.handleRead(s, self.peer)

                    if packet is not None:
                        self.peer.incoming.append(packet)

                except net.CloseConnectionException:
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
currentroomtype = 0

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
        currentcontrols.add((-PLAYER_SPEED, 0))

    if keys[pygame.K_RIGHT]:
        currentcontrols.add((PLAYER_SPEED, 0))

    if keys[pygame.K_UP]:
        currentcontrols.add((0, -PLAYER_SPEED))

    if keys[pygame.K_DOWN]:
        currentcontrols.add((0, PLAYER_SPEED))

    for obj in currentobjs:
        if obj.id == currentcontrolled:
            changed = False
            for v in currentcontrols:
                changed = True
                obj.x += v[0]
                obj.y += v[1]

            if changed: client.outgoingqueue.put(net.PlayerChangePos(obj.x, obj.y, currentroom))
            break


    while True:
        try:
            pack = client.incomingqueue.get_nowait()
            if isinstance(pack, net.SendObjectPacket):
                # pack.type
                obj = core.gobjTypes[pack.type].generateBasic(pack.x, pack.y, pack.data)
                obj.id = pack.uid
                currentobjs.append(obj)

            elif isinstance(pack, net.SendControlledUpdate):
                currentcontrolled = pack.objectid

            elif isinstance(pack, net.UpdateObjectPosition):
                for obj in currentobjs:
                    if obj.id == pack.uid:
                        obj.x = pack.x
                        obj.y = pack.y

            elif isinstance(pack, net.RemoveObjectPacket):
                toremove = None
                for obj in currentobjs:
                    if obj.id == pack.uid:
                        toremove = obj
                        break

                if toremove == None:
                    print('Warning! No object to remove!')

                else:
                    currentobjs.remove(toremove)

            elif isinstance(pack, net.SwitchRoomPacket):
                currentobjs.clear()
                currentcontrolled = -1
                currentroom = pack.roomid
                currentroomtype = pack.roomtype


        except queue.Empty:
            break



    screen.fill(WHITE)
    background = render.room_images[currentroomtype]
    if background is not None:
        rect = background[0].get_rect()
        rect.left = int(roomarea_width * background[1])
        rect.top = int(roomarea_height * background[2])
        screen.blit(background[0], rect)

    for obj in currentobjs:

        render.renderdict[obj.__class__](screen, obj)


    pygame.display.flip()

    fps = clock.tick(30)