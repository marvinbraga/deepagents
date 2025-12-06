# Maze class for labyrinth and dots
import pygame

class Maze:
    def __init__(self, screen, cell_size=20):
        self.screen = screen
        self.cell_size = cell_size
        self.width = screen.get_width() // cell_size
        self.height = screen.get_height() // cell_size

        # Simple maze layout: 1=wall, 0=path, 2=dot
        self.layout = [
            [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
            [1,2,2,2,2,2,2,2,2,1,2,2,2,2,2,2,2,2,1],
            [1,1,1,2,1,1,1,1,2,1,2,1,1,1,1,1,2,1,1],
            [1,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,1],
            [1,2,1,1,1,2,1,1,1,1,1,1,1,2,1,1,1,2,1],
            [1,2,2,2,2,2,2,2,2,1,2,2,2,2,2,2,2,2,1],
            [1,1,1,1,1,1,1,1,2,1,2,1,1,1,1,1,1,1,1],
            [1,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,1],
            [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
        ]
        self.dots = []  # List of (x,y) positions of dots
        self._init_dots()

    def _init_dots(self):
        for y, row in enumerate(self.layout):
            for x, cell in enumerate(row):
                if cell == 2:
                    self.dots.append((x * self.cell_size + self.cell_size // 2, y * self.cell_size + self.cell_size // 2))

    def draw(self):
        for y, row in enumerate(self.layout):
            for x, cell in enumerate(row):
                rect = pygame.Rect(x * self.cell_size, y * self.cell_size, self.cell_size, self.cell_size)
                if cell == 1:
                    pygame.draw.rect(self.screen, (0, 0, 255), rect)  # Blue walls
                elif cell == 2:
                    pygame.draw.circle(self.screen, (255, 255, 0), (x * self.cell_size + self.cell_size // 2, y * self.cell_size + self.cell_size // 2), 3)  # Yellow dots

    def is_wall(self, x, y):
        grid_x = x // self.cell_size
        grid_y = y // self.cell_size
        if 0 <= grid_x < len(self.layout[0]) and 0 <= grid_y < len(self.layout):
            return self.layout[grid_y][grid_x] == 1
        return True

    def collect_dot(self, x, y):
        center_x = x // self.cell_size * self.cell_size + self.cell_size // 2
        center_y = y // self.cell_size * self.cell_size + self.cell_size // 2
        if (center_x, center_y) in self.dots:
            self.dots.remove((center_x, center_y))
            self.layout[y // self.cell_size][x // self.cell_size] = 0  # Remove dot from layout
            return True
        return False