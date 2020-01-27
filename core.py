import server
import random

class Room():
    def __init__(self, roomtype, roomid):
        self.roomtype = roomtype
        self.roomobjects = []

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

class GameObject():
    def __init__(self, x, y, objid=-1):
        self.x = x
        self.y = y
        self.id = objid

class PlayerObj(GameObject):
    def __init__(self, x, y):
        super().__init__(x, y)

gobjTypes = [
    PlayerObj
]