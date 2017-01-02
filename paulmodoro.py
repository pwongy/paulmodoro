# ----------------------------------------------------------------------------
# Paul-modoro - A simple, cross-platform pomodoro timer
# Copyright (c) Paul Wong 2015-16
#
# Inspired by:
#   VNGRS's PomoWear Android app, available via the Play Store
#   Alex Holkner's countdown.py, available at:
#     https://spot.fedorapeople.org/flock/countdown.py
#
# Credits:
#   Andrian Sue - OS X implementations
# ----------------------------------------------------------------------------

# Import modules
import sys
import getopt
import time
from builtins import print

try:
    import pyglet       # For GUI
except ImportError:     # Convenience code for auto-installing Pyglet; should change per platform
    print("Pyglet not installed")

    from subprocess import call
    return_code = call("pip install pyglet")
    if return_code == 0:
        import pyglet
    else:
        print("Pyglet could not be installed")
finally:
    from pyglet.gl import *

# Platform-specific imports
if sys.platform.startswith("win"):
    # Floating windows
    from pyglet.libs.win32 import _user32
    from pyglet.libs.win32.constants import *

    # Flashing windows
    from ctypes import Structure, windll, POINTER, WINFUNCTYPE, sizeof
    from ctypes.wintypes import DWORD, HANDLE, BOOL, UINT
elif sys.platform.startswith("darwin"):
    # Floating windows
    from pyglet.libs.darwin.cocoapy import *
    NSApplication = ObjCClass('NSApplication')


# Initialise constants
app_name = "Paul-modoro"
version_no = "0.10.4"
build_date = "3 Nov 2016"
tag_line = "A Nightcap Initiative"

message_init = "Time to get things done"
message_pomodoro = "Focus on your work"
message_pomodoro_reset = "Let’s try that one again"
timer_pomodoro_end = "Stop"
message_break = "Chill out for a bit"
message_break_stop = "Seriously, go for a walk"
timer_break_end = "Focus"
message_break_end = "Get in the zone"
instruct_start = "SPACE to start"
instruct_stop = "SPACE to stop"
instruct_nothing = "SPACE to waste time"
instruct1 = instruct_start
instruct_quit = "ESC to quit"
instruct_exit_fs = "ESC to exit full screen"
instruct2 = instruct_quit

font_size_instruct_win = 12
font_size_instruct_fs = 18
font_size_message_win = 18
font_size_message_fs = 60
font_size_timer_win = 48
font_size_timer_fs = 160

circle_size_win = 10
circle_size_fs = 16

click_count = 0
click_time = -1

colors = {"red":   (250/255, 69/255, 64/255, 1),    # Python colors are [R,G,B,A], each from 0 > 1
          "green": (41/255, 191/255, 97/255, 1),
          "blue":  (67/255, 133/255, 255/255, 1)}

# Layout dimensions
win_taskbar_height = 40     # Dirty hack for now

padding = 10
window_width, window_height = 360, 240
dim_timer_x = 0
dim_timer_y = 0
dim_message_x = 0
dim_message_y = 0
dim_inst1_x = 0
dim_inst2_x = 0


def set_layout(width, height):
    global dim_timer_x, dim_timer_y, dim_message_x, dim_message_y, dim_inst1_x, dim_inst2_x
    global font_size_timer, font_size_message

    # Update dimensions...
    dim_timer_x = width // 2
    dim_timer_y = height // 2 - padding
    dim_message_x = width // 2
    dim_message_y = height // 2 - 2 * padding
    dim_inst1_x = padding
    dim_inst2_x = width - padding

    # ...and font sizes
    if width == window_width:   # Windowed mode
        font_size_timer = font_size_timer_win
        font_size_message = font_size_message_win
        font_size_instruct = font_size_instruct_win
    else:
        font_size_timer = font_size_timer_fs
        font_size_message = font_size_message_fs
        font_size_instruct = font_size_instruct_fs

    # Set dimensions
    timer.label.x = dim_timer_x
    timer.label.y = dim_timer_y
    timer.label.font_size = font_size_timer
    message_label.x = dim_message_x
    message_label.y = dim_message_y
    message_label.font_size = font_size_message
    inst1_label.x = dim_inst1_x
    inst1_label.font_size = font_size_instruct
    inst2_label.x = dim_inst2_x
    inst2_label.font_size = font_size_instruct

    return

