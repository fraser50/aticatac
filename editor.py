import pygame
import sys
import json
import os

import core

RED = (255, 0, 0)
YELLOW = (255, 255, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)

PINK = (245, 0, 190)

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

GREY = (200, 200, 200)

roomarea_width  = 512
roomarea_height = 512

EDIT_ROOM_SIZE = 64

MAP_FILE = 'map.json'

cameraX = (-roomarea_width / 2) + EDIT_ROOM_SIZE
cameraY = (-roomarea_height / 2) + EDIT_ROOM_SIZE

mouseX = 0
mouseY = 0

SPEED = 3 # 4

doorColours = [
    WHITE,
    RED,
    GREEN,
    BLUE
]

doorToDisp = [
    (0, -1),
    (1, 0),
    (0, 1),
    (-1, 0)
]

def findDoors(room):
    return (
        pygame.Rect(((room.x * EDIT_ROOM_SIZE) - cameraX) + ((EDIT_ROOM_SIZE / 2) - 8),
                    ((room.y * EDIT_ROOM_SIZE) - cameraY), 16, 16),

        pygame.Rect(((room.x * EDIT_ROOM_SIZE) - cameraX + EDIT_ROOM_SIZE - 16),
                    ((room.y * EDIT_ROOM_SIZE) - cameraY) + ((EDIT_ROOM_SIZE / 2) - 8), 16, 16),

        pygame.Rect(((room.x * EDIT_ROOM_SIZE) - cameraX) + ((EDIT_ROOM_SIZE / 2) - 8),
                    ((room.y * EDIT_ROOM_SIZE) - cameraY + EDIT_ROOM_SIZE - 16), 16, 16),

        pygame.Rect(((room.x * EDIT_ROOM_SIZE) - cameraX - 0),
                    ((room.y * EDIT_ROOM_SIZE) - cameraY
                     ) + ((EDIT_ROOM_SIZE / 2) - 8), 16, 16)
    )


def validateRoom(x, y, map, type):
    for i in range(4):
        if map.getRoom(x + doorToDisp[i][0], y + doorToDisp[i][1]) is not None:
            room = map.getRoom(x + doorToDisp[i][0], y + doorToDisp[i][1])
            if room.doors[(i + 2) % 4] >= 0 and type[0][i] == -1:
                return False

    return True

    '''if map.getRoom(x + doorToDisp[0][0], y + doorToDisp[0][1]) is not None:
        northroom = map.getRoom(x + doorToDisp[0][0], y + doorToDisp[0][1])
        if northroom.doors[2] >= 0 and type[0][0] >= 0:
            return True

        else:
            return False'''

def closeHandler(map):
    with open(MAP_FILE, 'w') as f:
        f.write(json.dumps(map.toDict(), indent=4))

    sys.exit()

clock = pygame.time.Clock()

pygame.init()

screen = pygame.display.set_mode((roomarea_width, roomarea_height))

if os.path.exists(MAP_FILE):
    with open(MAP_FILE, 'r') as f:
        gamemap = core.GameMap.fromDict(json.loads(f.read()))

else:
    gamemap = core.GameMap()

