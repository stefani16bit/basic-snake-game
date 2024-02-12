from typing import (
    Callable
)

import pygame, random, mysql.connector

DATABASE_HOST = 'localhost'
DATABASE_USER = 'root'
DATABASE_PASSWORD = 'root'
DATABASE_NAME = 'snake_game'

SCREEN_WIDTH = 500
SCREEN_HEIGHT = 500

PLAYABLE_WIDTH = 500
PLAYABLE_HEIGHT = 450

GRID_SIZE = 10
GAME_SPEED = 10

MAX_SPAWNED_APPLES_COUNT = 1

non_playable_width = SCREEN_WIDTH - PLAYABLE_WIDTH
non_playable_height = SCREEN_HEIGHT - PLAYABLE_HEIGHT

database_connection = None

def perform_database_query(query, data, is_update_query = False):
    cursor = None

    try:
        cursor = database_connection.cursor()
        cursor.execute(query, data)
    
        if is_update_query:
            database_connection.commit()
        else:
            return (True, cursor.fetchall())
    except Exception as exception:
        print(f'Failed to perform database query: {exception}')
    finally:
        if cursor:
            cursor.close()

    return (is_update_query, None)

def register_user_score(user_name):
    (success, _) = perform_database_query('INSERT INTO scores (user_name, score) VALUES (%s, %s) ON DUPLICATE KEY UPDATE user_name = user_name', (user_name, 0), True)
    return success

def update_user_score(user_name, score):
    (success, _) = perform_database_query('UPDATE scores SET score = %s WHERE user_name = %s', (score, user_name,))
    return success

def get_user_score(user_name):
    (success, result) = perform_database_query('SELECT score FROM scores WHERE user_name = %s', (user_name,))
    return result[0][0] if success and len(result) > 0 else None

def capture_user_input(input_changed=None, can_accept_input=lambda _: True, min_length=0, max_length=255, on_invalid_input=lambda: None):
    continue_capturing_inputs = True

    last_captured_input = ''
    captured_input = ''

    while continue_capturing_inputs:
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                break

            if event.type == pygame.KEYDOWN:
                match event.key:
                    case pygame.K_RETURN:
                        if len(captured_input) < min_length:
                            on_invalid_input(0)
                        else:
                            continue_capturing_inputs = False
                    case pygame.K_BACKSPACE:
                        captured_input = captured_input[:-1]
                    case _:
                        if not can_accept_input(event.unicode):
                            on_invalid_input(1)
                        elif len(captured_input) >= max_length:
                            on_invalid_input(2)
                        else:
                            captured_input += event.unicode

                if last_captured_input != captured_input and input_changed and isinstance(input_changed, Callable):
                    input_changed(captured_input)

                last_captured_input = captured_input

    return captured_input

def make_login_screen():
    surface = pygame.display.get_surface()

    input_font = pygame.font.SysFont('Consolas', 20)
    error_font = pygame.font.SysFont('Consolas', 20)

    def draw(text_to_draw, font, color):
        text_to_draw = font.render(text_to_draw, True, color)
        text_to_draw_rect = text_to_draw.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2))
        
        surface.fill((0, 170, 0, 255))
        surface.blit(text_to_draw, text_to_draw_rect)

        pygame.display.update()

    def on_input_changed(entered_user_name):
        draw(f'Nickname: {entered_user_name}', input_font, (255, 255, 255, 255))

    def on_invalid_input(error_code):
        error_message = None

        match error_code:
            case 0:
                error_message = 'Nickname must be at least 3 characters long'
            case 1:
                error_message = 'Nickname can only contain letters'

        if error_message:
            draw(error_message, error_font, (255, 0, 0, 255))

    draw('Enter your Nickname', input_font, (255, 255, 255, 255))

    return capture_user_input(input_changed=on_input_changed, can_accept_input=lambda unicode: unicode.isalpha(), min_length=3, max_length=20, on_invalid_input=on_invalid_input)

def make_game_over_screen(on_replay_interaction=lambda: None, on_exit_interaction=lambda: None):
    surface = pygame.display.get_surface()

    game_over_font = pygame.font.SysFont("Consolas", size=50)
    replay_font = pygame.font.SysFont("Consolas", size=20)

    game_over_text = game_over_font.render("Game Over", True, (255, 0, 0, 0))
    game_over_text_rect = game_over_text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2))

    replay_text = replay_font.render("Press Enter to play again or ESC to go back.", True, (0, 0, 0, 255))
    replay_text_rect = replay_text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + game_over_font.get_height()))
    
    surface.fill((0, 170, 0, 255))

    surface.blit(game_over_text, game_over_text_rect)
    surface.blit(replay_text, replay_text_rect)

    pygame.display.update()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                break
            elif event.type == pygame.KEYDOWN:
                match event.key:
                    case pygame.K_RETURN:
                        on_replay_interaction()
                    case pygame.K_ESCAPE:
                        on_exit_interaction()

