import pygame
import math
import random
import sys

# Initialize Pygame
pygame.init()

# Constants
WIDTH, HEIGHT = 800, 600
FPS = 60
SHIP_SIZE = 20
BULLET_SIZE = 5
BULLET_SPEED = 10
SHIP_SPEED = 0.1
SHIP_ROTATION_SPEED = 5
ASTEROID_SIZES = [40, 25, 15]
ASTEROID_SPEEDS = [1, 1.5, 2]

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)

# Set up the display
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Asteroids")
clock = pygame.time.Clock()
font = pygame.font.Font(None, 36)

class Ship:
    def __init__(self):
        self.x = WIDTH // 2
        self.y = HEIGHT // 2
        self.angle = 0
        self.vx = 0
        self.vy = 0
        self.radius = SHIP_SIZE

    def update(self):
        # Apply friction
        self.vx *= 0.99
        self.vy *= 0.99

        # Update position
        self.x += self.vx
        self.y += self.vy

        # Wrap around screen
        self.x = self.x % WIDTH
        self.y = self.y % HEIGHT

    def rotate(self, direction):
        self.angle += direction * SHIP_ROTATION_SPEED

    def thrust(self):
        rad_angle = math.radians(self.angle)
        self.vx += math.cos(rad_angle) * SHIP_SPEED
        self.vy += math.sin(rad_angle) * SHIP_SPEED

    def draw(self, screen):
        rad_angle = math.radians(self.angle)
        # Ship points
        points = [
            (self.x + math.cos(rad_angle) * SHIP_SIZE, self.y + math.sin(rad_angle) * SHIP_SIZE),
            (self.x + math.cos(rad_angle + 2.5) * SHIP_SIZE * 0.6, self.y + math.sin(rad_angle + 2.5) * SHIP_SIZE * 0.6),
            (self.x + math.cos(rad_angle - 2.5) * SHIP_SIZE * 0.6, self.y + math.sin(rad_angle - 2.5) * SHIP_SIZE * 0.6)
        ]
        pygame.draw.polygon(screen, WHITE, points)

class Asteroid:
    def __init__(self, x=None, y=None, size=0, speed_mult=1):
        self.size = size
        self.radius = ASTEROID_SIZES[size]
        if x is None:
            self.x = random.randint(self.radius, WIDTH - self.radius)
            self.y = random.randint(self.radius, HEIGHT - self.radius)
        else:
            self.x = x
            self.y = y
        self.vx = random.uniform(-ASTEROID_SPEEDS[size] * speed_mult, ASTEROID_SPEEDS[size] * speed_mult)
        self.vy = random.uniform(-ASTEROID_SPEEDS[size] * speed_mult, ASTEROID_SPEEDS[size] * speed_mult)
        self.angle = random.uniform(0, 360)
        self.rotation_speed = random.uniform(-2, 2)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.angle += self.rotation_speed

        # Wrap around screen
        if self.x < -self.radius:
            self.x = WIDTH + self.radius
        elif self.x > WIDTH + self.radius:
            self.x = -self.radius
        if self.y < -self.radius:
            self.y = HEIGHT + self.radius
        elif self.y > HEIGHT + self.radius:
            self.y = -self.radius

    def draw(self, screen):
        # Draw as irregular polygon
        points = []
        for i in range(8):
            angle = math.radians(self.angle + i * 45)
            r = self.radius + random.uniform(-5, 5)
            px = self.x + math.cos(angle) * r
            py = self.y + math.sin(angle) * r
            points.append((px, py))
        pygame.draw.polygon(screen, WHITE, points, 2)

class Bullet:
    def __init__(self, x, y, angle):
        self.x = x
        self.y = y
        rad_angle = math.radians(angle)
        self.vx = math.cos(rad_angle) * BULLET_SPEED
        self.vy = math.sin(rad_angle) * BULLET_SPEED
        self.radius = BULLET_SIZE
        self.lifetime = 60  # frames

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.lifetime -= 1

    def draw(self, screen):
        pygame.draw.circle(screen, WHITE, (int(self.x), int(self.y)), self.radius)

    def is_alive(self):
        return self.lifetime > 0