while True:

    mouseX, mouseY = pygame.mouse.get_pos()

    selectedX = int((cameraX + mouseX) / EDIT_ROOM_SIZE)
    selectedY = int((cameraY + mouseY) / EDIT_ROOM_SIZE)

    if cameraX + mouseX < 0: selectedX -= 1
    if cameraY + mouseY < 0: selectedY -= 1

    selectedDoor = -1

    if gamemap.getRoom(selectedX, selectedY) is not None:
        selectedRoomDoors = findDoors(gamemap.getRoom(selectedX, selectedY))
        mouserect = pygame.Rect(mouseX, mouseY, 0, 0)
        for x in range(len(selectedRoomDoors)):
            if mouserect.colliderect(selectedRoomDoors[x]) and gamemap.getRoom(selectedX, selectedY).doors[x] >= 0:
                selectedDoor = x
                break


    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            closeHandler(gamemap)

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: # Left click
                room = gamemap.getRoom(selectedX, selectedY)
                if room == None or selectedDoor == -1: continue
                disp = doorToDisp[selectedDoor]

                newX = room.x + disp[0]
                newY = room.y + disp[1]

                if gamemap.getRoom(newX, newY) is None:
                    possibleTypes = core.roomTypes[1:]
                    possibleTypes = list(filter(lambda a: validateRoom(newX, newY, gamemap, a), zip(possibleTypes, range(len(possibleTypes)))))

                    if len(possibleTypes) > 0:
                        gamemap.setRoom(core.RoomData(newX, newY, possibleTypes[0][1] + 1))

                else:
                    room.doors[selectedDoor] += 1
                    room.doors[selectedDoor] %= len(doorColours)
                    gamemap.getRoom(newX, newY).doors[(selectedDoor + 2) % 4] = room.doors[selectedDoor]

            elif event.button == 3:
                room = gamemap.getRoom(selectedX, selectedY)
                if room is not None and selectedDoor == -1 and room.type > 0:
                    possibleTypes = core.roomTypes[1:]
                    possibleTypes = list(filter(lambda a: validateRoom(selectedX, selectedY, gamemap, a),
                                                zip(possibleTypes, range(len(possibleTypes)))))



                    currentIndex = -1
                    for x in range(len(possibleTypes)):
                        if possibleTypes[x][1] + 1 == room.type:
                            currentIndex = x
                            break

                    currentIndex = (currentIndex + 1) % len(possibleTypes)
                    newDoors = possibleTypes[currentIndex][0][:]
                    for x in range(4):
                        if newDoors[x] == 0 and room.doors[x] >= 0:
                            newDoors[x] = room.doors[x]

                    room.doors = newDoors
                    room.type = possibleTypes[currentIndex][1] + 1


    keys = pygame.key.get_pressed()

    if keys[pygame.K_LEFT]:
        cameraX -= SPEED

    if keys[pygame.K_RIGHT]:
        cameraX += SPEED

    if keys[pygame.K_UP]:
        cameraY -= SPEED

    if keys[pygame.K_DOWN]:
        cameraY += SPEED

    if keys[pygame.K_ESCAPE]:
        closeHandler(gamemap)


    screen.fill(WHITE)

    for room in gamemap.rooms:
        if room.x == selectedX and room.y == selectedY and selectedDoor == -1:
            pygame.draw.rect(screen, GREY,
                             pygame.Rect(((room.x * EDIT_ROOM_SIZE) - cameraX), ((room.y * EDIT_ROOM_SIZE) - cameraY),
                                         EDIT_ROOM_SIZE, EDIT_ROOM_SIZE))

        if room.type == 0:
            pygame.draw.rect(screen, PINK,
                             pygame.Rect(((room.x * EDIT_ROOM_SIZE) - cameraX), ((room.y * EDIT_ROOM_SIZE) - cameraY),
                                         EDIT_ROOM_SIZE, EDIT_ROOM_SIZE))

        pygame.draw.rect(screen, BLACK,
                         pygame.Rect(((room.x * EDIT_ROOM_SIZE) - cameraX), ((room.y * EDIT_ROOM_SIZE) - cameraY),
                                     EDIT_ROOM_SIZE, EDIT_ROOM_SIZE), 2)

        doors = findDoors(room)

        for x in range(4):
            if room.doors[x] >= 0:
                if selectedDoor == x and room == gamemap.getRoom(selectedX, selectedY):

                    chosenColour = tuple(
                        map(lambda x: (200 / 255) * x, doorColours[room.doors[x]])
                    )

                    pygame.draw.rect(screen, chosenColour, doors[x])

                else:
                    pygame.draw.rect(screen, doorColours[room.doors[x]], doors[x])

                pygame.draw.rect(screen, BLACK, doors[x], 2)


    pygame.display.flip()
    fps = clock.tick(60)