def initialize_game(entered_user_name=None):
    surface = pygame.display.get_surface()

    entered_user_name = entered_user_name or make_login_screen()
    assert entered_user_name, 'User name is required'

    if not register_user_score(entered_user_name):
        exit('Failed to register user score')

    last_score = get_user_score(entered_user_name) or 0

    def run():
        snake_body = [(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)]

        snake_speed_x = 0
        snake_speed_y = 0

        spawned_apples = []

        current_score = 0

        def award_score():
            nonlocal current_score
            current_score += 10

            if current_score > last_score:
                if not update_user_score(entered_user_name, current_score):
                    print('Failed to update user score')

        def draw_snake():
            for _, snake_body_part in enumerate(snake_body):
                pygame.draw.rect(
                    pygame.display.get_surface(),
                    (0, 0, 255, 255),
                    pygame.Rect(
                        snake_body_part[0],
                        snake_body_part[1],
                        GRID_SIZE,
                        GRID_SIZE
                    )
                )

        def draw_apples():
            for _, apple in enumerate(spawned_apples):
                pygame.draw.rect(
                    pygame.display.get_surface(),
                    (255, 0, 0, 255),
                    pygame.Rect(
                        apple[0],
                        apple[1],
                        GRID_SIZE,
                        GRID_SIZE
                    )
                )

        def draw_hud():
            font = pygame.font.SysFont('Consolas', 20)

            current_score_text = font.render(f'Score: {current_score}', True, (255, 255, 255, 255))
            last_score_text = font.render(f'Last Score: {last_score}', True, (255, 255, 255, 255))
            user_name_text = font.render(f'User: {entered_user_name}', True, (255, 255, 255, 255))

            font_height = current_score_text.get_height()

            current_score_text_rect = current_score_text.get_rect(center=(0 + current_score_text.get_width() // 2, font_height // 2))
            last_score_text_rect = last_score_text.get_rect(center=(0 + last_score_text.get_width() // 2, font_height * 2 - font_height // 2))
            user_name_text_rect = user_name_text.get_rect(center=(SCREEN_WIDTH - user_name_text.get_width() // 2, font_height // 2))

            surface.blit(current_score_text, current_score_text_rect)
            surface.blit(last_score_text, last_score_text_rect)
            surface.blit(user_name_text, user_name_text_rect)

        def draw_grid():
            for x in range(0, PLAYABLE_WIDTH, GRID_SIZE):
                pygame.draw.line(
                    pygame.display.get_surface(),
                    (0, 0, 0, 255),
                    (x, non_playable_height),
                    (x, SCREEN_HEIGHT)
                )

            for y in range(non_playable_height, SCREEN_HEIGHT, GRID_SIZE):
                pygame.draw.line(
                    pygame.display.get_surface(),
                    (0, 0, 0, 255),
                    (0, y),
                    (PLAYABLE_WIDTH, y)
                )

        FPS = pygame.time.Clock()

        while True:
            events = pygame.event.get()

            for event in events:
                if event.type == pygame.QUIT:
                    pygame.quit()
                elif event.type == pygame.KEYDOWN:
                    match event.key:
                        case pygame.K_UP | pygame.K_w:
                            snake_speed_x, snake_speed_y = 0, -1
                        case pygame.K_DOWN | pygame.K_s:
                            snake_speed_x, snake_speed_y = 0, 1
                        case pygame.K_LEFT | pygame.K_a:
                            snake_speed_x, snake_speed_y = -1, 0
                        case pygame.K_RIGHT | pygame.K_d:
                            snake_speed_x, snake_speed_y = 1, 0
            
            for index in range(len(snake_body) - 1, 0, -1):
                (body_x, body_y) = snake_body[index]

                if body_x == snake_body[0][0] and body_y == snake_body[0][1]:
                    return

                snake_body[index] = snake_body[index - 1]

            (previous_snake_head_x, previous_snake_head_y) = snake_body[0]

            snake_body[0] = (
                snake_body[0][0] + snake_speed_x * GRID_SIZE,
                snake_body[0][1] + snake_speed_y * GRID_SIZE
            )

            (snake_head_x, snake_head_y) = snake_body[0]

            if snake_head_x < 0 or snake_head_x >= PLAYABLE_WIDTH or snake_head_y < non_playable_height or snake_head_y >= SCREEN_HEIGHT:
                return

            for index in range(len(spawned_apples)):
                (apple_x, apple_y) = spawned_apples[index]
                
                if snake_head_x == apple_x and snake_head_y == apple_y:
                    award_score()

                    snake_body.append((previous_snake_head_x, previous_snake_head_y))
                    spawned_apples.pop(index)
                    
                    break

            if len(spawned_apples) < MAX_SPAWNED_APPLES_COUNT:
                spawned_apples.append((
                    random.randrange(non_playable_height, PLAYABLE_WIDTH, GRID_SIZE),
                    random.randrange(non_playable_height, PLAYABLE_HEIGHT, GRID_SIZE)
                ))

            surface.fill((0, 170, 0, 255))

            draw_snake()
            draw_apples()
            draw_hud()
            draw_grid()

            pygame.display.update()

            FPS.tick(GAME_SPEED)

    run()

    make_game_over_screen(
        on_replay_interaction=lambda: initialize_game(entered_user_name),
        on_exit_interaction=lambda: pygame.quit()
    )

def main():
    global database_connection

    try:
        database_connection = mysql.connector.connect(
            host=DATABASE_HOST,
            user=DATABASE_USER,
            password=DATABASE_PASSWORD,
            database=DATABASE_NAME
        )
    except Exception as exception:
        exit(f'Failed to connect to database: {exception}')

    pygame.init()

    pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption('Snake Game')

    initialize_game()

if __name__ == '__main__':
    main()