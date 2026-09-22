import pygame
import random
import os
import math
import sys
import json
from supabase import create_client, Client

# ==========================================
# 1. SUPABASE CONNECTION CONFIGURATION
# ==========================================
SUPABASE_URL = "https://fidqfllnzxjcdpaiuykb.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZpZHFmbGxuenhqY2RwYWl1eWtiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTAwMzUyMTIsImV4cCI6MjEwNTYxMTIxMn0.cKxT0xcLg4jxDl_6PYwXsysWhDG_Q8h7YjlJ0rKFYNc"  # Paste your long eyJ... key here

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"Supabase connection initialization failed: {e}")
    supabase = None

# ==========================================
# 2. PYGAME & AUDIO INITIALIZATION
# ==========================================
pygame.init()
try:
    pygame.mixer.init()
    pygame.mixer.music.load('Spaceship-Game-BGM.mp3')
    pygame.mixer.music.set_volume(0.8)
    pygame.mixer.music.play(-1)
except Exception as e:
    print(f"Audio/Music error: {e}")

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Space Shooter: Ultimate Edition")

font = pygame.font.SysFont("Arial", 20)
large_font = pygame.font.SysFont("Arial", 48)

def safe_load_sound(filepath):
    try:
        return pygame.mixer.Sound(filepath)
    except Exception:
        return pygame.mixer.Sound(buffer=bytes([0] * 44))

explosion_sound = safe_load_sound('ExplosionSoundEffect.mp3')
levelup_sound = safe_load_sound('LevelUp.mp3')
heal_sound = safe_load_sound('HealSound.mp3')
shield_sound = safe_load_sound('ShieldSound.mp3')
laser_sound = safe_load_sound('LaserSoundEffect.mp3')
bought_sound = safe_load_sound('CashSound.mp3')
tank_shoot_sound = safe_load_sound('Tank-Shoots.mp3')

reload_sounds = [
    safe_load_sound('GunReloadSound1.mp3'),
    safe_load_sound('GunReloadSound2.mp3'),
    safe_load_sound('GunReloadSound3.mp3')
]

explosion_sound.set_volume(0.5)
laser_sound.set_volume(0.25)
tank_shoot_sound.set_volume(0.4)
shield_sound.set_volume(1.5)

