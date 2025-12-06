# Game logic class
import pygame
from maze import Maze
from entities import PacMan, GhostFactory
from constants import SCREEN_WIDTH, SCREEN_HEIGHT

class Score:
    def __init__(self):
        self.points = 0
        self.font = pygame.font.SysFont(None, 36)

    def add_points(self, points):
        self.points += points

    def draw(self, screen):
        text = self.font.render(f"Score: {self.points}", True, (255, 255, 255))
        screen.blit(text, (10, 10))

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Pac-Man")
        self.clock = pygame.time.Clock()
        self.running = True
        self.game_over = False

        self.maze = Maze(self.screen)
        self.pacman = PacMan(100, 100)
        self.ghosts = GhostFactory.create_ghosts()
        self.score = Score()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

    def update(self):
        if self.game_over:
            return

        keys = pygame.key.get_pressed()
        self.pacman.move(self.maze, keys)

        # Collect dots
        if self.maze.collect_dot(self.pacman.x, self.pacman.y):
            self.score.add_points(10)

        # Move ghosts
        for ghost in self.ghosts:
            ghost.move(self.maze)

        # Check collisions with ghosts
        for ghost in self.ghosts:
            if abs(self.pacman.x - ghost.x) < 10 and abs(self.pacman.y - ghost.y) < 10:
                self.game_over = True
                break

    def draw(self):
        self.screen.fill((0, 0, 0))  # Black background
        self.maze.draw()
        self.pacman.draw(self.screen)
        for ghost in self.ghosts:
            ghost.draw(self.screen)
        self.score.draw(self.screen)

        if self.game_over:
            font = pygame.font.SysFont(None, 72)
            text = font.render("GAME OVER", True, (255, 0, 0))
            self.screen.blit(text, (SCREEN_WIDTH // 2 - 150, SCREEN_HEIGHT // 2 - 50))

        pygame.display.flip()

    def run(self):
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(60)
        pygame.quit()