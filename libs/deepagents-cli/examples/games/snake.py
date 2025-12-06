import pygame
import random
import sys

# Initialize Pygame
pygame.init()

# Set up the display
WIDTH, HEIGHT = 800, 600
BLOCK_SIZE = 20
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Snake Game")

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)

# Snake initial position and body
snake = [(WIDTH // 2, HEIGHT // 2)]
snake_direction = (BLOCK_SIZE, 0)

# Food
food = (random.randint(0, (WIDTH - BLOCK_SIZE) // BLOCK_SIZE) * BLOCK_SIZE,
        random.randint(0, (HEIGHT - BLOCK_SIZE) // BLOCK_SIZE) * BLOCK_SIZE)

# Game loop
clock = pygame.time.Clock()
running = True

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP and snake_direction != (0, BLOCK_SIZE):
                snake_direction = (0, -BLOCK_SIZE)
            elif event.key == pygame.K_DOWN and snake_direction != (0, -BLOCK_SIZE):
                snake_direction = (0, BLOCK_SIZE)
            elif event.key == pygame.K_LEFT and snake_direction != (BLOCK_SIZE, 0):
                snake_direction = (-BLOCK_SIZE, 0)
            elif event.key == pygame.K_RIGHT and snake_direction != (-BLOCK_SIZE, 0):
                snake_direction = (BLOCK_SIZE, 0)

    # Move snake
    head = (snake[0][0] + snake_direction[0], snake[0][1] + snake_direction[1])
    snake.insert(0, head)

    # Check if food eaten
    if head == food:
        food = (random.randint(0, (WIDTH - BLOCK_SIZE) // BLOCK_SIZE) * BLOCK_SIZE,
                random.randint(0, (HEIGHT - BLOCK_SIZE) // BLOCK_SIZE) * BLOCK_SIZE)
    else:
        snake.pop()

    # Check collisions
    if (head[0] < 0 or head[0] >= WIDTH or
        head[1] < 0 or head[1] >= HEIGHT or
        head in snake[1:]):
        running = False

    # Clear the screen
    screen.fill(BLACK)

    # Draw snake
    for segment in snake:
        pygame.draw.rect(screen, GREEN, (segment[0], segment[1], BLOCK_SIZE, BLOCK_SIZE))

    # Draw food
    pygame.draw.rect(screen, RED, (food[0], food[1], BLOCK_SIZE, BLOCK_SIZE))

    # Update the display
    pygame.display.flip()

    # Cap the frame rate
    clock.tick(10)

# Quit Pygame
pygame.quit()
sys.exit()