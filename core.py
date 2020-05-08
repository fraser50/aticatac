import server
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
    def generateBasic(cls, x, y):
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