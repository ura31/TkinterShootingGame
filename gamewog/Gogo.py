import tkinter as tk
import random, time, math
import pygame
from tkinter import messagebox

# ===================== 설정 =====================
WIDTH, HEIGHT = 1200, 800
PLAYER_SIZE = 50
BULLET_SIZE = 20
ENEMY_SIZE = 50
ITEM_SIZE = 30
SURVIVAL_TIME = 180  
PLAYER_X, PLAYER_Y = WIDTH // 2, HEIGHT // 2 # 플레이어 캔버스 고정 위치

# pygame 초기화 및 BGM 재생 (경로 문제 발생 시 예외 처리)
pygame.mixer.init()
try:
    pygame.mixer.music.load("sound/bgm.ogg")
    pygame.mixer.music.play(-1)
except pygame.error:
    print("BGM 로드 실패. 'sound/bgm.ogg' 파일 경로를 확인하세요.")


# ===================== Player 클래스 (GIF) =====================
class PlayerGIF:
    def __init__(self, canvas, gif_path, x, y, speed=5):
        self.canvas = canvas
        self.frames = []
        i = 0
        while True:
            try:
                frame = tk.PhotoImage(file=gif_path, format=f"gif -index {i}")
                self.frames.append(frame)
                i += 1
            except:
                break
        self.frame_index = 0
        self.x = x 
        self.y = y 
        self.speed = speed
        self.id = canvas.create_image(self.x, self.y, image=self.frames[self.frame_index])
        self.direction = (0, -1)
        self.hp = 5
        self.bullet_count = 1
        self.shield = False
        self.shield_id = None
        self.shield_image = None 

    def animate(self):
        if self.frames:
            self.frame_index = (self.frame_index + 1) % len(self.frames)
            self.canvas.itemconfig(self.id, image=self.frames[self.frame_index])

    def move(self, dx=0, dy=0):
        if dx != 0 or dy != 0:
            self.direction = (dx, dy)


# ===================== Bullet 클래스 =====================
class BulletBase:
    def __init__(self, canvas, x, y, dx, dy, speed, image_obj):
        self.canvas = canvas
        self.x = x
        self.y = y
        self.dx = dx
        self.dy = dy
        self.speed = speed
        self.image = image_obj
        self.id = self.canvas.create_image(self.x, self.y, image=self.image)

    def move(self):
        self.x += self.dx * self.speed
        self.y += self.dy * self.speed
        self.canvas.coords(self.id, self.x, self.y)
        return 0 <= self.x <= WIDTH and 0 <= self.y <= HEIGHT

class PlayerBullet(BulletBase):
    def __init__(self, canvas, x, y, dx, dy, image_obj):
        super().__init__(canvas, x, y, dx, dy, speed=15, image_obj=image_obj)
        try:
            pygame.mixer.Sound("sound/bullet.ogg").play()
        except pygame.error:
            pass

class BossBullet(BulletBase):
    def __init__(self, canvas, x, y, dx, dy, image_obj):
        super().__init__(canvas, x, y, dx, dy, speed=10, image_obj=image_obj)

# ===================== Enemy 클래스 =====================
class Enemy:
    def __init__(self, canvas, images, type_id, x, y, speed=2): 
        self.canvas = canvas
        self.images = images
        self.frame_index = 0
        self.type_id = type_id
        self.x = x 
        self.y = y 
        self.speed = speed
        self.hp = 1 if type_id != 3 else 10
        self.attack_cooldown = 100
        self.frame_count = 0
        self.id = canvas.create_image(self.x, self.y, image=self.images[self.frame_index])
        self.dash_cooldown = 200

    def update_frame(self):
        self.frame_index = (self.frame_index + 1) % len(self.images)
        self.canvas.itemconfig(self.id, image=self.images[self.frame_index])

    def move_enemy(self, player, game):
        dx = PLAYER_X - self.x
        dy = PLAYER_Y - self.y
        dist = max((dx**2 + dy**2)**0.5, 0.01)
        
        self.x += self.speed * dx / dist
        self.y += self.speed * dy / dist
        
        if self.type_id == 2:
            self.dash_cooldown -= 1
            if self.dash_cooldown <= 0:
                self.x += dx / dist * 80
                self.y += dy / dist * 80
                self.dash_cooldown = 200

        elif self.type_id == 3:
            self.frame_count += 1
            if self.frame_count >= self.attack_cooldown:
                self.frame_count = 0
                for angle in range(0, 360, 45):
                    rad = angle * math.pi / 180
                    game.enemy_bullets.append(BossBullet(game.canvas, self.x, self.y, math.cos(rad), math.sin(rad), game.boss_bullet_img))
            
            self.dash_cooldown -= 1
            if self.dash_cooldown <= 0:
                self.x += dx / dist * 100
                self.y += dy / dist * 100
                self.dash_cooldown = 200
                
        self.canvas.coords(self.id, self.x, self.y)
        self.update_frame()

# ===================== Item 클래스 =====================
class Item:
    def __init__(self, canvas, type_id, images, x=None, y=None):
        self.canvas = canvas
        self.type_id = type_id
        self.x = x if x is not None else random.randint(50, WIDTH-50)
        self.y = y if y is not None else random.randint(50, HEIGHT-50)
        self.image = images[type_id-1] 
        self.id = self.canvas.create_image(self.x, self.y, image=self.image)


# ===================== Game 클래스 =====================
class Game:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Tk Survivor")
        self.canvas = tk.Canvas(self.root, width=WIDTH, height=HEIGHT)
        self.canvas.pack()

        # 모든 이미지 및 사운드 사전 로드 및 참조 유지
        self.load_images()
        
        # 배경
        self.TILE_WIDTH = self.bg_image.width()
        self.TILE_HEIGHT = self.bg_image.height()
        self.bg_tiles = []
        for i in range(-1, 2):
            for j in range(-1, 2):
                x = WIDTH / 2 + i * self.TILE_WIDTH
                y = HEIGHT / 2 + j * self.TILE_HEIGHT
                tid = self.canvas.create_image(x, y, image=self.bg_image)
                self.bg_tiles.append(tid)

        self.player = PlayerGIF(self.canvas, "image/player.gif", PLAYER_X, PLAYER_Y)
        self.player.shield_image = self.shield_img 

        self.bullets = []
        self.enemy_bullets = []
        self.enemies = []
        self.items = []

        self.start_time = time.time()
        self.game_over = False
        self.pressed_keys = set()
        self.frame_count = 0

        # UI
        self.hp_text = self.canvas.create_text(100, 30, text=f"HP: {self.player.hp}", fill="red", font=("Arial", 20))
        self.time_text = self.canvas.create_text(WIDTH - 150, 30, text=f"Time: {SURVIVAL_TIME}", fill="yellow", font=("Arial", 20))

        self.root.bind("<KeyPress>", self.key_press)
        self.root.bind("<KeyRelease>", self.key_release)
        self.root.bind("<Key-w>", self.key_press)
        self.root.bind("<Key-s>", self.key_press)
        self.root.bind("<Key-a>", self.key_press)
        self.root.bind("<Key-d>", self.key_press)
        self.root.bind("<KeyRelease-w>", self.key_release)
        self.root.bind("<KeyRelease-s>", self.key_release)
        self.root.bind("<KeyRelease-a>", self.key_release)
        self.root.bind("<KeyRelease-d>", self.key_release)


        self.main_loop()
        self.root.mainloop()

    def load_images(self):
        self.bg_image = tk.PhotoImage(file="image/bgimg.png")
        self.enemy1_imgs = [tk.PhotoImage(file=f"image/enemy1_{i}.png") for i in range(1, 5)]
        self.enemy2_imgs = [tk.PhotoImage(file=f"image/enemy2_{i}.png") for i in range(1, 5)]
        self.enemy_boss_imgs = [tk.PhotoImage(file=f"image/enemy_boss{i}.png") for i in range(1, 5)]
        self.player_bullet_img = tk.PhotoImage(file="image/bullet.png")
        self.boss_bullet_img = tk.PhotoImage(file="image/boss_bullet.png")
        item_files = ["image/item_hp.png", "image/item_speed.png", "image/item_power.png", "image/item_shield.png"]
        self.item_images = [tk.PhotoImage(file=f) for f in item_files]
        self.shield_img = tk.PhotoImage(file="image/shield.png")
        
        # 아이템 획득 사운드
        try:
            self.item_sound = pygame.mixer.Sound("sound/item.ogg")
        except pygame.error:
            self.item_sound = None
            print("아이템 획득 사운드 ('sound/item.ogg') 로드 실패.")

    # ------------------ 키 입력 ------------------
    def key_press(self, event):
        self.pressed_keys.add(event.keysym)
        if event.char in ('w', 'a', 's', 'd'):
            self.pressed_keys.add(event.char)
        if event.keysym == "space": self.shoot()

    def key_release(self, event):
        if event.keysym in self.pressed_keys:
            self.pressed_keys.remove(event.keysym)
        if event.char in ('w', 'a', 's', 'd'):
            if event.char in self.pressed_keys:
                self.pressed_keys.remove(event.char)

    # ------------------ 총알 발사 ------------------
    def shoot(self):
        dx, dy = self.player.direction
        if dx == 0 and dy == 0: dy = -1
        for i in range(self.player.bullet_count):
            offset = (i - (self.player.bullet_count - 1) / 2) * 10
            self.bullets.append(PlayerBullet(self.canvas, self.player.x + offset, self.player.y, dx, dy, self.player_bullet_img))

    # ------------------ 배경 이동 ------------------
    def move_world(self, dx, dy):
        move_x = -dx * self.player.speed
        move_y = -dy * self.player.speed

        for tile_id in self.bg_tiles:
            self.canvas.move(tile_id, move_x, move_y)
            x, y = self.canvas.coords(tile_id)
            if x < -self.TILE_WIDTH / 2: self.canvas.move(tile_id, self.TILE_WIDTH * 3, 0)
            if x > WIDTH + self.TILE_WIDTH / 2: self.canvas.move(tile_id, -self.TILE_WIDTH * 3, 0)
            if y < -self.TILE_HEIGHT / 2: self.canvas.move(tile_id, 0, self.TILE_HEIGHT * 3)
            if y > HEIGHT + self.TILE_HEIGHT / 2: self.canvas.move(tile_id, 0, -self.TILE_HEIGHT * 3)

        for enemy in self.enemies:
            self.canvas.move(enemy.id, move_x, move_y)
            enemy.x += move_x
            enemy.y += move_y

        for item in self.items:
            self.canvas.move(item.id, move_x, move_y)
            item.x += move_x
            item.y += move_y
            
        for bullet in self.enemy_bullets:
            self.canvas.move(bullet.id, move_x, move_y)
            bullet.x += move_x
            bullet.y += move_y

    # ------------------ 아이템 충돌 ------------------
    def check_item_collision(self):
        for item in self.items[:]:
            dx = self.player.x - item.x
            dy = self.player.y - item.y
            
            if (dx**2 + dy**2)**0.5 < (PLAYER_SIZE + ITEM_SIZE) // 2:
                
                # Item 1: HP (100% 획득)
                if item.type_id == 1:
                    self.player.hp = min(5, self.player.hp + 1)
                    
                # Item 2: Speed (100% 획득)
                elif item.type_id == 2:
                    self.player.speed = min(self.player.speed + 1, 12)
                    
                # Item 3: Power (100% 획득)
                elif item.type_id == 3:
                    self.player.bullet_count = min(self.player.bullet_count + 1, 3)
                    
                # Item 4: Shield (100% 획득)
                elif item.type_id == 4:
                    if not self.player.shield:
                        self.player.shield = True
                        if not self.player.shield_id:
                            self.player.shield_id = self.canvas.create_image(self.player.x, self.player.y, image=self.player.shield_image)
                            try:
                                pygame.mixer.Sound("sound/shieldUp.ogg").play() # 쉴드 전용 사운드
                            except pygame.error:
                                pass

                # 아이템 획득 사운드 재생 (쉴드가 아닐 때, 또는 쉴드 중복 획득일 때 일반 아이템 사운드)
                if self.item_sound:
                    try:
                        if item.type_id != 4 or (item.type_id == 4 and self.player.shield):
                             self.item_sound.play()
                    except pygame.error:
                        pass
                        
                self.canvas.delete(item.id)
                self.items.remove(item)

    # ------------------ 적 충돌 (아이템 드롭 100%) ------------------
    def check_enemy_collision(self):
        for enemy in self.enemies[:]:
            dx = self.player.x - enemy.x
            dy = self.player.y - enemy.y
            
            if (dx**2 + dy**2)**0.5 < (PLAYER_SIZE + ENEMY_SIZE) // 2:
                if self.player.shield:
                    self.player.shield = False
                    if self.player.shield_id:
                        self.canvas.delete(self.player.shield_id)
                        self.player.shield_id = None
                    try: pygame.mixer.Sound("sound/shieldDown.ogg").play()
                    except pygame.error: pass
                else:
                    self.player.hp -= 1
                    
                if enemy in self.enemies:
                    self.canvas.delete(enemy.id)
                    self.enemies.remove(enemy)
                    
            for bullet in self.bullets[:]:
                dx2 = bullet.x - enemy.x
                dy2 = bullet.y - enemy.y
                
                if (dx2**2 + dy2**2)**0.5 < (BULLET_SIZE + ENEMY_SIZE) // 2:
                    enemy.hp -= 1
                    
                    self.canvas.delete(bullet.id)
                    self.bullets.remove(bullet)
                    
                    if enemy.hp <= 0:
                        if enemy in self.enemies:
                            self.canvas.delete(enemy.id)
                            self.enemies.remove(enemy)
                            
                            # 아이템 드롭 확률 
                            if random.random() < 0.3: 
                                type_id = random.randint(1, 4)
                                self.items.append(Item(self.canvas, type_id, self.item_images, x=enemy.x, y=enemy.y))

    # ------------------ 적 생성 ------------------
    def spawn_enemy(self):
        elapsed = time.time() - self.start_time
        speed_base = 2 if elapsed < 60 else 3 if elapsed < 120 else 4
        
        if elapsed < 20:
            type_id = 1
            images = self.enemy1_imgs
        elif elapsed < 60:
            type_id = random.choices([1, 2], [0.7, 0.3])[0]
            images = self.enemy1_imgs if type_id == 1 else self.enemy2_imgs
        else:
            type_id = random.choices([1, 2, 3], [0.6, 0.3, 0.1])[0]
            images = self.enemy1_imgs if type_id == 1 else self.enemy2_imgs if type_id == 2 else self.enemy_boss_imgs
            
        spawn_dist = max(WIDTH, HEIGHT) / 2 + ENEMY_SIZE 
        angle = random.uniform(0, 2 * math.pi)
        
        x = PLAYER_X + math.cos(angle) * spawn_dist
        y = PLAYER_Y + math.sin(angle) * spawn_dist

        self.enemies.append(Enemy(self.canvas, images, type_id, x=x, y=y, speed=speed_base))

    # ------------------ 메인 루프 ------------------
    def main_loop(self):
        if self.game_over: return
        
        dx = dy = 0
        if "Up" in self.pressed_keys or "w" in self.pressed_keys: dy = -1
        if "Down" in self.pressed_keys or "s" in self.pressed_keys: dy = 1
        if "Left" in self.pressed_keys or "a" in self.pressed_keys: dx = -1
        if "Right" in self.pressed_keys or "d" in self.pressed_keys: dx = 1
        
        self.player.move(dx, dy)
        self.move_world(dx, dy)

        for bullet in self.bullets[:]:
            if not bullet.move():
                self.canvas.delete(bullet.id)
                self.bullets.remove(bullet)
                
        for bullet in self.enemy_bullets[:]:
            if not bullet.move():
                self.canvas.delete(bullet.id)
                self.enemy_bullets.remove(bullet)
            else:
                dx2 = self.player.x - bullet.x
                dy2 = self.player.y - bullet.y
                
                if (dx2**2 + dy2**2)**0.5 < (PLAYER_SIZE + BULLET_SIZE) // 2:
                    if self.player.shield:
                        self.player.shield = False
                        if self.player.shield_id:
                            self.canvas.delete(self.player.shield_id)
                            self.player.shield_id = None
                        try: pygame.mixer.Sound("sound/shieldDown.ogg").play()
                        except pygame.error: pass
                    else:
                        self.player.hp -= 1
                    
                    self.canvas.delete(bullet.id)
                    self.enemy_bullets.remove(bullet)

        for enemy in self.enemies: enemy.move_enemy(self.player, self)
        self.check_enemy_collision()
        self.check_item_collision()

        # 쉴드 이미지 
        if self.player.shield and not self.player.shield_id:
             self.player.shield_id = self.canvas.create_image(self.player.x, self.player.y, image=self.player.shield_image)
        elif not self.player.shield and self.player.shield_id:
            self.canvas.delete(self.player.shield_id)
            self.player.shield_id = None

        if self.frame_count % 3 == 0:
            self.player.animate() 
            
        self.canvas.itemconfig(self.hp_text, text=f"HP: {self.player.hp}")
        remaining = SURVIVAL_TIME - int(time.time() - self.start_time)
        self.canvas.itemconfig(self.time_text, text=f"Time: {max(0, remaining)}")

        self.frame_count += 1
        spawn_delay = 50 if remaining > 120 else 35 if remaining > 60 else 15
        if self.frame_count % spawn_delay == 0: self.spawn_enemy()

        if self.player.hp <= 0:
            self.game_over = True
            try: pygame.mixer.Sound("sound/lose.ogg").play()
            except pygame.error: pass
            messagebox.showinfo("Game Over", "플레이어가 사망했습니다!")
            self.root.destroy()
            return
            
        if remaining <= 0:
            self.game_over = True
            messagebox.showinfo("Clear!", "3분 생존 성공!")
            self.root.destroy()
            return

        self.root.after(30, self.main_loop)



Game()