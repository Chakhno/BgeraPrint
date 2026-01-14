#!/usr/bin/env python
# coding: utf-8

# In[1]:


from gtts import gTTS
import os
import subprocess
import platform
import re
import time
import requests
from pydub import AudioSegment
from pydub.playback import play
import sys
from pathlib import Path
import json

if hasattr(sys, "_MEIPASS"):
    BASE_DIR = Path(sys._MEIPASS)
else:
    BASE_DIR = Path(__file__).parent

if getattr(sys, 'frozen', False):
    PERSISTENT_DIR = Path(sys.executable).parent
else:
    PERSISTENT_DIR = Path(__file__).parent
    
    
def resource_path(rel_path):
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, rel_path)
    return os.path.join(os.path.dirname(__file__), rel_path)

bin_folder = resource_path("assets/bin")
ffmpeg_path = os.path.join(bin_folder, "ffmpeg.exe")
ffprobe_path = os.path.join(bin_folder, "ffprobe.exe")

if bin_folder not in os.environ["PATH"]:
    os.environ["PATH"] += os.pathsep + bin_folder

AudioSegment.converter = ffmpeg_path
AudioSegment.ffprobe = ffprobe_path 


ASSETS = BASE_DIR / "assets"
AUDIO_GEO = ASSETS / "audio_geo"
AUDIO_ENG = ASSETS / "audio_eng"
MODELS = ASSETS / "models"
DOWNLOADS = Path.home() / "Downloads"
CONFIG_PATH = PERSISTENT_DIR / "config.json"

welcome = AudioSegment.from_mp3(AUDIO_ENG / "welcome.mp3")
language = AudioSegment.from_mp3(AUDIO_ENG / "language.mp3")

play(welcome)
print("Welcome to BgeraPrint by Luka Chakhnashvili!")


if not CONFIG_PATH.exists():
    play(language)
    lan = input("Press 1 for English, or 2 for Georgian ")
    
    if lan == "1":
        ip  = AudioSegment.from_mp3(AUDIO_ENG / "ip.mp3")
        port = AudioSegment.from_mp3(AUDIO_ENG / "port.mp3")
        printer_model = AudioSegment.from_mp3(AUDIO_ENG / "printer_model.mp3")
        wrong_letter = AudioSegment.from_mp3(AUDIO_ENG / "wrong_letter.mp3")
        
    elif lan == "2":
        ip  = AudioSegment.from_mp3(AUDIO_GEO / "ip.mp3")
        port = AudioSegment.from_mp3(AUDIO_GEO / "port.mp3")
        printer_model = AudioSegment.from_mp3(AUDIO_GEO / "printer_model.mp3")
        wrong_letter = AudioSegment.from_mp3(AUDIO_GEO / "wrong_letter.mp3")
        
    play(printer_model)
    
    while True:
        printer = input("Please type model of your QIDI Printer (e.g. xmax3): ")
        
        potential_path = ASSETS / f"{printer}.ini"
        
        if potential_path.exists():
            break
        else:
            print("Please enter the correct name ")
            play(wrong_letter)
            
    play(ip)
    ip = input("Enter printer IP: ")
    
    play(port)
    port = input("Enter printer port (7125): ")

    with open(CONFIG_PATH, "w") as f:
        json.dump({"lan":lan, "printer":printer, "ip": ip, "port": port}, f)

with open(CONFIG_PATH) as f:
    cfg = json.load(f)

    

lan = cfg["lan"] 
PRINTER = cfg["printer"]
PRINTER_IP = cfg["ip"]
PRINTER_PORT = cfg["port"]

    
if lan == "1":
    AUDIO = AUDIO_ENG
    lingo = 'english'
    
elif lan == "2":
    AUDIO = AUDIO_GEO
    lingo = 'georgian'
    

intro = AudioSegment.from_mp3(AUDIO / "intro.mp3")

instruction = AudioSegment.from_mp3(AUDIO / "instruction.mp3")

size_change = AudioSegment.from_mp3(AUDIO_GEO / "size_change.mp3")
print_takes = AudioSegment.from_mp3(AUDIO_GEO / "print_takes.mp3")
print_confirm = AudioSegment.from_mp3(AUDIO_GEO / "print_confirm.mp3")
model_dimensions = AudioSegment.from_mp3(AUDIO_GEO / "model_dimensions.mp3")

