import core
import pygame

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

# Foods
foodImages = (
    loadImage('assets/graphics/food/chocolate.png', 64, 64),
)

door_keys = (
    loadImage('assets/graphics/door/door_red.png', core.DOOR_SIZE, core.DOOR_SIZE),
    loadImage('assets/graphics/door/door_green.png', core.DOOR_SIZE, core.DOOR_SIZE),
    loadImage('assets/graphics/door/door_blue.png', core.DOOR_SIZE, core.DOOR_SIZE),
)

room_generic = loadImage('assets/graphics/room/room_generic.png', 512, 512)
room_3way = loadImage('assets/graphics/room/room_3way_junction.png', 512, 512)

graveimg = loadImage('assets/graphics/grave.png', 64, 64)

# Room background info: (surface, x_percent_offset, y_percent_offset)
# The only real reason the offsets exist is because I didn't manage to exactly centre the corridor image
room_images = (
    (room_generic, 0, 0),
    None,
    (room_3way, 0.03, 0),
    (room_3way, 0.03, 0),
    (room_3way, 0.03, 0),
    None,
    None,
    (room_generic, 0, 0)
)


class RenderState():
    def __init__(self, width, height):
        self.width = width
        self.height = height


def renderPlayer(surface, obj):
    rect = playerimg.get_rect()
    rect.left = obj.x
    rect.top = obj.y

    if obj.resurrect == 0:
        surface.blit(playerimg, rect)

    else:
        h = int((obj.resurrect / 100) * rect.height)
        arearect = pygame.Rect(0, h, rect.width, rect.height)
        rect.top += h
        surface.blit(playerimg, rect, arearect)


def renderDoor(surface, obj):
    door_surface = pygame.Surface((core.DOOR_SIZE, core.DOOR_SIZE), pygame.SRCALPHA, 32)
    door_surface.blit(doorclosedimg, (0, 0))

    if obj.colour != 0:
        door_surface.blit(door_keys[obj.colour - 1], (0, 0))

    transformedsurface = pygame.transform.rotate(door_surface, obj.rotation * 90)

    surface.blit(transformedsurface, pygame.Rect(obj.x, obj.y, core.DOOR_SIZE, core.DOOR_SIZE))


def renderFood(surface, obj):
    foodImg = foodImages[obj.getData()]
    rect = foodImg.get_rect()
    rect.left = obj.x
    rect.y = obj.y
    surface.blit(foodImg, rect)


def renderGrave(surface, obj):
    rect = graveimg.get_rect()
    rect.left = obj.x
    rect.top = obj.y
    surface.blit(graveimg, rect)


renderdict = {
    core.PlayerObj : renderPlayer,
    core.Door : renderDoor,
    core.Food : renderFood,
    core.Grave : renderGrave
}

BACKGROUND = 0
SCENE = 1
PLAYER = 2
THROW = 3

renderOrder = {
    core.PlayerObj : PLAYER,
    core.Door : BACKGROUND,
    core.Food : SCENE,
    core.Grave : SCENE
}