refresh_rate = 10           # Refresh rate

key_sound_none = "None"
key_sound_brown = "Brown"
key_sound_cafe = "Cafe"
key_sound_ticking = "Ticking"

fade_time = 3               # In seconds

# Default options
screen_position = "R"       # Bottom right of screen
is_topmost = False          # Non-floating window
is_fullscreen = False       # Start in small window

bg_sound = key_sound_none
is_silent = False

font_size_timer = font_size_timer_win
font_size_message = font_size_message_win
font_size_instruct = font_size_instruct_win
circle_size = circle_size_win
circle_spacing = 2 * circle_size

# Testing overrides
is_testing = not True
test_length = 5/60          # Interval in minutes


def usage():
    print("""
    Usage: paulmodoro.py [-b | -c | -t] [-l] [-z] [-q] [-h]

    Options:
      -b    Play brown noise during pomodoros
      -c    Play cafe sounds during pomodoros
      -t    Play ticking sound during pomodoros
      -l    Align window to the left on multi-screen setups
      -z    Starts Paulmodoro as a floating window (i.e. always on top)
      -q    Shorter task intervals (for testing)
      -h    Shows this help message""")

# Get any options there were included with the command line
try:
    opts, args = getopt.getopt(sys.argv[1:], "bctlzqh")
except getopt.GetoptError:  # If options not recognised, display usage info
    usage()
    sys.exit(2)
for opt, arg in opts:
    if opt == '-b':
        bg_sound = key_sound_brown
    elif opt == '-c':
        bg_sound = key_sound_cafe
    elif opt == '-t':
        bg_sound = key_sound_ticking
    elif opt == '-l':
        screen_position = "L"
    elif opt == '-z':
        is_topmost = True
    elif opt == '-q':
        is_testing = True
    elif opt == '-h':       # Also display usage info if help requested explicitly
        usage()
        sys.exit()

# Load resources
if bg_sound == key_sound_brown:
    background_noise = pyglet.media.load("resources/brown_noise.wav", streaming=False)
elif bg_sound == key_sound_cafe:
    background_noise = pyglet.media.load("resources/restaurant_ambiance_soundBible.wav", streaming=False)
elif bg_sound == key_sound_ticking:
    background_noise = pyglet.media.load("resources/clock_ticking.wav", streaming=False)
alarm = pyglet.media.load('resources/bell_down_short.wav', streaming=False)


def scale_circle(circle, size):
    circle.width = size
    circle.height = size
    return circle

circle_complete = scale_circle(pyglet.resource.image("resources/circle_filled.png"), circle_size)
circle_incomplete = scale_circle(pyglet.resource.image("resources/circle_stroke.png"), circle_size)


# Welcome prompt
print("\n%s" % app_name)
print("Version %s" % version_no)
print("Build date: %s" % build_date)

print("\nToggle hotkeys:")
print("  F/F11: Full screen")
print("  S:     Silent mode (mute background noise)")
print("  Z:     Always on top")


# Define main object classes
class Task(object):
    def __init__(self, task_type, task_length_mins, task_color):
        self.type = task_type
        self.length = task_length_mins
        self.color = task_color


class Tracker(object):
    # Define task types
    pomodoro = Task("pomodoro", 25, "red")
    short_break = Task("short break", 5, "blue")
    long_break = Task("long break", 15, "blue")

    # Shorten intervals when testing
    if is_testing:
        pomodoro.length, short_break.length, long_break.length = test_length, test_length, test_length

    def __init__(self):
        self.pomo_count = 0
        self.circle_count = 0
        self.current_task = Tracker.pomodoro
        self.next_task = Tracker.short_break
        self.stop_break_attempts = 0

    def add_pomodoro(self):
        self.pomo_count += 1

    def update_tasks(self):
        if self.current_task.type == Tracker.pomodoro.type:
            self.current_task = self.next_task
            self.next_task = Tracker.pomodoro
        else:
            self.current_task = self.next_task

            if (self.pomo_count + 1) % 4 == 0:
                self.next_task = Tracker.long_break     # Long break after 4 pomodoros
            else:
                self.next_task = Tracker.short_break    # Short break

        # Update background colour to indicate readiness for next task
        set_bg_color("green")


