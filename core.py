import server
import random

class Room():
    def __init__(self, roomtype, roomid):
        self.roomtype = roomtype
        self.roomobjects = []
        self.toremove = []
        self.roomid = roomid
        self.players = [] # A list of players that are currently observing this room
        self.newobjects = []

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


class GameObject():
    def __init__(self, x, y, objid=-1):
        self._x = x
        self._y = y
        self.id = objid
        self.poschange = False

    @classmethod
    def generateBasic(cls, x, y):
        raise NotImplementedError

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

class PlayerObj(GameObject):
    def __init__(self, x, y):
        super().__init__(x, y)

    @classmethod
    def generateBasic(cls, x, y):
        return PlayerObj(x, y)

class Door(GameObject):
    def __init__(self, x, y, roomtogo):
        super().__init__(x, y)
        self.roomtogo = roomtogo

    @classmethod
    def generateBasic(cls, x, y):
        return Door(x, y, None)

gobjTypes = [
    PlayerObj,
    Door
]