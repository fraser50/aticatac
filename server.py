import threading
import socket
import select
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

            if rd.type == 0:
                room.addObject(core.Food(128, 128, 0))

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

    def changeRoom(self, room, x=256 - 32, y=256 - 32):
        if self.room != None:
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

        #self.rooms = [core.Room(0, 0, self), core.Room(0, 1, self)]

        with open('map.json', 'r') as f:
            self.rooms = buildMap(core.GameMap.fromDict(json.loads(f.read())), self)

        #self.rooms[0].addObject(core.Door(300, 300, 1, 3, 1))
        #self.rooms[1].addObject(core.Door(16, 16, 0, 0, 0))
        self.outgoingqueue = queue.Queue() # This queue is for packets that should be sent to everyone in a room
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

                if p.currobj != None:
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
                        p.tosend.put_nowait(net.SendObjectPacket(obj.x, obj.y, obj.getData(), core.gobjDict[obj.__class__], obj.id))

                room.newobjects.clear()

                for obj in room.roomobjects:
                    obj.update(room)

                    if obj.poschange:
                        obj.poschange = False
                        for p in room.players:
                            if p.currobj != obj:
                                p.tosend.put(net.UpdateObjectPosition(obj.id, obj.x, obj.y))



class AticAtacServer(threading.Thread):
    def __init__(self):
        super().__init__(name='AticAtacServer')
        self.active = True

    def run(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setblocking(False)
        self.sock.bind(('127.0.0.1', 13225))
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
    try:
        serverthread.join()

    except KeyboardInterrupt:
        serverthread.active = False
        serverthread.join()