class Timer(object):
    tracker = Tracker()
    player = pyglet.media.Player()

    def __init__(self):
        self.start = '%s:00' % Tracker.pomodoro.length
        self.label = pyglet.text.Label(self.start, font_size=font_size_timer,
                                       x=dim_timer_x, y=dim_timer_y,
                                       anchor_x='center', anchor_y='bottom')
        self.label.color = (255, 255, 255, 255)
        self.reset(Tracker.pomodoro)

        self.is_pomodoro = True
        self.running = False
        self.time = 0
        self.length_0 = 0
        self.task_logged = False

    def reset(self, task):
        if task.type == Tracker.pomodoro.type:
            self.is_pomodoro = True
        else:
            self.is_pomodoro = False

        self.running = False
        self.time = task.length * 60 + 0.9      # Extra to avoid rounding/floor error
        self.length_0 = self.time
        self.label.text = "%02d:00" % task.length
        self.task_logged = False

        if self.tracker.pomo_count > 0:
            set_bg_color(timer.tracker.current_task.color)

            if self.is_pomodoro:
                message_label.text = message_pomodoro
            else:
                message_label.text = message_break
        else:
            # Set initial background color manually
            set_bg_color("green")

    def update(self, dt):
        if self.running:
            # Do things when timer is first started
            if not self.task_logged:
                if self.is_pomodoro:
                    message_label.text = message_pomodoro
                    print("\nStarted %s #%d" % (self.tracker.current_task.type, (self.tracker.pomo_count + 1)))

                    # Loop background noise
                    if bg_sound != key_sound_none:
                        looper = pyglet.media.SourceGroup(background_noise.audio_format, None)
                        looper.queue(background_noise)
                        looper.loop = True
                        self.player.queue(looper)

                    if self.tracker.pomo_count % 4 == 0:
                        self.tracker.circle_count = 0
                else:
                    message_label.text = message_break
                    print("Taking a %s" % self.tracker.current_task.type)

                # Update background colour
                set_bg_color(self.tracker.current_task.color)

                self.task_logged = True

            # Fade in background noise
            elapsed = self.length_0 - self.time
            if self.is_pomodoro:
                if is_silent:
                    self.player.volume = 0
                else:
                    if elapsed <= fade_time:
                        self.player.volume = elapsed/fade_time
                    else:
                        self.player.volume = 1
            # else:
            #     self.player.volume = 0              # Mute during breaks

            # Increment timer
            self.time -= dt
            m, s = divmod(self.time, 60)
            self.label.text = '%02d:%02d' % (m, s)

            # Fade out background noise
            if self.is_pomodoro and self.time <= fade_time and not is_silent:
                self.player.volume = max([self.time/fade_time, 0])

            # Do things when timer runs down completely
            if self.time <= 0:
                self.running = False                # Stop timer running

                # Sounds
                self.player.pause()                 # Pause background noise (if playing)
                self.player.volume = 0
                alarm.play()                        # Play alarm sound

                # Window
                inst1_label.text = instruct_start
                set_window_flash(window, 0)         # Flash/bounce the window/icon

                # Counter
                if self.is_pomodoro:
                    self.tracker.add_pomodoro()     # Update pomodoro count
                    if self.tracker.pomo_count == 1:
                        print("  You have now completed %d pomodoro" % self.tracker.pomo_count)
                    else:
                        print("  You have now completed %d pomodoros" % self.tracker.pomo_count)

                    # Add a circle to indicator
                    self.tracker.circle_count += 1

                    # Update text labels
                    self.label.text = timer_pomodoro_end
                    message_label.text = "Take a %s" % self.tracker.next_task.type
                else:
                    self.label.text = timer_break_end
                    message_label.text = message_break_end
                    self.tracker.stop_break_attempts = 0

                # Since current task finished, prepare for next task
                self.tracker.update_tasks()


