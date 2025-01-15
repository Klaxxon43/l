import pygame, levels, math, random, os, sys
from os import listdir
from os.path import isfile, join
pygame.init()

pygame.display.set_caption("Platformer")

WIDTH, HEIGHT = 1000, 800
FPS = 60
PLAYER_VEL = 5

window = pygame.display.set_mode((WIDTH, HEIGHT))


def flip(sprites):
    return [pygame.transform.flip(sprite, True, False) for sprite in sprites]


def load_sprite_sheets(dir1, dir2, width, height, direction=False):
    path = join("assets", dir1, dir2)
    images = [f for f in listdir(path) if isfile(join(path, f))]

    all_sprites = {}

    for image in images:
        sprite_sheet = pygame.image.load(join(path, image)).convert_alpha()

        sprites = []
        for i in range(sprite_sheet.get_width() // width):
            surface = pygame.Surface((width, height), pygame.SRCALPHA, 32)
            rect = pygame.Rect(i * width, 0, width, height)
            surface.blit(sprite_sheet, (0, 0), rect)
            sprites.append(pygame.transform.scale2x(surface))

        if direction:
            all_sprites[image.replace(".png", "") + "_right"] = sprites
            all_sprites[image.replace(".png", "") + "_left"] = flip(sprites)
        else:
            all_sprites[image.replace(".png", "")] = sprites

    return all_sprites


def get_block(size):
    path = join("assets", "Terrain", "Terrain.png")
    image = pygame.image.load(path).convert_alpha()
    surface = pygame.Surface((size, size), pygame.SRCALPHA, 32)
    rect = pygame.Rect(96, 0, size, size)
    surface.blit(image, (0, 0), rect)

    return pygame.transform.scale2x(surface)


class Player(pygame.sprite.Sprite):
    COLOR = (255, 0, 0)
    GRAVITY = 1
    SPRITES = None
    ANIMATION_DELAY = 3

    def __init__(self, x, y, width, height, skin="MaskDude"):
        super().__init__()
        self.rect = pygame.Rect(x, y, width, height)
        self.x_vel = 0
        self.y_vel = 0
        self.mask = None
        self.direction = "left"
        self.animation_count = 0
        self.fall_count = 0
        self.jump_count = 0
        self.hit = False
        self.hit_count = 0
        self.speed = 70
        self.set_skin(skin)

    def set_skin(self, skin):
        self.SPRITES = load_sprite_sheets("MainCharacters", skin, 32, 32, True)
        self.skin = skin  # Сохраняем текущий скин

    # Остальные методы класса Player остаются без изменений

    def jump(self):
        self.y_vel = -self.GRAVITY * 6
        self.animation_count = 0
        self.jump_count += 1
        if self.jump_count == 1:
            self.fall_count = 0

    def move(self, dx, dy):
        self.rect.x += dx
        self.rect.y += dy

    def make_hit(self):
        self.hit = True

    def move_left(self, vel):
        self.x_vel = -vel
        if self.direction != "left":
            self.direction = "left"
            self.animation_count = 0

    def move_right(self, vel):
        self.x_vel = vel
        if self.direction != "right":
            self.direction = "right"
            self.animation_count = 0

    def loop(self, fps, level_objects):
        dt = 1 / fps
        self.y_vel += min(1, self.fall_count * self.GRAVITY * dt)
        self.move(self.x_vel * self.speed * dt, self.y_vel * self.speed * dt)

        if self.hit:
            self.hit_count += 1
        if self.hit_count > fps * 2:
            self.hit = False
            self.hit_count = 0

        self.fall_count += 1
        self.update_sprite()

        # Обработка столкновений со стенами
        for obj in level_objects:
            if isinstance(obj, Block) and self.rect.colliderect(obj.rect):
                print(f"Collision detected with block at {obj.rect.topleft}")
                if self.x_vel > 0:  # Столкновение справа
                    self.rect.right = obj.rect.left
                    self.x_vel *= -1  # Отскок в обратную сторону
                elif self.x_vel < 0:  # Столкновение слева
                    self.rect.left = obj.rect.right
                    self.x_vel *= -1  # Отскок в обратную сторону

                if self.y_vel > 0:  # Столкновение снизу (приземление)
                    self.rect.bottom = obj.rect.top
                    self.landed()
                elif self.y_vel < 0:  # Столкновение сверху
                    self.rect.top = obj.rect.bottom
                    self.hit_head()

    def landed(self):
        self.fall_count = 0
        self.y_vel = 0
        self.jump_count = 0

    def hit_head(self):
        self.count = 0
        self.y_vel *= -1

    def update_sprite(self):
        sprite_sheet = "idle"
        if self.hit:
            sprite_sheet = "hit"
        elif self.y_vel < 0:
            if self.jump_count == 1:
                sprite_sheet = "jump"
            elif self.jump_count == 2:
                sprite_sheet = "double_jump"
        elif self.y_vel > self.GRAVITY * 2:
            sprite_sheet = "fall"
        elif self.x_vel != 0:
            sprite_sheet = "run"

        sprite_sheet_name = sprite_sheet + "_" + self.direction
        sprites = self.SPRITES[sprite_sheet_name]
        sprite_index = (self.animation_count //
                        self.ANIMATION_DELAY) % len(sprites)
        self.sprite = sprites[sprite_index]
        self.animation_count += 1
        self.update()

    def update(self):
        self.rect = self.sprite.get_rect(topleft=(self.rect.x, self.rect.y))
        self.mask = pygame.mask.from_surface(self.sprite)

    def draw(self, win, offset_x):
        win.blit(self.sprite, (self.rect.x - offset_x, self.rect.y))


class Object(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height, name=None):
        super().__init__()
        self.rect = pygame.Rect(x, y, width, height)
        self.image = pygame.Surface((width, height), pygame.SRCALPHA)
        self.width = width
        self.height = height
        self.name = name

    def draw(self, win, offset_x):
        win.blit(self.image, (self.rect.x - offset_x, self.rect.y))


class Block(Object):
    def __init__(self, x, y, size):
        super().__init__(x, y, size, size)
        block = get_block(size)
        self.image.blit(block, (0, 0))
        self.mask = pygame.mask.from_surface(self.image)


class Fire(Object):
    ANIMATION_DELAY = 3

    def __init__(self, x, y, width, height):
        super().__init__(x, y, width, height, "fire")
        self.fire = load_sprite_sheets("Traps", "Fire", width, height)
        self.image = self.fire["off"][0]
        self.mask = pygame.mask.from_surface(self.image)
        self.animation_count = 0
        self.animation_name = "off"

    def on(self):
        self.animation_name = "on"

    def off(self):
        self.animation_name = "off"

    def loop(self):
        sprites = self.fire[self.animation_name]
        sprite_index = (self.animation_count //
                        self.ANIMATION_DELAY) % len(sprites)
        self.image = sprites[sprite_index]
        self.animation_count += 1

        self.rect = self.image.get_rect(topleft=(self.rect.x, self.rect.y))
        self.mask = pygame.mask.from_surface(self.image)

        if self.animation_count // self.ANIMATION_DELAY > len(sprites):
            self.animation_count = 0


class Mob(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height, asset_path="assets/mob.png"):
        super().__init__()
        self.image = pygame.image.load(asset_path).convert_alpha()
        self.rect = self.image.get_rect(topleft=(x, y))
        self.width = width
        self.height = height
        self.health = 5
        self.direction = 1  # 1 = right, -1 = left
        self.move_speed = 2  # Скорость движения моба
        self.platform_width = 0  # Текущая длина платформы под мобом

    def update(self, dt, level_objects, player):
        self.check_ground(level_objects)
        self.move(dt)
        self.check_collision_with_player(player)

    def move(self, dt):
        self.rect.x += self.direction * self.move_speed * dt

        if self.rect.x + self.platform_width > self.rect.x + self.width and self.direction == 1:  # Достиг правого края платформы
            self.direction *= -1
        elif self.rect.x < self.rect.x - self.platform_width and self.direction == -1:  # Достиг левого края платформы
            self.direction *= -1

    def check_ground(self, level_objects):
        self.platform_width = 0
        for obj in level_objects:
            if isinstance(obj, Block) and self.rect.colliderect(obj.rect):
                if self.rect.bottom == obj.rect.top:  # Столкновение снизу
                    self.platform_width += obj.rect.width

    def check_collision_with_player(self, player):
        if player.rect.colliderect(self.rect):
            player.health -= 1
            print("Урон игроку! Здоровье игрока:", player.health)  # Сообщение об уроне


def get_background(name):
    image = pygame.image.load(join("assets", "Background", name))
    _, _, width, height = image.get_rect()
    tiles = []

    for i in range(WIDTH // width + 1):
        for j in range(HEIGHT // height + 1):
            pos = (i * width, j * height)
            tiles.append(pos)

    return tiles, image


def draw(window, background, bg_image, player, objects, offset_x):
    for tile in background:
        window.blit(bg_image, tile)

    for obj in objects:
        obj.draw(window, offset_x)

    player.draw(window, offset_x)

    pygame.display.update()


def handle_vertical_collision(player, objects, dy):
    collided_objects = []
    for obj in objects:
        if pygame.sprite.collide_mask(player, obj):
            if dy > 0:
                player.rect.bottom = obj.rect.top
                player.landed()
            elif dy < 0:
                player.rect.top = obj.rect.bottom
                player.hit_head()

            collided_objects.append(obj)

    return collided_objects


def collide(player, objects, dx):
    player.move(dx, 0)
    player.update()
    collided_object = None
    for obj in objects:
        if pygame.sprite.collide_mask(player, obj):
            collided_object = obj
            break

    player.move(-dx, 0)
    player.update()
    return collided_object


def handle_move(player, objects):
    keys = pygame.key.get_pressed()

    player.x_vel = 0
    collide_left = collide(player, objects, -PLAYER_VEL * 2)
    collide_right = collide(player, objects, PLAYER_VEL * 2)

    if keys[pygame.K_LEFT] and not collide_left:
        player.move_left(PLAYER_VEL)
    if keys[pygame.K_RIGHT] and not collide_right:
        player.move_right(PLAYER_VEL)

    vertical_collide = handle_vertical_collision(player, objects, player.y_vel)
    to_check = [collide_left, collide_right, *vertical_collide]

    for obj in to_check:
        if obj and obj.name == "fire":
            player.make_hit()


def levels_menu(window, skin="MaskDude"):
    font = pygame.font.Font(None, 74)
    button_font = pygame.font.Font(None, 36)

    selected_level = 1
    running = True
    num_levels = 50
    levels_per_page = 20
    current_page = 1

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                pygame.quit()
                quit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    selected_level = max(1, selected_level - 5)
                if event.key == pygame.K_DOWN:
                    selected_level = min(num_levels, selected_level + 5)
                if event.key == pygame.K_LEFT:
                    selected_level = max(1, selected_level - 1)
                if event.key == pygame.K_RIGHT:
                    selected_level = min(num_levels, selected_level + 1)
                if event.key == pygame.K_RETURN:
                    running = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                for i in range(levels_per_page):
                    level_index = (current_page - 1) * levels_per_page + i
                    if level_index >= num_levels:
                        break
                    level_rect = level_texts[i].get_rect(center=(WIDTH // 2 + (i % 5) * 100 - 200, HEIGHT // 2 + (i // 5) * 40 - 100))
                    if level_rect.collidepoint(event.pos):
                        selected_level = level_index + 1
                        running = False
                if next_page_rect.collidepoint(event.pos) and current_page < (num_levels + levels_per_page - 1) // levels_per_page:
                    current_page += 1
                if prev_page_rect.collidepoint(event.pos) and current_page > 1:
                    current_page -= 1
                if back_button_rect.collidepoint(event.pos):
                    running = False
                    main_menu(window)  # Возвращение в главное меню

        background, bg_image = get_background('Gray.png')
        for tile in background:
            window.blit(bg_image, tile)

        title_text = font.render("Выбор уровня", True, (255, 255, 255))  # Изменено название
        title_rect = title_text.get_rect(center=(WIDTH // 2, HEIGHT // 3))
        window.blit(title_text, title_rect)

        level_texts = []
        start_index = (current_page - 1) * levels_per_page
        end_index = min(start_index + levels_per_page, num_levels)

        for i in range(start_index, end_index):
            level_text = button_font.render(str(i + 1), True, (255, 255, 255))
            level_texts.append(level_text)

        for i, level_text in enumerate(level_texts):
            level_rect = level_text.get_rect(center=(WIDTH // 2 + (i % 5) * 100 - 200, HEIGHT // 2 + (i // 5) * 40 - 100))
            window.blit(level_text, level_rect)
            if (i + start_index + 1) == selected_level:
                pygame.draw.rect(window, (255, 255, 0), level_rect.inflate(10, 10), 2)

        next_page_text = button_font.render("Next Page", True, (255, 255, 255))
        next_page_rect = next_page_text.get_rect(center=(WIDTH // 2 + 200, HEIGHT - 100))
        window.blit(next_page_text, next_page_rect)

        prev_page_text = button_font.render("Prev Page", True, (255, 255, 255))
        prev_page_rect = prev_page_text.get_rect(center=(WIDTH // 2 - 200, HEIGHT - 100))
        window.blit(prev_page_text, prev_page_rect)

        # Кнопка "Назад"
        back_button_text = button_font.render("Назад", True, (255, 255, 255))
        back_button_rect = back_button_text.get_rect(center=(WIDTH // 2, HEIGHT - 50))
        window.blit(back_button_text, back_button_rect)
        pygame.draw.rect(window, (255, 255, 0), back_button_rect.inflate(10, 10), 2)

        pygame.display.update()

    start_game(window, selected_level, skin)  # Запуск игры, если уровень выбран


def main_menu(window):
    font = pygame.font.Font(None, 74)
    button_font = pygame.font.Font(None, 36)

    running = True
    selected_skin = "MaskDude"
    selected_background = "Blue.png"

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                pygame.quit()
                quit()

            if event.type == pygame.MOUSEBUTTONDOWN:
                if play_button_rect.collidepoint(event.pos):
                    levels_menu(window, selected_skin, selected_background)  # Переход на меню выбора уровней
                elif stats_button_rect.collidepoint(event.pos):
                    show_stats()  # Функция для отображения статистики
                elif settings_button_rect.collidepoint(event.pos):
                    show_settings()  # Функция для отображения настроек
                elif skin_button_rect.collidepoint(event.pos):
                    selected_skin, selected_background = skin_menu(window)  # Переход на меню выбора скинов

        background, bg_image = get_background('Gray.png')
        for tile in background:
            window.blit(bg_image, tile)

        title_text = font.render("Главное меню", True, (255, 255, 255))
        title_rect = title_text.get_rect(center=(WIDTH // 2, HEIGHT // 3))
        window.blit(title_text, title_rect)

        # Кнопка "Играть"
        play_button_text = button_font.render("Играть", True, (255, 255, 255))
        play_button_rect = play_button_text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        window.blit(play_button_text, play_button_rect)
        pygame.draw.rect(window, (255, 255, 0), play_button_rect.inflate(10, 10), 2)

        # Кнопка "Статистика"
        stats_button_text = button_font.render("Статистика", True, (255, 255, 255))
        stats_button_rect = stats_button_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 50))
        window.blit(stats_button_text, stats_button_rect)
        pygame.draw.rect(window, (255, 255, 0), stats_button_rect.inflate(10, 10), 2)

        # Кнопка "Настройки"
        settings_button_text = button_font.render("Настройки", True, (255, 255, 255))
        settings_button_rect = settings_button_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 100))
        window.blit(settings_button_text, settings_button_rect)
        pygame.draw.rect(window, (255, 255, 0), settings_button_rect.inflate(10, 10), 2)

        # Кнопка "Скин"
        skin_button_text = button_font.render("Скин", True, (255, 255, 255))
        skin_button_rect = skin_button_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 150))
        window.blit(skin_button_text, skin_button_rect)
        pygame.draw.rect(window, (255, 255, 0), skin_button_rect.inflate(10, 10), 2)

        pygame.display.update()

    pygame.quit()
    quit()


def skin_menu(window):
    font = pygame.font.Font(None, 74)
    button_font = pygame.font.Font(None, 36)

    skins = ["MaskDude", "VirtualGuy", "PinkMan", "NinjaFrog"]
    backgrounds = ["Blue.png", "Brown.png", "Gray.png", "Green.png", "Pink.png", "Purple.png", "Yellow.png"]
    current_skin_index = 0
    current_background_index = 0
    selected_skin = skins[current_skin_index]
    selected_background = backgrounds[current_background_index]

    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                pygame.quit()
                quit()

            if event.type == pygame.MOUSEBUTTONDOWN:
                if left_arrow_rect.collidepoint(event.pos):
                    current_skin_index = (current_skin_index - 1) % len(skins)
                elif right_arrow_rect.collidepoint(event.pos):
                    current_skin_index = (current_skin_index + 1) % len(skins)
                elif select_button_rect.collidepoint(event.pos):
                    selected_skin = skins[current_skin_index]
                elif back_button_rect.collidepoint(event.pos):
                    running = False
                    main_menu(window)  # Возвращение в главное меню
                elif left_bg_arrow_rect.collidepoint(event.pos):
                    current_background_index = (current_background_index - 1) % len(backgrounds)
                elif right_bg_arrow_rect.collidepoint(event.pos):
                    current_background_index = (current_background_index + 1) % len(backgrounds)
                elif select_bg_button_rect.collidepoint(event.pos):
                    selected_background = backgrounds[current_background_index]

        background, bg_image = get_background('Gray.png')
        for tile in background:
            window.blit(bg_image, tile)

        title_text = font.render("Выбор скина и фона", True, (255, 255, 255))
        title_rect = title_text.get_rect(center=(WIDTH // 2, HEIGHT // 3))
        window.blit(title_text, title_rect)

        # Отображение текущего скина
        skin_name = skins[current_skin_index]
        skin_sprites = load_sprite_sheets("MainCharacters", skin_name, 32, 32, True)["idle_right"]
        skin_image = skin_sprites[(pygame.time.get_ticks() // 100) % len(skin_sprites)]
        skin_image = pygame.transform.scale2x(skin_image)
        skin_rect = skin_image.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        window.blit(skin_image, skin_rect)

        # Отображение стрелок для скинов
        left_arrow_text = button_font.render("<", True, (255, 255, 255))
        left_arrow_rect = left_arrow_text.get_rect(center=(WIDTH // 2 - 100, HEIGHT // 2))
        window.blit(left_arrow_text, left_arrow_rect)

        right_arrow_text = button_font.render(">", True, (255, 255, 255))
        right_arrow_rect = right_arrow_text.get_rect(center=(WIDTH // 2 + 100, HEIGHT // 2))
        window.blit(right_arrow_text, right_arrow_rect)

        # Кнопка "Выбрать" для скина
        select_button_text = button_font.render("Выбрать", True, (255, 255, 255))
        select_button_rect = select_button_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 100))
        window.blit(select_button_text, select_button_rect)
        pygame.draw.rect(window, (255, 255, 0), select_button_rect.inflate(10, 10), 2)

        # Отображение текущего фона
        background_name = backgrounds[current_background_index]
        background_image = pygame.image.load(join("assets", "Background", background_name)).convert()
        background_image = pygame.transform.scale(background_image, (100, 100))
        background_rect = background_image.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 200))
        window.blit(background_image, background_rect)

        # Отображение стрелок для фонов
        left_bg_arrow_text = button_font.render("<", True, (255, 255, 255))
        left_bg_arrow_rect = left_bg_arrow_text.get_rect(center=(WIDTH // 2 - 100, HEIGHT // 2 + 200))
        window.blit(left_bg_arrow_text, left_bg_arrow_rect)

        right_bg_arrow_text = button_font.render(">", True, (255, 255, 255))
        right_bg_arrow_rect = right_bg_arrow_text.get_rect(center=(WIDTH // 2 + 100, HEIGHT // 2 + 200))
        window.blit(right_bg_arrow_text, right_bg_arrow_rect)

        # Кнопка "Выбрать" для фона
        select_bg_button_text = button_font.render("Выбрать фон", True, (255, 255, 255))
        select_bg_button_rect = select_bg_button_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 300))
        window.blit(select_bg_button_text, select_bg_button_rect)
        pygame.draw.rect(window, (255, 255, 0), select_bg_button_rect.inflate(10, 10), 2)

        # Кнопка "Назад"
        back_button_text = button_font.render("Назад", True, (255, 255, 255))
        back_button_rect = back_button_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 350))
        window.blit(back_button_text, back_button_rect)
        pygame.draw.rect(window, (255, 255, 0), back_button_rect.inflate(10, 10), 2)

        # Отображение "Выбрано" если текущий скин выбран
        if skin_name == selected_skin:
            selected_text = button_font.render("Выбрано", True, (255, 255, 255, 128))
            selected_rect = selected_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 50))
            window.blit(selected_text, selected_rect)

        # Отображение "Выбрано" если текущий фон выбран
        if background_name == selected_background:
            selected_bg_text = button_font.render("Выбрано", True, (255, 255, 255, 128))
            selected_bg_rect = selected_bg_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 250))
            window.blit(selected_bg_text, selected_bg_rect)

        pygame.display.update()

    return selected_skin, selected_background

# Заглушки для функций статистики и настроек
def show_stats():
    print("Отображение статистики")
    # Здесь будет код для отображения статистики

def show_settings():
    print("Отображение настроек")
    # Здесь будет код для отображения настроек


def start_game(window, level_number, skin="MaskDude", background_name="Blue.png"):
    """Запускает игру с выбранным уровнем, скином и фоном."""
    clock = pygame.time.Clock()
    background, bg_image = get_background(background_name)  # Загрузка фона
    player = Player(100, 100, 50, 50, skin)

    level_objects = levels.get_level_data(level_number)  # загружаем уровень на основе выбора пользователя

    offset_x = 0
    scroll_area_width = 200

    stop_button = pygame.image.load("assets/stop.png").convert_alpha()
    stop_button_rect = stop_button.get_rect(topright=(WIDTH - 10, 10))

    run = True
    while run:
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
                break

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE and player.jump_count < 2:
                    player.jump()

            if event.type == pygame.MOUSEBUTTONDOWN:
                if stop_button_rect.collidepoint(event.pos):
                    run = False
                    pause_menu(window, level_number, skin, background_name)

        player.loop(FPS, level_objects)
        handle_move(player, level_objects)
        draw(window, background, bg_image, player, level_objects, offset_x)

        window.blit(stop_button, stop_button_rect)

        if ((player.rect.right - offset_x >= WIDTH - scroll_area_width) and player.x_vel > 0) or (
                (player.rect.left - offset_x <= scroll_area_width) and player.x_vel < 0):
            offset_x += player.x_vel

        pygame.display.update()

    pygame.quit()
    quit()


def pause_menu(window, level_number, skin, background_name):
    font = pygame.font.Font(None, 74)
    button_font = pygame.font.Font(None, 36)

    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                pygame.quit()
                quit()

            if event.type == pygame.MOUSEBUTTONDOWN:
                if resume_button_rect.collidepoint(event.pos):
                    start_game(window, level_number, skin, background_name)
                elif menu_button_rect.collidepoint(event.pos):
                    main_menu(window)
                elif restart_button_rect.collidepoint(event.pos):
                    start_game(window, level_number, skin, background_name)

        background, bg_image = get_background(background_name)
        for tile in background:
            window.blit(bg_image, tile)

        title_text = font.render("Пауза", True, (255, 255, 255))
        title_rect = title_text.get_rect(center=(WIDTH // 2, HEIGHT // 3))
        window.blit(title_text, title_rect)

        # Кнопка "Продолжить"
        resume_button_text = button_font.render("Продолжить", True, (255, 255, 255))
        resume_button_rect = resume_button_text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        window.blit(resume_button_text, resume_button_rect)
        pygame.draw.rect(window, (255, 255, 0), resume_button_rect.inflate(10, 10), 2)

        # Кнопка "Меню"
        menu_button_text = button_font.render("Меню", True, (255, 255, 255))
        menu_button_rect = menu_button_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 50))
        window.blit(menu_button_text, menu_button_rect)
        pygame.draw.rect(window, (255, 255, 0), menu_button_rect.inflate(10, 10), 2)

        # Кнопка "Перезапуск"
        restart_button_text = button_font.render("Перезапуск", True, (255, 255, 255))
        restart_button_rect = restart_button_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 100))
        window.blit(restart_button_text, restart_button_rect)
        pygame.draw.rect(window, (255, 255, 0), restart_button_rect.inflate(10, 10), 2)

        pygame.display.update()


if __name__ == "__main__":
    pygame.init()
    window = pygame.display.set_mode((WIDTH, HEIGHT))
    main_menu(window) # Вызов главного меню ПЕРВЫМ
