# Entity classes: PacMan, Ghost, etc.
import pygame
from abc import ABC, abstractmethod

# Strategy Pattern for Movement
class MovementStrategy(ABC):
    @abstractmethod
    def move(self, entity, maze, dx, dy):
        pass

class KeyboardMovement(MovementStrategy):
    def move(self, entity, maze, dx, dy):
        new_x = entity.x + dx * entity.speed
        new_y = entity.y + dy * entity.speed
        if not maze.is_wall(new_x, new_y):
            entity.x = new_x
            entity.y = new_y
        entity.direction = (dx, dy)

class AIMovement(MovementStrategy):
    def move(self, entity, maze, dx, dy):
        # Simple AI: random movement or chase Pac-Man
        import random
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        random.shuffle(directions)
        for dx, dy in directions:
            new_x = entity.x + dx * entity.speed
            new_y = entity.y + dy * entity.speed
            if not maze.is_wall(new_x, new_y):
                entity.x = new_x
                entity.y = new_y
                entity.direction = (dx, dy)
                break

class Entity:
    def __init__(self, x, y, speed=2):
        self.x = x
        self.y = y
        self.speed = speed
        self.direction = (0, 0)

    def draw(self, screen):
        pass

class PacMan(Entity):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.movement_strategy = KeyboardMovement()

    def draw(self, screen):
        pygame.draw.circle(screen, (255, 255, 0), (int(self.x), int(self.y)), 10)

    def move(self, maze, keys):
        dx, dy = 0, 0
        if keys[pygame.K_LEFT]:
            dx = -1
        elif keys[pygame.K_RIGHT]:
            dx = 1
        elif keys[pygame.K_UP]:
            dy = -1
        elif keys[pygame.K_DOWN]:
            dy = 1
        self.movement_strategy.move(self, maze, dx, dy)

class Ghost(Entity):
    def __init__(self, x, y, color):
        super().__init__(x, y)
        self.color = color
        self.movement_strategy = AIMovement()

    def draw(self, screen):
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), 10)

    def move(self, maze):
        self.movement_strategy.move(self, maze, 0, 0)

# Factory Pattern for Ghosts
class GhostFactory:
    @staticmethod
    def create_ghosts():
        colors = [(255, 0, 0), (255, 0, 255), (0, 255, 255), (255, 165, 0)]  # Red, Pink, Cyan, Orange
        positions = [(60, 40), (80, 40), (100, 40), (120, 40)]  # Example positions
        return [Ghost(x, y, color) for (x, y), color in zip(positions, colors)]