import pygame
import random
import sys

# Initialize Pygame
pygame.init()

# Constants
WIDTH, HEIGHT = 800, 600
BLOCK_SIZE = 30
BOARD_WIDTH = 10
BOARD_HEIGHT = 20
BOARD_X = (WIDTH - BOARD_WIDTH * BLOCK_SIZE) // 2
BOARD_Y = (HEIGHT - BOARD_HEIGHT * BLOCK_SIZE) // 2
FPS = 60
FALL_SPEED = 500  # milliseconds

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (128, 128, 128)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
CYAN = (0, 255, 255)
MAGENTA = (255, 0, 255)
ORANGE = (255, 165, 0)

# Tetromino shapes
SHAPES = [
    [['.....',
      '.....',
      'OOOO.',
      '.....',
      '.....'],
     ['.....',
      '..O..',
      '..O..',
      '..O..',
      '..O..']],

    [['.....',
      '.....',
      '.OO..',
      '.OO..',
      '.....']],

    [['.....',
      '.....',
      '..O..',
      '.OOO.',
      '.....'],
     ['.....',
      '..O..',
      '..OO.',
      '..O..',
      '.....'],
     ['.....',
      '.....',
      '.OOO.',
      '..O..',
      '.....'],
     ['.....',
      '..O..',
      '.OO..',
      '..O..',
      '.....']],

    [['.....',
      '.....',
      '..OO.',
      '.OO..',
      '.....'],
     ['.....',
      '..O..',
      '..OO.',
      '...O.',
      '.....']],

    [['.....',
      '.....',
      '.OO..',
      '..OO.',
      '.....'],
     ['.....',
      '...O.',
      '..OO.',
      '..O..',
      '.....']],

    [['.....',
      '.....',
      '.O...',
      '.OOO.',
      '.....'],
     ['.....',
      '..OO.',
      '..O..',
      '..O..',
      '.....'],
     ['.....',
      '.....',
      '.OOO.',
      '...O.',
      '.....'],
     ['.....',
      '..O..',
      '..O..',
      '.OO..',
      '.....']],

    [['.....',
      '.....',
      '...O.',
      '.OOO.',
      '.....'],
     ['.....',
      '..O..',
      '..O..',
      '..OO.',
      '.....'],
     ['.....',
      '.....',
      '.OOO.',
      '.O...',
      '.....'],
     ['.....',
      '.OO..',
      '..O..',
      '..O..',
      '.....']]
]

SHAPE_COLORS = [CYAN, YELLOW, MAGENTA, GREEN, RED, BLUE, ORANGE]

# Set up the display
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Tetris")
clock = pygame.time.Clock()
font = pygame.font.Font(None, 36)
small_font = pygame.font.Font(None, 24)

class Piece:
    def __init__(self, x, y, shape):
        self.x = x
        self.y = y
        self.shape = shape
        self.color = SHAPE_COLORS[shape]
        self.rotation = 0

    def get_shape(self):
        return SHAPES[self.shape][self.rotation]

    def rotate(self):
        self.rotation = (self.rotation + 1) % len(SHAPES[self.shape])

def create_board():
    return [[BLACK for _ in range(BOARD_WIDTH)] for _ in range(BOARD_HEIGHT)]

def draw_board(board, screen):
    for y in range(BOARD_HEIGHT):
        for x in range(BOARD_WIDTH):
            pygame.draw.rect(screen, board[y][x],
                           (BOARD_X + x * BLOCK_SIZE, BOARD_Y + y * BLOCK_SIZE,
                            BLOCK_SIZE, BLOCK_SIZE))
            pygame.draw.rect(screen, GRAY,
                           (BOARD_X + x * BLOCK_SIZE, BOARD_Y + y * BLOCK_SIZE,
                            BLOCK_SIZE, BLOCK_SIZE), 1)

def draw_piece(piece, screen):
    shape = piece.get_shape()
    for y in range(5):
        for x in range(5):
            if shape[y][x] == 'O':
                pygame.draw.rect(screen, piece.color,
                               (BOARD_X + (piece.x + x) * BLOCK_SIZE,
                                BOARD_Y + (piece.y + y) * BLOCK_SIZE,
                                BLOCK_SIZE, BLOCK_SIZE))
                pygame.draw.rect(screen, WHITE,
                               (BOARD_X + (piece.x + x) * BLOCK_SIZE,
                                BOARD_Y + (piece.y + y) * BLOCK_SIZE,
                                BLOCK_SIZE, BLOCK_SIZE), 1)

