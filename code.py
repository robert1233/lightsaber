import time
from digitalio import DigitalInOut, Direction, Pull
import audioio
import busio
import board
import adafruit_rgbled
import adafruit_lis3dh
import gc
from analogio import AnalogIn

#Custom Variables - Lower thresholds are more sensitive
HIT_THRESHOLD = 350
FAST_THRESHOLD = 125
SLOW_THRESHOLD = 50
COLOR_HIT = (255, 255, 255)  #White when hit

#PINS
POWER_PIN = board.D10
SWITCH_PIN = board.A1
AUDIO_PIN = board.A0
RED_PIN = board.D11
GREEN_PIN = board.D12
BLUE_PIN = board.D13
POTENTIOMETER_PIN = board.A2

#High power mode
enable = DigitalInOut(POWER_PIN)
enable.direction = Direction.OUTPUT
enable.value =False

#Audio
audio = audioio.AudioOut(AUDIO_PIN)

#LED
LED = adafruit_rgbled.RGBLED(RED_PIN, GREEN_PIN, BLUE_PIN)

#Potentiometer
potentiometer = AnalogIn(POTENTIOMETER_PIN)

#Switch
switch = DigitalInOut(SWITCH_PIN)
switch.direction = Direction.INPUT
switch.pull = Pull.UP

# Set up accelerometer on I2C bus, 4G range:
i2c = busio.I2C(board.SCL, board.SDA)
accel = adafruit_lis3dh.LIS3DH_I2C(i2c)
accel.range = adafruit_lis3dh.RANGE_4_G

#Color Calculator using potentiometer position
def wheel(pos):
    if pos < 0 or pos > 255:
        return (0, 0, 0)
    if pos < 85:
        return (255 - pos * 3, pos * 3, 0)
    if pos < 170:
        pos -= 85
        return (0, 255 - pos * 3, pos * 3)
    pos -= 170
    return (pos * 3, 0, 255 - pos * 3)

def play_wav(name, loop=False):
    print("playing", name)
    try:
        wave_file = open(name + '.wav', 'rb')
        wave = audioio.WaveFile(wave_file)
        audio.play(wave, loop=loop)
    except:
        return

def power(sound, duration, reverse):
    #Garbage Collction
    gc.collect()
    
    if reverse:
        LED.color = (0, 0, 0)
    else:
        #Get color from potentiometer
        color = potentiometer.value
        r, g, b = wheel(int(color/256))
        LED.color = (r, g, b)
        
    play_wav(sound)    
    while audio.playing:
        pass

#Initial mode is OFF
mode = 0

#Get color from potentiometer
pot = potentiometer.value
r, g, b = wheel(int(pot/256))
COLOR = (r, g, b)

#Bootup time
time.sleep(0.1)

# Main program loop, repeats indefinitely
while True:
    #Get color from potentiometer
    pot = potentiometer.value
    r, g, b = wheel(int(pot/256))

    if not switch.value:                    # button pressed?
        if mode == 0:                       # If currently off...
            enable.value = True
            power('on', 1.7, False)         # Power up!
            play_wav('idle', loop=True)     # Play background hum sound
            mode = 1                        # ON (idle) mode now
        else:                               # else is currently on...
            power('off', 1.15, True)        # Power down
            mode = 0                        # OFF mode now
            enable.value = False
        while not switch.value:             # Wait for button release
            time.sleep(0.2)                 # to avoid repeated triggering

    elif mode >= 1:                         # If not OFF mode...
        x, z = accel.acceleration
        accel_total = x * x + z * z

        if accel.tapped:
            TRIGGER_TIME = time.monotonic() # Save initial time of hit
            rand = random.randint(1,4)
            LED.color = COLOR_HIT
            play_wav('hit' + rand)            
            mode = 3
        elif mode is 1 and accel_total > FAST_THRESHOLD:
            TRIGGER_TIME = time.monotonic() # Save initial time of swing
            play_wav('fast')               # Start playing 'fast' sound
            LED.color = (r, g, b)
            mode = 2                        # SWING mode
        elif mode is 1 and accel_total > SLOW_THRESHOLD:
            TRIGGER_TIME = time.monotonic() # Save initial time of swing
            play_wav('slow')               # Start playing 'slow' sound
            LED.color = (r, g, b)
            mode = 2                        # SWING mode
        elif mode > 1:                      # If in SWING or HIT mode...
            if audio.playing:               # And sound currently playing...
                LED.color = (r, g, b)
            else:                           # No sound now, but still MODE > 1
                play_wav('idle', loop=True) # Resume background hum
                LED.color = (r, g, b)      # Set to idle color
                mode = 1                    # IDLE mode now
