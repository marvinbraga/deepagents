import math
import random
import sys
from abc import ABC, abstractmethod
from typing import List, Optional

import pygame

# Constants
WIDTH, HEIGHT = 800, 600
FPS = 60
SHIP_SIZE = 20
BULLET_SIZE = 5
BULLET_SPEED = 10 * FPS
SHIP_SPEED = 0.1 * FPS
SHIP_ROTATION_SPEED = 5
ASTEROID_SIZES = [40, 25, 15]
ASTEROID_SPEEDS = [s * FPS for s in [1, 1.5, 2]]

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)

# Initialize Pygame
pygame.init()

# Set up the display
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Asteroids")
clock = pygame.time.Clock()
font = pygame.font.Font(None, 36)


# Strategy Pattern for Movement
class MovementStrategy(ABC):
    @abstractmethod
    def move(self, entity, dt: float) -> None:
        pass


class LinearMovement(MovementStrategy):
    def move(self, entity, dt: float) -> None:
        entity.x += entity.vx * dt
        entity.y += entity.vy * dt

        # Wrap around screen
        entity.x = entity.x % WIDTH
        entity.y = entity.y % HEIGHT


class ThrustMovement(MovementStrategy):
    def move(self, entity, dt: float) -> None:
        # Apply friction
        entity.vx *= 0.99
        entity.vy *= 0.99

        # Update position
        entity.x += entity.vx * dt
        entity.y += entity.vy * dt

        # Wrap around screen
        entity.x = entity.x % WIDTH
        entity.y = entity.y % HEIGHT


class AsteroidMovement(MovementStrategy):
    def move(self, entity, dt: float) -> None:
        entity.x += entity.vx * dt
        entity.y += entity.vy * dt
        entity.angle += entity.rotation_speed * dt

        # Wrap around screen
        if entity.x < -entity.radius:
            entity.x = WIDTH + entity.radius
        elif entity.x > WIDTH + entity.radius:
            entity.x = -entity.radius
        if entity.y < -entity.radius:
            entity.y = HEIGHT + entity.radius
        elif entity.y > HEIGHT + entity.radius:
            entity.y = -entity.radius


class BulletMovement(MovementStrategy):
    def move(self, entity, dt: float) -> None:
        entity.x += entity.vx * dt
        entity.y += entity.vy * dt
        entity.lifetime -= 1


# Strategy Pattern for Rendering
class RenderStrategy(ABC):
    @abstractmethod
    def render(self, entity, screen) -> None:
        pass


class ShipRenderer(RenderStrategy):
    def render(self, entity, screen) -> None:
        rad_angle = math.radians(entity.angle)
        # Ship points
        points = [
            (entity.x + math.cos(rad_angle) * SHIP_SIZE, entity.y + math.sin(rad_angle) * SHIP_SIZE),
            (entity.x + math.cos(rad_angle + 2.5) * SHIP_SIZE * 0.6,
             entity.y + math.sin(rad_angle + 2.5) * SHIP_SIZE * 0.6),
            (entity.x + math.cos(rad_angle - 2.5) * SHIP_SIZE * 0.6,
             entity.y + math.sin(rad_angle - 2.5) * SHIP_SIZE * 0.6)
        ]
        pygame.draw.polygon(screen, WHITE, points)


class AsteroidRenderer(RenderStrategy):
    def render(self, entity, screen) -> None:
        # Draw as irregular polygon
        points = []
        for i in range(8):
            angle = math.radians(entity.angle + i * 45)
            r = entity.radius + random.uniform(-5, 5)
            px = entity.x + math.cos(angle) * r
            py = entity.y + math.sin(angle) * r
            points.append((px, py))
        pygame.draw.polygon(screen, WHITE, points, 2)


class BulletRenderer(RenderStrategy):
    def render(self, entity, screen) -> None:
        pygame.draw.circle(screen, WHITE, (int(entity.x), int(entity.y)), entity.radius)