# ==========================================
# 3. ASSET LOADING
# ==========================================
def load_and_scale(filename, width, height):
    try:
        img = pygame.image.load(filename).convert_alpha()
        return pygame.transform.scale(img, (width, height))
    except FileNotFoundError:
        surf = pygame.Surface((width, height), pygame.SRCALPHA)
        pygame.draw.polygon(surf, (0, 191, 255), [(width//2, 0), (0, height), (width, height)])
        return surf

picture_ship = load_and_scale("SpaceShip-Blue.png", 65, 70)
picture_missile = load_and_scale("Missile-Picture.png", 15, 30)
picture_enemy = load_and_scale("enemies.tiff", 20, 20)
picture_tank = load_and_scale("enemies-tank.png", 60, 60)

raw_boss = load_and_scale("boss-picture.png", 140, 120)
picture_boss = pygame.transform.rotate(raw_boss, 180)

raw_boss_missile = load_and_scale("boss-missile.png", 40, 80)
picture_boss_missile = pygame.transform.rotate(raw_boss_missile, 270)

# ==========================================
# 4. DATABASE & AUTH HELPERS
# ==========================================
SCORE_FILE = "highscore.json"
leaderboard = []

auth_mode = "LOGIN"  # "LOGIN" or "REGISTER"
auth_active_field = "username" # "username", "password", or "email"
input_username = ""
input_password = ""
input_email = ""
auth_message = ""
logged_in_user = None
user_best_score = 0

def load_leaderboard():
    global leaderboard
    leaderboard = []
    if supabase is not None:
        try:
            response = supabase.table("Player Info").select("high_score, username, level").order("high_score", desc=True).limit(5).execute()
            if response.data:
                for row in response.data:
                    u_name = row.get("username") or "Player"
                    u_score = int(row.get("high_score") or 0)
                    u_lvl = int(row.get("level") or 1)
                    leaderboard.append([u_score, u_name, u_lvl])
                return
        except Exception as e:
            print(f"Supabase fetch error: {e}")

    leaderboard.sort(key=lambda x: x[0], reverse=True)
    leaderboard = leaderboard[:5]

def handle_register():
    global auth_message, logged_in_user, game_state, user_best_score
    if not input_username or not input_password:
        auth_message = "Error: Username and Password required!"
        return
    if supabase is None:
        auth_message = "Error: Database offline."
        return

    try:
        # Check if username exists
        existing = supabase.table("Player Info").select("*").eq("username", input_username).execute()
        if existing.data and len(existing.data) > 0:
            auth_message = "Error: Username already exists!"
            return

        # Insert new player
        res = supabase.table("Player Info").insert({
            "username": input_username,
            "password": input_password,
            "email": input_email,
            "high_score": 0,
            "score": 0,
            "level": 1
        }).execute()

        logged_in_user = input_username
        user_best_score = 0
        auth_message = "Account Created! Welcome!"
        reset_game()
        game_state = "PLAYING"
    except Exception as e:
        auth_message = f"Registration Error: {str(e)[:30]}"

def handle_login():
    global auth_message, logged_in_user, game_state, user_best_score
    if not input_username or not input_password:
        auth_message = "Error: Username and Password required!"
        return
    if supabase is None:
        auth_message = "Error: Database offline."
        return

    try:
        res = supabase.table("Player Info").select("*").eq("username", input_username).eq("password", input_password).execute()
        if res.data and len(res.data) > 0:
            player_data = res.data[0]
            logged_in_user = player_data.get("username")
            user_best_score = int(player_data.get("high_score") or 0)
            auth_message = "Login successful!"
            reset_game()
            game_state = "PLAYING"
        else:
            auth_message = "Error: Invalid credentials!"
    except Exception as e:
        auth_message = f"Login Error: {str(e)[:30]}"

def update_user_score_in_supabase(final_score, level_reached):
    global user_best_score, logged_in_user
    if supabase is None or not logged_in_user:
        return

    new_high = max(user_best_score, final_score)
    user_best_score = new_high

    try:
        supabase.table("Player Info").update({
            "score": final_score,
            "high_score": new_high,
            "level": level_reached
        }).eq("username", logged_in_user).execute()
        load_leaderboard()
    except Exception as e:
        print(f"Failed to update score: {e}")

load_leaderboard()

# ==========================================
# 5. GAME STATE SETUP
# ==========================================
stars_back = [[random.randint(0, SCREEN_WIDTH), random.randint(0, SCREEN_HEIGHT), random.uniform(0.4, 0.8)] for _ in range(30)]
stars_mid = [[random.randint(0, SCREEN_WIDTH), random.randint(0, SCREEN_HEIGHT), random.uniform(1.2, 1.8)] for _ in range(20)]
stars_fore = [[random.randint(0, SCREEN_WIDTH), random.randint(0, SCREEN_HEIGHT), random.uniform(2.5, 3.5)] for _ in range(10)]

game_state = "AUTH"  # "AUTH", "PLAYING", "PAUSED", "SHOP", "GAMEOVER"
score = 0
player_health = 3.0       
player_max_health = 5.0   
ship_x = 350
ship_y = 400
ship_speed = 5
shield_count = 0
dual_shot_timer = 0
trio_shot_timer = 0
fire_cooldown = 0

cheat_100_bullets = False
cheat_godmode = False
cheat_money = False
saved_speed = 5
saved_missile_speed = 7

dodge_timer = 0
dodge_cooldown = 0
speed_boost_timer = 0
speed_boost_cooldown = 0

combo_count = 0
combo_timer = 0
combo_multiplier = 1.0

perm_shot_tier = 1
WEAPON_UPGRADE_COSTS = {2: 1000, 3: 2500, 4: 5000, 5: 10000, 6: 20000}
WEAPON_TIER_NAMES = {
    1: "Single Shot",
    2: "Permanent Dual Shot",
    3: "Permanent Trio Shot",
    4: "Permanent Quad Shot",
    5: "Permanent Penta Shot",
    6: "Permanent Hexa Shot"
}

current_mission = "NONE"
mission_desc = ""
mission_progress = 0
mission_start_score = 0
laser_storm_hit_taken = False

def select_new_mission():
    global current_mission, mission_desc, mission_progress, mission_start_score, laser_storm_hit_taken, score, anomaly_type
    missions = [
        ("SHIELD_HOARDER", "Hold 2 Shields at once"),
        ("SNIPER", "Defeat 3 Tanks"),
        ("COLLECTOR", "Collect 3 powerups in a level"),
        ("BOSS_HUNTER", "Hit the boss 10 times"),
        ("TANK_BUSTER", "Defeat 5 Tanks total"),
        ("METEOR_SURVIVOR", "Survive laser storm anomaly cleanly"),
        ("SCORE_CHASER", "Gain 500 points in this mission loop"),
        ("ULTIMATE_USER", "Fire your Ultimate Beam weapon")
    ]
    valid_missions = [m for m in missions if not (m[0] == "BOSS_HUNTER" and level % 10 != 0)]
    if not valid_missions:
        valid_missions = [m for m in missions if m[0] != "BOSS_HUNTER"]

    current_mission, mission_desc = random.choice(valid_missions)
    mission_progress = 0
    mission_start_score = score
    laser_storm_hit_taken = False
    
    if current_mission == "METEOR_SURVIVOR":
        anomaly_type = "LASER_STORM"
        trigger_laser_storm()

anomaly_type = "NONE" 
laser_storm_projectiles = [] 
laser_storm_duration = 0

ultimate_charge = 100 
ultimate_active_timer = 0 
q_mode_active = False

level = 1
score_needed_for_next_level = 100
level_speed_multiplier = 0.0  

is_boss_stage = False
boss_spawned = False
bosses = []

missiles = []
player_missile_speed = 7
boss_missiles = []
boss_missile_speed_base = 5

enemies = []
tanks = []
powerups = []
particles = []
floating_texts = []  

shake_intensity = 0
shake_timer = 0
powerup_speed = 3

clock = pygame.time.Clock()

def add_score(pts):
    global score, combo_count, combo_timer, combo_multiplier
    combo_count += 1
    combo_timer = 120  
    if combo_count >= 10:
        combo_multiplier = 2.5
    elif combo_count >= 5:
        combo_multiplier = 2.0
    elif combo_count >= 3:
        combo_multiplier = 1.5
    else:
        combo_multiplier = 1.0

    earned = int(pts * combo_multiplier)
    score += earned
    return earned

def spawn_floating_text(x, y, text, color=(255, 215, 0)):
    floating_texts.append([x, y, text, color, 40])  

def draw_pixel_heart(surface, x, y, size=20, full=True, half=False):
    heart_surf = pygame.Surface((18, 18), pygame.SRCALPHA)
    color = (255, 0, 0) if full or half else (60, 60, 60)
    
    pygame.draw.rect(heart_surf, color, (2, 4, 4, 4))
    pygame.draw.rect(heart_surf, color, (4, 2, 4, 4))
    pygame.draw.rect(heart_surf, color, (12, 4, 4, 4))
    pygame.draw.rect(heart_surf, color, (10, 2, 4, 4))
    pygame.draw.rect(heart_surf, color, (2, 8, 14, 4))
    pygame.draw.rect(heart_surf, color, (4, 12, 10, 2))
    pygame.draw.rect(heart_surf, color, (6, 14, 6, 2))
    pygame.draw.rect(heart_surf, color, (8, 16, 2, 2))
    
    if half:
        gray_color = (60, 60, 60)
        pygame.draw.rect(heart_surf, gray_color, (9, 2, 7, 4))
        pygame.draw.rect(heart_surf, gray_color, (9, 8, 7, 4))
        pygame.draw.rect(heart_surf, gray_color, (9, 12, 5, 2))
        pygame.draw.rect(heart_surf, gray_color, (9, 14, 3, 2))
        pygame.draw.rect(heart_surf, gray_color, (9, 16, 1, 2))
        
    scaled_heart = pygame.transform.scale(heart_surf, (size, size))
    surface.blit(scaled_heart, (x, y))

def get_random_scout(hp=1.0):
    speed_bonus = level_speed_multiplier
    roll = random.random()
    if roll < 0.35:  
        enemy_x = random.randint(50, SCREEN_WIDTH - 50)
        enemy_y = random.randint(-150, -50)
        speed_x = 0
        speed_y = random.randint(3, 5) + speed_bonus
        type_str = "SINE"
    elif roll < 0.70:  
        enemy_x = random.choice([-20, SCREEN_WIDTH + 20])
        enemy_y = random.randint(50, 300)
        speed_x = random.randint(3, 6) + speed_bonus
        if enemy_x > 0:
            speed_x = -speed_x
        speed_y = 0
        type_str = "STANDARD"
    else:  
        enemy_x = random.randint(0, SCREEN_WIDTH - 20)
        enemy_y = random.randint(-150, -50)
        speed_x = 0
        speed_y = random.randint(4, 7) + speed_bonus
        type_str = "STANDARD"
    return [enemy_x, enemy_y, speed_x, speed_y, type_str, 0, hp]  

def trigger_laser_storm():
    global laser_storm_projectiles, laser_storm_duration, laser_storm_hit_taken
    laser_storm_projectiles = []
    laser_storm_duration = 400  
    if current_mission == "METEOR_SURVIVOR":
        laser_storm_hit_taken = False
    for _ in range(15):
        lx = random.randint(100, SCREEN_WIDTH - 100)
        ly = random.randint(-200, -50)
        lvx = random.uniform(-4, 4)
        lvy = random.uniform(4, 7)
        laser_storm_projectiles.append([lx, ly, lvx, lvy])

def spawn_standard_enemies():
    global enemies, tanks, anomaly_type
    count = 6
    hp_multiplier = 1.0

    enemies = [get_random_scout(hp=hp_multiplier) for _ in range(count)]

    tanks = []
    for _ in range(2):
        tank_x = random.randint(0, SCREEN_WIDTH - 60)
        tank_y = random.randint(-500, -100)
        tank_speed = random.randint(1, 3) + level_speed_multiplier
        tank_health = 3 * hp_multiplier
        tank_fire_timer = 0
        tanks.append([tank_x, tank_y, tank_speed, tank_health, tank_fire_timer])
        
    if level % 10 != 0: 
        if random.random() < 0.15 and current_mission != "METEOR_SURVIVOR":
            anomaly_type = random.choice(["WORMHOLE", "LASER_STORM"])
            if anomaly_type == "LASER_STORM":
                trigger_laser_storm()
        elif current_mission != "METEOR_SURVIVOR":
            anomaly_type = "NONE"

def reset_game():
    global score, player_health, ship_x, ship_y, shield_count, dual_shot_timer, trio_shot_timer, ship_speed
    global missiles, boss_missiles, enemies, tanks, powerups, particles, shake_intensity, shake_timer
    global level, score_needed_for_next_level, level_speed_multiplier, is_boss_stage, boss_spawned, bosses
    global ultimate_charge, ultimate_active_timer, q_mode_active, anomaly_type, laser_storm_projectiles, perm_shot_tier, player_missile_speed
    global dodge_timer, dodge_cooldown, speed_boost_timer, speed_boost_cooldown, combo_count, combo_timer, combo_multiplier, floating_texts
    global cheat_100_bullets, cheat_godmode, cheat_money, saved_speed, saved_missile_speed
    
    cheat_100_bullets = False
    cheat_godmode = False
    cheat_money = False
    
    score = 0
    player_health = 3.0  
    ship_x = 350
    ship_y = 400
    ship_speed = 5  
    player_missile_speed = 7
    saved_speed = 5
    saved_missile_speed = 7
    perm_shot_tier = 1 
    shield_count = 0
    dual_shot_timer = 0
    trio_shot_timer = 0
    ultimate_charge = 100
    ultimate_active_timer = 0
    q_mode_active = False
    dodge_timer = 0
    dodge_cooldown = 0
    speed_boost_timer = 0
    speed_boost_cooldown = 0
    combo_count = 0
    combo_timer = 0
    combo_multiplier = 1.0
    
    anomaly_type = "NONE"
    laser_storm_projectiles = []
    missiles = []
    boss_missiles = []
    bosses = []
    powerups = []
    particles = []
    floating_texts = []
    shake_intensity = 0
    shake_timer = 0
    
    level = 1
    score_needed_for_next_level = 100
    level_speed_multiplier = 0.0
    is_boss_stage = False
    boss_spawned = False

    select_new_mission()
    spawn_standard_enemies()

def trigger_shake(duration, intensity):
    global shake_timer, shake_intensity
    shake_timer = duration
    shake_intensity = intensity

def spawn_explosion(x, y, count=15, color_set=None):
    explosion_sound.play()  
    if color_set is None:
        color_set = [(255, 69, 0), (255, 140, 0), (255, 215, 0)]
    for _ in range(count):
        p_x = x
        p_y = y
        p_vx = random.uniform(-4, 4)
        p_vy = random.uniform(-4, 4)
        p_life = random.randint(20, 40)
        p_color = random.choice(color_set)
        particles.append([p_x, p_y, p_vx, p_vy, p_life, p_color])

def fire_missiles():
    laser_sound.play()  
    if q_mode_active or cheat_100_bullets:
        for i in range(50):
            vx = random.uniform(-12, 12)
            vy = -random.uniform(5, player_missile_speed + 5)
            missiles.append([ship_x + 25, ship_y, vx, vy])
        return

    temp_boost = 1
    if trio_shot_timer > 0:
        temp_boost = 3
    elif dual_shot_timer > 0:
        temp_boost = 2
    
    active_tier = max(perm_shot_tier, temp_boost)
    
    if active_tier == 1:
        missiles.append([ship_x + 25, ship_y, 0, -player_missile_speed])
    elif active_tier == 2:
        missiles.append([ship_x + 10, ship_y, 0, -player_missile_speed])
        missiles.append([ship_x + 40, ship_y, 0, -player_missile_speed])
    elif active_tier == 3:
        missiles.append([ship_x + 25, ship_y, 0, -player_missile_speed])
        missiles.append([ship_x + 10, ship_y, -2, -player_missile_speed])
        missiles.append([ship_x + 40, ship_y, 2, -player_missile_speed])
    elif active_tier == 4:
        missiles.append([ship_x + 15, ship_y, -1, -player_missile_speed])
        missiles.append([ship_x + 35, ship_y, 1, -player_missile_speed])
        missiles.append([ship_x + 5, ship_y, -3, -player_missile_speed])
        missiles.append([ship_x + 45, ship_y, 3, -player_missile_speed])
    elif active_tier == 5:
        missiles.append([ship_x + 25, ship_y, 0, -player_missile_speed])
        missiles.append([ship_x + 15, ship_y, -2, -player_missile_speed])
        missiles.append([ship_x + 35, ship_y, 2, -player_missile_speed])
        missiles.append([ship_x + 5, ship_y, -4, -player_missile_speed])
        missiles.append([ship_x + 45, ship_y, 4, -player_missile_speed])
    elif active_tier >= 6: 
        missiles.append([ship_x + 15, ship_y, -1, -player_missile_speed])
        missiles.append([ship_x + 35, ship_y, 1, -player_missile_speed])
        missiles.append([ship_x + 5, ship_y, -3, -player_missile_speed])
        missiles.append([ship_x + 45, ship_y, 3, -player_missile_speed])
        missiles.append([ship_x - 5, ship_y, -5, -player_missile_speed])
        missiles.append([ship_x + 55, ship_y, 5, -player_missile_speed])

# ==========================================
# 6. MAIN GAME LOOP
# ==========================================
Game_Activated = True
while Game_Activated:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            Game_Activated = False
            
        elif event.type == pygame.KEYDOWN:
            if game_state == "AUTH":
                if event.key == pygame.K_TAB:
                    # Cycle active field
                    if auth_mode == "LOGIN":
                        auth_active_field = "password" if auth_active_field == "username" else "username"
                    else:
                        fields = ["username", "password", "email"]
                        idx = fields.index(auth_active_field)
                        auth_active_field = fields[(idx + 1) % len(fields)]
                        
                elif event.key == pygame.K_UP or event.key == pygame.K_DOWN:
                    # Toggle between Login / Register mode
                    auth_mode = "REGISTER" if auth_mode == "LOGIN" else "LOGIN"
                    auth_message = f"Switched to {auth_mode} mode."
                    
                elif event.key == pygame.K_RETURN:
                    if auth_mode == "LOGIN":
                        handle_login()
                    else:
                        handle_register()
                        
                elif event.key == pygame.K_BACKSPACE:
                    if auth_active_field == "username":
                        input_username = input_username[:-1]
                    elif auth_active_field == "password":
                        input_password = input_password[:-1]
                    elif auth_active_field == "email":
                        input_email = input_email[:-1]
                else:
                    if event.unicode.isprintable() and len(event.unicode) > 0:
                        if auth_active_field == "username" and len(input_username) < 15:
                            input_username += event.unicode
                        elif auth_active_field == "password" and len(input_password) < 20:
                            input_password += event.unicode
                        elif auth_active_field == "email" and len(input_email) < 30:
                            input_email += event.unicode

            elif event.key == pygame.K_ESCAPE and game_state in ["PLAYING", "PAUSED"]:
                game_state = "PAUSED" if game_state == "PLAYING" else "PLAYING"

            elif game_state in ["PLAYING", "SHOP"]:
                if event.key == pygame.K_p:
                    cheat_godmode = not cheat_godmode
                    if cheat_godmode:
                        saved_speed = ship_speed
                        saved_missile_speed = player_missile_speed
                        ship_speed = 20
                        player_missile_speed = 25
                        player_health = player_max_health
                        shield_count = 2
                    else:
                        ship_speed = saved_speed
                        player_missile_speed = saved_missile_speed
                elif event.key == pygame.K_o:
                    cheat_money = not cheat_money
                        
            elif game_state == "GAMEOVER":
                if event.key == pygame.K_r:
                    reset_game()
                    game_state = "PLAYING"
                    
            elif game_state == "SHOP":
                if event.key == pygame.K_1: 
                    if score >= 150:
                        score -= 150
                        ship_speed += 1
                        saved_speed += 1
                        bought_sound.play()  
                elif event.key == pygame.K_2: 
                    if score >= 100 and shield_count < 2:
                        score -= 100
                        shield_count += 1
                        shield_sound.play()  
                        bought_sound.play()
                        if current_mission == "SHIELD_HOARDER" and shield_count == 2:
                            score += 300
                            select_new_mission()
                elif event.key == pygame.K_3: 
                    if score >= 120 and player_health < player_max_health:
                        score -= 120
                        player_health = min(player_max_health, player_health + 1.0)
                        heal_sound.play()    
                        bought_sound.play()  
                elif event.key == pygame.K_4: 
                    if score >= 150:
                        score -= 150
                        bought_sound.play()  
                elif event.key == pygame.K_5: 
                    if score >= 250:
                        score -= 250
                        player_missile_speed += 1
                        saved_missile_speed += 1
                        bought_sound.play()  
                elif event.key == pygame.K_6: 
                    next_tier = perm_shot_tier + 1
                    if next_tier in WEAPON_UPGRADE_COSTS:
                        needed_score = WEAPON_UPGRADE_COSTS[next_tier]
                        if score >= needed_score:
                            score -= needed_score
                            perm_shot_tier = next_tier
                            bought_sound.play()  
                            
                            if next_tier == 2:
                                reload_sounds[0].play()
                            elif next_tier == 3:
                                reload_sounds[0].play()
                                reload_sounds[1].play()
                            else:
                                reload_sounds[0].play()
                                reload_sounds[1].play()
                                reload_sounds[2].play()
                elif event.key == pygame.K_RETURN: 
                    level += 1
                    level_speed_multiplier += 0.2
                    score_needed_for_next_level = score + 150
                    is_boss_stage = False
                    boss_spawned = False
                    bosses = []
                    boss_missiles = []
                    spawn_standard_enemies()
                    game_state = "PLAYING"
                    
            elif game_state == "PLAYING":
                if event.key == pygame.K_c:
                    if dodge_cooldown <= 0:
                        dodge_timer = 20  
                        dodge_cooldown = 120  
                        shield_sound.play()

                elif event.key == pygame.K_v or event.key == pygame.K_LCTRL:
                    if speed_boost_cooldown <= 0:
                        speed_boost_timer = 180  
                        speed_boost_cooldown = 360  
                        bought_sound.play()

                elif event.key == pygame.K_q:
                    q_mode_active = not q_mode_active

                elif event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
                    if ultimate_active_timer == 0:
                        ultimate_active_timer = 120 
                        trigger_shake(120, 10)
                        
                        if current_mission == "ULTIMATE_USER":
                            score += 300
                            select_new_mission()
            
    ultimate_charge = 100

    if cheat_godmode:
        player_health = player_max_health
        shield_count = 2
    if cheat_money:
        score += 9999

    if game_state == "PLAYING":
        if fire_cooldown > 0:
            fire_cooldown -= 1

        if dodge_timer > 0:
            dodge_timer -= 1
        if dodge_cooldown > 0:
            dodge_cooldown -= 1

        if speed_boost_timer > 0:
            speed_boost_timer -= 1
        if speed_boost_cooldown > 0:
            speed_boost_cooldown -= 1

        if combo_timer > 0:
            combo_timer -= 1
            if combo_timer <= 0:
                combo_count = 0
                combo_multiplier = 1.0

        current_spd = ship_speed
        if speed_boost_timer > 0:
            current_spd *= 2
        if dodge_timer > 0:
            current_spd *= 1.8  

        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            ship_x -= current_spd
        if keys[pygame.K_RIGHT]:
            ship_x += current_spd
        if keys[pygame.K_UP]:
            ship_y -= current_spd
        if keys[pygame.K_DOWN]:
            ship_y += current_spd
            
        if keys[pygame.K_SPACE] and fire_cooldown <= 0:
            fire_missiles()
            fire_cooldown = 10 if not (q_mode_active or cheat_100_bullets) else 5
            
        max_bottom_y = SCREEN_HEIGHT + 250 - 70 
        
        if anomaly_type == "WORMHOLE":
            if ship_x < -40:
                ship_x = SCREEN_WIDTH - 25
                spawn_explosion(ship_x, ship_y, count=6, color_set=[(147, 112, 219), (0, 255, 255)])
            elif ship_x > SCREEN_WIDTH + 15:
                ship_x = -15
                spawn_explosion(ship_x, ship_y, count=6, color_set=[(147, 112, 219), (0, 255, 255)])
            if ship_y < -40:
                ship_y = max_bottom_y - 10
                spawn_explosion(ship_x, ship_y, count=6, color_set=[(147, 112, 219), (0, 255, 255)])
            elif ship_y > max_bottom_y + 20:
                ship_y = 0
                spawn_explosion(ship_x, ship_y, count=6, color_set=[(147, 112, 219), (0, 255, 255)])
        else:
            ship_x = max(0, min(ship_x, SCREEN_WIDTH - 65))
            ship_y = max(0, min(ship_y, max_bottom_y))

        if random.random() < 0.6:
            p_color = (0, 255, 255) if speed_boost_timer > 0 else (255, 140, 0)
            particles.append([ship_x + 32, ship_y + 65, random.uniform(-1, 1), random.uniform(2, 5), 15, p_color])

    for star in stars_back:
        star[1] += star[2] + level_speed_multiplier * 0.3
        if star[1] > SCREEN_HEIGHT:
            star[0] = random.randint(0, SCREEN_WIDTH)
            star[1] = 0
            
    for star in stars_mid:
        star[1] += star[2] + level_speed_multiplier * 0.6
        if star[1] > SCREEN_HEIGHT:
            star[0] = random.randint(0, SCREEN_WIDTH)
            star[1] = 0
            
    for star in stars_fore:
        star[1] += star[2] + level_speed_multiplier * 1.0
        if star[1] > SCREEN_HEIGHT:
            star[0] = random.randint(0, SCREEN_WIDTH)
            star[1] = 0

    if game_state == "PLAYING":
        if not is_boss_stage and len(enemies) == 0:
            spawn_standard_enemies()
        
        if current_mission == "SCORE_CHASER":
            if score - mission_start_score >= 500:
                score += 300
                select_new_mission()

        if level % 10 == 0:
            is_boss_stage = True
            if not boss_spawned:
                bosses = []
                num_bosses = level // 10  
                boss_max_hp = 20 + num_bosses * 15
                boss_spd = 2 + level_speed_multiplier
                
                for idx in range(num_bosses):
                    target_stop_y = min(280, 50 + (idx * 65))
                    start_x = (SCREEN_WIDTH // (num_bosses + 1)) * (idx + 1) - 60
                    bosses.append({
                        "x": start_x,
                        "y": -150 - (idx * 100),
                        "target_y": target_stop_y,
                        "hp": boss_max_hp,
                        "max_hp": boss_max_hp,
                        "speed": boss_spd,
                        "dir": 1 if idx % 2 == 0 else -1,
                        "fire_timer": 0,
                        "pattern_angle": 0.0
                    })
                
                boss_spawned = True
                enemies = []
                tanks = []
                boss_missiles = []
        else:
            is_boss_stage = False
            boss_spawned = False
            bosses = []
            
            if score >= score_needed_for_next_level:
                level += 1
                level_speed_multiplier += 0.2
                score_needed_for_next_level += 150
                levelup_sound.play()  
                spawn_standard_enemies() 

        if ultimate_active_timer > 0:
            ultimate_active_timer -= 1

            beam_rect = pygame.Rect(ship_x - 15, 0, 95, ship_y)
            beam_damage = 1.5 if q_mode_active else 0.5
            
            enemies_to_remove = []
            for enemy in enemies:
                enemy_rect = pygame.Rect(enemy[0], enemy[1], 20, 20)
                if beam_rect.colliderect(enemy_rect):
                    enemy[6] -= beam_damage
                    if enemy[6] <= 0:
                        spawn_explosion(enemy[0]+10, enemy[1]+10, count=15)
                        pts = add_score(10)
                        spawn_floating_text(enemy[0], enemy[1], f"+{pts}")
                        if enemy not in enemies_to_remove:
                            enemies_to_remove.append(enemy)

            for enemy in enemies_to_remove:
                if enemy in enemies:
                    enemies.remove(enemy)
                    enemies.append(get_random_scout(hp=1.0))
                    
            tanks_to_remove = []
            for tank in tanks:
                tank_rect = pygame.Rect(tank[0], tank[1], 60, 60)
                if beam_rect.colliderect(tank_rect):
                    tank[3] -= beam_damage
                    if tank[3] <= 0:
                        spawn_explosion(tank[0]+30, tank[1]+30, count=25)
                        pts = add_score(50)
                        spawn_floating_text(tank[0], tank[1], f"+{pts}")
                        if tank not in tanks_to_remove:
                            tanks_to_remove.append(tank)
                    
                        if current_mission == "SNIPER":
                            mission_progress += 1
                            if mission_progress >= 3:
                                score += 300
                                select_new_mission()
                        if current_mission == "TANK_BUSTER":
                            mission_progress += 1
                            if mission_progress >= 5:
                                score += 350
                                select_new_mission()

            for tank in tanks_to_remove:
                if tank in tanks:
                    tanks.remove(tank)
                            
            if is_boss_stage and boss_spawned:
                for b in bosses[:]:
                    if b in bosses:
                        b_rect = pygame.Rect(b["x"], b["y"], 120, 120)
                        if beam_rect.colliderect(b_rect):
                            b["hp"] -= beam_damage 
                            spawn_explosion(b["x"] + 60, b["y"] + 110, count=2, color_set=[(0, 255, 0), (255, 255, 255)])
                            
                            if current_mission == "BOSS_HUNTER":
                                mission_progress += 1
                                if mission_progress >= 10:
                                    score += 400
                                    select_new_mission()
                                    
                            if b["hp"] <= 0 and b in bosses:
                                spawn_explosion(b["x"] + 60, b["y"] + 60, count=60)
                                pts = add_score(500)
                                spawn_floating_text(b["x"] + 40, b["y"], f"+{pts}")
                                bosses.remove(b)
                                if len(bosses) == 0:
                                    game_state = "SHOP"

        for missile in missiles[:]:
            missile[0] += missile[2]
            missile[1] += missile[3]
            if missile[1] < -30 or missile[0] < -30 or missile[0] > SCREEN_WIDTH + 30:
                missiles.remove(missile)
                
        for bm in boss_missiles[:]:
            bm[0] += bm[2]
            bm[1] += bm[3]
            if bm[1] > SCREEN_HEIGHT + 40 or bm[0] < -40 or bm[0] > SCREEN_WIDTH + 40:
                boss_missiles.remove(bm)

        if anomaly_type == "LASER_STORM":
            laser_storm_duration -= 1
            if laser_storm_duration <= 0:
                anomaly_type = "NONE"
                laser_storm_projectiles = []
                if current_mission == "METEOR_SURVIVOR":
                    if not laser_storm_hit_taken:
                        score += 400
                        spawn_floating_text(ship_x, ship_y, "+400 MISSION BONUS!", (0, 255, 0))
                    select_new_mission()
            else:
                for lp in laser_storm_projectiles[:]:
                    lp[0] += lp[2]
                    lp[1] += lp[3]
                    if lp[1] > SCREEN_HEIGHT + 20 or lp[0] < -20 or lp[0] > SCREEN_WIDTH + 20:
                        lp[0] = random.randint(50, SCREEN_WIDTH - 50)
                        lp[1] = random.randint(-150, -30)
                        lp[2] = random.uniform(-4, 4)
                        lp[3] = random.uniform(4, 7)

        if not is_boss_stage:
            for enemy in enemies[:]:
                if enemy[4] == "SINE":
                    enemy[5] += 0.1
                    enemy[0] += math.sin(enemy[5]) * 4
                    enemy[1] += enemy[3]
                else:
                    enemy[0] += enemy[2]
                    enemy[1] += enemy[3]
                
                off_left = enemy[2] < 0 and enemy[0] < -30
                off_right = enemy[2] > 0 and enemy[0] > SCREEN_WIDTH + 30
                off_bottom = enemy[1] > SCREEN_HEIGHT + 250
                
                if off_left or off_right or off_bottom:
                    enemies.remove(enemy)
                    enemies.append(get_random_scout(hp=1.0))

            for tank in tanks:
                tank[1] += tank[2]
                
                tank[4] += 1
                if tank[4] >= 90 and tank[1] > 0:
                    tank[4] = 0
                    boss_missiles.append([tank[0] + 10, tank[1] + 60, 0, 6 + level_speed_multiplier])
                    tank_shoot_sound.play()

                if tank[1] > SCREEN_HEIGHT + 250:
                    tank[0] = random.randint(0, SCREEN_WIDTH - 60)
                    tank[1] = random.randint(-300, -100)
                    tank[2] = random.randint(1, 3) + level_speed_multiplier
                    tank[3] = 3
                    tank[4] = 0
                    
        else:
            if boss_spawned:
                for b in bosses:
                    if b["y"] < b["target_y"]:
                        b["y"] += 2
                    else:
                        b["x"] += b["speed"] * b["dir"]
                        if b["x"] <= 20 or b["x"] >= SCREEN_WIDTH - 140:
                            b["dir"] *= -1
                            
                    b["fire_timer"] += 1
                    if b["fire_timer"] >= 60: 
                        b["fire_timer"] = 0
                        b_center_x = b["x"] + 60
                        
                        b["pattern_angle"] += 0.2
                        b_missile_spd = boss_missile_speed_base + level_speed_multiplier
                        
                        num_missiles = 25
                        for offset in range(num_missiles):
                            ang = b["pattern_angle"] + (offset * (2 * math.pi / num_missiles))
                            vx = math.cos(ang) * b_missile_spd
                            vy = math.sin(ang) * b_missile_spd
                            boss_missiles.append([b_center_x - 20, b["y"] + 60, vx, vy])

        for powerup in powerups[:]:
            powerup[1] += powerup_speed
            if powerup[1] > SCREEN_HEIGHT + 250:
                powerups.remove(powerup)

        if dual_shot_timer > 0:
            dual_shot_timer -= 1
        if trio_shot_timer > 0:
            trio_shot_timer -= 1
                
        ship_rect = pygame.Rect(ship_x, ship_y, 65, 70)
        is_invincible = (dodge_timer > 0) or cheat_godmode
        
        for enemy in enemies[:]:
            enemy_rect = pygame.Rect(enemy[0], enemy[1], 20, 20)
            
            if ship_rect.colliderect(enemy_rect):
                spawn_explosion(enemy[0] + 10, enemy[1] + 10, count=10)
                if not is_invincible:
                    if shield_count > 0:
                        shield_count -= 1
                        trigger_shake(10, 5)
                    else:
                        player_health -= 0.5
                        trigger_shake(20, 10)
                enemies.remove(enemy)
                if not is_boss_stage:
                    enemies.append(get_random_scout(hp=1.0))
                
            for missile in missiles[:]:
                missile_rect = pygame.Rect(missile[0], missile[1], 15, 30)
                if missile_rect.colliderect(enemy_rect):
                    if missile in missiles:
                        missiles.remove(missile)
                    enemy[6] -= 1.0
                    spawn_explosion(enemy[0] + 10, enemy[1] + 10, count=5)
                    trigger_shake(8, 3)
                    if enemy[6] <= 0:
                        pts = add_score(10)
                        spawn_floating_text(enemy[0], enemy[1], f"+{pts}")
                        
                        if random.random() < 0.25:
                            p_type = random.choice(["shield", "dual", "trio", "health"])
                            powerups.append([enemy[0], enemy[1], p_type])
                        
                        if enemy in enemies:
                            enemies.remove(enemy)

        if not is_boss_stage:
            for tank in tanks[:]:
                tank_rect = pygame.Rect(tank[0], tank[1], 60, 60)
                
                if ship_rect.colliderect(tank_rect):
                    spawn_explosion(tank[0] + 30, tank[1] + 30, count=25)
                    if not is_invincible:
                        if shield_count > 0:
                            shield_count -= 1
                            trigger_shake(15, 8)
                        else:
                            player_health -= 1.0
                            trigger_shake(35, 20)
                    tanks.remove(tank)
                    
                for missile in missiles[:]:
                    missile_rect = pygame.Rect(missile[0], missile[1], 15, 30)
                    if missile_rect.colliderect(tank_rect):
                        if missile in missiles:
                            missiles.remove(missile)
                        tank[3] -= 1
                        spawn_explosion(missile[0], missile[1], count=5)
                        trigger_shake(5, 2)
                        if tank[3] <= 0:
                            spawn_explosion(tank[0] + 30, tank[1] + 30, count=25)
                            trigger_shake(20, 12)
                            pts = add_score(50)
                            spawn_floating_text(tank[0], tank[1], f"+{pts}")
                            
                            if current_mission == "SNIPER":
                                mission_progress += 1
                                if mission_progress >= 3:
                                    score += 300
                                    select_new_mission()
                            if current_mission == "TANK_BUSTER":
                                mission_progress += 1
                                if mission_progress >= 5:
                                    score += 350
                                    select_new_mission()
                                    
                            if tank in tanks:
                                tanks.remove(tank)

        if anomaly_type == "LASER_STORM":
            for lp in laser_storm_projectiles[:]:
                lp_rect = pygame.Rect(lp[0], lp[1], 10, 24)
                if ship_rect.colliderect(lp_rect):
                    laser_storm_hit_taken = True  
                    spawn_explosion(lp[0], lp[1], count=8, color_set=[(255, 0, 0), (255, 100, 100)])
                    if not is_invincible:
                        if shield_count > 0:
                            shield_count -= 1
                            trigger_shake(12, 6)
                        else:
                            player_health -= 0.5
                            trigger_shake(20, 12)
                    laser_storm_projectiles.remove(lp)

        for bm in boss_missiles[:]:
            bm_rect = pygame.Rect(bm[0], bm[1], 40, 80)
            if ship_rect.colliderect(bm_rect):
                spawn_explosion(bm[0] + 20, bm[1] + 40, count=10, color_set=[(147, 112, 219), (128, 0, 128), (255, 255, 255)])
                if not is_invincible:
                    if shield_count > 0:
                        shield_count -= 1
                        trigger_shake(12, 6)
                    else:
                        player_health -= 0.5
                        trigger_shake(22, 11)
                boss_missiles.remove(bm)

        if is_boss_stage and boss_spawned:
            for b in bosses[:]:
                if b in bosses:
                    b_rect = pygame.Rect(b["x"], b["y"], 120, 120)
                    
                    if ship_rect.colliderect(b_rect):
                        if not is_invincible:
                            if shield_count > 0:
                                shield_count -= 1
                                trigger_shake(20, 10)
                            else:
                                player_health -= 1.5
                                trigger_shake(40, 25)
                        b["hp"] -= 5
                        
                    for missile in missiles[:]:
                        missile_rect = pygame.Rect(missile[0], missile[1], 15, 30)
                        if missile_rect.colliderect(b_rect):
                            if missile in missiles:
                                missiles.remove(missile)
                            b["hp"] -= 1
                            spawn_explosion(missile[0], missile[1], count=8)
                            trigger_shake(6, 3)
                            
                            if current_mission == "BOSS_HUNTER":
                                mission_progress += 1
                                if mission_progress >= 10:
                                    score += 400
                                    select_new_mission()
                            
                            if b["hp"] <= 0 and b in bosses:
                                spawn_explosion(b["x"] + 60, b["y"] + 60, count=60)
                                pts = add_score(500)
                                spawn_floating_text(b["x"] + 40, b["y"], f"+{pts}")
                                bosses.remove(b)
                                if len(bosses) == 0:
                                    game_state = "SHOP"

        for powerup in powerups[:]:
            powerup_rect = pygame.Rect(powerup[0], powerup[1], 20, 20)
            if ship_rect.colliderect(powerup_rect):
                if powerup[2] == "shield":
                    shield_count = min(2, shield_count + 1)
                    shield_sound.play()  
                    if current_mission == "SHIELD_HOARDER" and shield_count == 2:
                        score += 300
                        select_new_mission()
                elif powerup[2] == "dual":
                    dual_shot_timer = 300
                    trio_shot_timer = 0
                    reload_sounds[0].play()  
                    reload_sounds[1].play()  
                    reload_sounds[2].play()  
                elif powerup[2] == "trio":
                    trio_shot_timer = 300
                    dual_shot_timer = 0
                    reload_sounds[0].play()  
                    reload_sounds[1].play()  
                    reload_sounds[2].play()  
                elif powerup[2] == "health":
                    player_health = min(player_max_health, player_health + 1.0)
                    heal_sound.play()  
                
                if current_mission == "COLLECTOR":
                    mission_progress += 1
                    if mission_progress >= 3:
                        score += 300
                        select_new_mission()
                        
                powerups.remove(powerup)
                
        if player_health <= 0:
            spawn_explosion(ship_x + 32, ship_y + 35, count=50)
            trigger_shake(50, 25)
            update_user_score_in_supabase(score, level)
            game_state = "GAMEOVER"

    for p in particles[:]:
        p[0] += p[2]
        p[1] += p[3]
        p[4] -= 1
        if p[4] <= 0:
            particles.remove(p)

    for ft in floating_texts[:]:
        ft[1] -= 1  
        ft[4] -= 1
        if ft[4] <= 0:
            floating_texts.remove(ft)

    render_offset_x = 0
    render_offset_y = 0
    if shake_timer > 0:
        shake_timer -= 1
        render_offset_x = random.randint(-shake_intensity, shake_intensity)
        render_offset_y = random.randint(-shake_intensity, shake_intensity)

    display_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    display_surface.fill((0, 0, 0))
    
    for star in stars_back:
        pygame.draw.circle(display_surface, (100, 100, 100), (int(star[0]), int(star[1])), 1)
    for star in stars_mid:
        pygame.draw.circle(display_surface, (180, 180, 180), (int(star[0]), int(star[1])), 2)
    for star in stars_fore:
        pygame.draw.circle(display_surface, (255, 255, 255), (int(star[0]), int(star[1])), 3)

    # ==========================================
    # 7. RENDERING SCREEN STATES
    # ==========================================
    if game_state == "AUTH":
        title_surf = large_font.render(f"SPACE SHOOTER: {auth_mode}", True, (0, 191, 255))
        display_surface.blit(title_surf, (50, 40))
        
        info_surf = font.render("[UP/DOWN]: Switch Mode | [TAB]: Change Field | [ENTER]: Submit", True, (180, 180, 180))
        display_surface.blit(info_surf, (50, 95))

        # Username Field
        u_color = (0, 255, 255) if auth_active_field == "username" else (200, 200, 200)
        u_surf = font.render(f"Username: {input_username}" + ("|" if auth_active_field == "username" else ""), True, u_color)
        display_surface.blit(u_surf, (50, 150))

        # Password Field
        p_color = (0, 255, 255) if auth_active_field == "password" else (200, 200, 200)
        masked_pass = "*" * len(input_password)
        p_surf = font.render(f"Password: {masked_pass}" + ("|" if auth_active_field == "password" else ""), True, p_color)
        display_surface.blit(p_surf, (50, 190))

        # Email Field (Register Only)
        if auth_mode == "REGISTER":
            e_color = (0, 255, 255) if auth_active_field == "email" else (200, 200, 200)
            e_surf = font.render(f"Email: {input_email}" + ("|" if auth_active_field == "email" else ""), True, e_color)
            display_surface.blit(e_surf, (50, 230))

        # Error / Status Message
        msg_color = (255, 50, 50) if "Error" in auth_message else (50, 255, 50)
        msg_surf = font.render(auth_message, True, msg_color)
        display_surface.blit(msg_surf, (50, 280))

        # Leaderboard
        lead_title = font.render("🏆 SUPABASE LEADERBOARD 🏆", True, (255, 215, 0))
        display_surface.blit(lead_title, (450, 40))
        for idx, entry in enumerate(leaderboard):
            lvl_val = entry[2] if len(entry) > 2 else 1
            lead_text = f"{idx+1}. {entry[1]} - {entry[0]} (Lvl {lvl_val})"
            lead_surf = font.render(lead_text, True, (255, 255, 255))
            display_surface.blit(lead_surf, (450, 90 + (idx * 30)))

    elif game_state == "PAUSED":
        pause_surf = large_font.render("GAME PAUSED", True, (255, 255, 0))
        sub_surf = font.render("Press 'ESC' to Resume", True, (255, 255, 255))
        display_surface.blit(pause_surf, (SCREEN_WIDTH // 2 - pause_surf.get_width() // 2, 230))
        display_surface.blit(sub_surf, (SCREEN_WIDTH // 2 - sub_surf.get_width() // 2, 300))
        
    elif game_state == "GAMEOVER":
        for p in particles:
            pygame.draw.rect(display_surface, p[5], (int(p[0]), int(p[1]), 4, 4))
            
        go_surf = large_font.render("GAME OVER", True, (255, 0, 0))
        score_surf = font.render(f"Your Score: {score} | Best: {user_best_score} (Lvl {level})", True, (255, 255, 255))
        restart_surf = font.render("Press 'R' to Restart", True, (0, 255, 0))
        
        display_surface.blit(go_surf, (50, 50))
        display_surface.blit(score_surf, (50, 150))
        display_surface.blit(restart_surf, (50, 480))
        
        lead_title = font.render("🏆 SUPABASE LEADERBOARD 🏆", True, (255, 215, 0))
        display_surface.blit(lead_title, (430, 50))
        for idx, entry in enumerate(leaderboard):
            lvl_val = entry[2] if len(entry) > 2 else 1
            lead_text = f"{idx+1}. {entry[1]} - {entry[0]} (Lvl {lvl_val})"
            lead_surf = font.render(lead_text, True, (255, 255, 255))
            display_surface.blit(lead_surf, (430, 100 + (idx * 30)))
            
    elif game_state == "SHOP":
        shop_title = large_font.render("🚀 SPACE STATION UPGRADE SHOP 🚀", True, (0, 191, 255))
        coins_surf = font.render(f"Available Score (Credits): {score}", True, (255, 215, 0))
        
        op1 = font.render("Press [1] Upgrade Engine Speed (+1 Speed) ----------- Cost: 150 Score", True, (255, 255, 255))
        op2 = font.render("Press [2] Recharge Shield Battery (+1 Shield) -------- Cost: 100 Score", True, (255, 255, 255))
        op3 = font.render("Press [3] Buy Hull Repairs (+1 Heart) --------------- Cost: 120 Score", True, (255, 255, 255))
        op4 = font.render("Press [4] Instant Ultimate Booster (+50% Charge) ----- Cost: 150 Score", True, (0, 255, 150))
        op5 = font.render("Press [5] Upgrade Projectile Velocity (+1 Missile Speed) - Cost: 250 Score", True, (255, 150, 50))
        
        next_tier = perm_shot_tier + 1
        if next_tier in WEAPON_UPGRADE_COSTS:
            up_name = WEAPON_TIER_NAMES[next_tier]
            up_cost = WEAPON_UPGRADE_COSTS[next_tier]
            op6 = font.render(f"Press [6] UPGRADE WEAPONS -> {up_name} ----- Cost: {up_cost} Score", True, (147, 112, 219))
        else:
            op6 = font.render("Press [6] UPGRADE WEAPONS -> MAX LEVEL REACHED", True, (100, 100, 100))
        
        status_surf = font.render(f"Stats: Speed: {ship_speed} | Gun Tier: {WEAPON_TIER_NAMES[perm_shot_tier]} | Missile Spd: {player_missile_speed} | Shields: {shield_count}/2", True, (100, 255, 100))
        exit_surf = large_font.render("Press ENTER to fly to Level " + str(level + 1), True, (0, 255, 0))
        
        display_surface.blit(shop_title, (SCREEN_WIDTH // 2 - shop_title.get_width() // 2, 30))
        display_surface.blit(coins_surf, (100, 110))
        display_surface.blit(op1, (100, 170))
        display_surface.blit(op2, (100, 210))
        display_surface.blit(op3, (100, 250))
        display_surface.blit(op4, (100, 290))
        display_surface.blit(op5, (100, 330))
        display_surface.blit(op6, (100, 370))
        display_surface.blit(status_surf, (100, 420))
        display_surface.blit(exit_surf, (SCREEN_WIDTH // 2 - exit_surf.get_width() // 2, 480))

    elif game_state == "PLAYING":
        for missile in missiles:
            display_surface.blit(picture_missile, (missile[0], missile[1]))
            
        for bm in boss_missiles:
            display_surface.blit(picture_boss_missile, (bm[0], bm[1]))

        if anomaly_type == "LASER_STORM":
            for lp in laser_storm_projectiles:
                pygame.draw.line(display_surface, (255, 50, 50), (int(lp[0]), int(lp[1])), (int(lp[0] + lp[2]*2), int(lp[1] + lp[3]*2)), 3)

        for enemy in enemies:
            display_surface.blit(picture_enemy, (enemy[0], enemy[1]))

        if not is_boss_stage:
            for tank in tanks:
                display_surface.blit(picture_tank, (tank[0], tank[1]))
        else:
            if boss_spawned:
                for b in bosses:
                    display_surface.blit(picture_boss, (b["x"], b["y"]))
                    health_ratio = max(0, b["hp"] / b["max_hp"])
                    pygame.draw.rect(display_surface, (100, 0, 0), (b["x"], b["y"] - 15, 120, 8))
                    pygame.draw.rect(display_surface, (255, 0, 0), (b["x"], b["y"] - 15, int(120 * health_ratio), 8))

        for powerup in powerups:
            if powerup[2] == "shield":
                pygame.draw.circle(display_surface, (0, 191, 255), (int(powerup[0] + 10), int(powerup[1] + 10)), 10)
            elif powerup[2] == "dual":
                pygame.draw.circle(display_surface, (255, 140, 0), (int(powerup[0] + 10), int(powerup[1] + 10)), 10)
            elif powerup[2] == "trio":
                pygame.draw.circle(display_surface, (147, 112, 219), (int(powerup[0] + 10), int(powerup[1] + 10)), 10)
            elif powerup[2] == "health":
                pygame.draw.circle(display_surface, (255, 0, 0), (int(powerup[0] + 10), int(powerup[1] + 10)), 10)
            
        if dodge_timer % 4 < 2:  
            display_surface.blit(picture_ship, (ship_x, ship_y))

        if ultimate_active_timer > 0:
            if q_mode_active:
                pygame.draw.rect(display_surface, (255, 0, 0), (ship_x - 15, 0, 95, ship_y))
                pygame.draw.rect(display_surface, (255, 180, 180), (ship_x + 5, 0, 55, ship_y))
            else:
                pygame.draw.rect(display_surface, (0, 191, 255), (ship_x - 15, 0, 95, ship_y))
                pygame.draw.rect(display_surface, (200, 240, 255), (ship_x + 5, 0, 55, ship_y))

        if shield_count >= 1:
            pygame.draw.circle(display_surface, (0, 191, 255), (int(ship_x + 32), int(ship_y + 35)), 45, 2)
        if shield_count == 2:
            pygame.draw.circle(display_surface, (255, 0, 255), (int(ship_x + 32), int(ship_y + 35)), 51, 2)

        for p in particles:
            pygame.draw.rect(display_surface, p[5], (int(p[0]), int(p[1]), 4, 4))

        for ft in floating_texts:
            ft_surf = font.render(ft[2], True, ft[3])
            display_surface.blit(ft_surf, (ft[0], ft[1]))
        
        score_surface = font.render(f"Score: {score}", True, (255, 255, 255))
        level_surface = font.render(f"Level: {level}", True, (50, 255, 50))
        user_surface = font.render(f"Pilot: {logged_in_user}", True, (0, 191, 255))
        
        best_surface = font.render(f"Best: {user_best_score}", True, (255, 215, 0))
        
        shield_txt = f"Shields: {shield_count}/2"
        shield_color = (0, 191, 255) if shield_count == 1 else (255, 0, 255) if shield_count == 2 else (120, 120, 120)
        shield_surface = font.render(shield_txt, True, shield_color)
        
        dodge_str = "DODGE [C]: READY" if dodge_cooldown <= 0 else f"DODGE [C]: {dodge_cooldown // 60 + 1}s"
        dodge_surf = font.render(dodge_str, True, (0, 255, 255) if dodge_cooldown <= 0 else (100, 100, 100))
        
        spd_str = "2x SPEED [V]: READY" if speed_boost_cooldown <= 0 else f"2x SPEED [V]: {speed_boost_cooldown // 60 + 1}s"
        spd_surf = font.render(spd_str, True, (255, 255, 0) if speed_boost_cooldown <= 0 else (100, 100, 100))

        combo_str = f"COMBO: {combo_count}x ({combo_multiplier:.1f}x Multiplier!)" if combo_count > 1 else ""
        combo_surf = font.render(combo_str, True, (255, 100, 0))

        mission_title_surf = font.render("🎯 RUN CHALLENGE MISSION:", True, (255, 215, 0))
        if current_mission in ["SNIPER", "COLLECTOR", "BOSS_HUNTER", "TANK_BUSTER"]:
            target_goal = 10 if current_mission == "BOSS_HUNTER" else 5 if current_mission == "TANK_BUSTER" else 3
            mission_desc_surf = font.render(f"» {mission_desc} ({mission_progress}/{target_goal})", True, (200, 200, 200))
        elif current_mission == "SCORE_CHASER":
            current_gained = max(0, score - mission_start_score)
            mission_desc_surf = font.render(f"» {mission_desc} ({current_gained}/500 pts)", True, (200, 200, 200))
        elif current_mission == "METEOR_SURVIVOR" and anomaly_type == "LASER_STORM":
            status_text = "⚠️ DAMAGED" if laser_storm_hit_taken else "✅ PERFECT"
            mission_desc_surf = font.render(f"» {mission_desc} ({status_text})", True, (200, 200, 200))
        else:
            mission_desc_surf = font.render(f"» {mission_desc}", True, (200, 200, 200))
            
        display_surface.blit(score_surface, (10, 10))
        display_surface.blit(level_surface, (10, 35))
        display_surface.blit(user_surface, (10, 60))
        display_surface.blit(best_surface, (10, 85))
        display_surface.blit(shield_surface, (10, 110))
        display_surface.blit(dodge_surf, (10, 135))
        display_surface.blit(spd_surf, (10, 160))
        display_surface.blit(combo_surf, (10, 185))
        
        weapon_display_surf = font.render(f"Gun Mode: {WEAPON_TIER_NAMES[perm_shot_tier]}", True, (147, 112, 219))
        display_surface.blit(weapon_display_surf, (10, 210))
        
        display_surface.blit(mission_title_surf, (10, 500))
        display_surface.blit(mission_desc_surf, (15, 525))

        if is_boss_stage:
            boss_alert_surf = font.render("⚠️ OP BOSS WARNING! ⚠️", True, (255, 50, 50))
            display_surface.blit(boss_alert_surf, (SCREEN_WIDTH // 2 - boss_alert_surf.get_width() // 2, 15))
        elif anomaly_type != "NONE":
            anomaly_alert = font.render(f"⚠️ {anomaly_type} ANOMALY DETECTED! ⚠️", True, (255, 140, 0))
            display_surface.blit(anomaly_alert, (SCREEN_WIDTH // 2 - anomaly_alert.get_width() // 2, 15))

        for i in range(5):
            heart_x = SCREEN_WIDTH - 174 + (i * 32)
            heart_y = 15
            is_full = player_health >= i + 1
            is_half = player_health == i + 0.5
            draw_pixel_heart(display_surface, heart_x, heart_y, size=24, full=is_full, half=is_half)

    screen.blit(display_surface, (render_offset_x, render_offset_y))
    pygame.display.flip()
    
    clock.tick(60)
    
pygame.quit()
sys.exit()

