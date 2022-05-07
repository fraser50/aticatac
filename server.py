import threading
import socket
import select
import time

import core
import random
import queue
from time import sleep
import net
import json

allowedchars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_'

doorPositions = (
    (256 - (core.DOOR_SIZE / 2), 0),
    (512 - core.DOOR_SIZE, 256 - (core.DOOR_SIZE / 2)),
    (256 - (core.DOOR_SIZE / 2), 512 - core.DOOR_SIZE),
    (0, 256 - (core.DOOR_SIZE / 2))
)

# Make sure doorPositions only includes integers
doorPositions = tuple(map(lambda x: tuple(map(lambda y: int(y), x)), doorPositions))


def buildMap(gamemap, game):

    rooms = []

    for rd in gamemap.rooms:
        room = core.Room(rd.type, len(rooms), game)
        for x in range(4):
            if core.roomTypes[rd.type][x] == -1:
                continue

            nextroom = gamemap.getRoom(rd.x + core.doorToDisp[x][0], rd.y + core.doorToDisp[x][1])

            togo = -1 if nextroom is None else gamemap.rooms.index(nextroom)

            door = core.Door(doorPositions[x][0], doorPositions[x][1], togo, x, rd.doors[x])

            if x % 2 != 0:
                # Add offset to door positions depending on the room. (Makes corridors look good)
                # Protected variables are accessed below to prevent poschange from becoming True.
                door._x += int(512 * core.roomDoorOffsets[rd.type][0]) * (-1 if x == 1 else 1)
                door._y += int(512 * core.roomDoorOffsets[rd.type][1]) * (-1 if x == 1 else 1)

            room.addObject(door)

        rooms.append(room)

    return rooms


class Player(net.ConnectedPeer):
    def __init__(self, name, conn, gp):
        super().__init__(conn)
        self.name = name
        self.gp = gp
        self.controlledobject = -1


class GamePlayer():
    def __init__(self, name, room):
        self.name = name
        self.room = room
        self.tohandle = queue.Queue()
        self.tosend = queue.Queue()
        self.currobj = None
        self.food = 100
        self.counter = 0

    def changeRoom(self, room, x=256 - 32, y=256 - 32):
        if self.room is not None:
            self.room.deleteObject(self.currobj)
            self.room.players.remove(self)

        self.room = room
        self.room.players.append(self)
        self.currobj = core.PlayerObj(x, y)
        room.addObject(self.currobj)
        self.tosend.put(net.SwitchRoomPacket(room.roomid, room.roomtype))
        self.tosend.put(net.SendControlledUpdate(self.currobj.id))

        for obj in self.room.roomobjects:
            if obj != self.currobj:
                self.tosend.put(net.SendObjectPacket(obj.x, obj.y, core.gobjDict[obj.__class__], obj.getData(), obj.id))


class AticAtacGame(threading.Thread):
    def __init__(self):
        super().__init__(name='AticAtacGame')
        self.active = True

        with open('map.json', 'r') as f:
            self.rooms = buildMap(core.GameMap.fromDict(json.loads(f.read())), self)

        self.populateFood()

        self.outgoingqueue = queue.Queue()  # This queue is for packets that should be sent to everyone in a room
        # Format (packet, roomid)

        self.players = []
        self.newplayers = queue.Queue()
        self.offlineplayers = queue.Queue()

    def run(self):
        while self.active:
            sleep(1/30)

            while not self.offlineplayers.empty():
                p = self.offlineplayers.get_nowait()
                p.room.players.remove(p)
                self.players.remove(p)

                if p.currobj is not None:
                    p.room.deleteObject(p.currobj)

            while not self.newplayers.empty():
                p = self.newplayers.get_nowait()

                self.players.append(p)
                p.changeRoom(self.rooms[0])

            for p in self.players:
                while not p.tohandle.empty():
                    packet = p.tohandle.get_nowait()
                    if isinstance(packet, net.PlayerChangePos):
                        if p.currobj is not None and packet.rid == p.room.roomid:
                            p.currobj.x = packet.x
                            p.currobj.y = packet.y

            for room in self.rooms:

                for obj in room.todelete:
                    room.roomobjects.remove(obj)

                    rop = net.RemoveObjectPacket(obj.id)

                    for p in room.players:
                        p.tosend.put_nowait(rop)

                room.todelete.clear()

                for obj in room.newobjects:
                    for p in room.players:
                        p.tosend.put_nowait(net.SendObjectPacket(obj.x, obj.y, core.gobjDict[obj.__class__], obj.getData(), obj.id))

                room.newobjects.clear()

                for obj in room.roomobjects:
                    obj.update(room)

                    if obj.poschange:
                        obj.poschange = False
                        for p in room.players:
                            if p.currobj != obj:
                                p.tosend.put(net.UpdateObjectPosition(obj.id, obj.x, obj.y))

                for p in self.players:
                    p.counter += 1
                    if p.counter == 20: # 90
                        p.counter = 0
                        p.food -= 1
                        if p.food % 5 == 0 and p.food >= 0:
                            p.tosend.put(net.SetFoodPacket(p.food))

                    if p.food == 0 and p.currobj is not None:
                        p.food = -1
                        p.room.deleteObject(p.currobj)
                        p.room.addObject(core.Grave(p.currobj.x, p.currobj.y))
                        p.currobj = None
                        p.tosend.put(net.AnnounceDeathPacket())

    def populateFood(self):
        for room in random.sample(self.rooms, int(len(self.rooms)/2)):
            self.addFood(room)

    def addFood(self, room):
        foodRect = core.SimpleRect(0, 0, 68, 68)
        objRect = core.SimpleRect(0, 0, 68, 68)

        noSpace = True

        while noSpace:
            roomDims = core.roomDimensions[room.roomtype]
            foodX = random.randrange(roomDims[0], roomDims[2]-64)
            foodY = random.randrange(roomDims[1], roomDims[3]-64)

            foodRect.x = foodX
            foodRect.y = foodY

            noSpace = False
            for obj in room.roomobjects:
                objRect.x = obj.x
                objRect.y = obj.y

                if foodRect.collides(objRect):
                    noSpace = True
                    break

        food = core.Food(foodRect.x, foodRect.y, 0)
        room.addObject(food)