wrong_letter = AudioSegment.from_mp3(AUDIO / "wrong_letter.mp3")
manual_stl = AudioSegment.from_mp3(AUDIO / "manual_stl.mp3")

time_path = AUDIO / "time.mp3"
model_mp3_path = AUDIO / "model.mp3"


def shape_sounds(shape):
    shape_init = AudioSegment.from_mp3(AUDIO / f"{shape}_init.mp3")
    
    if AUDIO == AUDIO_GEO:
        shape_dimensions = AudioSegment.from_mp3(AUDIO / f"{shape}_dimensions.mp3")
        return shape_init, shape_dimensions
    else:
        return shape_init, 1
    

def stl_path(shape):
    return DOWNLOADS / f"{shape}.stl"

def size_mp3_path(shape):
    return AUDIO / f"{shape}.mp3"


lion = MODELS / "lion.stl"
giraffe = MODELS / "giraffe.stl"
turtle = MODELS / "Turtle.stl"
wolf = MODELS / "wolf.stl"

builtin_models = {
    'lion': lion,
    'turtle': turtle,
    'giraffe': giraffe,
    'wolf': wolf
}


PRINT_CONFIG = ASSETS / f"{PRINTER}.ini"
    
OUTPUT_GCODE = DOWNLOADS / "model.gcode"
FILE_PATH = OUTPUT_GCODE 

system_platform = platform.system()


# In[ ]:


def bundled_path(relative):
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    return base / relative

OPENSCAD = bundled_path("assets/bin/openscad.exe")
slicer   = bundled_path("assets/bin/prusa-slicer-console.exe")

openscad_path = str(OPENSCAD)
SLICER = str(slicer)


# In[15]:


w = 20
l = 20
h = 20
d = 20
n = 4

ready_to_slice = False

ansp = None
ansfp = None


shapes = {
    'cube': {
        'shape': 'cube',
        'pattern': r'([wlh])(\d+)',
        'variables': {'w': w, 'l': l, 'h': h},
    },
    'cylinder': {
        'shape': 'cylinder',
        'pattern': r'([dh])(\d+)',
        'variables': {'d': d, 'h': h},
    },
    'cone': {
        'shape': 'cone',
        'pattern': r'([dh])(\d+)',
        'variables': {'d': d, 'h': h},
    },
    'pyramid': {
        'shape': 'pyramid',
        'pattern': r'([dhn])(\d+)',
        'variables': {'d': d, 'h': h, 'n': n},
    },
    'sphere': {
        'shape': 'sphere',
        'pattern': r'([d])(\d+)',
        'variables': {'d': d},
    }
}

SHAPES = {
    "cube": lambda p: f"cube([{p['w']}, {p['l']}, {p['h']}]);",
    "cylinder": lambda p: f"cylinder(h={p['h']}, d={p['d']}, $fn=128);",
    "cone": lambda p: f"cylinder(h={p['h']}, d1={p['d']}, d2=0, $fn=128);",
    "pyramid": lambda p: f"cylinder(h={p['h']}, d1={p['d']}, d2=0, $fn={p['n']});",
    "sphere": lambda p: f"sphere(d={p['d']}, $fn = 128);"
}


# In[16]:


def openscad_stl(scad_filename,scad_content,openscad_path,stl_filename):
    
    print(f"Creating OpenSCAD file: {scad_filename}...")
    with open(scad_filename, "w") as f:
        f.write(scad_content)

    
    print(f"Converting to STL using: {openscad_path}...")
    
   
    command = [openscad_path, "-o", stl_filename, scad_filename]

    try:
        
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"Success! Generated: {stl_filename}")
        else:
            print("Error running OpenSCAD:")
            print(result.stderr)
            
    except FileNotFoundError:
        print("Error: Could not find the OpenSCAD executable.")
        
        

def stl(shape, **params):
    scad_content = SHAPES[shape](params)
    
    scad_file_path = str(DOWNLOADS / f"{shape}.scad")
    stl_file_path = str(DOWNLOADS / f"{shape}.stl")
    
    openscad_stl(
        scad_file_path,
        scad_content,
        openscad_path,
        stl_file_path
    )

    
