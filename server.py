import threading
import socket
import select
import struct
import core
import binascii
import random

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
    def __init__(self, name, conn, room):
        super().__init__(conn)
        self.name = name
        self.room = room
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


packet_types = [
    SetNamePacket,
    PlayerChangePos,
    SendObjectPacket,
    SendControlledUpdate,
    UpdateObjectPosition
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


class AticAtacServer(threading.Thread):
    def __init__(self):
        super().__init__(name='AticAtacServer')
        self.active = True

    def run(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setblocking(False)
        self.sock.bind(('127.0.0.1', 13225))
        self.sock.listen(5)
        self.rooms = []
        self.rooms.append(core.Room(0, 0))

        self.sockets = [self.sock]

        self.players = []

        self.socktoplayer = {}

        self.todelete = []

        while self.active:

            readable, writable, exceptional = select.select(self.sockets, self.sockets, self.sockets, 0.125)
            for s in readable:
                if s == self.sock:
                    conn, addr = s.accept()
                    conn.setblocking(False)
                    self.sockets.append(conn)
                    print('Connection accepted from ' + addr[0] + ':' + str(addr[1]))
                    p = Player('test', conn, self.rooms[0])
                    self.sockets.append(conn)
                    self.socktoplayer[conn] = p
                    self.players.append(p)

                    for obj in p.room.roomobjects:
                        p.sendPacket(SendObjectPacket(obj.x, obj.y, 0, obj.id))

                    pobj = core.PlayerObj(random.randrange(0, 496), random.randrange(0, 496))
                    p.room.addObject(pobj)

                    p.controlledobject = pobj.id

                    p.sendPacket(SendControlledUpdate(pobj.id))

                    annouceplayer = SendObjectPacket(pobj.x, pobj.y, 0, pobj.id)
                    for pl in self.players:
                        if p.room == pl.room:
                            pl.sendPacket(annouceplayer)


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
                    if isinstance(packet, PlayerChangePos):
                        for obj in p.room.roomobjects:
                            if obj.id == p.controlledobject:
                                obj.x = packet.x
                                obj.y = packet.y

                                objmovepack = UpdateObjectPosition(obj.id, obj.x, obj.y)

                                for pl in self.players:
                                    if pl != p and pl.room == p.room:
                                        pl.sendPacket(objmovepack)

                p.incoming.clear()

        self.sock.close()

if __name__ == '__main__':
    serverthread = AticAtacServer()
    serverthread.start()
    try:
        serverthread.join()

    except KeyboardInterrupt:
        serverthread.active = False
        serverthread.join()