def start_stop_timer():
    if timer.running:
        if timer.is_pomodoro:   # Stopping a pomodoro
            timer.reset(timer.tracker.current_task)
            timer.player.pause()
            timer.player.volume = 0
            set_bg_color("green")
            message_label.text = message_pomodoro_reset
            inst1_label.text = instruct_start
            print("  Pomodoro cancelled")
        else:   # Stopping a break
            # Do nothing; remind user to stop working
            message_label.text = message_break_stop
            inst1_label.text = instruct_nothing
            if timer.tracker.stop_break_attempts == 0:
                print("  You should really take a break")

            timer.tracker.stop_break_attempts += 1
            print("  Stop break attempts: %d" % timer.tracker.stop_break_attempts)

            # TODO: Add other messages

    else:
        timer.reset(timer.tracker.current_task)
        timer.running = True
        if timer.is_pomodoro:   # Starting a pomodoro
            timer.player.play()
            inst1_label.text = instruct_stop
        else:   # Starting a break
            inst1_label.text = instruct_nothing


def set_window_floating(win):
    """
    Always on top hack, based on code from:
        https://ython.wordpress.com/2011/03/23/pyglet-set-window-as-always-on-top-topmost-on-win32/
    Code corrected by Paul Wong.

    @param win The window to set as floating
    """

    if sys.platform.startswith("win"):
        _user32.SetWindowPos(
                win._hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE)
    elif sys.platform.startswith("darwin"):
        win._nswindow.setLevel_(1)
    return True


def set_window_normal(win):
    if sys.platform.startswith("win"):
        _user32.SetWindowPos(
                win._hwnd, HWND_NOTOPMOST, 0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE)
    elif sys.platform.startswith("darwin"):
        win._nswindow.setLevel_(0)
    return False


def toggle_window_fullscreen(win, fs):
    global is_fullscreen

    if fs:
        win.set_fullscreen(False)
        is_fullscreen = False
        inst2_label.text = instruct_quit
    else:
        win.set_fullscreen(True)
        is_fullscreen = True
        inst2_label.text = instruct_exit_fs

    set_layout(win.width, win.height)

    return


def set_window_flash(win, count):
    if sys.platform.startswith("win"):          # Make taskbar icon flash orange
        # Flag constants
        FLASHW_ALL = 0x03
        FLASHW_TIMERNOFG = 0x0C

        class FlashWInfo(Structure):
            _fields_ = [("cbSize", UINT),
                        ("hwnd", HANDLE),
                        ("dwFlags", DWORD),
                        ("uCount", UINT),
                        ("dwTimeout", DWORD)]

        flash_window_ex_proto = WINFUNCTYPE(BOOL, POINTER(FlashWInfo))
        flash_window_ex = flash_window_ex_proto(("FlashWindowEx", windll.user32))

        params = FlashWInfo(sizeof(FlashWInfo),
                            win._hwnd,
                            FLASHW_ALL | FLASHW_TIMERNOFG, count, 0)
        flash_window_ex(params)
    elif sys.platform.startswith("darwin"):     # Make dock icon bounce
        if count == 0:
            bounce_count = 0     # Bounce forever
        elif count == 1:
            bounce_count = 10    # Bounce for 1 second (i.e. once)
        else:
            bounce_count = 0     # Default to forever

        NSApp = NSApplication.sharedApplication()
        NSApp.requestUserAttention_(bounce_count)


def set_bg_color(color):
    pyglet.gl.glClearColor(*colors[color])


def draw_circles(win, how_many):
    # Calculate spacing for GUI
    x_start = win.width//2 - circle_spacing - circle_size - (circle_spacing - circle_size)//2

    # Define draw operation
    if how_many > 4:    # This should never occur
        pass
    else:
        for i in range(0, how_many):
            circle_complete.blit(x_start + i * circle_spacing, win.height - circle_spacing)
        for i in range(how_many, 4):
            circle_incomplete.blit(x_start + i * circle_spacing, win.height - circle_spacing)


# Make a window
window = pyglet.window.Window(width=window_width,
                              height=window_height)
window.activate()
window.set_caption(app_name)

# Set icon
icon_32 = pyglet.image.load("resources/icon_32.png")
icon_64 = pyglet.image.load("resources/icon_64.png")
icon_128 = pyglet.image.load("resources/icon_128.png")
icon_256 = pyglet.image.load("resources/icon_256.png")
window.set_icon(icon_32, icon_64, icon_128, icon_256)

