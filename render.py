import core
from pygame import Rect

RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

def renderPlayer(surface, obj):
    surface.fill(GREEN, Rect(obj.x, obj.y, 16, 16))

def renderDoor(surface, obj):
    surface.fill(RED, Rect(obj.x, obj.y, 16, 16))


renderdict = {
    core.PlayerObj : renderPlayer,
    core.Door : renderDoor
}