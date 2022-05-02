import struct
import socket

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
    def __init__(self, x, y, rid):
        super().__init__(1)
        self.x = x
        self.y = y
        self.rid = rid

    def toBytes(self):
        return struct.pack('!iiH', self.x, self.y, self.rid)

    @classmethod
    def fromBytes(cls, bstr):
        x, y, rid = struct.unpack('!iiH', bstr)
        return PlayerChangePos(x, y, rid)


class SendObjectPacket(Packet):
    def __init__(self, x, y, type, data, uid):
        super().__init__(2)

        self.x = x
        self.y = y
        self.type = type
        self.data = data
        self.uid = uid

    def toBytes(self):
        return struct.pack('!iibbH', self.x, self.y, self.type, self.data, self.uid)

    @classmethod
    def fromBytes(cls, bstr):
        x, y, type, data, uid = struct.unpack('!iibbH', bstr)
        return SendObjectPacket(x, y, type, data, uid)


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
        return RemoveObjectPacket(struct.unpack('!H', bstr)[0])


class SwitchRoomPacket(Packet):
    def __init__(self, roomid, roomtype):
        super().__init__(6)

        self.roomid = roomid
        self.roomtype = roomtype

    def toBytes(self):
        return struct.pack('!Hb', self.roomid, self.roomtype)

    @classmethod
    def fromBytes(cls, bstr):
        roomid, roomtype = struct.unpack('!Hb', bstr)
        return SwitchRoomPacket(roomid, roomtype)


class SetFoodPacket(Packet):
    def __init__(self, food):
        super().__init__(7)
        self.food = food

    def toBytes(self):
        return struct.pack('!H', self.food)

    @classmethod
    def fromBytes(cls, bstr):
        food = struct.unpack('!H', bstr)[0]
        return SetFoodPacket(food)


packet_types = [
    SetNamePacket,
    PlayerChangePos,
    SendObjectPacket,
    SendControlledUpdate,
    UpdateObjectPosition,
    RemoveObjectPacket,
    SwitchRoomPacket,
    SetFoodPacket
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
        raise CloseConnectionException()

    p.currdata += datareceived

    if p.currentpos == 2:
        if p.currdata != magicbytes:
            raise CloseConnectionException()

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