def handle_shape(
    shape,
    pattern,
    variables,
    lingo
):
    
    variables = variables.copy()
    
        
    sounds = shape_sounds(shape)

    play(sounds[0])

    while True:
        ansd = input()

        if ansd == 'p':
            return True, stl_path(shape)

        matches = re.findall(pattern, ansd)

        for letter, number_str in matches:
            variables[letter] = int(number_str)

        print("Final dimensions:", variables)

        dimensions = ", ".join(str(v) for v in variables.values())
        
        if lingo == 'georgian':
            gTTS(text=dimensions, lang='en', slow=False).save(size_mp3_path(shape))
            play(sounds[1]) 
            play(AudioSegment.from_mp3(size_mp3_path(shape)))
            play(size_change)
            
        elif lingo == 'english':
            gTTS(text=f"Dimensions of the {shape} are {dimensions} millimeters. If you want you can change the dimensions or press P and Enter to initiate printing-procedures.", lang='en', slow=False).save(size_mp3_path(shape))
            play(AudioSegment.from_mp3(size_mp3_path(shape)))
        


# In[ ]:


def model_dim_audio(STL_FILE, lingo, ans):
    dimensions = info_stl(SLICER, STL_FILE)
    print("Dimensions of your model are " + f'{dimensions} milimeters')
    
    if lingo == 'georgian':
        gTTS(text=f'{dimensions}', lang='en', slow=False).save(model_mp3_path)
        play(model_dimensions)
        play(AudioSegment.from_mp3(model_mp3_path))
        play(size_change)
        
    elif lingo == 'english':
        if ans == 'm':
            text = f"Dimensions of model are {dimensions} millimeters. You can scale the model by typing the scale number or press P and Enter to initiate printing-procedures."
        else:
            text = f"Dimensions of {ans} are {dimensions} millimeters. You can scale the model by typing the scale number or press P and Enter to initiate printing-procedures."
        
        gTTS(text=text, lang='en', slow=False).save(model_mp3_path)
        play(AudioSegment.from_mp3(model_mp3_path))
    
    print("You can scale the model or press 'p' to initiate printing procedures.") 
    
def handle_model(STL_FILE, lingo, ans):
    model_dim_audio(STL_FILE, lingo, ans)

    while True:
        factor = input("Write the scale value (e.g. 2) or press 'p' to slice")

        if factor == 'p':
            return True, STL_FILE

        resize_stl(SLICER, STL_FILE, factor, OUTPUT_STL)
        STL_FILE = OUTPUT_STL

        model_dim_audio(STL_FILE, lingo, ans)


# In[17]:


def info_stl(SLICER, STL_FILE):
    
    cmd = [
        SLICER,
        "--info", STL_FILE
    ]

    
    info = subprocess.run(cmd, shell=False, capture_output=True, text=True)
    
    sizes = [round(float(line.split("=")[1]))
         for line in info.stdout.splitlines()
         if line.startswith("size_")]

    x, y, z = sizes
    
    return sizes


def resize_stl(SLICER, STL_FILE, factor, OUTPUT_STL):
    
    cmd = [
        SLICER,
        "--export-stl", f"--scale",str(factor), 
        "--output",
        OUTPUT_STL, STL_FILE
    ]

    
    scaled_stl = subprocess.run(cmd, shell=False, capture_output=True, text=True)
    
    return scaled_stl



# In[18]:


def slicer(SLICER, STL_FILE, PRINT_CONFIG, OUTPUT_GCODE):
    
    print("Slicing:", STL_FILE)

    cmd = [
        SLICER,
        "--load", PRINT_CONFIG,
        "--printer-technology", "FFF",
        "--slice",
        "--export-gcode",
        "--output", OUTPUT_GCODE,
        STL_FILE
    ]

    
    slicing_result = subprocess.run(cmd, shell=False, capture_output=True, text=True)

    
    if slicing_result.returncode != 0:
        print("---ERROR DURING SLICING!---")
        print(slicing_result.stderr)
        
    else:
        print("Slicing successful.")


    
    print_time_tag = "; estimated printing time (normal mode) = "
    raw_time_string = ""
    estimated_time_formatted = "N/A"

    
    if not os.path.exists(OUTPUT_GCODE):
        print(f"Error: G-code file not found at {OUTPUT_GCODE}")
    else:
        try:
            with open(OUTPUT_GCODE, 'r') as f:
                for line in f:
                    if line.startswith(print_time_tag):
                        raw_time_string = line.split(print_time_tag)[-1].strip()
                        break
        except Exception as e:
            print(f"An error occurred while reading the G-code file: {e}")


    
    if raw_time_string:
        
        hours = 0
        minutes = 0
        seconds = 0

        
        match = re.search(r'(\d+)h', raw_time_string)
        if match:
            hours = int(match.group(1))

        match = re.search(r'(\d+)m', raw_time_string)
        if match:
            minutes = int(match.group(1))

        match = re.search(r'(\d+)s', raw_time_string)
        if match:
            seconds = int(match.group(1))

        
        if seconds > 0:
            minutes += 1

        
        if minutes >= 60:
            hours += minutes // 60
            minutes = minutes % 60

        
        parts = []
        if hours > 0:
            parts.append(f"{hours} hour{'s' if hours > 1 else ''}")

        
        if minutes > 0 or (hours == 0 and minutes == 0 and seconds == 0):
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")

        
        if parts:
            estimated_time_formatted = " ".join(parts)
        else:
            estimated_time_formatted = "1 minute"
            
        return OUTPUT_GCODE, estimated_time_formatted