class AticAtacServer(threading.Thread):
    def __init__(self, ip='127.0.0.1', port=13225):
        super().__init__(name='AticAtacServer')
        self.ip = ip
        self.port = port
        self.active = True

    def run(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setblocking(False)
        self.sock.bind((self.ip, self.port))
        self.sock.listen(5)

        self.sockets = [self.sock]

        self.players = []

        self.socktoplayer = {}

        self.todelete = []

        self.gamethread = AticAtacGame()
        self.gamethread.start()

        while self.active:
            for p in self.players:
                while not p.gp.tosend.empty():
                    packet = p.gp.tosend.get_nowait()
                    p.sendPacket(packet)

            readable, writable, exceptional = select.select(self.sockets, self.sockets, self.sockets, 0.125)
            for s in readable:
                if s == self.sock:
                    conn, addr = s.accept()
                    conn.setblocking(False)
                    self.sockets.append(conn)
                    print('Connection accepted from ' + addr[0] + ':' + str(addr[1]))
                    p = Player('test', conn, GamePlayer('test', None))
                    self.socktoplayer[conn] = p
                    self.players.append(p)

                    self.gamethread.newplayers.put_nowait(p.gp)

                else:
                    try:
                        p = self.socktoplayer[s]

                    except:
                        continue

                    packet = None

                    try:
                        packet = net.handleRead(s, p)

                    except net.CloseConnectionException:
                        self.todelete.append(p)

                    if packet is not None:
                        p.incoming.append(packet)

            for s in writable:
                p = None
                try:
                    p = self.socktoplayer[s]

                except:
                    continue

                if len(p.tosend) > 0:
                    try:
                        p.tosend = p.tosend[s.send(p.tosend):]

                    except ConnectionError:
                        self.todelete.append(p)

            for s in exceptional:
                self.todelete.append(self.socktoplayer[s])

            for p in self.todelete:

                try:
                    self.players.remove(p)
                    del self.socktoplayer[p.conn]
                    self.sockets.remove(p.conn)
                    self.gamethread.offlineplayers.put_nowait(p.gp)
                    addr = p.conn.getpeername()
                    print("Closed connection from: " + addr[0] + ":" + str(addr[1]))
                    p.conn.close()

                except:
                    print("Encountered an error attempting to disconnect user!")

            self.todelete.clear()

            for p in self.players:
                for packet in p.incoming:
                    p.gp.tohandle.put_nowait(packet)

                p.incoming.clear()

        self.sock.close()
        self.gamethread.active = False
        self.gamethread.join()


if __name__ == '__main__':
    serverthread = AticAtacServer()
    serverthread.start()
    print('Server started on ' + serverthread.ip + ':' + str(serverthread.port))
    try:
        while True:
            time.sleep(10)

    except KeyboardInterrupt:
        print('Stopping server')
        serverthread.active = False
        serverthread.join()