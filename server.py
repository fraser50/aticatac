import threading
import socket
import select
import struct
import core
import binascii
import random
import queue
from time import sleep

allowedchars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_'

magicbytes = bytes(bytearray.fromhex('4861'))

class ConnectedPeer():
    def __init__(self, conn):
        self.conn = conn

        self.tosend = b''

        self.currentpos = 0
        self.len = 0
        self.currdata = b''
        self.incoming = []

    def sendPacket(self, pack):
        self.tosend += magicbytes
        packbytes = pack.toBytes()
        self.tosend += int(1 + len(packbytes)).to_bytes(2, byteorder='big')
        self.tosend += pack.packetid.to_bytes(1, byteorder='big')
        self.tosend += packbytes

class Player(ConnectedPeer):
    def __init__(self, name, conn, gp):
        super().__init__(conn)
        self.name = name
        self.gp = gp
        self.controlledobject = -1


class CloseConnectionException(Exception):
    pass


class Packet():
    def __init__(self, packetid):
        self.packetid = packetid

    def toBytes(self):
        raise NotImplementedError()

    @classmethod
    def fromBytes(cls, bstr):
        raise NotImplementedError()


class SetNamePacket(Packet):
    def __init__(self, name):
        super().__init__(0)
        self.name = name


class PlayerChangePos(Packet):

    def __init__(self, x, y):
        super().__init__(1)
        self.x = x
        self.y = y

    def toBytes(self):
        return struct.pack('!ii', self.x, self.y)

    @classmethod
    def fromBytes(cls, bstr):
        x, y = struct.unpack('!ii', bstr)
        return PlayerChangePos(x, y)


class SendObjectPacket(Packet):
    def __init__(self, x, y, type, uid):
        super().__init__(2)

        self.x = x
        self.y = y
        self.type = type
        self.uid = uid

    def toBytes(self):
        return struct.pack('!iibH', self.x, self.y, self.type, self.uid)

    @classmethod
    def fromBytes(cls, bstr):
        x, y, type, uid = struct.unpack('!iibH', bstr)
        return SendObjectPacket(x, y, type, uid)


class SendControlledUpdate(Packet):
    def __init__(self, objectid):
        super().__init__(3)

        self.objectid = objectid

    def toBytes(self):
        return struct.pack('!H', self.objectid)

    @classmethod
    def fromBytes(cls, bstr):
        return SendControlledUpdate(struct.unpack('!H', bstr)[0])

class UpdateObjectPosition(Packet):
    def __init__(self, uid, x, y):
        super().__init__(4)

        self.uid = uid
        self.x = x
        self.y = y

    def toBytes(self):
        return struct.pack('!Hii', self.uid, self.x, self.y)

    @classmethod
    def fromBytes(cls, bstr):
        uid, x, y = struct.unpack('!Hii', bstr)
        return UpdateObjectPosition(uid, x, y)

class RemoveObjectPacket(Packet):
    def __init__(self, uid):
        super().__init__(5)
        self.uid = uid

    def toBytes(self):
        return struct.pack('!H', self.uid)

    @classmethod
    def fromBytes(cls, bstr):
        return RemoveObjectPacket(struct.unpack('!H', bstr))


packet_types = [
    SetNamePacket,
    PlayerChangePos,
    SendObjectPacket,
    SendControlledUpdate,
    UpdateObjectPosition,
    RemoveObjectPacket
]

