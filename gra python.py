import pygame
import math
import random
import sys

pygame.init()
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
WIDTH, HEIGHT = screen.get_width(), screen.get_height()
pygame.display.set_caption("Roguelike")

MAP_WIDTH, MAP_HEIGHT = 4000, 4000
FPS = 60
BOSS_COLOR         = (20, 20, 20)
BULLET_COLOR       = (255, 240, 80)
ENEMY_BULLET_COLOR = (255, 80, 20)
GEM_COLOR          = (0, 200, 255)
BG_COLOR           = (18, 18, 28)
try:
    sword_icon = pygame.image.load("miecz.png").convert_alpha()
    sword_icon = pygame.transform.scale(sword_icon, (32, 32))
except:
    sword_icon = None
clock      = pygame.time.Clock()
font       = pygame.font.SysFont(None, 24)
bold_font  = pygame.font.SysFont(None, 32)
big_font   = pygame.font.SysFont(None, 72)
small_font = pygame.font.SysFont(None, 20)

CHARACTERS = {
    "Warrior": {"weapon": "Axe",    "damage": 4, "speed": 3.0, "color": (210,  80,  20),
                "ult_name": "Berserker Rage", "ult_desc": "5s: 3x DMG + nieśmiertelność"},
    "Rogue":   {"weapon": "Dagger", "damage": 1, "speed": 6.0, "color": (180,  20, 180),
                "ult_name": "Backstab Frenzy", "ult_desc": "4s: każdy atak = instant kill"},
    "Knight":  {"weapon": "Sword",  "damage": 2, "speed": 4.0, "color": ( 20, 120, 220),
                "ult_name": "Divine Smite", "ult_desc": "Piorun uderza we WSZYSTKICH wrogów"},
    "Brawler": {"weapon": "Fist",   "damage": 1, "speed": 4.5, "color": (220, 140,  20),
                "ult_name": "Rage Mode", "ult_desc": "3s: 3x speed + 3x DMG"},
}

settings = {"volume_music": 70, "volume_sfx": 80}

# ──────────────────────────────────────────────────────────────
#  PARTICLES
# ──────────────────────────────────────────────────────────────
particles = []

def spawn_particles(pos, color, count=8, speed_range=(1,4), life_range=(20,40)):
    for _ in range(count):
        a = random.uniform(0, 2*math.pi)
        s = random.uniform(*speed_range)
        l = random.randint(*life_range)
        particles.append({'pos': pygame.Vector2(pos),
                          'vel': pygame.Vector2(math.cos(a)*s, math.sin(a)*s),
                          'color': color, 'life': l, 'max_life': l,
                          'radius': random.uniform(2,5)})

def update_draw_particles(cam_x, cam_y):
    for p in particles[:]:
        p['pos'] += p['vel']; p['vel'] *= 0.92; p['life'] -= 1
        if p['life'] <= 0: particles.remove(p); continue
        r   = p['life']/p['max_life']
        col = tuple(min(255,int(c*r+30)) for c in p['color'])
        pygame.draw.circle(screen, col,
                           (int(p['pos'].x-cam_x), int(p['pos'].y-cam_y)),
                           max(1,int(p['radius']*r)))

levelup_flash = 0

# ──────────────────────────────────────────────────────────────
#  HAZARD ZONES
# ──────────────────────────────────────────────────────────────
class HazardZone:
    DURATION = 300
    def __init__(self, pos, radius=50, color=(255,60,0), harms_player=True):
        self.pos          = pygame.Vector2(pos)
        self.radius       = radius
        self.color        = color
        self.life         = self.DURATION
        self.anim         = random.uniform(0, math.pi*2)
        self.harms_player = harms_player
    @property
    def alive(self): return self.life > 0
    def update(self): self.life -= 1; self.anim += 0.08
    def draw(self, cam_x, cam_y):
        ratio = self.life/self.DURATION
        alpha = int(80*ratio+30)
        px,py = int(self.pos.x-cam_x), int(self.pos.y-cam_y)
        r     = self.radius + int(math.sin(self.anim)*6)
        s     = pygame.Surface((r*2,r*2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, alpha), (r,r), r)
        pygame.draw.circle(s, (*self.color, min(255,alpha+60)), (r,r), r, 3)
        screen.blit(s, (px-r, py-r))
    def touches(self, pos, radius):
        return self.pos.distance_to(pos) < self.radius+radius

# ──────────────────────────────────────────────────────────────
#  ITEM DEFINITIONS
# ──────────────────────────────────────────────────────────────
ITEM_DEFS = {
    # ── original 4 passives ──
    "magnet":        {"label":"Magnes",             "desc":"Zwieksza zasieg podnoszenia przedmiotow i gemow EXP.",        "color":(180,180,255), "type":"passive"},
    "trident":       {"label":"Trojzab",             "desc":"Kazdy atak strzela dodatkowo w 3 kierunki. Stackuje sie!",   "color":(100,200,255), "type":"passive"},
    "vampire_tooth": {"label":"Zab Wampira",         "desc":"Kradniesz 5% zadanych obrazen jako HP. Stackuje sie!",      "color":(200,  0, 80), "type":"passive"},
    "speed_boots":   {"label":"Buty Szybkosci",      "desc":"Trwale zwiekszasz swoja predkosc poruszania.",               "color":(255,220,  0), "type":"passive"},
    # ── 10 active ──
    "chain":         {"label":"Eteryczny Lancuch",   "desc":"Pocisk przeskakuje na 3 kolejne cele po trafieniu.",          "color":( 80,200,255), "type":"active"},
    "chalice":       {"label":"Kielich Krwiopijcy",  "desc":"Co kilka sekund wylewa krag palacy wrogow wokol gracza.",     "color":(180,  0, 60), "type":"active"},
    "mirror":        {"label":"Lustro Odbic",         "desc":"Odbija pociski wrogow z podwojoną siłą.",                    "color":(200,220,255), "type":"active"},
    "bell":          {"label":"Cmentarny Dzwon",      "desc":"Emituje fale dźwiekowa ogluszajaca wrogow na 1.5s.",         "color":(200,180, 80), "type":"active"},
    "shadows":       {"label":"Roj Cieni",            "desc":"Duszki krazace wokol gracza wgryzaja sie w wrogow (DoT).",   "color":( 80, 40,120), "type":"active"},
    "frost_staff":   {"label":"Lodowy Kostur",        "desc":"Strzela lodowymi kolcami zamrazajacymi wrogow.",             "color":( 80,200,255), "type":"active"},
    "poison_gaunt":  {"label":"Zatruta Rekawica",     "desc":"Co 4. atak wyrzuca chmure toksycznego gazu na ziemi.",      "color":( 80,200, 80), "type":"active"},
    "books":         {"label":"Orbita Ksiag",         "desc":"Lewitujace tomy krazace wokol; wybuch przy trafieniu wroga.", "color":(220,160, 40), "type":"active"},
    "holy_whip":     {"label":"Swiety Bicz Swiatla",  "desc":"Uderza w linii przed i za graczem, odpychajac wrogow.",     "color":(255,240,100), "type":"active"},
    "anvil":         {"label":"Kowadlo Przeznaczenia","desc":"Spada z nieba na najsilniejszego wroga, AoE obrazenia.",    "color":(140,140,160), "type":"active"},
    # ── 10 passive ──
    "hourglass":     {"label":"Srebrna Klepsydra",    "desc":"Przedluza wszystkie efekty (mrozenie, gaz, ogien) o 15%.",  "color":(200,200,200), "type":"passive"},
    "rusty_magnet":  {"label":"Zardzewialy Magnes",   "desc":"Zwieksza zasieg zbierania doswiadczenia o 25%.",            "color":(160,120, 60), "type":"passive"},
    "gargoyle_heart":{"label":"Serce Gargulca",       "desc":"+2 pancerz, ale -5% predkosci ruchu.",                     "color":(120, 80, 80), "type":"passive"},
    "phoenix_feather":{"label":"Pioro Feniksa",       "desc":"Jednorazowe wskrzeszenie z 20% zdrowia.",                  "color":(255,120, 20), "type":"passive"},
    "moon_amulet":   {"label":"Ksiezycowy Amulet",    "desc":"+10% szansa na trafienie krytyczne podczas ruchu.",         "color":(160,120,255), "type":"passive"},
    "unstable_essence":{"label":"Niestabilna Esencja","desc":"5% szansa na eksplozje przy podniesieniu EXP.",            "color":(255, 80,200), "type":"passive"},
    "leather_pouch": {"label":"Skorzany Mieszek",     "desc":"Zbierasz 20% wiecej EXP z kazdego gemu.",                  "color":(180,140, 80), "type":"passive"},
    "prophets_eye":  {"label":"Oko Proroka",          "desc":"Pokazuje na minimapie lokalizacje skrzyn i przedmiotow.",   "color":(255,200,  0), "type":"passive"},
    "heavy_boots":   {"label":"Ciezkie Buty",         "desc":"Zmniejsza odrzut gracza i zwieksza Twoj knockback o 10%.", "color":(100,100,120), "type":"passive"},
    "flow_rune":     {"label":"Runa Przeplywu",       "desc":"Skraca cooldown wszystkich broni o 8%.",                   "color":( 80,255,200), "type":"passive"},
    # ── 4 MIECZE ──
    "miecz_krwi":    {"label":"Miecz Krwi",
                      "desc":"7 DMG. Przywraca 3 HP przy kazdym trafieniu wroga.",
                      "color":(220, 20, 20), "type":"equipment_sword"},
    "miecz_blysk":   {"label":"Miecz Blyskawic",
                      "desc":"3 DMG (zwykly atak). Przy trafieniu zadaje 1 DMG wszystkim wrogom w promieniu 200px.",
                      "color":(80, 180, 255), "type":"equipment_sword"},
    "miecz_smierci": {"label":"Miecz Smierci",
                      "desc":"5 DMG. Kazdy atak ma 2.5% szansy na natychmiastowe zabicie wroga.",
                      "color":(80, 80, 80), "type":"equipment_sword"},
    "miecz_krola":   {"label":"Miecz Krola",
                      "desc":"999 DMG! Jesli nie zabijesz wroga przez 3.5s — umierasz. Wypada po pierwszym bossie.",
                      "color":(255, 200, 0), "type":"equipment_sword"},
}

# Only regular items drop from mobs/chests — swords are special drops
ALL_DROP_ITEMS = [k for k,v in ITEM_DEFS.items() if v["type"] in ("passive","active")]