def check_collision(obj1, obj2):
    dx = obj1.x - obj2.x
    dy = obj1.y - obj2.y
    distance = math.sqrt(dx**2 + dy**2)
    return distance < obj1.radius + obj2.radius

def reset_game():
    ship = Ship()
    asteroids = [Asteroid(speed_mult=1) for _ in range(5)]
    bullets = []
    score = 0
    lives = 3
    level = 1
    return ship, asteroids, bullets, score, lives, level

def show_menu(screen, font, score):
    menu_running = True
    while menu_running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    return True
                elif event.key == pygame.K_q:
                    return False

        screen.fill(BLACK)
        game_over_text = font.render("Game Over", True, WHITE)
        final_score_text = font.render(f"Final Score: {score}", True, WHITE)
        restart_text = font.render("Press R to Restart", True, WHITE)
        quit_text = font.render("Press Q to Quit", True, WHITE)
        screen.blit(game_over_text, (WIDTH // 2 - 100, HEIGHT // 2 - 80))
        screen.blit(final_score_text, (WIDTH // 2 - 100, HEIGHT // 2 - 40))
        screen.blit(restart_text, (WIDTH // 2 - 100, HEIGHT // 2))
        screen.blit(quit_text, (WIDTH // 2 - 100, HEIGHT // 2 + 40))
        pygame.display.flip()
        clock.tick(FPS)
    return False

def main():
    game_running = True
    while game_running:
        ship, asteroids, bullets, score, lives, level = reset_game()
        running = True

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    game_running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        # Shoot bullet
                        bullets.append(Bullet(ship.x, ship.y, ship.angle))

            keys = pygame.key.get_pressed()
            if keys[pygame.K_LEFT]:
                ship.rotate(-1)
            if keys[pygame.K_RIGHT]:
                ship.rotate(1)
            if keys[pygame.K_UP]:
                ship.thrust()

            # Update objects
            ship.update()
            for asteroid in asteroids:
                asteroid.update()
            bullets = [bullet for bullet in bullets if bullet.is_alive()]
            for bullet in bullets:
                bullet.update()

            # Check collisions
            # Bullets vs asteroids
            for bullet in bullets[:]:
                for asteroid in asteroids[:]:
                    if check_collision(bullet, asteroid):
                        bullets.remove(bullet)
                        asteroids.remove(asteroid)
                        score += (3 - asteroid.size) * 20
                        # Split asteroid if not smallest
                        if asteroid.size < 2:
                            for _ in range(2):
                                asteroids.append(Asteroid(asteroid.x, asteroid.y, asteroid.size + 1))
                        break

            # Ship vs asteroids
            for asteroid in asteroids:
                if check_collision(ship, asteroid):
                    lives -= 1
                    ship.x = WIDTH // 2
                    ship.y = HEIGHT // 2
                    ship.vx = 0
                    ship.vy = 0
                    if lives <= 0:
                        running = False
                    break

            # Level progression
            if not asteroids:
                level += 1
                num_asteroids = 5 + (level - 1)
                for _ in range(num_asteroids):
                    asteroids.append(Asteroid(speed_mult=level))

            # Draw everything
            screen.fill(BLACK)
            ship.draw(screen)
            for asteroid in asteroids:
                asteroid.draw(screen)
            for bullet in bullets:
                bullet.draw(screen)

            # Draw UI
            score_text = font.render(f"Score: {score}", True, WHITE)
            lives_text = font.render(f"Lives: {lives}", True, WHITE)
            level_text = font.render(f"Level: {level}", True, WHITE)
            screen.blit(score_text, (10, 10))
            screen.blit(lives_text, (WIDTH - 100, 10))
            screen.blit(level_text, (WIDTH // 2 - 50, 10))

            pygame.display.flip()
            clock.tick(FPS)

        # Show menu if not quit
        if game_running:
            restart = show_menu(screen, font, score)
            if not restart:
                game_running = False

if __name__ == "__main__":
    main()
    pygame.quit()
    sys.exit()