def handleRead(s, p):
    torecv = 0

    if p.len == 0:
        if len(p.currdata) < 2:
            torecv = 2 - len(p.currdata)

    else:
        torecv = p.len - p.currentpos + 4
        if torecv > 1024: torecv = 1024

    datareceived = None

    try:
        datareceived = s.recv(torecv)
        p.currentpos += len(datareceived)

    except socket.error:
        return

    if len(datareceived) == 0:
        #self.active = False
        print('Closing connection...')
        raise CloseConnectionException()  # TODO: disconnect client

    p.currdata += datareceived

    if p.currentpos == 2:
        if p.currdata != magicbytes:
            raise CloseConnectionException()  # TODO: disconnect client

        else:
            p.currdata = b''

    if p.currentpos == 4:
        p.len = int.from_bytes(p.currdata, byteorder='big')
        p.currdata = b''

    if p.len == len(p.currdata) and p.len > 0:

        packetid = p.currdata[0]
        p.currdata = p.currdata[1:]

        packet = None

        if packetid < len(packet_types):
            try:
                packet = packet_types[packetid].fromBytes(p.currdata)

            except:
                pass

        p.currentpos = 0
        p.len = 0
        p.currdata = b''

        return packet


class GamePlayer():
    def __init__(self, name, room):
        self.name = name
        self.room = room
        self.tohandle = queue.Queue()
        self.tosend = queue.Queue()
        self.currobj = None


class AticAtacGame(threading.Thread):
    def __init__(self):
        super().__init__(name='AticAtacGame')
        self.active = True

        self.rooms = [core.Room(0, 0), core.Room(0, 1)]
        self.outgoingqueue = queue.Queue() # This queue is for packets that should be sent to everyone in a room
        # Format (packet, roomid)

        self.players = []
        self.newplayers = queue.Queue()

    def run(self):
        while self.active:
            sleep(1/30)
            while not self.newplayers.empty():
                p = self.newplayers.get_nowait()
                p.room = self.rooms[0]

                pobj = core.PlayerObj(random.randrange(0, 496), random.randrange(0, 496))
                p.room.addObject(pobj)
                p.currobj = pobj

                p.room.players.append(p)
                self.players.append(p)

                for obj in p.room.roomobjects:
                    if obj != p.currobj:
                        p.tosend.put_nowait(SendObjectPacket(obj.x, obj.y, 0, obj.id))

                p.tosend.put_nowait(SendControlledUpdate(p.currobj.id))

            for p in self.players:
                while not p.tohandle.empty():
                    packet = p.tohandle.get_nowait()
                    if isinstance(packet, PlayerChangePos):
                        if p.currobj is not None:
                            p.currobj.x = packet.x
                            p.currobj.y = packet.y

            for room in self.rooms:
                for obj in room.newobjects:
                    for p in room.players:
                        p.tosend.put_nowait(SendObjectPacket(obj.x, obj.y, 0, obj.id))

                room.newobjects.clear()

                for obj in room.roomobjects:
                    if obj.poschange:
                        obj.poschange = False
                        for p in room.players:
                            if p.currobj != obj:
                                p.tosend.put(UpdateObjectPosition(obj.id, obj.x, obj.y))



class AticAtacServer(threading.Thread):
    def __init__(self):
        super().__init__(name='AticAtacServer')
        self.active = True

    def run(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setblocking(False)
        self.sock.bind(('127.0.0.1', 13225))
        self.sock.listen(5)
        #self.rooms = []
        #self.rooms.append(core.Room(0, 0))

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
                    self.sockets.append(conn)
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
                        packet = handleRead(s, p)

                    except CloseConnectionException:
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
                    p.tosend = p.tosend[s.send(p.tosend):]

            for s in exceptional:
                self.todelete.append(self.socktoplayer[s])

            for p in self.todelete:

                try:
                    self.players.remove(p)
                    del self.socktoplayer[p.conn]
                    self.sockets.remove(p.conn)

                except:
                    pass

            self.todelete.clear()

            for p in self.players:
                for packet in p.incoming:
                    p.gp.tohandle.put_nowait(packet)

                    '''if isinstance(packet, PlayerChangePos):
                        for obj in p.room.roomobjects:
                            if obj.id == p.controlledobject:
                                obj.x = packet.x
                                obj.y = packet.y

                                objmovepack = UpdateObjectPosition(obj.id, obj.x, obj.y)

                                for pl in self.players:
                                    if pl != p and pl.room == p.room:
                                        pl.sendPacket(objmovepack)
                    '''

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