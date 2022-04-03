# To get ImageTk with Python3
# sudo apt-get install python3-pil.imagetk

import tkinter as tk
from PIL import ImageTk,Image  

import subprocess

# 1080x1920
# /2 = 540x960
# /4 = 270x480

"""NOTES: 
- Should we just convert images to RGBA as soon as we open them? Any reason not to?
- Play with thumbail (i.e. resize) function. Make sure quality is what we expect

"""

# Constants
DISPLAY_W = 480
DISPLAY_H = 270

# Globals
current_img = None
alpha = 0

def toggle_fs(dummy=None):
    state = False if root.attributes('-fullscreen') else True
    root.attributes('-fullscreen', state)
    if not state:
        root.geometry('{}x{}}+100+100'.format(str(DISPLAY_W), str(DISPLAY_H)))

def img_update(dummy=None):
    print("Updating img")
    global current_img
    img = get_image("test.jpg")
    current_img = ImageTk.PhotoImage(img) 
    canvas.itemconfig(img_container, image=current_img)

def img_transition(dummy=None):
    # https://pillow.readthedocs.io/en/stable/reference/Image.html
    global alpha
    global current_img
    
    print("Blending with alpha = ", alpha)

    #img1 = get_image("test.png")
    #img2 = get_image("test.jpg")

    img = Image.blend(img1, img2, alpha)
    if alpha < 1:
        alpha += 0.05

    if alpha > 1.0:
        alpha = 1.0


    current_img = ImageTk.PhotoImage(img) 
    canvas.itemconfig(img_container, image=current_img)

    import time
    time.sleep(0.05)
    # Error - Images not the same size. Need to add black background of common 
    # size and then transition

def resize_image(img, size):
    img.thumbnail(size,Image.ANTIALIAS)
    img = img.convert("RGBA")
    return img

def open_image(filename):
    # open raises a number of exceptions if an error occurs - https://pillow.readthedocs.io/en/stable/reference/Image.html
    img = Image.open(filename)
    return img

def add_black_background(img, size):
    bg = Image.new("RGBA", size, (0, 0, 0, 255))
    bg.paste(img, (int((bg.size[0]-img.size[0])/2), 
                   int((bg.size[1]-img.size[1])/2)) )
    return bg

def get_image(filename):
    img = open_image(filename)
    img = resize_image(img, (DISPLAY_W, DISPLAY_H))
    img = add_black_background(img, (DISPLAY_W, DISPLAY_H))
    return img

def destroy(dummy=None):
    root.destroy()

def screen_off(dummy=None):
    subprocess.check_call('xset -display :0.0 dpms force off', shell=True) 

def screen_on(dummy=None):
    subprocess.check_call('xset -display :0.0 dpms force on', shell=True)


img1 = get_image("test.png")
img2 = get_image("test.jpg")


root = tk.Tk()  
canvas = tk.Canvas(root, bg='red', highlightthickness=0, width=DISPLAY_W, height=DISPLAY_H)  
canvas.pack(fill=tk.BOTH, expand=True) # configure canvas to occupy the whole main window

#root.attributes('-fullscreen', True) # make main window full-screen
root.bind('<Escape>', toggle_fs)
root.bind('n', img_update)
root.bind('t', img_transition)
root.bind('d', destroy)

root.bind('o', screen_off)
root.bind('p', screen_on)

root.config(cursor="none")

img = get_image("test.png")

current_img = ImageTk.PhotoImage(img)  
img_container = canvas.create_image(0,0, anchor=tk.NW, image=current_img) 

if 1:
    #root.after(1000, img_update)
    pass
else:
    from tkinter import ttk
    button= ttk.Button(root, text="Update", command=lambda:img_update())
    button.pack()




root.mainloop() 

print("Finished")


# To close window, call root.destroy(). Will need to recreate new window object
# to reopen window. Simple enough. 


"""

#%% ------------------  Adding text ---------------------------
# https://pillow.readthedocs.io/en/stable/reference/ImageDraw.html
img = img.convert("RGBA")
from PIL import ImageDraw, ImageFont
# make a blank image for the text, initialized to transparent text color
txt = Image.new("RGBA", img.size, (255, 255, 255, 0))
# get a font
fnt = ImageFont.truetype("Pillow/Tests/fonts/FreeMono.ttf", 40)
# get a drawing context
d = ImageDraw.Draw(txt)
# draw text, half opacity
d.text((10, 10), "Hello", font=fnt, fill=(0,0,0, 128))
# draw text, full opacity
d.text((10, 60), "World", font=fnt, fill=(0,0,0, 255))

img = Image.alpha_composite(img, txt)


"""