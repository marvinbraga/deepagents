import random
import sys

import pygame

# Inicializar Pygame
pygame.init()

# Definir cores
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)

# Dimensões da tela
WIDTH = 640
HEIGHT = 480

# Tamanho do bloco da cobra e comida
BLOCK_SIZE = 20

# Velocidade do jogo (FPS)
FPS = 10

# Fonte para texto
font = pygame.font.SysFont(None, 35)


# Função para desenhar a cobra
def draw_snake(snake_body):
    for block in snake_body:
        pygame.draw.rect(screen, GREEN, [block[0], block[1], BLOCK_SIZE, BLOCK_SIZE])


# Função para gerar comida
def generate_food():
    x = random.randint(0, (WIDTH - BLOCK_SIZE) // BLOCK_SIZE) * BLOCK_SIZE
    y = random.randint(0, (HEIGHT - BLOCK_SIZE) // BLOCK_SIZE) * BLOCK_SIZE
    return x, y


# Função para exibir mensagem na tela
def message_to_screen(msg, color):
    screen_text = font.render(msg, True, color)
    screen.blit(screen_text, [WIDTH / 2 - screen_text.get_width() / 2, HEIGHT / 2 - screen_text.get_height() / 2])


# Função principal do jogo
def game_loop():
    game_over = False
    game_close = False

    # Posição inicial da cobra
    x1 = WIDTH / 2
    y1 = HEIGHT / 2

    # Mudança na posição
    x1_change = 0
    y1_change = 0

    # Corpo da cobra
    snake_body = []
    length_of_snake = 1

    # Gerar comida inicial
    foodx, foody = generate_food()

    # Pontuação
    score = 0

    clock = pygame.time.Clock()

    while not game_over:

        while game_close:
            screen.fill(BLACK)
            message_to_screen("Você perdeu! Pressione Q para sair ou C para jogar novamente", RED)
            pygame.display.update()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    game_over = True
                    game_close = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_q:
                        game_over = True
                        game_close = False
                    if event.key == pygame.K_c:
                        game_loop()  # Reiniciar jogo

        # Eventos
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game_over = True
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT and x1_change != BLOCK_SIZE:
                    x1_change = -BLOCK_SIZE
                    y1_change = 0
                elif event.key == pygame.K_RIGHT and x1_change != -BLOCK_SIZE:
                    x1_change = BLOCK_SIZE
                    y1_change = 0
                elif event.key == pygame.K_UP and y1_change != BLOCK_SIZE:
                    y1_change = -BLOCK_SIZE
                    x1_change = 0
                elif event.key == pygame.K_DOWN and y1_change != -BLOCK_SIZE:
                    y1_change = BLOCK_SIZE
                    x1_change = 0

        # Verificar colisão com bordas
        if x1 >= WIDTH or x1 < 0 or y1 >= HEIGHT or y1 < 0:
            game_close = True

        # Mover cobra
        x1 += x1_change
        y1 += y1_change

        # Limpar tela
        screen.fill(BLACK)

        # Desenhar comida
        pygame.draw.rect(screen, RED, [foodx, foody, BLOCK_SIZE, BLOCK_SIZE])

        # Adicionar cabeça da cobra
        snake_head = []
        snake_head.append(x1)
        snake_head.append(y1)
        snake_body.append(snake_head)

        # Manter tamanho da cobra
        if len(snake_body) > length_of_snake:
            del snake_body[0]

        # Verificar colisão com própria cobra
        for block in snake_body[:-1]:
            if block == snake_head:
                game_close = True

        # Desenhar cobra
        draw_snake(snake_body)

        # Desenhar pontuação
        score_text = font.render("Pontuação: " + str(score), True, WHITE)
        screen.blit(score_text, [0, 0])

        pygame.display.update()

        # Verificar se comeu comida
        if x1 == foodx and y1 == foody:
            foodx, foody = generate_food()
            length_of_snake += 1
            score += 10

        clock.tick(FPS)

    pygame.quit()
    sys.exit()


# Configurar tela
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption('Jogo da Serpente')

# Iniciar jogo
game_loop()