# Base Entity Class
class Entity(ABC):
    def __init__(self, x: float, y: float, radius: float):
        self.x = x
        self.y = y
        self.radius = radius
        self.vx = 0.0
        self.vy = 0.0
        self.angle = 0.0
        self.movement_strategy: Optional[MovementStrategy] = None
        self.render_strategy: Optional[RenderStrategy] = None
        self.active = True

    def update(self, dt: float) -> None:
        if self.movement_strategy:
            self.movement_strategy.move(self, dt)

    def draw(self, screen) -> None:
        if self.render_strategy:
            self.render_strategy.render(self, screen)

    def is_active(self) -> bool:
        return self.active

    def deactivate(self) -> None:
        self.active = False


# Ship Entity
class Ship(Entity):
    def __init__(self):
        super().__init__(WIDTH // 2, HEIGHT // 2, SHIP_SIZE)
        self.movement_strategy = ThrustMovement()
        self.render_strategy = ShipRenderer()

    def rotate(self, direction: int) -> None:
        self.angle += direction * SHIP_ROTATION_SPEED

    def thrust(self) -> None:
        rad_angle = math.radians(self.angle)
        self.vx += math.cos(rad_angle) * SHIP_SPEED
        self.vy += math.sin(rad_angle) * SHIP_SPEED


# Asteroid Entity
class Asteroid(Entity):
    def __init__(self, x: Optional[float] = None, y: Optional[float] = None, size: int = 0, speed_mult: float = 1):
        self.size = size
        radius = ASTEROID_SIZES[size]
        if x is None:
            x = random.randint(radius, WIDTH - radius)
        if y is None:
            y = random.randint(radius, HEIGHT - radius)
        super().__init__(x, y, radius)
        self.vx = random.uniform(-ASTEROID_SPEEDS[size] * speed_mult, ASTEROID_SPEEDS[size] * speed_mult)
        self.vy = random.uniform(-ASTEROID_SPEEDS[size] * speed_mult, ASTEROID_SPEEDS[size] * speed_mult)
        self.angle = random.uniform(0, 360)
        self.rotation_speed = random.uniform(-2, 2)
        self.movement_strategy = AsteroidMovement()
        self.render_strategy = AsteroidRenderer()


# Bullet Entity
class Bullet(Entity):
    def __init__(self, x: float, y: float, angle: float):
        super().__init__(x, y, BULLET_SIZE)
        rad_angle = math.radians(angle)
        self.vx = math.cos(rad_angle) * BULLET_SPEED
        self.vy = math.sin(rad_angle) * BULLET_SPEED
        self.lifetime = 60  # frames
        self.movement_strategy = BulletMovement()
        self.render_strategy = BulletRenderer()

    def is_alive(self) -> bool:
        return self.lifetime > 0


# Factory Method Pattern for Entity Creation
class EntityFactory(ABC):
    @abstractmethod
    def create_entity(self, *args, **kwargs) -> Entity:
        pass


class ShipFactory(EntityFactory):
    def create_entity(self, *args, **kwargs) -> Ship:
        return Ship()


class AsteroidFactory(EntityFactory):
    def create_entity(self, *args, **kwargs) -> Asteroid:
        x = kwargs.get('x')
        y = kwargs.get('y')
        size = kwargs.get('size', 0)
        speed_mult = kwargs.get('speed_mult', 1)
        return Asteroid(x, y, size, speed_mult)


class BulletFactory(EntityFactory):
    def create_entity(self, *args, **kwargs) -> Bullet:
        x = kwargs['x']
        y = kwargs['y']
        angle = kwargs['angle']
        return Bullet(x, y, angle)


# Observer Pattern for Events
class Event(ABC):
    pass


class CollisionEvent(Event):
    def __init__(self, entity1: Entity, entity2: Entity):
        self.entity1 = entity1
        self.entity2 = entity2


class ScoreEvent(Event):
    def __init__(self, points: int):
        self.points = points


class LifeLostEvent(Event):
    def __init__(self):
        pass


class LevelCompleteEvent(Event):
    def __init__(self, level: int):
        self.level = level


class Observer(ABC):
    @abstractmethod
    def on_event(self, event: Event) -> None:
        pass


class EventManager:
    def __init__(self):
        self.observers: List[Observer] = []

    def add_observer(self, observer: Observer) -> None:
        self.observers.append(observer)

    def remove_observer(self, observer: Observer) -> None:
        self.observers.remove(observer)

    def notify(self, event: Event) -> None:
        for observer in self.observers:
            observer.on_event(event)


# Collision Detector
class CollisionDetector:
    @staticmethod
    def check_collision(entity1: Entity, entity2: Entity) -> bool:
        dx = entity1.x - entity2.x
        dy = entity1.y - entity2.y
        distance = math.sqrt(dx ** 2 + dy ** 2)
        return distance < entity1.radius + entity2.radius


# Score Manager
class ScoreManager(Observer):
    def __init__(self, event_manager: EventManager):
        self.score = 0
        self.lives = 3
        event_manager.add_observer(self)

    def on_event(self, event: Event) -> None:
        if isinstance(event, ScoreEvent):
            self.score += event.points
        elif isinstance(event, LifeLostEvent):
            self.lives -= 1

    def reset(self) -> None:
        self.score = 0
        self.lives = 3


# Level Manager
class LevelManager(Observer):
    def __init__(self, event_manager: EventManager, asteroid_factory: AsteroidFactory):
        self.level = 1
        self.asteroid_factory = asteroid_factory
        event_manager.add_observer(self)

    def on_event(self, event: Event) -> None:
        if isinstance(event, LevelCompleteEvent):
            self.level = event.level

    def create_asteroids_for_level(self) -> List[Asteroid]:
        num_asteroids = 5 + (self.level - 1)
        asteroids = []
        for _ in range(num_asteroids):
            asteroids.append(self.asteroid_factory.create_entity(speed_mult=self.level))
        return asteroids


# Input Handler
class InputHandler:
    def __init__(self):
        self.keys_pressed = {}

    def update(self) -> None:
        self.keys_pressed = pygame.key.get_pressed()

    def is_key_pressed(self, key: int) -> bool:
        return self.keys_pressed[key]


# Renderer
class Renderer:
    def __init__(self, screen, font):
        self.screen = screen
        self.font = font

    def clear_screen(self) -> None:
        self.screen.fill(BLACK)

    def draw_entity(self, entity: Entity) -> None:
        entity.draw(self.screen)

    def draw_ui(self, score: int, lives: int, level: int) -> None:
        score_text = self.font.render(f"Score: {score}", True, WHITE)
        lives_text = self.font.render(f"Lives: {lives}", True, WHITE)
        level_text = self.font.render(f"Level: {level}", True, WHITE)
        self.screen.blit(score_text, (10, 10))
        self.screen.blit(lives_text, (WIDTH - 100, 10))
        self.screen.blit(level_text, (WIDTH // 2 - 50, 10))

    def flip_display(self) -> None:
        pygame.display.flip()


# State Pattern for Game States
class GameState(ABC):
    @abstractmethod
    def handle_events(self, events: List[pygame.event.Event]) -> Optional['GameState']:
        pass

    @abstractmethod
    def update(self, dt: float) -> None:
        pass

    @abstractmethod
    def render(self, renderer: Renderer) -> None:
        pass


class PlayingState(GameState):
    def __init__(self, game):
        self.game = game
        self.input_handler = game.input_handler
        self.collision_detector = game.collision_detector
        self.event_manager = game.event_manager
        self.ship = game.ship_factory.create_entity()
        self.asteroids = game.level_manager.create_asteroids_for_level()
        self.bullets: List[Bullet] = []

    def handle_events(self, events: List[pygame.event.Event]) -> Optional[GameState]:
        for event in events:
            if event.type == pygame.QUIT:
                return None
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    self.bullets.append(self.game.bullet_factory.create_entity(
                        x=self.ship.x, y=self.ship.y, angle=self.ship.angle))

        self.input_handler.update()
        if self.input_handler.is_key_pressed(pygame.K_LEFT):
            self.ship.rotate(-1)
        if self.input_handler.is_key_pressed(pygame.K_RIGHT):
            self.ship.rotate(1)
        if self.input_handler.is_key_pressed(pygame.K_UP):
            self.ship.thrust()

        return self

    def update(self, dt: float) -> Optional[GameState]:
        self.ship.update(dt)
        for asteroid in self.asteroids:
            asteroid.update(dt)
        self.bullets = [bullet for bullet in self.bullets if bullet.is_alive()]
        for bullet in self.bullets:
            bullet.update(dt)

        # Check collisions
        self.check_collisions()

        # Level progression
        if not self.asteroids:
            self.event_manager.notify(LevelCompleteEvent(self.game.level_manager.level + 1))
            self.asteroids = self.game.level_manager.create_asteroids_for_level()

        # Check game over
        if self.game.score_manager.lives <= 0:
            return GameOverState(self.game)

        return self

    def check_collisions(self) -> None:
        # Bullets vs asteroids
        for bullet in self.bullets[:]:
            for asteroid in self.asteroids[:]:
                if self.collision_detector.check_collision(bullet, asteroid):
                    self.bullets.remove(bullet)
                    self.asteroids.remove(asteroid)
                    points = (3 - asteroid.size) * 20
                    self.event_manager.notify(ScoreEvent(points))
                    # Split asteroid if not smallest
                    if asteroid.size < 2:
                        for _ in range(2):
                            self.asteroids.append(self.game.asteroid_factory.create_entity(
                                x=asteroid.x, y=asteroid.y, size=asteroid.size + 1))
                    break

        # Ship vs asteroids
        for asteroid in self.asteroids:
            if self.collision_detector.check_collision(self.ship, asteroid):
                self.event_manager.notify(LifeLostEvent())
                self.ship.x = WIDTH // 2
                self.ship.y = HEIGHT // 2
                self.ship.vx = 0
                self.ship.vy = 0
                break

    def render(self, renderer: Renderer) -> None:
        renderer.clear_screen()
        renderer.draw_entity(self.ship)
        for asteroid in self.asteroids:
            renderer.draw_entity(asteroid)
        for bullet in self.bullets:
            renderer.draw_entity(bullet)
        renderer.draw_ui(self.game.score_manager.score, self.game.score_manager.lives, self.game.level_manager.level)
        renderer.flip_display()


class GameOverState(GameState):
    def __init__(self, game):
        self.game = game
        self.input_handler = game.input_handler

    def handle_events(self, events: List[pygame.event.Event]) -> Optional[GameState]:
        for event in events:
            if event.type == pygame.QUIT:
                return None
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    # Reset game
                    self.game.score_manager.reset()
                    self.game.level_manager.level = 1
                    return PlayingState(self.game)
                elif event.key == pygame.K_q:
                    return None
        return self

    def update(self, dt: float) -> None:
        pass

    def render(self, renderer: Renderer) -> None:
        renderer.clear_screen()
        game_over_text = renderer.font.render("Game Over", True, WHITE)
        final_score_text = renderer.font.render(f"Final Score: {self.game.score_manager.score}", True, WHITE)
        restart_text = renderer.font.render("Press R to Restart", True, WHITE)
        quit_text = renderer.font.render("Press Q to Quit", True, WHITE)
        renderer.screen.blit(game_over_text, (WIDTH // 2 - 100, HEIGHT // 2 - 80))
        renderer.screen.blit(final_score_text, (WIDTH // 2 - 100, HEIGHT // 2 - 40))
        renderer.screen.blit(restart_text, (WIDTH // 2 - 100, HEIGHT // 2))
        renderer.screen.blit(quit_text, (WIDTH // 2 - 100, HEIGHT // 2 + 40))
        renderer.flip_display()


# Main Game Class
class Game:
    def __init__(self):
        self.screen = screen
        self.clock = clock
        self.font = font
        self.event_manager = EventManager()
        self.input_handler = InputHandler()
        self.collision_detector = CollisionDetector()
        self.renderer = Renderer(self.screen, self.font)
        self.ship_factory = ShipFactory()
        self.asteroid_factory = AsteroidFactory()
        self.bullet_factory = BulletFactory()
        self.score_manager = ScoreManager(self.event_manager)
        self.level_manager = LevelManager(self.event_manager, self.asteroid_factory)
        self.current_state: Optional[GameState] = PlayingState(self)

    def run(self) -> None:
        while self.current_state is not None:
            dt = self.clock.tick(FPS) / 1000.0  # Convert to seconds
            events = pygame.event.get()
            new_state = self.current_state.handle_events(events)
            if new_state != self.current_state:
                self.current_state = new_state
                if self.current_state is None:
                    break
            new_state = self.current_state.update(dt)
            if new_state != self.current_state:
                self.current_state = new_state
                if self.current_state is None:
                    break
            self.current_state.render(self.renderer)


def main():
    game = Game()
    game.run()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
