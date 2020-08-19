import random
from pygame.rect import Rect

class Room():
    def __init__(self, roomtype, roomid, game):
        self.roomtype = roomtype
        self.roomobjects = []
        self.game = game
        self.roomid = roomid
        self.players = [] # A list of players that are currently observing this room
        self.newobjects = []
        self.todelete = []

    def addObject(self, gobj):
        idtaken = True

        while idtaken:
            idtaken = False
            chosenid = random.randrange(0, 65535)
            gobj.id = chosenid

            for obj in self.roomobjects:
                if obj.id == chosenid:
                    idtaken = True
                    break

        self.roomobjects.append(gobj)
        self.newobjects.append(gobj)

    def deleteObject(self, gobj):
        self.todelete.append(gobj)

class GameObject():
    def __init__(self, x, y, objid=-1):
        self._x = x
        self._y = y
        self.id = objid
        self.poschange = False

    @classmethod
    def generateBasic(cls, x, y,data):
        raise NotImplementedError

    def update(self, room):
        pass

    @property
    def x(self):
        return self._x

    @x.setter
    def x(self, x):
        self._x = x
        self.poschange = True

    @property
    def y(self):
        return self._y

    @y.setter
    def y(self, y):
        self._y = y
        self.poschange = True

    def getData(self):
        return 0

class PlayerObj(GameObject):
    def __init__(self, x, y):
        super().__init__(x, y)

    @classmethod
    def generateBasic(cls, x, y, data):
        return PlayerObj(x, y)

class Door(GameObject):
    def __init__(self, x, y, roomtogo):
        super().__init__(x, y)
        self.roomtogo = roomtogo

    @classmethod
    def generateBasic(cls, x, y, data):
        return Door(x, y, None)

    def update(self, room):
        for obj in room.roomobjects:
            if isinstance(obj, PlayerObj):
                prect = Rect(obj.x ,obj.y, 64, 64)
                myrect = Rect(self.x, self.y, 16, 16)

                if myrect.colliderect(prect):
                    for p in room.players:
                        if p.currobj == obj:
                            p.changeRoom(room.game.rooms[self.roomtogo])


gobjTypes = [
    PlayerObj,
    Door
]

gobjDict = {
    PlayerObj : 0,
    Door : 1
}

roomTypes = [
    [0, -1, 0, 0],
    [-1, 0, -1, 0],
    [0, -1, 0,-1],
    [0, 0, 0, -1],
    [0, -1, 0, 0],
    [0, 0, -1, 0],
    [-1, 0, 0, 0],
    [0, 0, 0, 0]
]
class RoomData():
    def __init__(self, x, y, type):
        self.x = x
        self.y = y
        self.floor = 0
        self.type = type
        #self.north = roomTypes[type][0]
        #self.east = roomTypes[type][1]
        #self.south = roomTypes[type][2]
        #self.west = roomTypes[type][3]
        self.doors = roomTypes[type][:]
        self.trap = -1
        self.passage1 = -1
        self.passage2 = -1


class GameMap():
    def __init__(self, startroom=True):
        self.rooms = []
        self.coordToRoom = {}

        if startroom:
            self.setRoom(RoomData(0, 0, 0))

    def setRoom(self, room):
        if (room.x, room.y) in self.coordToRoom.keys():
            self.rooms.remove(room)

        self.rooms.append(room)
        self.coordToRoom[(room.x, room.y)] = room

    def delRoom(self, room):
        self.rooms.remove(room)
        del self.coordToRoom[(room.x, room.y)]

    def getRoom(self, x, y):
        if (x, y) in self.coordToRoom.keys():
            return self.coordToRoom[(x, y)]

        else:
            return None

    def toDict(self):
        data = {}
        data['version'] = 0
        data['rooms'] = []

        for room in self.rooms:
            roomdict = {
                'x' : room.x,
                'y' : room.y,
                'floor' : room.floor,
                'passage1' : room.passage1,
                'passage2' : room.passage2,
                'doors' : room.doors,
                'type' : room.type
            }

            data['rooms'].append(roomdict)

        return data

    @classmethod
    def fromDict(cls, data):
        gmap = GameMap(startroom=False)
        for rdict in data['rooms']:
            room = RoomData(rdict['x'], rdict['y'], rdict['type'])
            room.floor = rdict['floor']
            room.passage1 = rdict['passage1']
            room.passage2 = rdict['passage2']
            room.doors = rdict['doors']

            gmap.setRoom(room)

        return gmap