def valid_move(board, piece, dx=0, dy=0):
    shape = piece.get_shape()
    for y in range(5):
        for x in range(5):
            if shape[y][x] == 'O':
                nx = piece.x + x + dx
                ny = piece.y + y + dy
                if nx < 0 or nx >= BOARD_WIDTH or ny >= BOARD_HEIGHT or \
                   (ny >= 0 and board[ny][nx] != BLACK):
                    return False
    return True

def place_piece(board, piece):
    shape = piece.get_shape()
    for y in range(5):
        for x in range(5):
            if shape[y][x] == 'O':
                board[piece.y + y][piece.x + x] = piece.color

def clear_lines(board):
    lines_cleared = 0
    for y in range(BOARD_HEIGHT):
        if all(color != BLACK for color in board[y]):
            del board[y]
            board.insert(0, [BLACK for _ in range(BOARD_WIDTH)])
            lines_cleared += 1
    return lines_cleared

def draw_text(text, font, color, x, y, screen):
    text_surface = font.render(text, True, color)
    screen.blit(text_surface, (x, y))

def main():
    board = create_board()
    current_piece = Piece(BOARD_WIDTH // 2 - 2, 0, random.randint(0, len(SHAPES) - 1))
    next_piece = Piece(BOARD_WIDTH // 2 - 2, 0, random.randint(0, len(SHAPES) - 1))
    score = 0
    level = 1
    lines = 0
    fall_time = 0
    fall_speed = FALL_SPEED

    running = True
    game_over = False

    while running:
        fall_time += clock.get_rawtime()
        clock.tick(FPS)

        if not game_over:
            if fall_time >= fall_speed:
                if valid_move(board, current_piece, dy=1):
                    current_piece.y += 1
                else:
                    place_piece(board, current_piece)
                    lines_cleared = clear_lines(board)
                    lines += lines_cleared
                    score += lines_cleared * 100 * level
                    level = lines // 10 + 1
                    fall_speed = max(50, FALL_SPEED - (level - 1) * 50)

                    current_piece = next_piece
                    next_piece = Piece(BOARD_WIDTH // 2 - 2, 0, random.randint(0, len(SHAPES) - 1))

                    if not valid_move(board, current_piece):
                        game_over = True
                fall_time = 0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT and not game_over:
                    if valid_move(board, current_piece, dx=-1):
                        current_piece.x -= 1
                elif event.key == pygame.K_RIGHT and not game_over:
                    if valid_move(board, current_piece, dx=1):
                        current_piece.x += 1
                elif event.key == pygame.K_DOWN and not game_over:
                    if valid_move(board, current_piece, dy=1):
                        current_piece.y += 1
                        score += 1
                elif event.key == pygame.K_UP and not game_over:
                    current_piece.rotate()
                    if not valid_move(board, current_piece):
                        current_piece.rotate()  # Rotate back if invalid
                        current_piece.rotate()
                        current_piece.rotate()
                        current_piece.rotate()
                elif event.key == pygame.K_r and game_over:
                    # Restart
                    board = create_board()
                    current_piece = Piece(BOARD_WIDTH // 2 - 2, 0, random.randint(0, len(SHAPES) - 1))
                    next_piece = Piece(BOARD_WIDTH // 2 - 2, 0, random.randint(0, len(SHAPES) - 1))
                    score = 0
                    level = 1
                    lines = 0
                    fall_speed = FALL_SPEED
                    game_over = False

        screen.fill(BLACK)
        draw_board(board, screen)
        if not game_over:
            draw_piece(current_piece, screen)

        # Draw UI
        draw_text(f"Score: {score}", font, WHITE, 10, 10, screen)
        draw_text(f"Level: {level}", font, WHITE, 10, 50, screen)
        draw_text(f"Lines: {lines}", font, WHITE, 10, 90, screen)
        draw_text("Next:", small_font, WHITE, WIDTH - 120, 10, screen)
        # Draw next piece (simplified)
        for y in range(5):
            for x in range(5):
                if SHAPES[next_piece.shape][0][y][x] == 'O':
                    pygame.draw.rect(screen, next_piece.color,
                                   (WIDTH - 100 + x * BLOCK_SIZE // 2,
                                    40 + y * BLOCK_SIZE // 2,
                                    BLOCK_SIZE // 2, BLOCK_SIZE // 2))

        if game_over:
            draw_text("Game Over", font, RED, WIDTH // 2 - 100, HEIGHT // 2 - 50, screen)
            draw_text("Press R to Restart", small_font, WHITE, WIDTH // 2 - 100, HEIGHT // 2, screen)

        pygame.display.flip()

if __name__ == "__main__":
    main()
    pygame.quit()
    sys.exit()