# Window settings
if is_topmost:
    is_topmost = set_window_floating(window)        # Always on top
glEnable(GL_BLEND)                                  # Alpha blending
glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

# Get display screens
all_screens = pyglet.window.get_platform().get_default_display().get_screens()
screen_count = len(all_screens)

# Set window location
if screen_position == "L" and all_screens[0].x < 0:
    win_x = all_screens[0].x + padding
    win_y = all_screens[0].y + all_screens[0].height - window_height - padding - win_taskbar_height
else:
    win_x = all_screens[screen_count - 1].width - window_width - padding
    win_y = all_screens[screen_count - 1].height - window_height - padding - win_taskbar_height

window.set_location(win_x, win_y)

# Add text message
message_label = pyglet.text.Label(message_init,
                                  font_size=font_size_message,
                                  x=dim_message_x, y=dim_message_y,
                                  anchor_x='center', anchor_y='top')

# Add instructions
inst1_label = pyglet.text.Label(instruct1,
                                font_size=font_size_instruct,
                                x=dim_inst1_x, y=padding,
                                anchor_x='left', anchor_y='bottom')
inst2_label = pyglet.text.Label(instruct2,
                                font_size=font_size_instruct,
                                x=dim_inst2_x, y=padding,
                                anchor_x='right', anchor_y='bottom')

# Uncomment to see window events in console
# window.push_handlers(pyglet.window.event.WindowEventLogger())


@window.event
def on_key_press(symbol, modifiers):
    if symbol == pyglet.window.key.SPACE:           # Start/stop timer
        start_stop_timer()
    elif symbol == pyglet.window.key.ESCAPE:        # Quit...or exit fullscreen
        if is_fullscreen:
            toggle_window_fullscreen(window, is_fullscreen)
            return True
        else:
            window.close()
            return True
    elif symbol == pyglet.window.key.Z:             # Toggle window always on top
        global is_topmost
        if is_topmost:
            is_topmost = set_window_normal(window)
        elif not is_topmost:
            is_topmost = set_window_floating(window)
    elif symbol == pyglet.window.key.F or symbol == pyglet.window.key.F11:      # Fullscreen mode
        toggle_window_fullscreen(window, is_fullscreen)
        if is_topmost:
            set_window_floating(window)
    elif symbol == pyglet.window.key.S:             # Silent mode (alarm still rings on finish)
        global is_silent
        if is_silent:
            is_silent = False
        else:
            is_silent = True


@window.event
def on_mouse_release(x, y, button, modifiers):
    if button == pyglet.window.mouse.RIGHT:
        start_stop_timer()
    elif button == pyglet.window.mouse.LEFT:
        global click_count, click_time
        t = time.time()

        if t - click_time < 0.25:   # Double click
            click_count += 1
            toggle_window_fullscreen(window, is_fullscreen)
        else:                       # First click
            click_count = 1
            click_time = time.time()


@window.event
def on_draw():
    # Clear screen first
    window.clear()

    # Redraw items
    draw_circles(window, timer.tracker.circle_count)
    timer.label.draw()
    message_label.draw()
    inst1_label.draw()
    inst2_label.draw()


@window.event
def on_resize(width, height):
    global circle_size, circle_complete, circle_incomplete, circle_spacing
    # print('The window was resized to %dx%d' % (width, height))

    # Update circle size and spacing...
    if width == window_width:   # Small window mode
        circle_size = circle_size_win
    else:                       # Full screen
        circle_size = circle_size_fs
    circle_spacing = 2 * circle_size

    # ...and drawables
    circle_complete = scale_circle(pyglet.resource.image("resources/circle_filled.png"), circle_size)
    circle_incomplete = scale_circle(pyglet.resource.image("resources/circle_stroke.png"), circle_size)

# Create the timer
timer = Timer()
pyglet.clock.schedule_interval(timer.update, 1/refresh_rate)

# Set layout parameters
set_layout(window_width, window_height)

# Run the app
pyglet.app.run()

# Use pyinstaller to freeze to .exe
# pyinstaller --onefile --noconsole paulmodoro.py