def upload_and_print(ip, port, file_path):
    url = f"http://{ip}:{port}/server/files/upload"

    
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found.")
        return

    filename = os.path.basename(file_path)

    
    payload = {'root': 'gcodes', 'print': 'true'}

    print(f"Sending {filename} to {ip}...")

    try:
        with open(file_path, 'rb') as f:
            files = {'file': (filename, f)}
            response = requests.post(url, data=payload, files=files)

        if response.status_code == 201:
            print("File uploaded and print started!")
            print(f"Server Response: {response.json()}")
        else:
            print(f"Failed! Server returned status code {response.status_code}")
            print(response.text)

    except requests.exceptions.ConnectionError:
        print("Connection Failed")
    except Exception as e:
        print("An error occurred")


# In[13]:


play(intro)
print("Press 'i' to listen instructions or start 3D modelling")

while True:
    ans = input()

    if ans == 'i':
        print('''This application lets you create and print 3D models using only the keyboard.
                You can generate basic shapes — such as a cube, cylinder, cone, pyramid, or sphere — or choose complex built-in models to print by typing the name of the shape, or the model respectively, and pressing Enter.
                You can also print your own model. For this, press 'm', and then Enter, and paste the full path to the desired stl file on your computer.

                Press 'i', and Enter, to listen to instructions again.''')
        play(instruction)

    elif ans in shapes:
        ready_to_slice, STL_FILE = handle_shape(**shapes[ans], lingo=lingo)
        if ready_to_slice:
            break
            
    elif ans in builtin_models:
        STL_FILE = builtin_models[ans]
        OUTPUT_STL = DOWNLOADS / f"{ans}_resized.stl"
        ready_to_slice, STL_FILE = handle_model(STL_FILE, lingo, ans)
        if ready_to_slice:
            break
            
    elif ans == 'm':
        play(manual_stl)
        
        STL_FILE = input("Please type the path to your .stl file")
        STL_FILE = STL_FILE.strip('"').strip("'")
        
        OUTPUT_STL = DOWNLOADS / "manual_stl_resized.stl"
        
        ready_to_slice, STL_FILE = handle_model(STL_FILE, lingo, ans)
        if ready_to_slice:
            break
        
    else: 
        print("The letter is incorrect. Please try again.")
        play(wrong_letter)
        
OUTPUT_GCODE, estimated_time_formatted = slicer(SLICER, STL_FILE, PRINT_CONFIG, OUTPUT_GCODE)

time = f"{estimated_time_formatted}"

if lingo == 'georgian':
    gTTS(text=time, lang='en', slow=False).save(time_path)
    play(print_takes)
    play(AudioSegment.from_mp3(time_path))   
    play(print_confirm)

    
elif lingo == 'english':
    gTTS(text=f"Print takes {time}. If you really want to start printing press P.", lang='en', slow=False).save(time_path)
    play(AudioSegment.from_mp3(time_path))


print(f"Print takes {time}. If you really want to start printing press P.")
    
while True:    
    ansfp = input()
    if ansfp == 'p':
        
        if __name__ == "__main__":
            upload_and_print(PRINTER_IP, PRINTER_PORT, FILE_PATH)
        break

        
    if ansfp == 'b':
        break
        
    else: 
        print("The letter is incorrect. Please try again.")
        play(wrong_letter)


# In[ ]:




