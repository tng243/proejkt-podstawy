import pygame
import math
import random
import sys

# --- KONFIGURACJA ---
pygame.init()
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
WIDTH, HEIGHT = screen.get_width(), screen.get_height()

MAP_WIDTH, MAP_HEIGHT = 4000, 4000
FPS = 60
BOSS_COLOR = (0, 0, 0)
BULLET_COLOR = (255, 255, 0)
ENEMY_BULLET_COLOR = (255, 100, 0)
GEM_COLOR = (0, 200, 255) # Niebieski dla zwykłego expa
BG_COLOR = (30, 30, 30)

clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 24) 
bold_font = pygame.font.SysFont(None, 32)

CHARACTERS = {
    "Warrior": {"weapon": "Axe",    "damage": 4, "speed": 3.0, "color": (180, 60,  0  )},
    "Rogue":   {"weapon": "Dagger", "damage": 1, "speed": 6.0, "color": (150, 0,   150)},
    "Knight":  {"weapon": "Sword",  "damage": 2, "speed": 4.0, "color": (0,   100, 200)},
    "Brawler": {"weapon": "Fist",   "damage": 1, "speed": 4.5, "color": (200, 120, 0  )},
}



def show_main_menu():
    options = list(CHARACTERS.keys())
    selected = 0
    while True:
        screen.fill((20, 20, 30))
        screen.blit(bold_font.render("SELECT YOUR CHARACTER", True, (255,255,255)), (WIDTH//2-160, HEIGHT//2-120))
        for i, name in enumerate(options):
            color = (255, 220, 0) if i == selected else (160, 160, 160)
            char = CHARACTERS[name]
            text = f"[{i+1}] {name} — {char['weapon']}"
            screen.blit(font.render(text, True, color), (WIDTH//2-150, HEIGHT//2-40 + i*45))
        screen.blit(font.render("ENTER to confirm", True, (100,100,100)), (WIDTH//2-80, HEIGHT//2+160))
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_1: selected = 0
                if e.key == pygame.K_2: selected = 1
                if e.key == pygame.K_3: selected = 2
                if e.key == pygame.K_4: selected = 3
                if e.key == pygame.K_RETURN: return options[selected]
                if e.key == pygame.K_ESCAPE: pygame.quit(); sys.exit()

class ExperienceGem:
    def __init__(self, pos, value, color=GEM_COLOR):
        self.pos = pygame.Vector2(pos)
        self.value = value
        self.color = color
        self.radius = 4 if value < 10 else 7

    def draw(self, cam_x, cam_y):
        px, py = int(self.pos.x - cam_x), int(self.pos.y - cam_y)
        # Rysowanie małego brylantu (romb)
        points = [(px, py - self.radius), (px + self.radius, py), (px, py + self.radius), (px - self.radius, py)]
        pygame.draw.polygon(screen, self.color, points)
        pygame.draw.polygon(screen, (255, 255, 255), points, 1) # Biała obwódka

class Player:
    def __init__(self):
        self.pos = pygame.Vector2(MAP_WIDTH // 2, MAP_HEIGHT // 2)
        self.hp = 100
        self.max_hp = 100
        self.speed = 4.0
        self.radius = 15
        self.pickup_range = 40
        self.attack_cooldown = 0
        self.base_cooldown = 450
        self.damage = 1
        self.level = 1
        self.exp = 0
        self.exp_to_next_level = 10
        self.weapon = "Magic Ball"
        self.sword_range = 90
        self.sword_timer = 0
        self.color = (0, 120, 0)

    def move(self, keys):
        vel = pygame.Vector2(0, 0)
        if keys[pygame.K_w]: vel.y = -1
        if keys[pygame.K_s]: vel.y = 1
        if keys[pygame.K_a]: vel.x = -1
        if keys[pygame.K_d]: vel.x = 1
        if vel.length() > 0:
            self.pos += vel.normalize() * self.speed
        self.pos.x = max(self.radius, min(MAP_WIDTH - self.radius, self.pos.x))
        self.pos.y = max(self.radius, min(MAP_HEIGHT - self.radius, self.pos.y))

    def check_level_up(self):
        if self.exp >= self.exp_to_next_level:
            self.exp -= self.exp_to_next_level
            self.level += 1
            self.exp_to_next_level = int(self.level * 12)
            self.hp = min(self.max_hp, self.hp + 15)
            return True
        return False

    def draw(self, cam_x, cam_y):
        px, py = int(self.pos.x - cam_x), int(self.pos.y - cam_y)

        if self.weapon == "Lightsaber" and self.sword_timer > 0:
            rng = int(self.sword_range * 1.5)
            s = pygame.Surface((rng*2, rng*2), pygame.SRCALPHA)
            pygame.draw.circle(s, (0, 255, 50, 100), (rng, rng), rng)
            screen.blit(s, (px - rng, py - rng))
            self.sword_timer -= 1

        elif self.weapon == "Sword" and self.sword_timer > 0:
            rng = self.sword_range
            s = pygame.Surface((rng*2, rng*2), pygame.SRCALPHA)
            pygame.draw.circle(s, (0, 200, 255, 100), (rng, rng), rng)
            screen.blit(s, (px - rng, py - rng))
            self.sword_timer -= 1

        elif self.weapon == "Axe" and self.sword_timer > 0:
            s = pygame.Surface((300, 300), pygame.SRCALPHA)
            pygame.draw.circle(s, (255, 100, 0, 120), (150, 150), 120)
            screen.blit(s, (px - 150, py - 150))
            self.sword_timer -= 1

        elif self.weapon == "Fist" and self.sword_timer > 0:
            s = pygame.Surface((160, 160), pygame.SRCALPHA)
            pygame.draw.circle(s, (255, 220, 0, 150), (80, 80), 80)
            screen.blit(s, (px - 80, py - 80))
            self.sword_timer -= 1

        pygame.draw.circle(screen, self.color, (px, py), self.radius)
        pygame.draw.circle(screen, (50, 255, 50), (px, py - 12), 9)
        pygame.draw.circle(screen, (0, 0, 0), (px - 3, py - 14), 2)
        pygame.draw.circle(screen, (0, 0, 0), (px + 3, py - 14), 2)
        
        
        

class Enemy:
    def __init__(self, player_level, player_pos, is_boss=False):
        angle = random.uniform(0, 2 * math.pi)
        spawn_dist = max(WIDTH, HEIGHT) / 2 + 100
        self.pos = pygame.Vector2(player_pos.x + math.cos(angle) * spawn_dist, player_pos.y + math.sin(angle) * spawn_dist)
        self.is_boss = is_boss
        tier = player_level // 5
        if is_boss:
            self.max_hp = 100 + (player_level * 15); self.radius = 40; self.speed = 1.2; self.color = BOSS_COLOR; self.attack_timer = 0 
            self.hp = self.max_hp
            
        else:
            self.hp = 1 + (tier * 3); self.radius = 12; self.speed = random.uniform(1.6, 2.4) + (tier * 0.4)
            self.color = (255, 0, 0) if tier == 0 else (200, 0, 100) if tier == 1 else (150, 0, 150)

    def update(self, player_pos):
        d = player_pos - self.pos
        if d.length() > 0: self.pos += d.normalize() * self.speed

        


     #boss health bar
 

def draw_boss_hud(boss):
    bar_w, bar_h = 500, 22
    bar_x = WIDTH // 2 - bar_w // 2
    bar_y = HEIGHT - 60
    hp_ratio = max(0, boss.hp / boss.max_hp)
    pygame.draw.rect(screen, (60, 0, 0), (bar_x, bar_y, bar_w, bar_h), border_radius=4)
    pygame.draw.rect(screen, (255, int(hp_ratio * 120), 0), (bar_x, bar_y, int(hp_ratio * bar_w), bar_h), border_radius=4)
    pygame.draw.rect(screen, (200, 200, 200), (bar_x, bar_y, bar_w, bar_h), 2, border_radius=4)
    screen.blit(bold_font.render("BOSS", True, (255, 60, 60)), (bar_x - 60, bar_y - 1))
    screen.blit(font.render(f"{int(boss.hp)} / {boss.max_hp}", True, (220, 220, 220)), (bar_x + bar_w + 10, bar_y + 3))

class Bullet:
    def __init__(self, start_pos, target_pos, color=BULLET_COLOR, pierce=1, speed=12, radius=5):
        self.pos = pygame.Vector2(start_pos)
        self.speed = speed; self.radius = radius; self.color = color; self.pierce = pierce
        direction = target_pos - start_pos
        self.dir = direction.normalize() if direction.length() > 0 else pygame.Vector2(1, 0)
    def update(self): self.pos += self.dir * self.speed

# --- FUNKCJE MENU (BEZ ZMIAN) ---
def show_stat_menu():
    while True:
        screen.fill((40, 70, 40))
        t = bold_font.render("WYBIERZ ULEPSZENIE:", True, (255, 255, 255))
        o = [font.render("[1] +20 MAX HP", True, (255, 50, 50)), font.render("[2] +1 DMG", True, (255, 255, 0)), font.render("[3] +0.5 SPD", True, (50, 255, 255))]
        screen.blit(t, (WIDTH//2-150, HEIGHT//2-100))
        for i, opt in enumerate(o): screen.blit(opt, (WIDTH//2-100, HEIGHT//2-20 + i*50))
        
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_1: return 'HP'
                if e.key == pygame.K_2: return 'DMG'
                if e.key == pygame.K_3: return 'SPD'
                if e.key == pygame.K_ESCAPE: pygame.quit(); sys.exit()

def show_weapon_menu(lvl):
    while True:
        screen.fill((70, 40, 70))
        txt = "POZIOM 5! WYBIERZ BRON:" if lvl == 5 else "POZIOM 10! EWOLUCJA:"
        opts = ["[1] LUK", "[2] MIECZ"] if lvl == 5 else ["[1] KARABIN", "[2] MIECZ SWIETLNY"]
        t = bold_font.render(txt, True, (255, 255, 255))
        screen.blit(t, (WIDTH//2-150, HEIGHT//2-100))
        for i, opt in enumerate(opts): screen.blit(font.render(opt, True, (255, 255, 255)), (WIDTH//2-100, HEIGHT//2 + i*50))
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_1: return "Bow" if lvl == 5 else "Machine Gun"
                if e.key == pygame.K_2: return "Sword" if lvl == 5 else "Lightsaber"

def main():
    
    chosen = show_main_menu()          
    char_data = CHARACTERS[chosen]     

    player = Player()
    player.weapon = char_data["weapon"]   
    player.damage = char_data["damage"]    
    player.speed  = char_data["speed"]     
    player.color  = char_data["color"] 
    
    enemies, bullets, enemy_bullets, gems = [], [], [], []
    spawn_timer = 0
    running = True

    while running:
        dt = clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE): running = False

        if player.check_level_up():
            if player.level == 5: player.weapon = show_weapon_menu(5)
            elif player.level == 10: player.weapon = show_weapon_menu(10)
            elif player.level % 2 == 0:
                c = show_stat_menu()
                if c == 'HP': player.max_hp += 20; player.hp += 20
                elif c == 'DMG': player.damage += 1
                elif c == 'SPD': player.speed += 0.5

        # Spawn
        spawn_timer += dt
        if spawn_timer > max(150, 1000 - (player.level * 40)):
            for _ in range(1 + player.level // 4): enemies.append(Enemy(player.level, player.pos))
            spawn_timer = 0
        if player.level % 10 == 0 and not any(e.is_boss for e in enemies): enemies.append(Enemy(player.level, player.pos, True))

        # Atak gracza
          # Atak gracza
        player.attack_cooldown -= dt
        if enemies and player.attack_cooldown <= 0:

            if player.weapon == "Axe":
                player.sword_timer = 15
                for e in enemies[:]:
                    if player.pos.distance_to(e.pos) < player.sword_range + e.radius:
                        e.hp -= player.damage
                        if e.hp <= 0:
                            gems.append(ExperienceGem(e.pos, 50 if e.is_boss else 3, (255, 0, 255) if e.is_boss else GEM_COLOR))
                            enemies.remove(e)
                player.attack_cooldown = player.base_cooldown * 2.5

            elif player.weapon == "Dagger":
                target = min(enemies, key=lambda e: player.pos.distance_to(e.pos)).pos
                for offset in [-15, 0, 15]:
                    angle = math.atan2(target.y - player.pos.y, target.x - player.pos.x)
                    spread = pygame.Vector2(math.cos(angle + math.radians(offset)), math.sin(angle + math.radians(offset)))
                    fake_target = player.pos + spread * 100
                    bullets.append(Bullet(player.pos, fake_target, (200, 0, 200), speed=18, radius=3))
                player.attack_cooldown = player.base_cooldown * 0.3

            elif player.weapon == "Sword":
                player.sword_timer = 10
                for e in enemies[:]:
                    if player.pos.distance_to(e.pos) < player.sword_range + e.radius:
                        e.hp -= player.damage
                        if e.hp <= 0:
                            gems.append(ExperienceGem(e.pos, 50 if e.is_boss else 3, (255, 0, 255) if e.is_boss else GEM_COLOR))
                            enemies.remove(e)
                player.attack_cooldown = player.base_cooldown * 1.2

            elif player.weapon == "Fist":
                player.sword_timer = 8
                for e in enemies[:]:
                    if player.pos.distance_to(e.pos) < player.sword_range + e.radius:
                        push_dir = (e.pos - player.pos).normalize()
                        e.pos += push_dir * 120
                        e.hp -= player.damage
                        if e.hp <= 0:
                            gems.append(ExperienceGem(e.pos, 50 if e.is_boss else 3, (255, 0, 255) if e.is_boss else GEM_COLOR))
                            enemies.remove(e)
                player.attack_cooldown = player.base_cooldown * 0.9

            elif player.weapon == "Lightsaber":
                player.sword_timer = 10
                for e in enemies[:]:
                    if player.pos.distance_to(e.pos) < player.sword_range * 1.5 + e.radius:
                        e.hp -= player.damage * 3
                        if e.hp <= 0:
                            gems.append(ExperienceGem(e.pos, 50 if e.is_boss else 3, (255, 0, 255) if e.is_boss else GEM_COLOR))
                            enemies.remove(e)
                player.attack_cooldown = player.base_cooldown * 0.8

            elif player.weapon == "Machine Gun":
                target = min(enemies, key=lambda e: player.pos.distance_to(e.pos)).pos
                bullets.append(Bullet(player.pos, target, (255, 200, 0), speed=16, radius=3))
                player.attack_cooldown = player.base_cooldown * 0.2

            elif player.weapon == "Bow":
                target = min(enemies, key=lambda e: player.pos.distance_to(e.pos)).pos
                bullets.append(Bullet(player.pos, target, (200, 200, 200), pierce=3))
                player.attack_cooldown = player.base_cooldown

            else:  # Magic Ball (default)
                target = min(enemies, key=lambda e: player.pos.distance_to(e.pos)).pos
                bullets.append(Bullet(player.pos, target, BULLET_COLOR))
                player.attack_cooldown = player.base_cooldown
                    

        # Ruch i podnoszenie EXP
        player.move(pygame.key.get_pressed())
        for g in gems[:]:
            if player.pos.distance_to(g.pos) < player.pickup_range:
                player.exp += g.value
                gems.remove(g)

        # Update pocisków i przeciwników
        for b in bullets[:]:
            b.update()
            if b.pos.distance_to(player.pos) > WIDTH: bullets.remove(b); continue
            for e in enemies[:]:
                if b.pos.distance_to(e.pos) < e.radius + b.radius:
                    e.hp -= player.damage; b.pierce -= 1
                    if b.pierce <= 0 and b in bullets: bullets.remove(b)
                    if e.hp <= 0 and e in enemies:
                        gems.append(ExperienceGem(e.pos, 50 if e.is_boss else 3, (255, 0, 255) if e.is_boss else GEM_COLOR))
                        enemies.remove(e)
                    break

        for e in enemies[:]:
            e.update(player.pos)
            if e.pos.distance_to(player.pos) < player.radius + e.radius:
                player.hp -= 0.4
                if player.hp <= 0: running = False
            if e.is_boss:
                e.attack_timer += dt
                if e.attack_timer > 1000:
                    enemy_bullets.append(Bullet(e.pos, player.pos, ENEMY_BULLET_COLOR, radius=8)); e.attack_timer = 0

        for eb in enemy_bullets[:]:
            eb.update()
            if eb.pos.distance_to(player.pos) < player.radius + eb.radius: player.hp -= 15; enemy_bullets.remove(eb)
            elif eb.pos.distance_to(player.pos) > WIDTH: enemy_bullets.remove(eb)

        # Kamera i Rysowanie
        cam_x = max(0, min(MAP_WIDTH - WIDTH, player.pos.x - WIDTH // 2))
        cam_y = max(0, min(MAP_HEIGHT - HEIGHT, player.pos.y - HEIGHT // 2))
        screen.fill(BG_COLOR)
        for x in range(0, MAP_WIDTH, 250): pygame.draw.line(screen, (45, 45, 45), (x-cam_x, -cam_y), (x-cam_x, MAP_HEIGHT-cam_y))
        for y in range(0, MAP_HEIGHT, 250): pygame.draw.line(screen, (45, 45, 45), (-cam_x, y-cam_y), (MAP_WIDTH-cam_x, y-cam_y))
        
        for g in gems: g.draw(cam_x, cam_y)
        for b in bullets: pygame.draw.circle(screen, b.color, (int(b.pos.x - cam_x), int(b.pos.y - cam_y)), b.radius)
        for eb in enemy_bullets: pygame.draw.circle(screen, eb.color, (int(eb.pos.x - cam_x), int(eb.pos.y - cam_y)), eb.radius)
        for e in enemies:
            pygame.draw.circle(screen, e.color, (int(e.pos.x - cam_x), int(e.pos.y - cam_y)), e.radius)
            if e.is_boss: pygame.draw.circle(screen, (255,0,0), (int(e.pos.x - cam_x), int(e.pos.y - cam_y)), e.radius, 3)
        
        player.draw(cam_x, cam_y)

        # HUD
        pygame.draw.rect(screen, (100, 0, 0), (20, 20, 200, 15))
        pygame.draw.rect(screen, (255, 0, 0), (20, 20, max(0, (player.hp/player.max_hp)*200), 15))
        pygame.draw.rect(screen, (0, 150, 255), (20, 40, min(200, (player.exp/player.exp_to_next_level)*200), 8))
        screen.blit(font.render(f"LVL: {player.level} | {player.weapon}", True, (255, 255, 255)), (20, 55))
        boss = next((e for e in enemies if e.is_boss), None)
        if boss:
            draw_boss_hud(boss)
        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()