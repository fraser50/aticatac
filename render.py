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
    surface.fill(RED, pygame.Rect(obj.x, obj.y, 16, 16))


renderdict = {
    core.PlayerObj : renderPlayer,
    core.Door : renderDoor
}