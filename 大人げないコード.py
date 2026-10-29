# =============================================================
#  UIFlow1 line trace  (servo version)
#  ATOM Matrix + Atomic Motion Base + Color Unit
#  wheels = 360 deg continuous rotation servos on S1 / S2
#
#  Button:
#    W  -> put sensor on WHITE, press
#    B  -> put sensor on BLACK line, press
#    >  -> put sensor on the RIGHT EDGE of the line, press to start
#          press again to stop
# =============================================================
from m5stack import *
from m5ui import *
from uiflow import *
from base.Motion import Motion
import unit
import time

# ===================== 設定 =====================
LEFT_CH = 3        # 左サーボ = S1
RIGHT_CH = 1       # 右サーボ = S2
LEFT_DIR = 1      # 前に進まない側の符号を反転する
RIGHT_DIR = -1

LEFT_GAIN = 1.0    # 左の力の倍率（左に曲がっていくなら上げる）
RIGHT_GAIN = 1.0   # 右の力の倍率（右に曲がっていくなら上げる）

LEFT_TRIM = 0      # 停止中に少し回ってしまう時の補正 (us, 例: -20 ~ 20)
RIGHT_TRIM = 0

BASE_SPEED = 50    # 直進の速さ (0 ~ 100)
MAX_SPEED = 100
KP = 40            # 曲がる強さ
KD = 100           # 蛇行をおさえる
EDGE = -1          # -1: ラインの右端 / 1: 左端
TARGET = 0.5

STRAIGHT_TEST = False  # True にするとラインを見ずにまっすぐ走る（左右の力合わせ用）

PULSE_PER_SPEED = 6    # speed 100 -> 1500 +/- 600 us
LOOP_MS = 25
LED_BRIGHT = 10

# ===================== 初期化 =====================
motion = Motion()
color_0 = unit.get(unit.COLOR, unit.PORTA)
rgb.setBrightness(LED_BRIGHT)

GLYPH_W  = ["X...X", "X...X", "X.X.X", "XX.XX", "X...X"]
GLYPH_B  = ["XXXX.", "X...X", "XXXX.", "X...X", "XXXX."]
GLYPH_GO = ["X....", "XXX..", "XXXXX", "XXX..", "X...."]
GLYPH_NG = ["X...X", ".X.X.", "..X..", ".X.X.", "X...X"]


def show_glyph(rows, col):
    pix = []
    for y in range(5):
        for x in range(5):
            pix.append(col if rows[y][x] == "X" else 0x000000)
    rgb.set_screen(pix)


def show_level(n):
    c = min(4, max(0, int(n * 5)))
    pix = []
    for y in range(5):
        for x in range(5):
            pix.append(0x00ff3c if x == c else 0x000000)
    rgb.set_screen(pix)


# ===================== サーボ・センサー =====================
def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def servo_speed(ch, speed, direction, trim):
    speed = clamp(speed, -100, 100)
    pulse = 1500 + trim + int(speed * PULSE_PER_SPEED * direction)
    motion.set_servo_pulse(ch, pulse)


def drive(left, right):
    servo_speed(LEFT_CH, left * LEFT_GAIN, LEFT_DIR, LEFT_TRIM)
    servo_speed(RIGHT_CH, right * RIGHT_GAIN, RIGHT_DIR, RIGHT_TRIM)


def stop():
    servo_speed(LEFT_CH, 0, LEFT_DIR, LEFT_TRIM)
    servo_speed(RIGHT_CH, 0, RIGHT_DIR, RIGHT_TRIM)


def brightness():
    v = color_0.rawData
    if isinstance(v, (tuple, list)):
        v = v[-1]
    return v


def sample(n=15):
    total = 0
    for _ in range(n):
        total += brightness()
        wait_ms(LOOP_MS)
    return total / n


# ===================== ボタン =====================
pressed = False


def buttonA_wasPressed():
    global pressed
    pressed = True
    pass
btnA.wasPressed(buttonA_wasPressed)


def take_press():
    global pressed
    p = pressed
    pressed = False
    return p


# ===================== メインループ =====================
state = "WHITE"
white = 0
black = 0
prev_err = 0.0
disp_t = 0

stop()
show_glyph(GLYPH_W, 0xffffff)
print("[1] sensor on WHITE, press button")

while True:
    if state == "WHITE":
        if take_press():
            white = sample()
            print("white =", white)
            show_glyph(GLYPH_B, 0x0050ff)
            print("[2] sensor on BLACK, press button")
            state = "BLACK"

    elif state == "BLACK":
        if take_press():
            black = sample()
            print("black =", black)
            if white - black > 30:
                show_glyph(GLYPH_GO, 0x00ff00)
                print("[3] put on line edge, press to start")
                state = "READY"
            else:
                print("white-black too small. move sensor closer to floor")
                show_glyph(GLYPH_NG, 0xff0000)
                wait_ms(1500)
                show_glyph(GLYPH_W, 0xffffff)
                state = "WHITE"

    elif state == "READY":
        if take_press():
            wait_ms(300)
            take_press()
            prev_err = 0.0
            state = "RUN"

    elif state == "RUN":
        if take_press():
            stop()
            show_glyph(GLYPH_GO, 0x00ff00)
            print("stopped. press to restart")
            state = "READY"
            continue

        t0 = time.ticks_ms()

        n = clamp((brightness() - black) / (white - black), 0.0, 1.0)

        if STRAIGHT_TEST:
            turn = 0
        else:
            err = (n - TARGET) * EDGE
            turn = KP * err + KD * (err - prev_err)
            prev_err = err

        left = clamp(BASE_SPEED + turn, -MAX_SPEED, MAX_SPEED)
        right = clamp(BASE_SPEED - turn, -MAX_SPEED, MAX_SPEED)
        drive(left, right)

        if time.ticks_diff(t0, disp_t) > 100:
            show_level(n)
            disp_t = t0

        dt = time.ticks_diff(time.ticks_ms(), t0)
        if dt < LOOP_MS:
            wait_ms(LOOP_MS - dt)
        continue

    wait_ms(20)