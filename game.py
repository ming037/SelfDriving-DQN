import numpy as np
import random

import matplotlib.pyplot as plt
import matplotlib.patches as patches

import pygame
import math
from pygame.locals import Rect, DOUBLEBUF, QUIT, K_ESCAPE, KEYDOWN, K_DOWN, K_LEFT, K_UP, K_RIGHT, KEYUP, K_LCTRL, K_RETURN, FULLSCREEN
X_MAX = 400
Y_MAX = 600

LEFT, RIGHT, STAY = 0, 1, 2
START, STOP = 0, 1
everything = pygame.sprite.Group()
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (166, 166 ,166)
car_position = [45, 125, 205, 285, 365]


class Lines(pygame.sprite.Sprite):
    def __init__(self, x_pos, y_pos):
        self.start_point = y_pos
        pygame.sprite.Sprite.__init__(self)
        self.image = pygame.Surface((10, 50))
        self.width = 50
        self.image.fill(WHITE)
        self.rect = self.image.get_rect()
        self.rect.x = x_pos
        self.rect.y = y_pos
        self.speedy = 7

    def update(self):
        self.rect.y += self.speedy
        if self.rect.top > Y_MAX + 100:
            self.rect.y = -100


class ObstacleSprite(pygame.sprite.Sprite):
    def __init__(self, x_pos, groups):
        super(ObstacleSprite, self).__init__()
        self.image = pygame.image.load("other.png").convert_alpha()
        self.image = pygame.transform.scale(self.image, (40, 60))
        self.rect = self.image.get_rect()
        self.rect.center = (x_pos, random.randint(-2500, 0))
        self.velocity = 6
        self.add(groups)
        self.save_x = x_pos
        self.check = False

    def update(self):
        x, y = self.rect.center
        if y > Y_MAX:
            x, y = self.save_x, random.randint(-2500, 0)
            self.velocity = 6
            self.check = False
        else:
            x, y = x, y + self.velocity
        self.rect.center = x, y

    def reset(self):
        x, y = self.save_x, random.randint(-2500, 0)
        self.velocity = 6
        self.rect.center = x, y
        self.check = False


class CarSprite(pygame.sprite.Sprite):
    def __init__(self, groups):
        super(CarSprite, self).__init__()
        self.image = pygame.image.load("car.png").convert_alpha()
        self.image = pygame.transform.scale(self.image, (40, 60))
        self.rect = self.image.get_rect()
        self.rect.center = (205, Y_MAX - 100)
        self.dx = self.dy = 0

        self.score = 0
        self.groups = [groups]
        self.mega = 1
        self.autopilot = False
        self.in_position = False
        self.velocity = 2

    def update(self):
        x, y = self.rect.center
        if not self.autopilot:
            # Handle movement
            self.rect.center = x + self.dx, y + self.dy
            if self.rect.center[0] < car_position[0]:
                self.rect.center = car_position[0], y
            if self.rect.center[0] > car_position[4]:
                self.rect.center = car_position[4], y

    def steer(self, direction, operation):
        v = 10
        if operation == START:
            if direction in (LEFT, RIGHT, STAY):
                self.dx = {LEFT: -v,
                           RIGHT: v,
                           STAY: 0}[direction]
        if operation == STOP:
            if direction in (LEFT, RIGHT, STAY):
                self.dx = 0

    def reset(self):
        self.rect.center = (205, Y_MAX - 100)
        self.dx = self.dy = 0


class Game:
    def __init__(self, screen_width, screen_height, show_game=True):
        self.screen_width = screen_width
        self.screen_height = screen_height

        self.screen = pygame.display.set_mode((X_MAX, Y_MAX), DOUBLEBUF)
        self.empty = pygame.Surface((X_MAX, Y_MAX))

        self.mycar = CarSprite(everything)
        self.mycar.add(everything)
        self.otherCar = pygame.sprite.Group()
        interval = 80
        for j in range(15):
            for i in range(4):
                line = Lines(interval + i * interval, j * 100)
                everything.add(line)
        # clock = pygame.time.Clock()

        for i in range(5):
            ObstacleSprite(car_position[i], [everything, self.otherCar])

        self.total_reward = 0.
        self.current_reward = 0.
        self.total_game = 0
        self.show_game = show_game

    def _get_state(self):
        tmp_x = self.screen_width  # 6
        tmp_y = self.screen_height  # 10
        state = np.zeros((tmp_x, tmp_y))
        div = 80

        state[int((self.mycar.rect.center[0] + 35)/div), int(500/60)] = 1
        for other in self.otherCar:
            if 0 <= other.rect.center[1] < Y_MAX:
                state[int((other.rect.center[0]+35)/div), int(other.rect.center[1]/60)] = 1
        return state

    def _draw_screen(self):
        title = " Avg: %0.3d Reward: %0.3f Total Game: %d" % (
                        self.total_reward / self.total_game,
                        self.current_reward,
                        self.total_game)

        pygame.display.set_caption(title)
        everything.clear(self.screen, self.empty)
        self.screen.fill(GRAY)
        everything.update()
        everything.draw(self.screen)
        pygame.display.flip()

    def reset(self):
        self.current_reward = 0
        self.total_game += 1

        self.mycar.reset()
        for other in self.otherCar:
            other.reset()

        self._update_block()
        return self._get_state()

    def _update_car(self, move):
        self.mycar.steer(move, START)
        self.mycar.update()
        self.mycar.steer(move, STOP)

    def _update_block(self):
        reward = 0
        my_y = self.mycar.rect.center[1]
        my_x = self.mycar.rect.center[0]
        for other in self.otherCar:
            other.update()
            temp_y = other.rect.center[1]
            temp_x = other.rect.center[0]
            calc_y = my_y-temp_y
            calc_x = my_x-temp_x
            if 100 <= temp_y <= Y_MAX:
                distance = math.sqrt(calc_x*calc_x+calc_y*calc_y)
                if distance > 300:
                    reward += 0.05
                elif distance > 200:
                    reward += 0.03
                elif distance > 100:
                    reward += 0.01
                else:
                    reward -= 0.05
        return reward

    def _is_gameover(self):
        hit = pygame.sprite.spritecollide(self.mycar, self.otherCar, False)
        if len(hit) >= 1:
            self.total_reward += self.current_reward
            return True
        else:
            return False

    def step(self, action):
        # action: 0: 좌, 1: 우, 2: 유지
        self._update_car(action)
        escape_reward = self._update_block()
        stable_reward = 1. / self.screen_height if action == 1 else 0
        gameover = self._is_gameover()

        if gameover:
            reward = -4
        else:
            reward = escape_reward # + stable_reward
            self.current_reward += reward
        if self.show_game:
            self._draw_screen()

        return self._get_state(), reward, gameover