# ──────────────────────────────────────────────────────────────
#  CHEST  (1.5% drop from mobs, contains random item)
# ──────────────────────────────────────────────────────────────
class Chest:
    def __init__(self, pos):
        self.pos    = pygame.Vector2(pos)
        self.radius = 16
        self.anim   = random.uniform(0, math.pi*2)
        self.opened = False

    def update(self):
        self.anim += 0.06

    def draw(self, cam_x, cam_y):
        bob = int(math.sin(self.anim)*3)
        px  = int(self.pos.x - cam_x)
        py  = int(self.pos.y - cam_y) + bob
        gs = pygame.Surface((self.radius*5, self.radius*5), pygame.SRCALPHA)
        pygame.draw.circle(gs, (255,200,50,40), (self.radius*2, self.radius*2), self.radius*2)
        screen.blit(gs, (px-self.radius*2, py-self.radius*2))
        r = self.radius
        pygame.draw.rect(screen, (120, 80, 30), (px-r, py-r, r*2, r*2), border_radius=4)
        pygame.draw.rect(screen, (200,150, 60), (px-r, py-r, r*2, r//2), border_radius=3)
        pygame.draw.circle(screen, (255,200,50), (px, py), 5)
        pygame.draw.circle(screen, (150,100,20), (px, py), 5, 1)
        pygame.draw.rect(screen, (220,170,70), (px-r, py-r, r*2, r*2), 2, border_radius=4)
        lbl = small_font.render("SKRZYNKA", True, (255,200,60))
        screen.blit(lbl, (px-lbl.get_width()//2, py-r-14))

# ──────────────────────────────────────────────────────────────
#  CHEST OPENING ANIMATION  (slot-machine spin)
# ──────────────────────────────────────────────────────────────
def show_chest_open_screen(final_item_id):
    all_ids = ALL_DROP_ITEMS
    spin_frames  = 90
    frame        = 0
    spin_idx     = 0
    current_show = random.choice(all_ids)

    card_w, card_h = 480, 380
    card_x = WIDTH//2 - card_w//2
    card_y = HEIGHT//2 - card_h//2
    icon_size = 120
    icon_y    = card_y + 50

    revealed   = False
    reveal_anim= 0.0

    while True:
        reveal_anim += 0.05

        if frame < spin_frames:
            frame += 1
            progress  = frame / spin_frames
            speed_mul = max(1, int((1-progress)*8) + 1)
            if frame % speed_mul == 0:
                spin_idx    = (spin_idx + 1) % len(all_ids)
                current_show = all_ids[spin_idx]
        else:
            current_show = final_item_id
            revealed     = True

        info  = ITEM_DEFS[current_show]
        color = info["color"]
        label = info["label"]

        dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.rect(dim, (0,0,0,200), dim.get_rect())
        screen.blit(dim, (0,0))

        if not revealed:
            title_col = (255, int(200*(frame/spin_frames)), 0)
            title_txt = bold_font.render("OTWIERASZ SKRZYNKE...", True, title_col)
        else:
            title_txt = bold_font.render("ZNALAZLES PRZEDMIOT!", True, (255,220,60))
        screen.blit(title_txt, (WIDTH//2-title_txt.get_width()//2, card_y-44))

        sh = pygame.Surface((card_w+20, card_h+20), pygame.SRCALPHA)
        pygame.draw.rect(sh, (0,0,0,120), sh.get_rect(), border_radius=20)
        screen.blit(sh, (card_x-10, card_y+8))

        card = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
        bg_alpha = 200 if revealed else 160
        pygame.draw.rect(card, (15,15,30,bg_alpha), (0,0,card_w,card_h), border_radius=16)
        stripe = pygame.Surface((card_w,8), pygame.SRCALPHA)
        pygame.draw.rect(stripe, (*color,200), (0,0,card_w,8), border_radius=4)
        card.blit(stripe, (0,0))
        border_alpha = 220 if revealed else 100
        pygame.draw.rect(card, (*color,border_alpha), (0,0,card_w,card_h), 2, border_radius=16)
        screen.blit(card, (card_x, card_y))

        if not revealed:
            progress = frame / spin_frames
            bar_w    = int(card_w * progress)
            bar_surf = pygame.Surface((bar_w, 4), pygame.SRCALPHA)
            pygame.draw.rect(bar_surf, (*color,180), (0,0,bar_w,4), border_radius=2)
            screen.blit(bar_surf, (card_x, card_y + card_h - 20))

        scale_p = 1.0 + math.sin(reveal_anim)*0.02 if revealed else 0.9 + math.sin(reveal_anim*6)*0.05
        icon_surf = pygame.Surface((icon_size, icon_size), pygame.SRCALPHA)
        ia = 160 if revealed else int(80 + math.sin(reveal_anim*6)*40)
        pygame.draw.rect(icon_surf, (*color,30), (0,0,icon_size,icon_size), border_radius=12)
        pygame.draw.rect(icon_surf, (*color,ia), (0,0,icon_size,icon_size), 2, border_radius=12)
        ph = small_font.render("[ IKONKA ]", True, (*color,ia))
        icon_surf.blit(ph, (icon_size//2-ph.get_width()//2, icon_size//2-ph.get_height()//2))
        ss   = int(icon_size*scale_p)
        iscl = pygame.transform.scale(icon_surf, (ss,ss))
        screen.blit(iscl, (card_x+card_w//2-ss//2, icon_y))

        name_alpha = 255 if revealed else int(150+math.sin(reveal_anim*6)*80)
        name_col   = color if revealed else tuple(min(255,c+50) for c in color)
        name_surf  = bold_font.render(label.upper(), True, name_col)
        name_y     = icon_y + icon_size + 18
        ns         = pygame.Surface(name_surf.get_size(), pygame.SRCALPHA)
        ns.blit(name_surf,(0,0)); ns.set_alpha(name_alpha)
        screen.blit(ns, (card_x+card_w//2-name_surf.get_width()//2, name_y))

        if revealed:
            div_y = name_y + name_surf.get_height() + 10
            pygame.draw.line(screen, (*color,80),
                             (card_x+30, div_y), (card_x+card_w-30, div_y), 1)
            desc  = info["desc"]
            words = desc.split(); lines=[]; cur=""
            for word in words:
                test=(cur+" "+word).strip()
                if font.size(test)[0] <= card_w-60: cur=test
                else:
                    if cur: lines.append(cur)
                    cur=word
            if cur: lines.append(cur)
            for li,line in enumerate(lines):
                ls=font.render(line,True,(200,200,220))
                screen.blit(ls,(card_x+card_w//2-ls.get_width()//2, div_y+12+li*24))

            hint=font.render("[ SPACJA / ENTER ]  kontynuuj",True,(100,100,140))
            screen.blit(hint,(card_x+card_w//2-hint.get_width()//2, card_y+card_h-36))
        else:
            hint=font.render("Losowanie...",True,(80,80,100))
            screen.blit(hint,(card_x+card_w//2-hint.get_width()//2, card_y+card_h-36))

        pygame.display.flip()
        clock.tick(60)
        for ev in pygame.event.get():
            if ev.type==pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type==pygame.KEYDOWN and ev.key in (pygame.K_SPACE,pygame.K_RETURN):
                if revealed: return

# ──────────────────────────────────────────────────────────────
#  ITEM PICKUP SCREEN  (direct item drop)
# ──────────────────────────────────────────────────────────────
def show_item_pickup_screen(item_id):
    info  = ITEM_DEFS[item_id]
    color = info["color"]
    card_w,card_h=420,340
    card_x=WIDTH//2-card_w//2; card_y=HEIGHT//2-card_h//2
    icon_size=120; icon_y=card_y+40; anim=0.0
    while True:
        anim+=0.05; sp=1.0+math.sin(anim)*0.015
        dim=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
        pygame.draw.rect(dim,(0,0,0,180),dim.get_rect()); screen.blit(dim,(0,0))
        sh=pygame.Surface((card_w+20,card_h+20),pygame.SRCALPHA)
        pygame.draw.rect(sh,(0,0,0,120),sh.get_rect(),border_radius=20)
        screen.blit(sh,(card_x-10,card_y+8))
        card=pygame.Surface((card_w,card_h),pygame.SRCALPHA)
        pygame.draw.rect(card,(15,15,30,240),(0,0,card_w,card_h),border_radius=16)
        st=pygame.Surface((card_w,8),pygame.SRCALPHA)
        pygame.draw.rect(st,(*color,200),(0,0,card_w,8),border_radius=4); card.blit(st,(0,0))
        pygame.draw.rect(card,(*color,180),(0,0,card_w,card_h),2,border_radius=16)
        screen.blit(card,(card_x,card_y))
        ic=pygame.Surface((icon_size,icon_size),pygame.SRCALPHA)
        pygame.draw.rect(ic,(*color,30),(0,0,icon_size,icon_size),border_radius=12)
        pygame.draw.rect(ic,(*color,160),(0,0,icon_size,icon_size),2,border_radius=12)
        ph=small_font.render("[ IKONKA ]",True,(*color,160))
        ic.blit(ph,(icon_size//2-ph.get_width()//2,icon_size//2-ph.get_height()//2))
        ss=int(icon_size*sp); iscl=pygame.transform.scale(ic,(ss,ss))
        screen.blit(iscl,(card_x+card_w//2-ss//2,icon_y))
        ns=bold_font.render(info["label"].upper(),True,color)
        ny=icon_y+icon_size+18
        screen.blit(ns,(card_x+card_w//2-ns.get_width()//2,ny))
        div_y=ny+ns.get_height()+10
        pygame.draw.line(screen,(*color,80),(card_x+30,div_y),(card_x+card_w-30,div_y),1)
        words=info["desc"].split(); lines=[]; cur=""
        for word in words:
            test=(cur+" "+word).strip()
            if font.size(test)[0]<=card_w-60: cur=test
            else:
                if cur: lines.append(cur)
                cur=word
        if cur: lines.append(cur)
        for li,line in enumerate(lines):
            ls=font.render(line,True,(200,200,220))
            screen.blit(ls,(card_x+card_w//2-ls.get_width()//2,div_y+12+li*24))
        hint=font.render("[ SPACJA / ENTER ]  kontynuuj",True,(100,100,140))
        screen.blit(hint,(card_x+card_w//2-hint.get_width()//2,card_y+card_h-36))
        pygame.display.flip(); clock.tick(60)
        for ev in pygame.event.get():
            if ev.type==pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type==pygame.KEYDOWN and ev.key in (pygame.K_SPACE,pygame.K_RETURN): return

item_notifications=[]
def push_item_notification(item_id): pass
def draw_item_notifications(): pass
def update_item_notifications(): pass

# ──────────────────────────────────────────────────────────────
#  DROPPED ITEM
# ──────────────────────────────────────────────────────────────
class DroppedItem:
    def __init__(self, pos, item_id):
        self.pos=pygame.Vector2(pos); self.item_id=item_id
        self.anim=random.uniform(0,math.pi*2); self.radius=14
        self.being_picked=False; self.pickup_anim=0
    def update(self):
        self.anim+=0.07
        if self.being_picked: self.pickup_anim+=1
    @property
    def done(self): return self.being_picked and self.pickup_anim>=40
    def draw(self, cam_x, cam_y):
        bob=int(math.sin(self.anim)*4)
        px=int(self.pos.x-cam_x); py=int(self.pos.y-cam_y)+bob
        info=ITEM_DEFS[self.item_id]; color=info["color"]
        gs=pygame.Surface((self.radius*6,self.radius*6),pygame.SRCALPHA)
        pygame.draw.circle(gs,(*color,50),(self.radius*3,self.radius*3),self.radius*3)
        screen.blit(gs,(px-self.radius*3,py-self.radius*3))
        pygame.draw.circle(screen,color,(px,py),self.radius)
        pygame.draw.circle(screen,(255,255,255),(px,py),self.radius,2)
        if self.being_picked:
            t=self.pickup_anim; rise=min(t*2.5,80); fade=max(0,255-int(t*7))
            lbl=bold_font.render(f"+ {info['label']}!",True,color)
            s=pygame.Surface(lbl.get_size(),pygame.SRCALPHA)
            s.blit(lbl,(0,0)); s.set_alpha(fade)
            screen.blit(s,(px-lbl.get_width()//2,py-20-int(rise)))
        else:
            lbl=small_font.render(info["label"],True,color)
            screen.blit(lbl,(px-lbl.get_width()//2,py-self.radius-14))

# ──────────────────────────────────────────────────────────────
#  EXP GEM
# ──────────────────────────────────────────────────────────────
class ExperienceGem:
    def __init__(self, pos, value, color=GEM_COLOR):
        self.pos=pygame.Vector2(pos); self.value=value; self.color=color
        self.radius=5 if value<10 else 8; self.anim=random.uniform(0,math.pi*2)
    def draw(self, cam_x, cam_y):
        self.anim+=0.08
        px=int(self.pos.x-cam_x); py=int(self.pos.y-cam_y)+int(math.sin(self.anim)*2)
        r=self.radius
        gs=pygame.Surface((r*6,r*6),pygame.SRCALPHA)
        pygame.draw.circle(gs,(*self.color,40),(r*3,r*3),r*3)
        screen.blit(gs,(px-r*3,py-r*3))
        pts=[(px,py-r),(px+r,py),(px,py+r),(px-r,py)]
        pygame.draw.polygon(screen,self.color,pts)
        pygame.draw.polygon(screen,tuple(min(255,c+80) for c in self.color),[(px,py-r),(px+r,py),(px,py)])
        pygame.draw.polygon(screen,(255,255,255),pts,1)

# ──────────────────────────────────────────────────────────────
#  ACTIVE ITEM STATES
# ──────────────────────────────────────────────────────────────
class ShadowOrb:
    def __init__(self, player, index, total):
        self.player=player; self.index=index; self.total=total
        self.angle=2*math.pi*index/total; self.orbit_r=60
        self.dot_timer=0; self.target=None
        self.pos=pygame.Vector2(
            player.pos.x+math.cos(self.angle)*self.orbit_r,
            player.pos.y+math.sin(self.angle)*self.orbit_r)
    def update(self, dt, enemies):
        self.angle+=0.04
        self.pos=pygame.Vector2(
            self.player.pos.x+math.cos(self.angle)*self.orbit_r,
            self.player.pos.y+math.sin(self.angle)*self.orbit_r)
        self.dot_timer+=dt
        if self.dot_timer>400 and enemies:
            near=min(enemies,key=lambda e:self.pos.distance_to(e.pos))
            if self.pos.distance_to(near.pos)<80:
                near.hp-=self.player.damage*0.5
                spawn_particles(near.pos,(80,20,120),count=3)
            self.dot_timer=0
    def draw(self, cam_x, cam_y):
        px=int(self.pos.x-cam_x); py=int(self.pos.y-cam_y)
        s=pygame.Surface((20,20),pygame.SRCALPHA)
        pygame.draw.circle(s,(120,40,200,180),(10,10),8)
        pygame.draw.circle(s,(200,100,255,200),(10,10),8,2)
        screen.blit(s,(px-10,py-10))

class BookOrb:
    def __init__(self, player, index, total):
        self.player=player; self.index=index; self.total=total
        self.angle=2*math.pi*index/total; self.orbit_r=75
        self.alive=True
        self.pos=pygame.Vector2(
            player.pos.x+math.cos(self.angle)*self.orbit_r,
            player.pos.y+math.sin(self.angle)*self.orbit_r)
    def update(self, enemies, gems, dropped_items):
        self.angle+=0.035
        self.pos=pygame.Vector2(
            self.player.pos.x+math.cos(self.angle)*self.orbit_r,
            self.player.pos.y+math.sin(self.angle)*self.orbit_r)
        if not self.alive: return
        for e in enemies[:]:
            if self.pos.distance_to(e.pos)<e.radius+12:
                spawn_particles(self.pos,(255,200,50),count=16,speed_range=(2,7))
                e.hp-=self.player.damage*3
                self.alive=False
                return
    def draw(self, cam_x, cam_y):
        if not self.alive: return
        px=int(self.pos.x-cam_x); py=int(self.pos.y-cam_y)
        s=pygame.Surface((22,28),pygame.SRCALPHA)
        pygame.draw.rect(s,(200,160,40,220),(2,2,18,24),border_radius=3)
        pygame.draw.rect(s,(255,220,80,220),(2,2,18,24),1,border_radius=3)
        screen.blit(s,(px-11,py-14))

class GasCloud:
    def __init__(self, pos, damage):
        self.pos=pygame.Vector2(pos); self.radius=55; self.damage=damage
        self.life=180; self.anim=0.0
    @property
    def alive(self): return self.life>0
    def update(self): self.life-=1; self.anim+=0.1
    def draw(self, cam_x, cam_y):
        ratio=self.life/180; alpha=int(60*ratio+20)
        px=int(self.pos.x-cam_x); py=int(self.pos.y-cam_y)
        r=self.radius+int(math.sin(self.anim)*5)
        s=pygame.Surface((r*2,r*2),pygame.SRCALPHA)
        pygame.draw.circle(s,(40,200,40,alpha),(r,r),r)
        pygame.draw.circle(s,(80,255,80,min(255,alpha+40)),(r,r),r,3)
        screen.blit(s,(px-r,py-r))
    def touches(self, pos, rad): return self.pos.distance_to(pos)<self.radius+rad

class IceSpike:
    def __init__(self, start, direction, damage):
        self.pos=pygame.Vector2(start)
        self.dir=pygame.Vector2(direction).normalize()
        self.speed=10; self.radius=6; self.damage=damage
        self.alive=True; self.color=(140,220,255)
    def update(self):
        self.pos+=self.dir*self.speed
    def draw(self, cam_x, cam_y):
        px=int(self.pos.x-cam_x); py=int(self.pos.y-cam_y)
        gs=pygame.Surface((24,24),pygame.SRCALPHA)
        pygame.draw.circle(gs,(140,220,255,100),(12,12),12)
        screen.blit(gs,(px-12,py-12))
        pygame.draw.circle(screen,self.color,(px,py),self.radius)

# ──────────────────────────────────────────────────────────────
#  PLAYER
# ──────────────────────────────────────────────────────────────
class Player:
    def __init__(self):
        self.pos               = pygame.Vector2(MAP_WIDTH//2, MAP_HEIGHT//2)
        self.hp                = 100
        self.max_hp            = 100
        self.speed             = 4.0
        self.base_speed        = 4.0
        self.radius            = 15
        self.pickup_range      = 40
        self.attack_cooldown   = 0
        self.base_cooldown     = 450
        self.damage            = 1
        self.level             = 1
        self.exp               = 0
        self.exp_to_next_level = 10
        self.weapon            = "Magic Ball"
        self.sword_range       = 90
        self.sword_timer       = 0
        self.color             = (0,140,50)
        self.trail             = []
        self.anim              = 0
        self.items             = {}
        self.moving            = False
        self.armor             = 0
        self.phoenix_used      = False
        self.attack_count      = 0
        # active item timers
        self.chalice_timer     = 0
        self.mirror_active     = True
        self.bell_timer        = 0
        self.frost_timer       = 0
        self.holy_whip_timer   = 0
        self.anvil_timer       = 0
        # world objects
        self.shadow_orbs       = []
        self.book_orbs         = []
        self.gas_clouds        = []
        self.ice_spikes        = []
        self.frozen_enemies    = {}
        # ── EQUIPMENT: sword slot ──
        self.equipped_sword    = None   # key of equipped sword or None
        self.king_sword_timer  = 0      # ms; counts down; 0 → death
        # ── ULT SYSTEM ──
        self.ult_exp           = 0      # current ult charge (EXP)
        self.ult_exp_needed    = 0      # set after character select (3x first lvl threshold)
        self.ult_ready         = False
        self.ult_active        = False
        self.ult_timer         = 0      # frames remaining for active ult effect
        self.ult_class         = None   # "Warrior","Rogue","Knight","Brawler"
        # Visual flash for ult activation
        self.ult_flash         = 0
        # Divine Smite: track lightning bolts drawn
        self.smite_bolts       = []     # list of (start, end, life) for visual

    def has(self, item_id): return self.items.get(item_id,0)>0

    def equip_sword(self, sword_id):
        self.equipped_sword = sword_id
        if sword_id == "miecz_krola":
            self.king_sword_timer = 3500

    def effective_damage(self):
        """Return damage considering equipped sword and ult."""
        sw = self.equipped_sword
        if sw == "miecz_krwi":    base = 7
        elif sw == "miecz_blysk":   base = 3
        elif sw == "miecz_smierci": base = 5
        elif sw == "miecz_krola":   base = 999
        else: base = self.damage
        return base * self.ult_damage_mult

    def add_item(self, item_id):
        if ITEM_DEFS[item_id]["type"] == "equipment_sword":
            self.equip_sword(item_id)
            return
        self.items[item_id] = self.items.get(item_id,0)+1
        cnt = self.items[item_id]
        if item_id=="magnet":          self.pickup_range+=60
        elif item_id=="rusty_magnet":  self.pickup_range+=25
        elif item_id=="speed_boots":   self.speed+=1.5
        elif item_id=="gargoyle_heart":
            self.armor+=2; self.speed=max(1.0, self.speed*0.95)
        elif item_id=="flow_rune":     self.base_cooldown=int(self.base_cooldown*0.92)
        elif item_id=="shadows":
            total=cnt; self.shadow_orbs=[]
            for i in range(total): self.shadow_orbs.append(ShadowOrb(self,i,total))
        elif item_id=="books":
            total=cnt*3; self.book_orbs=[]
            for i in range(total): self.book_orbs.append(BookOrb(self,i,total))

    @property
    def trident_count(self):       return self.items.get("trident",0)
    @property
    def life_steal(self):           return 0.05*self.items.get("vampire_tooth",0)
    @property
    def effect_duration_mult(self): return 1.0+0.15*self.items.get("hourglass",0)
    @property
    def crit_chance(self):
        base=0.1*self.items.get("moon_amulet",0)
        return base if self.moving else 0.0
    @property
    def knockback_mult(self):       return 1.0+0.1*self.items.get("heavy_boots",0)
    @property
    def exp_mult(self):             return 1.0+0.2*self.items.get("leather_pouch",0)

    def heal(self, amount): self.hp=min(self.max_hp, self.hp+amount)

    def take_damage(self, dmg):
        if self.ult_invincible:
            return 0
        actual=max(0, dmg-self.armor*0.5)
        self.hp-=actual
        if self.hp<=0 and self.has("phoenix_feather") and not self.phoenix_used:
            self.phoenix_used=True
            self.hp=int(self.max_hp*0.2)
            spawn_particles(self.pos,(255,120,20),count=30,speed_range=(3,9))
        return actual

    def move(self, keys):
        vel=pygame.Vector2(0,0)
        if keys[pygame.K_w]: vel.y=-1
        if keys[pygame.K_s]: vel.y= 1
        if keys[pygame.K_a]: vel.x=-1
        if keys[pygame.K_d]: vel.x= 1
        self.moving=(vel.length()>0)
        if self.moving:
            self.trail.append(pygame.Vector2(self.pos))
            if len(self.trail)>8: self.trail.pop(0)
            self.pos+=vel.normalize()*self.speed*self.ult_speed_mult
        self.pos.x=max(self.radius,min(MAP_WIDTH -self.radius,self.pos.x))
        self.pos.y=max(self.radius,min(MAP_HEIGHT-self.radius,self.pos.y))
        self.anim+=0.12

    def check_level_up(self):
        if self.exp>=self.exp_to_next_level:
            self.exp-=self.exp_to_next_level
            self.level+=1
            self.exp_to_next_level=int(self.level*12)
            self.hp=min(self.max_hp,self.hp+15)
            return True
        return False

    def update_king_sword(self, dt):
        if self.equipped_sword == "miecz_krola":
            self.king_sword_timer -= dt
            if self.king_sword_timer <= 0:
                self.hp = 0

    def charge_ult(self, exp_amount):
        """Call whenever player gains EXP. Returns True if ult just became ready."""
        if self.ult_ready or self.ult_active:
            return False
        self.ult_exp += exp_amount
        if self.ult_exp >= self.ult_exp_needed:
            self.ult_exp = self.ult_exp_needed
            self.ult_ready = True
            return True
        return False

    def activate_ult(self, enemies, enemy_bullets, hazard_zones):
        """Called on Q press. Returns True if ult was activated."""
        if not self.ult_ready or self.ult_active:
            return False
        self.ult_ready = False
        self.ult_active = True
        self.ult_exp = 0
        self.ult_flash = 40

        if self.ult_class == "Warrior":
            # Berserker Rage: 5s (300 frames) 3x DMG + invincibility
            self.ult_timer = 300
            spawn_particles(self.pos, (255, 80, 0), count=30, speed_range=(3, 9))

        elif self.ult_class == "Rogue":
            # Backstab Frenzy: 4s (240 frames) instant kill on attack
            self.ult_timer = 240
            spawn_particles(self.pos, (200, 0, 200), count=30, speed_range=(3, 9))

        elif self.ult_class == "Knight":
            # Divine Smite: instant — lightning hits ALL enemies on screen
            self.ult_timer = 60  # just visual cooldown
            self.smite_bolts = []
            for e in enemies:
                # Visual bolt
                self.smite_bolts.append([
                    pygame.Vector2(e.pos.x + random.uniform(-30, 30), e.pos.y - 400),
                    pygame.Vector2(e.pos),
                    30  # life frames
                ])
                e.hp -= self.effective_damage() * 10
                spawn_particles(e.pos, (255, 255, 100), count=16, speed_range=(2, 8))
            spawn_particles(self.pos, (255, 240, 80), count=40, speed_range=(2, 10))

        elif self.ult_class == "Brawler":
            # Rage Mode: 4s (240 frames) 3x speed + 3x DMG
            self.ult_timer = 240
            spawn_particles(self.pos, (255, 200, 0), count=30, speed_range=(3, 9))

        return True

    def update_ult(self, dt):
        """Call every frame in game loop."""
        if self.ult_active:
            self.ult_timer -= 1
            if self.ult_timer <= 0:
                self.ult_active = False
                self.smite_bolts = []
        # Decay smite bolts
        for bolt in self.smite_bolts[:]:
            bolt[2] -= 1
            if bolt[2] <= 0:
                self.smite_bolts.remove(bolt)
        if self.ult_flash > 0:
            self.ult_flash -= 1

    @property
    def ult_damage_mult(self):
        if not self.ult_active:
            return 1.0
        if self.ult_class in ("Warrior", "Brawler"):
            return 3.0
        return 1.0

    @property
    def ult_speed_mult(self):
        if self.ult_active and self.ult_class == "Brawler":
            return 3.0
        return 1.0

    @property
    def ult_invincible(self):
        return self.ult_active and self.ult_class == "Warrior"

    @property
    def ult_instant_kill(self):
        return self.ult_active and self.ult_class == "Rogue"

    def reset_king_timer(self):
        if self.equipped_sword == "miecz_krola":
            self.king_sword_timer = 3500

    def update_active_items(self, dt, enemies, gems, dropped_items, hazard_zones):
        eff = self.effect_duration_mult

        if self.has("chalice"):
            self.chalice_timer+=dt
            cd=int(3000/self.items.get("chalice",1))
            if self.chalice_timer>=cd:
                self.chalice_timer=0
                rng=90
                for e in enemies[:]:
                    if self.pos.distance_to(e.pos)<rng+e.radius:
                        e.hp-=self.damage*1.5
                        if random.random()<0.2: self.heal(1)
                        spawn_particles(e.pos,(180,0,60),count=5)
                hazard_zones.append(HazardZone(self.pos,radius=rng,color=(180,0,60),harms_player=False))

        if self.has("bell"):
            self.bell_timer+=dt
            if self.bell_timer>=5000:
                self.bell_timer=0
                stun_dur=int(90*eff)
                for e in enemies:
                    if self.pos.distance_to(e.pos)<250:
                        self.frozen_enemies[id(e)]=(e,stun_dur)
                        spawn_particles(e.pos,(200,180,80),count=8)

        if self.has("frost_staff"):
            self.frost_timer+=dt
            if self.frost_timer>=800:
                self.frost_timer=0
                for _ in range(3):
                    ang=random.uniform(0,2*math.pi)
                    self.ice_spikes.append(IceSpike(self.pos,(math.cos(ang),math.sin(ang)),self.damage))

        if self.has("holy_whip"):
            self.holy_whip_timer+=dt
            if self.holy_whip_timer>=2500:
                self.holy_whip_timer=0
                for e in enemies[:]:
                    d=e.pos-self.pos
                    if abs(d.x)<40 and d.length()<200:
                        push=(e.pos-self.pos).normalize()
                        e.pos+=push*150*self.knockback_mult
                        e.hp-=self.damage*2
                        spawn_particles(e.pos,(255,240,100),count=10)

        if self.has("anvil"):
            self.anvil_timer+=dt
            if self.anvil_timer>=8000 and enemies:
                self.anvil_timer=0
                target=max(enemies,key=lambda e:e.hp)
                spawn_particles(target.pos,(180,180,200),count=20,speed_range=(3,8))
                for e in enemies[:]:
                    if e.pos.distance_to(target.pos)<80:
                        e.hp-=self.damage*8

        freeze_dur=int(120*eff)
        for sp in self.ice_spikes[:]:
            sp.update()
            if sp.pos.distance_to(self.pos)>800:
                self.ice_spikes.remove(sp); continue
            for e in enemies[:]:
                if sp.pos.distance_to(e.pos)<e.radius+sp.radius:
                    e.hp-=sp.damage
                    self.frozen_enemies[id(e)]=(e,freeze_dur)
                    spawn_particles(e.pos,(140,220,255),count=6)
                    if sp in self.ice_spikes: self.ice_spikes.remove(sp)
                    break

        for eid in list(self.frozen_enemies.keys()):
            e,frames=self.frozen_enemies[eid]
            if frames<=0 or e not in enemies:
                del self.frozen_enemies[eid]
            else:
                self.frozen_enemies[eid]=(e,frames-1)

        for orb in self.shadow_orbs:
            orb.update(dt, enemies)

        for orb in self.book_orbs[:]:
            orb.update(enemies, gems, dropped_items)
            if not orb.alive:
                self.book_orbs.remove(orb)

        for gc in self.gas_clouds[:]:
            gc.update()
            if not gc.alive: self.gas_clouds.remove(gc); continue
            for e in enemies:
                if gc.touches(e.pos,e.radius):
                    e.hp-=self.damage*0.03

    def draw(self, cam_x, cam_y):
        global levelup_flash
        px=int(self.pos.x-cam_x); py=int(self.pos.y-cam_y)

        for i,t in enumerate(self.trail):
            alpha=int(60*(i/len(self.trail)))
            ts=pygame.Surface((self.radius*2,self.radius*2),pygame.SRCALPHA)
            pygame.draw.circle(ts,(*self.color,alpha),(self.radius,self.radius),self.radius-2)
            screen.blit(ts,(int(t.x-cam_x)-self.radius,int(t.y-cam_y)-self.radius))

        if self.weapon=="Lightsaber" and self.sword_timer>0:
            rng=int(self.sword_range*1.5)
            s=pygame.Surface((rng*2,rng*2),pygame.SRCALPHA)
            pygame.draw.circle(s,(0,255,100,80),(rng,rng),rng)
            pygame.draw.circle(s,(100,255,150,180),(rng,rng),rng,2)
            screen.blit(s,(px-rng,py-rng)); self.sword_timer-=1
        elif self.weapon=="Sword" and self.sword_timer>0:
            rng=self.sword_range
            s=pygame.Surface((rng*2,rng*2),pygame.SRCALPHA)
            pygame.draw.circle(s,(0,180,255,70),(rng,rng),rng)
            pygame.draw.circle(s,(100,200,255,200),(rng,rng),rng,2)
            screen.blit(s,(px-rng,py-rng)); self.sword_timer-=1
        elif self.weapon=="Axe" and self.sword_timer>0:
            s=pygame.Surface((300,300),pygame.SRCALPHA)
            pygame.draw.circle(s,(255,120,20,90),(150,150),120)
            pygame.draw.circle(s,(255,150,50,200),(150,150),120,2)
            screen.blit(s,(px-150,py-150)); self.sword_timer-=1
        elif self.weapon=="Fist" and self.sword_timer>0:
            s=pygame.Surface((160,160),pygame.SRCALPHA)
            pygame.draw.circle(s,(255,220,0,120),(80,80),80)
            pygame.draw.circle(s,(255,240,80,220),(80,80),80,2)
            screen.blit(s,(px-80,py-80)); self.sword_timer-=1

        if self.has("mirror"):
            br=self.radius+20
            bs=pygame.Surface((br*2,br*2),pygame.SRCALPHA)
            pygame.draw.circle(bs,(200,220,255,30),(br,br),br)
            pygame.draw.circle(bs,(200,220,255,120),(br,br),br,2)
            screen.blit(bs,(px-br,py-br))

        gr=self.radius+8
        gs=pygame.Surface((gr*2,gr*2),pygame.SRCALPHA)
        pygame.draw.circle(gs,(*self.color,60),(gr,gr),gr)
        screen.blit(gs,(px-gr,py-gr))

        if levelup_flash>0:
            fr=self.radius+levelup_flash*3
            fs=pygame.Surface((int(fr*2),int(fr*2)),pygame.SRCALPHA)
            pygame.draw.circle(fs,(255,255,100,int(levelup_flash*8)),(int(fr),int(fr)),int(fr))
            screen.blit(fs,(px-int(fr),py-int(fr)))
            levelup_flash-=1

        pygame.draw.circle(screen,self.color,(px,py),self.radius)
        pygame.draw.circle(screen,tuple(min(255,c+60) for c in self.color),(px,py),self.radius,2)
        ey=py-12+int(math.sin(self.anim))
        pygame.draw.circle(screen,(200,240,200),(px,ey),9)
        pygame.draw.circle(screen,(0,0,0),(px-3,ey-1),3)
        pygame.draw.circle(screen,(0,0,0),(px+3,ey-1),3)
        pygame.draw.circle(screen,(255,255,255),(px-2,ey-2),1)
        pygame.draw.circle(screen,(255,255,255),(px+4,ey-2),1)

        for orb in self.shadow_orbs: orb.draw(cam_x,cam_y)
        for orb in self.book_orbs:   orb.draw(cam_x,cam_y)
        for sp in self.ice_spikes:   sp.draw(cam_x,cam_y)
        for gc in self.gas_clouds:   gc.draw(cam_x,cam_y)

        # ── ULT VISUAL EFFECTS ──
        if self.ult_active:
            if self.ult_class == "Warrior":
                # Red fiery aura
                r = self.radius + 14 + int(math.sin(self.anim*2)*5)
                s = pygame.Surface((r*2,r*2), pygame.SRCALPHA)
                pygame.draw.circle(s, (255,80,0,80), (r,r), r)
                pygame.draw.circle(s, (255,140,0,200), (r,r), r, 3)
                screen.blit(s, (px-r, py-r))
            elif self.ult_class == "Rogue":
                # Purple assassin aura
                r = self.radius + 12 + int(math.sin(self.anim*3)*4)
                s = pygame.Surface((r*2,r*2), pygame.SRCALPHA)
                pygame.draw.circle(s, (180,0,200,70), (r,r), r)
                pygame.draw.circle(s, (220,80,255,200), (r,r), r, 3)
                screen.blit(s, (px-r, py-r))
            elif self.ult_class == "Brawler":
                # Golden speed aura + motion blur
                r = self.radius + 10 + int(math.sin(self.anim*4)*6)
                s = pygame.Surface((r*2,r*2), pygame.SRCALPHA)
                pygame.draw.circle(s, (255,200,0,80), (r,r), r)
                pygame.draw.circle(s, (255,240,80,200), (r,r), r, 3)
                screen.blit(s, (px-r, py-r))

        if self.ult_flash > 0:
            fr = self.radius + self.ult_flash * 3
            fs = pygame.Surface((int(fr*2),int(fr*2)), pygame.SRCALPHA)
            ult_cols = {"Warrior":(255,80,0), "Rogue":(220,0,255), "Knight":(255,255,100), "Brawler":(255,200,0)}
            uc = ult_cols.get(self.ult_class, (255,255,255))
            pygame.draw.circle(fs, (*uc, int(self.ult_flash*5)), (int(fr),int(fr)), int(fr))
            screen.blit(fs, (px-int(fr), py-int(fr)))

        # Draw smite lightning bolts (Knight ult)
        for bolt in self.smite_bolts:
            start, end, life = bolt
            alpha = int(255 * life / 30)
            sx, sy = int(start.x - cam_x), int(start.y - cam_y)
            ex2, ey2 = int(end.x - cam_x), int(end.y - cam_y)
            # Jagged lightning: draw 3 segments
            mid1 = pygame.Vector2((sx+ex2)//2 + random.randint(-20,20), (sy+ey2)//2 + random.randint(-20,20))
            pygame.draw.line(screen, (255,255,100), (sx,sy), (int(mid1.x),int(mid1.y)), 3)
            pygame.draw.line(screen, (255,255,100), (int(mid1.x),int(mid1.y)), (ex2,ey2), 3)
            pygame.draw.line(screen, (255,255,255), (sx,sy), (int(mid1.x),int(mid1.y)), 1)
            pygame.draw.line(screen, (255,255,255), (int(mid1.x),int(mid1.y)), (ex2,ey2), 1)

        for eid,(e,_) in self.frozen_enemies.items():
            ex=int(e.pos.x-cam_x); ey2=int(e.pos.y-cam_y)
            fs=pygame.Surface((e.radius*3,e.radius*3),pygame.SRCALPHA)
            pygame.draw.circle(fs,(140,220,255,80),(e.radius,e.radius),e.radius+4)
            screen.blit(fs,(ex-e.radius,ey2-e.radius))

# ──────────────────────────────────────────────────────────────
#  BOSS
# ──────────────────────────────────────────────────────────────
class Boss:
    PHASE_IDLE="idle"; PHASE_SPIN="spin"; PHASE_DASH="dash"; PHASE_TELEPORT="teleport"
    SPIN_COOLDOWN=4000; DASH_COOLDOWN=6000; TELEPORT_COOLDOWN=8000

    def __init__(self, player_level, player_pos):
        angle=random.uniform(0,2*math.pi); dist=max(WIDTH,HEIGHT)/2+100
        self.pos=pygame.Vector2(player_pos.x+math.cos(angle)*dist,
                                player_pos.y+math.sin(angle)*dist)
        self.is_boss=True; self.max_hp=200+player_level*20; self.hp=self.max_hp
        self.radius=40; self.speed=1.4; self.color=BOSS_COLOR; self.anim=0.0
        self.spin_timer=self.SPIN_COOLDOWN
        self.dash_timer=self.DASH_COOLDOWN
        self.teleport_timer=self.TELEPORT_COOLDOWN
        self.phase=self.PHASE_IDLE; self.phase_timer=0
        self.dash_dir=pygame.Vector2(1,0); self.dash_speed=18; self.blink_flash=0

    def update(self, dt, player_pos, enemy_bullets, hazard_zones):
        self.anim+=0.08
        self.spin_timer-=dt; self.dash_timer-=dt; self.teleport_timer-=dt
        if self.phase==self.PHASE_IDLE:
            d=player_pos-self.pos
            if d.length()>0: self.pos+=d.normalize()*self.speed
            if self.spin_timer<=0: self._start_spin(enemy_bullets)
            elif self.teleport_timer<=0: self._start_teleport(player_pos,hazard_zones)
            elif self.dash_timer<=0: self._start_dash(player_pos)
        elif self.phase==self.PHASE_SPIN:
            self.phase_timer-=1
            if self.phase_timer<=0: self.phase=self.PHASE_IDLE; self.spin_timer=self.SPIN_COOLDOWN
        elif self.phase==self.PHASE_DASH:
            self.phase_timer-=1; self.pos+=self.dash_dir*self.dash_speed
            self.pos.x=max(self.radius,min(MAP_WIDTH-self.radius,self.pos.x))
            self.pos.y=max(self.radius,min(MAP_HEIGHT-self.radius,self.pos.y))
            if self.phase_timer<=0: self.phase=self.PHASE_IDLE; self.dash_timer=self.DASH_COOLDOWN
        elif self.phase==self.PHASE_TELEPORT:
            self.blink_flash-=1
            if self.blink_flash<=0: self.phase=self.PHASE_IDLE; self.teleport_timer=self.TELEPORT_COOLDOWN

    def _start_spin(self, eb):
        self.phase=self.PHASE_SPIN; self.phase_timer=40; self.spin_timer=99999
        for i in range(16):
            a=2*math.pi/16*i; fake=self.pos+pygame.Vector2(math.cos(a),math.sin(a))*100
            eb.append(Bullet(self.pos,fake,(255,60,0),speed=6,radius=7))
        spawn_particles(self.pos,(255,80,0),count=24,speed_range=(2,8))

    def _start_dash(self, pp):
        self.phase=self.PHASE_DASH; self.phase_timer=20; self.dash_timer=99999
        d=pp-self.pos; self.dash_dir=d.normalize() if d.length()>0 else pygame.Vector2(1,0)
        spawn_particles(self.pos,(255,160,0),count=12)

    def _start_teleport(self, pp, hz):
        hz.append(HazardZone(self.pos))
        for _ in range(20):
            np=pygame.Vector2(random.randint(200,MAP_WIDTH-200),random.randint(200,MAP_HEIGHT-200))
            if np.distance_to(pp)>300: break
        self.pos=np; self.blink_flash=30; self.phase=self.PHASE_TELEPORT
        self.teleport_timer=99999
        spawn_particles(self.pos,(200,0,255),count=20,speed_range=(3,8))

    def draw(self, cam_x, cam_y):
        px=int(self.pos.x-cam_x); py=int(self.pos.y-cam_y); bob=int(math.sin(self.anim)*3)
        if self.phase==self.PHASE_SPIN:
            rng=self.radius+60; rs=pygame.Surface((rng*2,rng*2),pygame.SRCALPHA)
            pygame.draw.circle(rs,(255,80,0,100),(rng,rng),rng)
            pygame.draw.circle(rs,(255,160,0,200),(rng,rng),rng,4)
            screen.blit(rs,(px-rng,py-rng+bob))
        if self.phase==self.PHASE_DASH:
            for i in range(4):
                tr=self.radius-i*4; al=max(0,150-i*40)
                ts=pygame.Surface((tr*2,tr*2),pygame.SRCALPHA)
                pygame.draw.circle(ts,(255,100,0,al),(tr,tr),tr)
                screen.blit(ts,(px-tr+i*10,py-tr+bob))
        if self.blink_flash>0:
            fr=self.radius+self.blink_flash*4
            fs=pygame.Surface((int(fr*2),int(fr*2)),pygame.SRCALPHA)
            pygame.draw.circle(fs,(180,0,255,int(self.blink_flash*6)),(int(fr),int(fr)),int(fr))
            screen.blit(fs,(px-int(fr),py-int(fr)))
        for rr,al in [(self.radius+18,40),(self.radius+10,80)]:
            rs=pygame.Surface((rr*2,rr*2),pygame.SRCALPHA)
            pygame.draw.circle(rs,(255,40,40,al),(rr,rr),rr,3)
            screen.blit(rs,(px-rr,py-rr+bob))
        pygame.draw.circle(screen,(30,30,30),(px,py+bob),self.radius)
        pygame.draw.circle(screen,(200,0,0),(px,py+bob),self.radius,3)
        for ex in [-10,10]:
            pygame.draw.circle(screen,(220,0,0),(px+ex,py+bob-8),6)
            pygame.draw.circle(screen,(255,80,80),(px+ex,py+bob-8),3)
        bw=self.radius*2+20; hpr=max(0,self.hp/self.max_hp)
        pygame.draw.rect(screen,(80,0,0),(px-bw//2,py-self.radius-14,bw,6),border_radius=3)
        pygame.draw.rect(screen,(255,60,0),(px-bw//2,py-self.radius-14,int(hpr*bw),6),border_radius=3)
        lbs={self.PHASE_SPIN:("SPIN!",(255,160,0)),self.PHASE_DASH:("DASH!",(255,80,0)),
             self.PHASE_TELEPORT:("TELEPORT!",(180,0,255))}
        if self.phase in lbs:
            t,c=lbs[self.phase]; l=bold_font.render(t,True,c)
            screen.blit(l,(px-l.get_width()//2,py-self.radius-34))

# ──────────────────────────────────────────────────────────────
#  REGULAR ENEMY
# ──────────────────────────────────────────────────────────────
class Enemy:
    def __init__(self, player_level, player_pos):
        angle=random.uniform(0,2*math.pi); dist=max(WIDTH,HEIGHT)/2+100
        self.pos=pygame.Vector2(player_pos.x+math.cos(angle)*dist,
                                player_pos.y+math.sin(angle)*dist)
        self.is_boss=False; tier=player_level//5
        self.hp=1+tier*3; self.radius=12
        self.speed=random.uniform(1.6,2.4)+tier*0.4
        self.color=(220,40,40) if tier==0 else (200,20,120) if tier==1 else (160,0,200)
        self.anim=random.uniform(0,math.pi*2)

    def update(self, player_pos, frozen=False):
        self.anim+=0.1
        if frozen: return
        d=player_pos-self.pos
        if d.length()>0: self.pos+=d.normalize()*self.speed

    def draw(self, cam_x, cam_y):
        px=int(self.pos.x-cam_x); py=int(self.pos.y-cam_y); bob=int(math.sin(self.anim)*2)
        gs=pygame.Surface((self.radius*4,self.radius*4),pygame.SRCALPHA)
        pygame.draw.circle(gs,(*self.color,40),(self.radius*2,self.radius*2),self.radius*2)
        screen.blit(gs,(px-self.radius*2,py-self.radius*2+bob))
        pygame.draw.circle(screen,self.color,(px,py+bob),self.radius)
        pygame.draw.circle(screen,tuple(min(255,c+60) for c in self.color),(px,py+bob),self.radius,2)
        for ex in [-4,4]:
            pygame.draw.circle(screen,(255,255,255),(px+ex,py+bob-4),3)
            pygame.draw.circle(screen,(0,0,0),(px+ex,py+bob-4),2)

# ──────────────────────────────────────────────────────────────
#  BULLET
# ──────────────────────────────────────────────────────────────
class Bullet:
    def __init__(self, start, target, color=BULLET_COLOR, pierce=1, speed=12, radius=5):
        self.pos=pygame.Vector2(start); self.speed=speed; self.radius=radius
        self.color=color; self.pierce=pierce
        d=target-start; self.dir=d.normalize() if d.length()>0 else pygame.Vector2(1,0)
    def update(self): self.pos+=self.dir*self.speed

def fire_trident(player, target_pos, bullets, color, speed, radius, pierce=1):
    cnt=player.trident_count
    if not cnt: return
    ba=math.atan2(target_pos.y-player.pos.y, target_pos.x-player.pos.x)
    for _ in range(cnt):
        for deg in [-30,0,30]:
            a=ba+math.radians(deg)
            fake=player.pos+pygame.Vector2(math.cos(a),math.sin(a))*100
            bullets.append(Bullet(player.pos,fake,color,pierce=pierce,speed=speed,radius=radius))

def draw_bullet(b, cam_x, cam_y):
    px=int(b.pos.x-cam_x); py=int(b.pos.y-cam_y)
    gs=pygame.Surface((b.radius*4,b.radius*4),pygame.SRCALPHA)
    pygame.draw.circle(gs,(*b.color,80),(b.radius*2,b.radius*2),b.radius*2)
    screen.blit(gs,(px-b.radius*2,py-b.radius*2))
    pygame.draw.circle(screen,b.color,(px,py),b.radius)
    pygame.draw.circle(screen,(255,255,255),(px,py),max(1,b.radius-2))

# ──────────────────────────────────────────────────────────────
#  CHAIN LIGHTNING
# ──────────────────────────────────────────────────────────────
def chain_lightning(start_pos, enemies, damage, jumps=3):
    hit=set(); pos=pygame.Vector2(start_pos)
    for _ in range(jumps):
        candidates=[e for e in enemies if id(e) not in hit]
        if not candidates: break
        nxt=min(candidates,key=lambda e:pos.distance_to(e.pos))
        if pos.distance_to(nxt.pos)>400: break
        spawn_particles(nxt.pos,(80,200,255),count=8,speed_range=(2,6))
        nxt.hp-=damage
        hit.add(id(nxt)); pos=pygame.Vector2(nxt.pos)

# ──────────────────────────────────────────────────────────────
#  HUD
# ──────────────────────────────────────────────────────────────
def draw_hud(player):
    ps=pygame.Surface((280,155),pygame.SRCALPHA)
    pygame.draw.rect(ps,(0,0,0,150),ps.get_rect(),border_radius=12)
    pygame.draw.rect(ps,(60,60,90,200),ps.get_rect(),1,border_radius=12)
    screen.blit(ps,(14,14))
    hp_r=max(0,player.hp/player.max_hp)
    bx,by,bw,bh=24,24,250,18
    pygame.draw.rect(screen,(60,0,0),(bx,by,bw,bh),border_radius=6)
    pygame.draw.rect(screen,(int(255*(1-hp_r)),int(200*hp_r),0),(bx,by,int(hp_r*bw),bh),border_radius=6)
    pygame.draw.rect(screen,(200,200,200),(bx,by,bw,bh),1,border_radius=6)
    screen.blit(small_font.render(f"HP  {int(player.hp)} / {player.max_hp}",True,(240,240,240)),(bx+4,by+2))
    exp_r=min(1.0,player.exp/player.exp_to_next_level)
    ex,ey,ew,eh=24,50,250,10
    pygame.draw.rect(screen,(0,30,80),(ex,ey,ew,eh),border_radius=5)
    pygame.draw.rect(screen,(40,160,255),(ex,ey,int(exp_r*ew),eh),border_radius=5)
    pygame.draw.rect(screen,(80,120,200),(ex,ey,ew,eh),1,border_radius=5)
    screen.blit(font.render(f"LVL {player.level}   {player.weapon}",True,(255,255,180)),(24,66))

    # ── ULT BAR ──
    ux,uy,uw,uh=24,84,250,14
    ult_r = min(1.0, player.ult_exp / max(1, player.ult_exp_needed)) if not player.ult_ready and not player.ult_active else 1.0
    ULT_COLORS = {
        "Warrior": (255,80,0), "Rogue": (200,0,200),
        "Knight":  (255,240,80), "Brawler": (255,200,0),
    }
    ult_col = ULT_COLORS.get(player.ult_class, (200,200,200))
    pygame.draw.rect(screen,(20,10,30),(ux,uy,uw,uh),border_radius=5)
    if player.ult_active:
        # pulsujący pasek podczas aktywnego ulta
        pulse = int(abs(math.sin(pygame.time.get_ticks()*0.005))*80)
        active_col = tuple(min(255, c+pulse) for c in ult_col)
        pygame.draw.rect(screen,active_col,(ux,uy,uw,uh),border_radius=5)
        lbl = small_font.render("⚡ ULT AKTYWNY!", True, (255,255,255))
    elif player.ult_ready:
        pulse = int(abs(math.sin(pygame.time.get_ticks()*0.008))*60)
        rc = tuple(min(255,c+pulse) for c in ult_col)
        pygame.draw.rect(screen,rc,(ux,uy,uw,uh),border_radius=5)
        lbl = small_font.render("⚡ ULT GOTOWY! [Q]", True, (255,255,255))
    else:
        pygame.draw.rect(screen,ult_col,(ux,uy,int(ult_r*uw),uh),border_radius=5)
        lbl = small_font.render(f"ULT {int(ult_r*100)}%", True, ult_col)
    pygame.draw.rect(screen,ult_col,(ux,uy,uw,uh),1,border_radius=5)
    screen.blit(lbl,(ux+4,uy+1))

    if player.items:
        ix=24
        for item_id,cnt in player.items.items():
            col=ITEM_DEFS[item_id]["color"]
            pygame.draw.circle(screen,col,(ix+8,122),7)
            pygame.draw.circle(screen,(255,255,255),(ix+8,122),7,1)
            if cnt>1: screen.blit(small_font.render(str(cnt),True,(255,255,255)),(ix+16,116))
            ix+=26+(8 if cnt>1 else 0)

# ──────────────────────────────────────────────────────────────
#  EQUIPMENT HUD  (left side, under HP bar — 4 slots)
# ──────────────────────────────────────────────────────────────
def draw_equipment_hud(player):
    SLOT_SIZE = 42
    SLOT_GAP  = 6
    PANEL_X   = 14
    PANEL_Y   = 140   # poniżej paska HP/EXP/itemów

    # 4 sloty: helm, zbroja, broń, rękawice
    slots = [
        ("HELM",     None,                None),
        ("ZBROJA",   None,                None),
        ("BRON",     player.equipped_sword, "sword"),
        ("REKAWICE", None,                None),
    ]

    panel_w = len(slots) * (SLOT_SIZE + SLOT_GAP) - SLOT_GAP + 20
    panel_h = SLOT_SIZE + 46   # slot + etykieta + ewentualny pasek króla

    ps = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    pygame.draw.rect(ps, (0,0,0,150), ps.get_rect(), border_radius=10)
    pygame.draw.rect(ps, (60,60,90,200), ps.get_rect(), 1, border_radius=10)
    screen.blit(ps, (PANEL_X, PANEL_Y))

    title = small_font.render("EKWIPUNEK", True, (140,140,190))
    screen.blit(title, (PANEL_X + panel_w//2 - title.get_width()//2, PANEL_Y + 4))

    for i, (label, item_id, kind) in enumerate(slots):
        sx = PANEL_X + 10 + i * (SLOT_SIZE + SLOT_GAP)
        sy = PANEL_Y + 22

        filled  = item_id is not None
        col     = ITEM_DEFS[item_id]["color"] if filled else (40, 42, 60)
        brd     = ITEM_DEFS[item_id]["color"] if filled else (65, 68, 95)

        # Slot background
        ss = pygame.Surface((SLOT_SIZE, SLOT_SIZE), pygame.SRCALPHA)
        pygame.draw.rect(ss, (*col[:3], 40 if filled else 15),
                         (0,0,SLOT_SIZE,SLOT_SIZE), border_radius=7)
        pygame.draw.rect(ss, (*brd[:3], 200),
                         (0,0,SLOT_SIZE,SLOT_SIZE), 2, border_radius=7)
        screen.blit(ss, (sx, sy))

        cx = sx + SLOT_SIZE//2
        cy = sy + SLOT_SIZE//2

        if filled and kind == "sword":
            sw = item_id
            ic = ITEM_DEFS[sw]["color"]
            # glow
            glow = pygame.Surface((SLOT_SIZE, SLOT_SIZE), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*ic, 50), (SLOT_SIZE//2, SLOT_SIZE//2), SLOT_SIZE//2)
            screen.blit(glow, (sx, sy))
            # blade
            pygame.draw.line(screen, ic, (cx, cy-16), (cx, cy+9), 3)
            # crossguard
            pygame.draw.line(screen, (170,170,170), (cx-9, cy+5), (cx+9, cy+5), 2)
            # pommel
            pygame.draw.circle(screen, (140,100,40), (cx, cy+13), 3)
            # per-sword accent
            if sw == "miecz_krwi":
                for dy in [-10, -3, 4]:
                    pygame.draw.circle(screen, (255,20,20), (cx, cy+dy), 2)
            elif sw == "miecz_blysk":
                for ox,oy in [(-6,-7),(6,-10),(-4,5)]:
                    pygame.draw.line(screen,(80,200,255),(cx+ox,cy+oy),(cx+ox+3,cy+oy-4),1)
            elif sw == "miecz_smierci":
                pygame.draw.line(screen,(40,40,40),(cx,cy-16),(cx,cy+9),5)
                pygame.draw.line(screen,(200,200,200),(cx,cy-16),(cx,cy+9),2)
            elif sw == "miecz_krola":
                gg = pygame.Surface((SLOT_SIZE,SLOT_SIZE), pygame.SRCALPHA)
                pygame.draw.circle(gg,(255,215,0,60),(SLOT_SIZE//2,SLOT_SIZE//2),SLOT_SIZE//2)
                screen.blit(gg,(sx,sy))
                pygame.draw.circle(screen,(255,215,0),(cx,cy-17),3)
        else:
            # empty placeholder icon per slot type
            dim_c = (50,52,72)
            if label == "HELM":
                pygame.draw.arc(screen, dim_c,
                                (cx-10, cy-9, 20, 16), 0, math.pi, 2)
                pygame.draw.line(screen, dim_c, (cx-10, cy+2), (cx+10, cy+2), 2)
            elif label == "ZBROJA":
                pts = [(cx,cy-12),(cx+9,cy-6),(cx+9,cy+6),(cx,cy+12),(cx-9,cy+6),(cx-9,cy-6)]
                pygame.draw.polygon(screen, dim_c, pts, 2)
            elif label == "BRON":
                if sword_icon:
                    screen.blit(sword_icon, (cx - 16, cy - 16))
                else:
                    pygame.draw.line(screen, dim_c, (cx,cy-13),(cx,cy+8), 2)
                    pygame.draw.line(screen, dim_c, (cx-7,cy+4),(cx+7,cy+4), 2)
            elif label == "REKAWICE":
                pygame.draw.rect(screen, dim_c, (cx-8, cy-5, 16, 12), 2, border_radius=3)
                for fi in range(4):
                    pygame.draw.rect(screen, dim_c, (cx-7+fi*5, cy-11, 4, 8), 2, border_radius=2)

        # Slot label below
        lbl_s = small_font.render(label, True, brd[:3] if filled else (70,72,95))
        screen.blit(lbl_s, (cx - lbl_s.get_width()//2, sy + SLOT_SIZE + 2))

    # Miecz Krola timer bar — directly under the 4 slots
    if player.equipped_sword == "miecz_krola":
        bar_x  = PANEL_X + 10
        bar_y  = PANEL_Y + 22 + SLOT_SIZE + 18
        bar_w  = panel_w - 20
        ratio  = max(0.0, player.king_sword_timer / 3500)
        pygame.draw.rect(screen, (40,28,0),  (bar_x, bar_y, bar_w, 10), border_radius=4)
        pygame.draw.rect(screen, (255, int(200*ratio), 0),
                                              (bar_x, bar_y, int(bar_w*ratio), 10), border_radius=4)
        pygame.draw.rect(screen, (255,200,0),(bar_x, bar_y, bar_w, 10), 1, border_radius=4)
        secs = max(0.0, player.king_sword_timer / 1000)
        t = small_font.render(f"ZABIJ! {secs:.1f}s", True, (255,215,0))
        screen.blit(t, (bar_x + bar_w//2 - t.get_width()//2, bar_y - 14))

def draw_boss_hud(boss):
    bw,bh=500,22; bx=WIDTH//2-bw//2; by=HEIGHT-60; hpr=max(0,boss.hp/boss.max_hp)
    panel=pygame.Surface((bw+130,bh+20),pygame.SRCALPHA)
    pygame.draw.rect(panel,(0,0,0,160),panel.get_rect(),border_radius=8)
    screen.blit(panel,(bx-75,by-10))
    pygame.draw.rect(screen,(50,0,0),(bx,by,bw,bh),border_radius=5)
    pygame.draw.rect(screen,(255,int(hpr*80),0),(bx,by,int(hpr*bw),bh),border_radius=5)
    pygame.draw.rect(screen,(200,50,50),(bx,by,bw,bh),2,border_radius=5)
    screen.blit(bold_font.render("BOSS",True,(255,60,60)),(bx-55,by+1))
    screen.blit(font.render(f"{int(boss.hp)} / {boss.max_hp}",True,(220,220,220)),(bx+bw+10,by+4))
    plabs={Boss.PHASE_SPIN:(255,160,0),Boss.PHASE_DASH:(255,80,0),Boss.PHASE_TELEPORT:(180,0,255)}
    if boss.phase in plabs:
        pt=bold_font.render(boss.phase.upper(),True,plabs[boss.phase])
        screen.blit(pt,(bx+bw//2-pt.get_width()//2,by-28))

def draw_minimap(player, enemies, boss, gems, chests, cam_x, cam_y):
    mm=140; mmx=WIDTH-mm-14; mmy=14; sc=mm/MAP_WIDTH
    ms=pygame.Surface((mm,mm),pygame.SRCALPHA)
    pygame.draw.rect(ms,(0,0,0,160),ms.get_rect(),border_radius=6)
    pygame.draw.rect(ms,(60,60,90,220),ms.get_rect(),1,border_radius=6)
    vx=int(cam_x*sc); vy=int(cam_y*sc)
    pygame.draw.rect(ms,(80,80,120,100),(vx,vy,int(WIDTH*sc),int(HEIGHT*sc)))
    for e in enemies:
        pygame.draw.circle(ms,(255,60,60),(int(e.pos.x*sc),int(e.pos.y*sc)),2)
    if boss:
        pygame.draw.circle(ms,(255,0,0),(int(boss.pos.x*sc),int(boss.pos.y*sc)),5)
    for g in gems[:30]:
        pygame.draw.circle(ms,(0,180,255),(int(g.pos.x*sc),int(g.pos.y*sc)),1)
    if player.has("prophets_eye"):
        for c in chests:
            pygame.draw.circle(ms,(255,200,50),(int(c.pos.x*sc),int(c.pos.y*sc)),3)
    ppx=int(player.pos.x*sc); ppy=int(player.pos.y*sc)
    pygame.draw.circle(ms,player.color,(ppx,ppy),4)
    pygame.draw.circle(ms,(255,255,255),(ppx,ppy),4,1)
    screen.blit(ms,(mmx,mmy))
    lbl=small_font.render("MAPA",True,(100,100,140))
    screen.blit(lbl,(mmx+mm//2-lbl.get_width()//2,mmy+mm+2))

def draw_background(cam_x, cam_y):
    cx,cy=int(cam_x),int(cam_y); screen.fill(BG_COLOR)
    gc=(28,28,42); gc2=(38,38,60)
    for x in range(-(cx%100),WIDTH+100,100):  pygame.draw.line(screen,gc,(x,0),(x,HEIGHT))
    for y in range(-(cy%100),HEIGHT+100,100): pygame.draw.line(screen,gc,(0,y),(WIDTH,y))
    for x in range(-(cx%500),WIDTH+500,500):  pygame.draw.line(screen,gc2,(x,0),(x,HEIGHT),2)
    for y in range(-(cy%500),HEIGHT+500,500): pygame.draw.line(screen,gc2,(0,y),(WIDTH,y),2)

# ──────────────────────────────────────────────────────────────
#  MENUS
# ──────────────────────────────────────────────────────────────
# ──────────────────────────────────────────────────────────────
#  HELPERS: draw tiled dark background for menus
# ──────────────────────────────────────────────────────────────
_menu_anim = 0.0

def draw_menu_bg():
    global _menu_anim
    _menu_anim += 0.01
    screen.fill((8, 8, 18))
    for x in range(0, WIDTH+80, 80):
        alpha = int(18 + 8*math.sin(_menu_anim + x*0.003))
        pygame.draw.line(screen, (20, 20, 40), (x, 0), (x, HEIGHT))
    for y in range(0, HEIGHT+80, 80):
        pygame.draw.line(screen, (20, 20, 40), (0, y), (WIDTH, y))
    # Floating particles in background
    import time
    t = time.time()
    for i in range(12):
        px = int((WIDTH*0.1 + WIDTH*0.8 * ((i*137+int(t*20))%100)/100))
        py = int((HEIGHT * ((i*0.17 + t*0.04*(1+i%3)) % 1.0)))
        r  = 1 + i%3
        a  = int(30 + 20*math.sin(t+i))
        s  = pygame.Surface((r*4,r*4), pygame.SRCALPHA)
        pygame.draw.circle(s, (80,80,180,a), (r*2,r*2), r)
        screen.blit(s, (px,py))

def draw_menu_title(text, y=None, color=(255,220,60)):
    if y is None: y = HEIGHT//8
    shadow = big_font.render(text, True, (0,0,0))
    screen.blit(shadow, (WIDTH//2 - shadow.get_width()//2 + 3, y+3))
    surf = big_font.render(text, True, color)
    screen.blit(surf, (WIDTH//2 - surf.get_width()//2, y))
    return y + surf.get_height() + 10

def draw_menu_button(label, cx, cy, w, h, selected, color=(255,220,60), index=None):
    """Draw a single menu button. Returns its rect."""
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    if selected:
        pygame.draw.rect(s, (*color, 40),  (0,0,w,h), border_radius=14)
        pygame.draw.rect(s, (*color, 220), (0,0,w,h), 2, border_radius=14)
    else:
        pygame.draw.rect(s, (25,25,45,200), (0,0,w,h), border_radius=14)
        pygame.draw.rect(s, (55,55,85,180), (0,0,w,h), 2, border_radius=14)
    screen.blit(s, (cx, cy))
    if index is not None:
        idx_s = small_font.render(f"[{index}]", True, color if selected else (70,70,100))
        screen.blit(idx_s, (cx+10, cy+8))
    tc = color if selected else (160,160,180)
    t  = bold_font.render(label, True, tc)
    screen.blit(t, (cx + w//2 - t.get_width()//2, cy + h//2 - t.get_height()//2))
    return pygame.Rect(cx, cy, w, h)

# ──────────────────────────────────────────────────────────────
#  SETTINGS MENU
# ──────────────────────────────────────────────────────────────
def show_settings_menu():
    keys   = ["volume_music","volume_sfx"]
    labels = ["Głośność muzyki","Głośność SFX"]
    sel    = 0
    while True:
        draw_menu_bg()
        draw_menu_title("USTAWIENIA", HEIGHT//7, (200,200,255))

        for i,(k,lbl) in enumerate(zip(keys,labels)):
            y   = HEIGHT//2 - 60 + i*90
            col = (255,255,100) if i==sel else (140,140,170)
            # Label
            ls = bold_font.render(lbl, True, col)
            screen.blit(ls, (WIDTH//2 - 220, y))
            # Bar
            val=settings[k]; bx=WIDTH//2-220; bby=y+36; bbw=440
            pygame.draw.rect(screen,(30,30,55),(bx,bby,bbw,16),border_radius=8)
            pygame.draw.rect(screen,col,(bx,bby,int(val/100*bbw),16),border_radius=8)
            pygame.draw.rect(screen,(100,100,140),(bx,bby,bbw,16),1,border_radius=8)
            vs = font.render(f"{val}%", True, (220,220,220))
            screen.blit(vs, (bx+bbw+14, bby-2))
            if i==sel:
                # arrows
                screen.blit(bold_font.render("◄", True, col), (bx-28, bby-4))
                screen.blit(bold_font.render("►", True, col), (bx+bbw+46, bby-4))

        draw_menu_button("← WRÓĆ", WIDTH//2-100, HEIGHT*4//5, 200, 50, False, (160,160,200))
        hint = small_font.render("↑↓ wybierz   ◄► zmień wartość   ESC wróć", True, (60,60,90))
        screen.blit(hint, (WIDTH//2 - hint.get_width()//2, HEIGHT*4//5+60))

        pygame.display.flip(); clock.tick(60)
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE: return
                if ev.key == pygame.K_UP:    sel = (sel-1) % len(keys)
                if ev.key == pygame.K_DOWN:  sel = (sel+1) % len(keys)
                if ev.key == pygame.K_LEFT:  settings[keys[sel]] = max(0,   settings[keys[sel]]-5)
                if ev.key == pygame.K_RIGHT: settings[keys[sel]] = min(100, settings[keys[sel]]+5)

# ──────────────────────────────────────────────────────────────
#  MAIN MENU  (Rozpocznij / Ustawienia / Wyjście)
# ──────────────────────────────────────────────────────────────
def show_main_menu():
    opts   = ["ROZPOCZNIJ GRĘ", "USTAWIENIA", "WYJŚCIE"]
    colors = [(255,220,60), (160,160,220), (220,80,80)]
    sel    = 0
    btn_w, btn_h = 380, 64
    btn_gap      = 22

    while True:
        draw_menu_bg()

        # Title
        ty = draw_menu_title("ROGUELIKE", HEIGHT//7)
        sub = font.render("Przeżyj jak najdłużej", True, (90,90,130))
        screen.blit(sub, (WIDTH//2 - sub.get_width()//2, ty))

        total_h = len(opts)*(btn_h+btn_gap) - btn_gap
        start_y = HEIGHT//2 - total_h//2 + 30

        for i,(label,col) in enumerate(zip(opts,colors)):
            by = start_y + i*(btn_h+btn_gap)
            draw_menu_button(label, WIDTH//2-btn_w//2, by, btn_w, btn_h, i==sel, col)

        hint = small_font.render("↑↓ lub mysz   ENTER potwierdź", True, (50,50,80))
        screen.blit(hint, (WIDTH//2 - hint.get_width()//2, HEIGHT-40))

        pygame.display.flip(); clock.tick(60)
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE: pygame.quit(); sys.exit()
                if ev.key == pygame.K_UP:     sel = (sel-1) % len(opts)
                if ev.key == pygame.K_DOWN:   sel = (sel+1) % len(opts)
                if ev.key == pygame.K_RETURN:
                    if sel == 0:
                        chosen = show_character_select()
                        if chosen: return chosen
                    elif sel == 1:
                        show_settings_menu()
                    elif sel == 2:
                        pygame.quit(); sys.exit()
            if ev.type == pygame.MOUSEMOTION:
                mx,my = ev.pos
                for i in range(len(opts)):
                    by = start_y + i*(btn_h+btn_gap)
                    if WIDTH//2-btn_w//2 <= mx <= WIDTH//2+btn_w//2 and by <= my <= by+btn_h:
                        sel = i
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                mx,my = ev.pos
                for i in range(len(opts)):
                    by = start_y + i*(btn_h+btn_gap)
                    if WIDTH//2-btn_w//2 <= mx <= WIDTH//2+btn_w//2 and by <= my <= by+btn_h:
                        sel = i
                        if sel == 0:
                            chosen = show_character_select()
                            if chosen: return chosen
                        elif sel == 1:
                            show_settings_menu()
                        elif sel == 2:
                            pygame.quit(); sys.exit()

# ──────────────────────────────────────────────────────────────
#  CHARACTER SELECT
# ──────────────────────────────────────────────────────────────
def show_character_select():
    options = list(CHARACTERS.keys())
    selected = 0
    ULT_COLS = {"Warrior":(255,80,0),"Rogue":(200,0,200),"Knight":(255,240,80),"Brawler":(255,200,0)}

    CW, CH = 300, 340   # card width / height — plenty of room
    GAP    = 28
    total_w = len(options)*CW + (len(options)-1)*GAP
    start_x = WIDTH//2 - total_w//2

    while True:
        draw_menu_bg()
        draw_menu_title("WYBIERZ POSTAĆ", HEIGHT//10, (200,200,255))

        cards_y = HEIGHT//2 - CH//2

        for i, name in enumerate(options):
            char   = CHARACTERS[name]
            cx     = start_x + i*(CW+GAP)
            cy     = cards_y
            is_sel = (i == selected)
            col    = char['color']
            uc     = ULT_COLS.get(name, (200,200,200))

            # Card background
            card = pygame.Surface((CW, CH), pygame.SRCALPHA)
            if is_sel:
                pygame.draw.rect(card, (*col, 55),  (0,0,CW,CH), border_radius=18)
                pygame.draw.rect(card, (*col, 230), (0,0,CW,CH), 3, border_radius=18)
                # Glow strip at top
                strip = pygame.Surface((CW, 6), pygame.SRCALPHA)
                pygame.draw.rect(strip, (*col,200), (0,0,CW,6), border_radius=3)
                card.blit(strip, (0,0))
            else:
                pygame.draw.rect(card, (22,22,42,210), (0,0,CW,CH), border_radius=18)
                pygame.draw.rect(card, (55,55,85,160), (0,0,CW,CH), 2, border_radius=18)
            screen.blit(card, (cx, cy))

            # Hotkey badge
            badge_col = col if is_sel else (60,60,80)
            bs = pygame.Surface((26,22), pygame.SRCALPHA)
            pygame.draw.rect(bs, (*badge_col,180), (0,0,26,22), border_radius=5)
            screen.blit(bs, (cx+10, cy+10))
            screen.blit(small_font.render(f"[{i+1}]", True, (255,255,255)), (cx+13, cy+12))

            # Avatar circle
            av_cx = cx + CW//2
            av_cy = cy + 66
            av_r  = 36
            ag = pygame.Surface((av_r*4, av_r*4), pygame.SRCALPHA)
            pygame.draw.circle(ag, (*col, 40 if is_sel else 15), (av_r*2,av_r*2), av_r*2)
            screen.blit(ag, (av_cx-av_r*2, av_cy-av_r*2))
            pygame.draw.circle(screen, col if is_sel else tuple(c//2 for c in col), (av_cx,av_cy), av_r)
            pygame.draw.circle(screen, (255,255,255) if is_sel else (120,120,140), (av_cx,av_cy), av_r, 2)
            # Eyes
            pygame.draw.circle(screen,(220,240,220),(av_cx-10,av_cy-6),8)
            pygame.draw.circle(screen,(220,240,220),(av_cx+10,av_cy-6),8)
            pygame.draw.circle(screen,(0,0,0),(av_cx-10,av_cy-6),4)
            pygame.draw.circle(screen,(0,0,0),(av_cx+10,av_cy-6),4)
            pygame.draw.circle(screen,(255,255,255),(av_cx-8,av_cy-8),2)
            pygame.draw.circle(screen,(255,255,255),(av_cx+12,av_cy-8),2)

            # Name
            nc = (255,255,255) if is_sel else (160,160,185)
            ns = bold_font.render(name.upper(), True, nc)
            screen.blit(ns, (cx + CW//2 - ns.get_width()//2, cy + 116))

            # Divider
            div_col = (*col,120) if is_sel else (50,50,75,120)
            dsurf = pygame.Surface((CW-40,1), pygame.SRCALPHA)
            pygame.draw.rect(dsurf, div_col, (0,0,CW-40,1))
            screen.blit(dsurf, (cx+20, cy+140))

            # Stats rows
            def stat_row(label, value, color, row):
                y2 = cy + 150 + row*22
                ls2 = small_font.render(label, True, (120,120,150))
                vs2 = small_font.render(value,  True, color)
                screen.blit(ls2, (cx+20,  y2))
                screen.blit(vs2, (cx+CW-vs2.get_width()-20, y2))

            stat_row("BROŃ",    char['weapon'],             (200,200,220), 0)
            stat_row("OBRAZENIA", "█"*char['damage'],       (255,90,90),   1)
            stat_row("PRĘDKOŚĆ", "█"*int(char['speed']),   (80,220,255),  2)

            # ULT section
            ult_div = pygame.Surface((CW-40,1), pygame.SRCALPHA)
            pygame.draw.rect(ult_div, (*uc,100), (0,0,CW-40,1))
            screen.blit(ult_div, (cx+20, cy+218))

            ult_label_s = small_font.render("⚡  ULT [Q]", True, uc)
            screen.blit(ult_label_s, (cx+20, cy+226))

            ult_name_s = bold_font.render(char['ult_name'], True, uc if is_sel else tuple(c//2+80 for c in uc))
            screen.blit(ult_name_s, (cx + CW//2 - ult_name_s.get_width()//2, cy+244))

            # Ult desc — word-wrap inside card
            desc_words = char['ult_desc'].split()
            desc_lines = []; cur_line = ""
            for word in desc_words:
                test = (cur_line+" "+word).strip()
                if small_font.size(test)[0] <= CW-30:
                    cur_line = test
                else:
                    if cur_line: desc_lines.append(cur_line)
                    cur_line = word
            if cur_line: desc_lines.append(cur_line)
            for li, line in enumerate(desc_lines):
                ds = small_font.render(line, True, (140,140,170))
                screen.blit(ds, (cx + CW//2 - ds.get_width()//2, cy+268+li*18))

        # Bottom buttons
        btn_y = HEIGHT - 80
        draw_menu_button("← WRÓĆ",        WIDTH//2-340, btn_y, 180, 46, False, (140,140,200))
        draw_menu_button("WYBIERZ  ENTER →", WIDTH//2+160, btn_y, 220, 46, True,  (255,220,60))

        hint = small_font.render("◄ ► lub klawisze 1–4 aby wybrać",True,(55,55,85))
        screen.blit(hint, (WIDTH//2 - hint.get_width()//2, HEIGHT-26))

        pygame.display.flip(); clock.tick(60)

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE: return None   # back to main menu
                if ev.key == pygame.K_LEFT:  selected = (selected-1) % len(options)
                if ev.key == pygame.K_RIGHT: selected = (selected+1) % len(options)
                if ev.key == pygame.K_1: selected = 0
                if ev.key == pygame.K_2: selected = 1
                if ev.key == pygame.K_3: selected = 2
                if ev.key == pygame.K_4: selected = 3
                if ev.key == pygame.K_RETURN: return options[selected]
            if ev.type == pygame.MOUSEMOTION:
                mx,my = ev.pos
                for i in range(len(options)):
                    cx = start_x + i*(CW+GAP)
                    if cx <= mx <= cx+CW and cards_y <= my <= cards_y+CH:
                        selected = i
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                mx,my = ev.pos
                # Back button
                if WIDTH//2-340 <= mx <= WIDTH//2-160 and btn_y <= my <= btn_y+46:
                    return None
                # Select button or card double-click
                if WIDTH//2+160 <= mx <= WIDTH//2+380 and btn_y <= my <= btn_y+46:
                    return options[selected]
                for i in range(len(options)):
                    cx = start_x + i*(CW+GAP)
                    if cx <= mx <= cx+CW and cards_y <= my <= cards_y+CH:
                        if i == selected:
                            return options[selected]   # double-click selects
                        selected = i

# ──────────────────────────────────────────────────────────────
#  PAUSE MENU
# ──────────────────────────────────────────────────────────────
def show_pause_menu():
    """Returns True to continue, False to quit to main menu."""
    opts   = ["WRÓĆ DO GRY", "USTAWIENIA", "MENU GŁÓWNE"]
    colors = [(100,220,100), (160,160,220), (220,80,80)]
    sel    = 0
    btn_w, btn_h = 340, 58
    btn_gap      = 18

    while True:
        # dim the frozen game
        dim = pygame.Surface((WIDTH,HEIGHT), pygame.SRCALPHA)
        pygame.draw.rect(dim,(0,0,0,160), dim.get_rect())
        screen.blit(dim,(0,0))

        # Panel
        pw,ph = 480, 360
        px,py = WIDTH//2-pw//2, HEIGHT//2-ph//2
        ps = pygame.Surface((pw,ph), pygame.SRCALPHA)
        pygame.draw.rect(ps,(12,12,28,230),(0,0,pw,ph),border_radius=20)
        pygame.draw.rect(ps,(80,80,140,200),(0,0,pw,ph),2,border_radius=20)
        screen.blit(ps,(px,py))

        # Title
        t = big_font.render("PAUZA", True, (255,220,60))
        screen.blit(t,(WIDTH//2-t.get_width()//2, py+24))

        total_h = len(opts)*(btn_h+btn_gap)-btn_gap
        start_y = py+ph//2 - total_h//2 + 20

        for i,(label,col) in enumerate(zip(opts,colors)):
            by = start_y + i*(btn_h+btn_gap)
            draw_menu_button(label, WIDTH//2-btn_w//2, by, btn_w, btn_h, i==sel, col)

        hint = small_font.render("↑↓   ENTER", True,(55,55,90))
        screen.blit(hint,(WIDTH//2-hint.get_width()//2, py+ph-30))

        pygame.display.flip(); clock.tick(60)

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE: return True   # resume
                if ev.key == pygame.K_UP:    sel = (sel-1)%len(opts)
                if ev.key == pygame.K_DOWN:  sel = (sel+1)%len(opts)
                if ev.key == pygame.K_RETURN:
                    if sel == 0: return True
                    elif sel == 1: show_settings_menu()
                    elif sel == 2: return False
            if ev.type == pygame.MOUSEMOTION:
                mx,my = ev.pos
                for i in range(len(opts)):
                    by = start_y + i*(btn_h+btn_gap)
                    if WIDTH//2-btn_w//2<=mx<=WIDTH//2+btn_w//2 and by<=my<=by+btn_h:
                        sel=i
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button==1:
                mx,my = ev.pos
                for i in range(len(opts)):
                    by = start_y + i*(btn_h+btn_gap)
                    if WIDTH//2-btn_w//2<=mx<=WIDTH//2+btn_w//2 and by<=my<=by+btn_h:
                        sel=i
                        if sel==0: return True
                        elif sel==1: show_settings_menu()
                        elif sel==2: return False

def show_game_over(level, kill_count):
    alpha=0; overlay=pygame.Surface((WIDTH,HEIGHT)); overlay.fill((0,0,0))
    while True:
        alpha=min(200,alpha+4); overlay.set_alpha(alpha); screen.blit(overlay,(0,0))
        t=big_font.render("GAME OVER",True,(220,40,40))
        screen.blit(t,(WIDTH//2-t.get_width()//2,HEIGHT//2-120))
        for i,(lbl,val) in enumerate([("Poziom",str(level)),("Zabici wrogowie",str(kill_count))]):
            tx=bold_font.render(f"{lbl}: {val}",True,(200,200,220))
            screen.blit(tx,(WIDTH//2-tx.get_width()//2,HEIGHT//2-20+i*40))
        r=font.render("[ R ] - Zagraj ponownie     [ ESC ] - Wyjdz",True,(120,120,150))
        screen.blit(r,(WIDTH//2-r.get_width()//2,HEIGHT//2+100))
        pygame.display.flip(); clock.tick(60)
        for e in pygame.event.get():
            if e.type==pygame.KEYDOWN:
                if e.key==pygame.K_r: return True
                if e.key==pygame.K_ESCAPE: pygame.quit(); sys.exit()

def show_stat_menu():
    opts=[{"key":"HP","label":"+20 MAX HP","color":(255,80,80)},
          {"key":"DMG","label":"+1 OBRAZENIA","color":(255,220,60)},
          {"key":"SPD","label":"+0.5 SZYBKOSC","color":(60,220,255)}]
    sel=0
    while True:
        ov=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
        pygame.draw.rect(ov,(0,0,0,180),ov.get_rect()); screen.blit(ov,(0,0))
        t=bold_font.render("WYBIERZ ULEPSZENIE",True,(255,255,100))
        screen.blit(t,(WIDTH//2-t.get_width()//2,HEIGHT//2-130))
        cw,ch=200,90; total=len(opts)*(cw+24); ssx=WIDTH//2-total//2
        for i,opt in enumerate(opts):
            cx=ssx+i*(cw+24); cy=HEIGHT//2-ch//2; is_sel=i==sel
            cs=pygame.Surface((cw,ch),pygame.SRCALPHA)
            if is_sel:
                pygame.draw.rect(cs,(*opt['color'],50),(0,0,cw,ch),border_radius=10)
                pygame.draw.rect(cs,(*opt['color'],220),(0,0,cw,ch),2,border_radius=10)
            else:
                pygame.draw.rect(cs,(30,30,50,200),(0,0,cw,ch),border_radius=10)
                pygame.draw.rect(cs,(60,60,80,180),(0,0,cw,ch),1,border_radius=10)
            screen.blit(cs,(cx,cy))
            screen.blit(small_font.render(f"[{i+1}]",True,(120,120,150) if not is_sel else opt['color']),(cx+8,cy+8))
            lbl=bold_font.render(opt['label'],True,opt['color'] if is_sel else (160,160,180))
            screen.blit(lbl,(cx+cw//2-lbl.get_width()//2,cy+36))
        pygame.display.flip(); clock.tick(60)
        for e in pygame.event.get():
            if e.type==pygame.KEYDOWN:
                if e.key==pygame.K_1: return 'HP'
                if e.key==pygame.K_2: return 'DMG'
                if e.key==pygame.K_3: return 'SPD'
                if e.key==pygame.K_LEFT: sel=(sel-1)%len(opts)
                if e.key==pygame.K_RIGHT: sel=(sel+1)%len(opts)
                if e.key==pygame.K_RETURN: return opts[sel]['key']
                if e.key==pygame.K_ESCAPE: pygame.quit(); sys.exit()

def show_weapon_menu(lvl, current_weapon):
    if lvl==5:
        opts=[("Luk","Bow",(200,200,200)),("Miecz","Sword",(0,160,255)),("Zostaw bron",None,(120,120,120))]
    else:
        opts=[("Karabin","Machine Gun",(255,200,0)),("Miecz Swietlny","Lightsaber",(0,255,100)),("Zostaw bron",None,(120,120,120))]
    sel=0
    while True:
        ov=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
        pygame.draw.rect(ov,(0,0,0,200),ov.get_rect()); screen.blit(ov,(0,0))
        t=bold_font.render(f"POZIOM {lvl} - WYBIERZ BRON",True,(255,220,0))
        screen.blit(t,(WIDTH//2-t.get_width()//2,HEIGHT//2-130))
        cw,ch=200,80; total=len(opts)*(cw+24); ssx=WIDTH//2-total//2
        for i,(label,key,color) in enumerate(opts):
            cx=ssx+i*(cw+24); cy=HEIGHT//2-ch//2; is_sel=i==sel
            cs=pygame.Surface((cw,ch),pygame.SRCALPHA)
            if is_sel:
                pygame.draw.rect(cs,(*color,60),(0,0,cw,ch),border_radius=10)
                pygame.draw.rect(cs,(*color,220),(0,0,cw,ch),2,border_radius=10)
            else:
                pygame.draw.rect(cs,(30,30,50,200),(0,0,cw,ch),border_radius=10)
                pygame.draw.rect(cs,(70,70,100,200),(0,0,cw,ch),1,border_radius=10)
            screen.blit(cs,(cx,cy))
            screen.blit(small_font.render(f"[{i+1}]",True,(120,120,150)),(cx+8,cy+8))
            lbl=bold_font.render(label,True,color if is_sel else (160,160,180))
            screen.blit(lbl,(cx+cw//2-lbl.get_width()//2,cy+28))
        nav=font.render("< > lub 1-3 | ENTER",True,(80,80,110))
        screen.blit(nav,(WIDTH//2-nav.get_width()//2,HEIGHT//2+80))
        pygame.display.flip(); clock.tick(60)
        for e in pygame.event.get():
            if e.type==pygame.KEYDOWN:
                if e.key==pygame.K_1: return opts[0][1] or current_weapon
                if e.key==pygame.K_2: return opts[1][1] or current_weapon
                if e.key==pygame.K_3: return current_weapon
                if e.key==pygame.K_LEFT: sel=(sel-1)%len(opts)
                if e.key==pygame.K_RIGHT: sel=(sel+1)%len(opts)
                if e.key==pygame.K_RETURN:
                    ch=opts[sel][1]; return ch if ch else current_weapon

# ──────────────────────────────────────────────────────────────
#  SWORD SPECIAL EFFECTS  (called after a confirmed hit)
# ──────────────────────────────────────────────────────────────
def apply_sword_effect(player, hit_enemy, all_enemies, enemies, boss_ref, gems, dropped_items, chests, kill_count_box):
    sw = player.equipped_sword
    if sw is None:
        return

    if sw == "miecz_krwi":
        player.heal(3)
        spawn_particles(player.pos, (220,0,0), count=5, speed_range=(1,3))

    elif sw == "miecz_blysk":
        for e in all_enemies[:]:
            if e is not hit_enemy and e.pos.distance_to(hit_enemy.pos) < 200:
                e.hp -= 1
                spawn_particles(e.pos, (80,180,255), count=3)
                if e.hp <= 0:
                    kill_enemy(e, enemies, boss_ref, gems, dropped_items, chests)
                    kill_count_box[0] += 1

    elif sw == "miecz_smierci":
        if random.random() < 0.025:
            hit_enemy.hp = 0
            spawn_particles(hit_enemy.pos, (60,0,60), count=20, speed_range=(2,7))

    elif sw == "miecz_krola":
        player.reset_king_timer()

# ──────────────────────────────────────────────────────────────
#  KILL HELPER
# ──────────────────────────────────────────────────────────────
first_boss_killed=False

def kill_enemy(e, regular_enemies, boss_ref, gems, dropped_items, chests):
    global first_boss_killed
    is_boss=getattr(e,'is_boss',False)
    gems.append(ExperienceGem(e.pos,50 if is_boss else 3,(255,0,255) if is_boss else GEM_COLOR))
    spawn_particles(e.pos,e.color,count=12)
    if is_boss:
        if not first_boss_killed:
            first_boss_killed=True
            # Drop a random sword on first boss kill
            sword_pool = ["miecz_krwi","miecz_blysk","miecz_smierci","miecz_krola"]
            dropped_items.append(DroppedItem(e.pos, random.choice(sword_pool)))
        boss_ref[0]=None
    else:
        # 1% item drop
        if random.random()<0.01:
            dropped_items.append(DroppedItem(e.pos,random.choice(ALL_DROP_ITEMS)))
        # 1.5% chest drop  ← zmienione z 3% na 1.5%
        if random.random()<0.015:
            chests.append(Chest(e.pos+pygame.Vector2(random.uniform(-20,20),random.uniform(-20,20))))
        regular_enemies.remove(e)

# ──────────────────────────────────────────────────────────────
#  MAIN
# ──────────────────────────────────────────────────────────────
def main():
    global levelup_flash, first_boss_killed

    while True:
        chosen = show_main_menu()
        if chosen is None: continue   # wróć do main menu (nie powinno się zdarzyć, ale na wszelki wypadek)
        char_data=CHARACTERS[chosen]
        player=Player()
        player.weapon=char_data["weapon"]; player.damage=char_data["damage"]
        player.speed=char_data["speed"];   player.color=char_data["color"]
        player.base_speed=char_data["speed"]
        # ── Inicjalizacja ult ──
        player.ult_class = chosen  # "Warrior","Rogue","Knight","Brawler"
        player.ult_exp_needed = 30  # 3x próg pierwszego poziomu (10 EXP × 3)

        enemies=[]; boss_ref=[None]; bullets=[]; enemy_bullets=[]
        gems=[]; dropped_items=[]; hazard_zones=[]; chests=[]
        particles.clear()
        spawn_timer=0; boss_spawned_lvl=set()
        levelup_flash=0; kill_count=0; first_boss_killed=False; running=True
        quit_to_menu=False

        while running:
            dt=clock.tick(FPS)
            for event in pygame.event.get():
                if event.type==pygame.QUIT: pygame.quit(); sys.exit()
                if event.type==pygame.KEYDOWN and event.key==pygame.K_ESCAPE:
                    if not show_pause_menu():
                        running=False; quit_to_menu=True; break   # wróć do main menu
                if event.type==pygame.KEYDOWN and event.key==pygame.K_q:
                    player.activate_ult(enemies, enemy_bullets, hazard_zones)

            boss=boss_ref[0]; boss_active=boss is not None

            # ── Miecz Krola tick ──
            player.update_king_sword(dt)
            # ── Ult update ──
            player.update_ult(dt)

            # ── Level up ──
            if player.check_level_up():
                levelup_flash=30
                spawn_particles(player.pos,(255,255,100),count=20,speed_range=(2,6),life_range=(30,60))
                if player.level==5:   player.weapon=show_weapon_menu(5,player.weapon)
                elif player.level==10: player.weapon=show_weapon_menu(10,player.weapon)
                elif player.level%2==0:
                    c=show_stat_menu()
                    if c=='HP': player.max_hp+=20; player.hp+=20
                    elif c=='DMG': player.damage+=1
                    elif c=='SPD': player.speed+=0.5

            # ── Boss spawn ──
            lvl_key=(player.level//10)*10
            if player.level>=10 and lvl_key not in boss_spawned_lvl and not boss_active:
                boss_spawned_lvl.add(lvl_key)
                boss_ref[0]=Boss(player.level,player.pos)
                enemies.clear(); enemy_bullets.clear()
                boss=boss_ref[0]; boss_active=True

            # ── Regular enemy spawn ──
            if not boss_active:
                spawn_timer+=dt
                if spawn_timer>max(150,1000-player.level*40):
                    for _ in range(1+player.level//4):
                        enemies.append(Enemy(player.level,player.pos))
                    spawn_timer=0

            # ── Player attack ──
            player.attack_cooldown-=dt
            all_targets=([boss] if boss_active else [])+enemies

            if all_targets and player.attack_cooldown<=0:
                nearest=min(all_targets,key=lambda e:player.pos.distance_to(e.pos))
                target=nearest.pos
                kc_box=[kill_count]   # mutable box so inner functions can update

                def apply_dmg(e, dmg):
                    crit=player.crit_chance>0 and random.random()<player.crit_chance
                    actual=dmg*(2 if crit else 1)
                    e.hp-=actual
                    player.heal(actual*player.life_steal)
                    if crit: spawn_particles(e.pos,(255,255,0),count=6)

                def melee_hit(rng, dmg_mult=1):
                    tgts=([boss] if boss_active else [])+enemies[:]
                    for e in tgts:
                        if id(e) in player.frozen_enemies: continue
                        if player.pos.distance_to(e.pos)<rng+e.radius:
                            if player.ult_instant_kill:
                                e.hp = 0
                                spawn_particles(e.pos,(200,0,200),count=12)
                            else:
                                apply_dmg(e, player.effective_damage()*dmg_mult)
                                spawn_particles(e.pos,(255,120,20),count=5)
                            apply_sword_effect(player, e, all_targets,
                                               enemies, boss_ref, gems, dropped_items, chests, kc_box)
                            if e.hp<=0:
                                kill_enemy(e,enemies,boss_ref,gems,dropped_items,chests)
                                kc_box[0]+=1

                player.attack_count+=1

                if player.weapon=="Axe":
                    player.sword_timer=15; melee_hit(player.sword_range)
                    fire_trident(player,target,bullets,(255,120,20),speed=14,radius=4)
                    player.attack_cooldown=player.base_cooldown*2.5

                elif player.weapon=="Dagger":
                    for offset in [-15,0,15]:
                        ang=math.atan2(target.y-player.pos.y,target.x-player.pos.x)
                        spd=pygame.Vector2(math.cos(ang+math.radians(offset)),math.sin(ang+math.radians(offset)))
                        bullets.append(Bullet(player.pos,player.pos+spd*100,(220,40,220),speed=18,radius=3))
                    if player.has("chain"):
                        chain_lightning(target,enemies,player.damage*0.8)
                    fire_trident(player,target,bullets,(220,40,220),speed=18,radius=3)
                    player.attack_cooldown=player.base_cooldown*0.3

                elif player.weapon=="Sword":
                    player.sword_timer=10; melee_hit(player.sword_range)
                    fire_trident(player,target,bullets,(0,180,255),speed=12,radius=4)
                    player.attack_cooldown=player.base_cooldown*1.2

                elif player.weapon=="Fist":
                    player.sword_timer=8
                    for e in (([boss] if boss_active else [])+enemies[:]):
                        if id(e) in player.frozen_enemies: continue
                        if player.pos.distance_to(e.pos)<player.sword_range+e.radius:
                            push=(e.pos-player.pos).normalize()
                            e.pos+=push*120*player.knockback_mult
                            apply_dmg(e,player.effective_damage())
                            spawn_particles(e.pos,(255,220,0),count=8)
                            apply_sword_effect(player, e, all_targets,
                                               enemies, boss_ref, gems, dropped_items, chests, kc_box)
                            if e.hp<=0:
                                kill_enemy(e,enemies,boss_ref,gems,dropped_items,chests); kc_box[0]+=1
                    fire_trident(player,target,bullets,(255,220,0),speed=12,radius=4)
                    player.attack_cooldown=player.base_cooldown*0.9

                elif player.weapon=="Lightsaber":
                    player.sword_timer=10; melee_hit(player.sword_range*1.5,dmg_mult=3)
                    fire_trident(player,target,bullets,(0,255,100),speed=14,radius=4)
                    player.attack_cooldown=player.base_cooldown*0.8

                elif player.weapon=="Machine Gun":
                    bullets.append(Bullet(player.pos,target,(255,200,0),speed=16,radius=3))
                    if player.has("chain"):
                        chain_lightning(target,enemies,player.damage*0.6)
                    fire_trident(player,target,bullets,(255,200,0),speed=16,radius=3)
                    player.attack_cooldown=player.base_cooldown*0.2

                elif player.weapon=="Bow":
                    bullets.append(Bullet(player.pos,target,(220,210,180),pierce=3))
                    fire_trident(player,target,bullets,(220,210,180),speed=12,radius=4,pierce=3)
                    player.attack_cooldown=player.base_cooldown

                else:  # Magic Ball
                    bullets.append(Bullet(player.pos,target,BULLET_COLOR))
                    if player.has("chain"):
                        chain_lightning(target,enemies,player.damage*0.7)
                    fire_trident(player,target,bullets,BULLET_COLOR,speed=12,radius=5)
                    player.attack_cooldown=player.base_cooldown

                if player.has("poison_gaunt") and player.attack_count%4==0:
                    player.gas_clouds.append(GasCloud(target,player.damage))

                kill_count=kc_box[0]

            # ── Move ──
            player.move(pygame.key.get_pressed())

            # ── Active items update ──
            player.update_active_items(dt,enemies,gems,dropped_items,hazard_zones)

            # ── Gems ──
            for g in gems[:]:
                if player.pos.distance_to(g.pos)<player.pickup_range:
                    spawn_particles(g.pos,g.color,count=6,speed_range=(1,3),life_range=(15,25))
                    if player.has("unstable_essence") and random.random()<0.05:
                        spawn_particles(player.pos,(255,80,200),count=14,speed_range=(2,6))
                        for e in enemies[:]:
                            if player.pos.distance_to(e.pos)<60:
                                e.hp-=player.damage*2
                    gem_val = int(g.value*player.exp_mult)
                    player.exp += gem_val
                    player.charge_ult(gem_val)
                    gems.remove(g)

            # ── Dropped items ──
            for it in dropped_items[:]:
                it.update()
                if not it.being_picked and player.pos.distance_to(it.pos)<player.pickup_range:
                    it.being_picked=True
                if it.done:
                    pid=it.item_id
                    player.add_item(pid)
                    spawn_particles(it.pos,ITEM_DEFS[pid]["color"],count=16,speed_range=(2,6),life_range=(25,50))
                    dropped_items.remove(it)
                    show_item_pickup_screen(pid)

            # ── Chests ──
            for ch in chests[:]:
                ch.update()
                if player.pos.distance_to(ch.pos)<player.pickup_range+ch.radius and not ch.opened:
                    ch.opened=True
                    item_id=random.choice(ALL_DROP_ITEMS)
                    player.add_item(item_id)
                    spawn_particles(ch.pos,(255,200,50),count=20,speed_range=(2,7),life_range=(20,50))
                    chests.remove(ch)
                    show_chest_open_screen(item_id)

            # ── Bullets ──
            for b in bullets[:]:
                b.update()
                if b.pos.distance_to(player.pos)>WIDTH+200:
                    if b in bullets: bullets.remove(b)
                    continue
                tgts=([boss] if boss_active else [])+enemies[:]
                for e in tgts:
                    if b.pos.distance_to(e.pos)<e.radius+b.radius:
                        if player.ult_instant_kill and not getattr(e,'is_boss',False):
                            e.hp = 0
                            spawn_particles(e.pos,(200,0,200),count=12)
                        else:
                            apply_dmg(e,player.effective_damage())
                        apply_sword_effect(player, e, tgts,
                                           enemies, boss_ref, gems, dropped_items, chests, [kill_count])
                        spawn_particles(e.pos,b.color,count=4)
                        b.pierce-=1
                        if b.pierce<=0 and b in bullets: bullets.remove(b)
                        if e.hp<=0:
                            kill_enemy(e,enemies,boss_ref,gems,dropped_items,chests); kill_count+=1
                        break

            # ── Mirror ──
            if player.has("mirror"):
                for eb in enemy_bullets[:]:
                    if eb.pos.distance_to(player.pos)<player.radius+30:
                        eb.dir=-eb.dir; eb.speed*=2; eb.color=(200,220,255)
                        enemy_bullets.remove(eb)
                        bullets.append(eb)

            # ── Boss ──
            if boss_active:
                boss.update(dt,player.pos,enemy_bullets,hazard_zones)
                boss=boss_ref[0]; boss_active=boss is not None
                if boss_active and boss.pos.distance_to(player.pos)<player.radius+boss.radius:
                    player.take_damage(0.6)
                    if player.hp<=0: running=False

            # ── Regular enemies ──
            for e in enemies[:]:
                frozen=id(e) in player.frozen_enemies
                e.update(player.pos,frozen=frozen)
                if not frozen and e.pos.distance_to(player.pos)<player.radius+e.radius:
                    player.take_damage(0.4)
                    if player.hp<=0: running=False

            # ── Enemy bullets ──
            for eb in enemy_bullets[:]:
                eb.update()
                if eb.pos.distance_to(player.pos)<player.radius+eb.radius:
                    player.take_damage(15)
                    spawn_particles(player.pos,(255,60,60),count=10)
                    enemy_bullets.remove(eb)
                elif eb.pos.distance_to(player.pos)>WIDTH+400:
                    enemy_bullets.remove(eb)

            # ── Hazard zones ──
            for hz in hazard_zones[:]:
                hz.update()
                if not hz.alive: hazard_zones.remove(hz); continue
                if hz.harms_player and hz.touches(player.pos,player.radius):
                    player.take_damage(0.3)
                    if player.hp<=0: running=False

            if player.hp<=0: running=False

            # ── Camera ──
            cam_x=max(0,min(MAP_WIDTH-WIDTH,   player.pos.x-WIDTH//2))
            cam_y=max(0,min(MAP_HEIGHT-HEIGHT, player.pos.y-HEIGHT//2))

            # ── Draw ──
            draw_background(cam_x,cam_y)
            for hz in hazard_zones: hz.draw(cam_x,cam_y)
            for g  in gems:          g.draw(cam_x,cam_y)
            for it in dropped_items: it.draw(cam_x,cam_y)
            for ch in chests:        ch.draw(cam_x,cam_y)
            for e  in enemies:       e.draw(cam_x,cam_y)
            if boss_active:          boss.draw(cam_x,cam_y)
            for b  in bullets:       draw_bullet(b,cam_x,cam_y)
            for eb in enemy_bullets: draw_bullet(eb,cam_x,cam_y)
            update_draw_particles(cam_x,cam_y)
            player.draw(cam_x,cam_y)
            draw_hud(player)
            draw_equipment_hud(player)
            draw_minimap(player,enemies,boss if boss_active else None,gems,chests,cam_x,cam_y)
            if boss_active: draw_boss_hud(boss)
            pygame.display.flip()

        if quit_to_menu: continue   # wróć do głównej pętli bez game over
        if not show_game_over(player.level,kill_count): break

if __name__=="__main__":
    main()