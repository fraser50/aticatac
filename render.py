import core
import pygame
#from pygame import Rect

RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)


def loadImage(path, width, height):
    img = pygame.image.load(path)
    img = pygame.transform.scale(img, (width, height,))
    return img

playerimg = loadImage('assets/graphics/player.png', 64, 64)
doorclosedimg = loadImage('assets/graphics/door/door_closed.png', core.DOOR_SIZE, core.DOOR_SIZE)

door_keys = (
    loadImage('assets/graphics/door/door_red.png', core.DOOR_SIZE, core.DOOR_SIZE),
    loadImage('assets/graphics/door/door_green.png', core.DOOR_SIZE, core.DOOR_SIZE),
    loadImage('assets/graphics/door/door_blue.png', core.DOOR_SIZE, core.DOOR_SIZE),
)

class RenderState():
    def RenderState(self, width, height):
        self.width = width
        self.height = height

def renderPlayer(surface, obj):
    rect = playerimg.get_rect()
    rect.left = obj.x
    rect.top = obj.y
    surface.blit(playerimg, rect)
    #surface.fill(GREEN, pygame.Rect(obj.x, obj.y, 16, 16))

def renderDoor(surface, obj):
    door_surface = pygame.Surface((core.DOOR_SIZE, core.DOOR_SIZE), pygame.SRCALPHA, 32)
    door_surface.blit(doorclosedimg, (0, 0))

    if obj.colour != 0:
        door_surface.blit(door_keys[obj.colour - 1], (0, 0))

    transformedsurface = pygame.transform.rotate(door_surface, obj.rotation * 90)

    surface.blit(transformedsurface, pygame.Rect(obj.x, obj.y, core.DOOR_SIZE, core.DOOR_SIZE))


renderdict = {
    core.PlayerObj : renderPlayer,
    core.Door : renderDoor
}