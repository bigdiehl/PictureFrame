import time

import config
import math
import os

import tkinter as tk
from PIL import ImageTk, Image, ExifTags, ImageFilter

import database
import image_utils

# Supporting Enums
class view_state:
    INIT = 0
    DISPLAY = 1
    TRANSITION = 2
    PAUSED = 3

class view_signal:
    PLAY = 0
    PAUSE = 1
    TRANSITION_NOW = 2

viewer_signal = None




class Viewer:
    """Picture viewer based on Tkinter GUI elements"""
    def __init__(self, pic_buffer):
        self.pic_buffer = pic_buffer #Handle pic_buffer that is shared with manager

        self.alive = True
        self.sleep = False
        self.sleep_now = False
        self.state = view_state.INIT
        self.last_state = None

        self.t_next_frame = 0
        self.t_next_pic = 0

        self.display_running = True

    def kill(self):
        self.alive = False


    def run(self):
        """Main event loop. Implements a state machine. """
                
        if self.state == view_state.INIT:
            self.wait_for_manager_ready()
            self.viewer_init()

            self.state = view_state.DISPLAY
            self.t_next_pic = time.time() + config.TIME_DELAY

        while self.alive and self.display_running:

            t = time.time()
        
            # Check signal from other thread/processes.
            global viewer_signal
            if viewer_signal is not None: #Signal is received
                if viewer_signal == view_signal.PLAY:
                    self.state = self.last_state

                elif viewer_signal == view_signal.PAUSE:
                    self.last_state = self.state
                    self.state = view_state.PAUSED

                elif viewer_signal == view_signal.TRANSITION_NOW:
                    print("Transitioning now...")
                    self.get_next_pic()
                    self.display_now()
                    self.state = view_state.DISPLAY
                    self.t_next_pic = t + config.TIME_DELAY
                    
                viewer_signal = None
                

            if self.state == view_state.DISPLAY:
                # Note - Try to do any extra things during the display time. Try to not
                # do anything computationally expensive during transition time.
                
                # If it is time to transition, prepare variables and change state
                if t > self.t_next_pic:
                    self.start_transition()
                    self.state = view_state.TRANSITION
                    self.t_next_frame = t + 1.0/config.FPS

                    self.start_time = time.time() # For debugging

                # See if we need to prepare the next picture
                if not next_pic_ready:
                    self.get_next_pic()
                    next_pic_ready = True

            elif self.state == view_state.TRANSITION:

                # If time for next slide, change. Otherwise wait. 
                if t > self.t_next_frame:
                    self.t_next_frame += 1.0/config.FPS
                    done = self.step_transition()

                    # See if transition is over.
                    if done:
                        self.state = view_state.DISPLAY 
                        #print("Transition time: ", time.time() - self.start_time)
                        next_pic_ready = False
                        self.t_next_pic = t + config.TIME_DELAY
                    
            elif self.state == view_state.PAUSED:
                pass
            
            self.draw_slide()

            # Sleep to reduce CPU load? Maybe make this more sophisticated?
            # Sleep different depending on the state?
            if 1:
                if self.state == view_state.TRANSITION:
                    time.sleep(1.0/config.FPS/2) 
                else:
                    time.sleep(0.1)
                    
            while self.sleep:
                time.sleep(0.1)
                
            # Ensures that we will run at least one complete loop before sleeping. 
            if self.sleep_now:
                self.sleep = True

        #EndWhilemanager












class ViewerBase:
    """Base class for picture frame viewer. Derived class can implement specific 
    methods (e.g. tkinter libary objects and methods go in TkinterViewer subclass)"""

    def __init__(self, pic_buffer):
        self.pic_buffer = pic_buffer #Handle pic_buffer that is shared with manager

        self.alive = True
        self.sleep = False
        self.sleep_now = False
        self.state = view_state.INIT
        self.last_state = None

        self.t_next_frame = 0
        self.t_next_pic = 0
        
    def kill(self):
        self.alive = False
        
    def go_to_sleep(self):
        self.sleep_now = True
        
    def wake_up(self):
        self.sleep = False
        self.sleep_now = False

    def run(self):
        """Main event loop. Implements a state machine. """
        
        next_pic_ready = False
        self.t_next_pic = time.time() + config.TIME_DELAY

        while self.alive and self.display_running():

            t = time.time()
        
            # Check signal from other thread/processes.
            global viewer_signal
            if viewer_signal is not None: #Signal is received
                if viewer_signal == view_signal.PLAY:
                    self.state = self.last_state

                elif viewer_signal == view_signal.PAUSE:
                    self.last_state = self.state
                    self.state = view_state.PAUSED

                elif viewer_signal == view_signal.TRANSITION_NOW:
                    print("Transitioning now...")
                    self.get_next_pic()
                    self.display_now()
                    self.state = view_state.DISPLAY
                    self.t_next_pic = t + config.TIME_DELAY
                    
                viewer_signal = None
                

            if self.state == view_state.DISPLAY:
                # Note - Try to do any extra things during the display time. Try to not
                # do anything computationally expensive during transition time.
                
                # If it is time to transition, prepare variables and change state
                if t > self.t_next_pic:
                    self.start_transition()
                    self.state = view_state.TRANSITION
                    self.t_next_frame = t + 1.0/config.FPS

                    self.start_time = time.time() # For debugging

                # See if we need to prepare the next picture
                if not next_pic_ready:
                    self.get_next_pic()
                    next_pic_ready = True

            elif self.state == view_state.TRANSITION:

                # If time for next slide, change. Otherwise wait. 
                if t > self.t_next_frame:
                    self.t_next_frame += 1.0/config.FPS
                    done = self.step_transition()

                    # See if transition is over.
                    if done:
                        self.state = view_state.DISPLAY 
                        #print("Transition time: ", time.time() - self.start_time)
                        next_pic_ready = False
                        self.t_next_pic = t + config.TIME_DELAY
                    
            elif self.state == view_state.PAUSED:
                pass
            
            self.draw_slide()

            # Sleep to reduce CPU load? Maybe make this more sophisticated?
            # Sleep different depending on the state?
            if 1:
                if self.state == view_state.TRANSITION:
                    time.sleep(1.0/config.FPS/2) 
                else:
                    time.sleep(0.1)
                    
            while self.sleep:
                time.sleep(0.1)
                
            # Ensures that we will run at least one complete loop before sleeping. 
            if self.sleep_now:
                self.sleep = True

        #EndWhilemanager

    def wait_for_manager_ready(self):
       """Returns when Manager thread is initialized"""
       while not self.manager.ready:
           sleep(0.1)

    def get_next_pic(self):
        """Retrieve the next picture's path from the manager and prepare it for
        display"""
        raise ValueError("Method should be implemented in child class")

    def viewer_init(self):
        """Run when Viewer enters INIT state"""
        raise ValueError("Method should be implemented in child class")

    def display_now(self):
        """Force a change of pictures now (i.e. skip transition)"""
        raise ValueError("Method should be implemented in child class")

    def start_transition(self):
        """Prep transition variables to start new transition"""
        raise ValueError("Method should be implemented in child class")

    def step_transition(self):
        """Step transition by one frame. Return True if transition is over"""
        raise ValueError("Method should be implemented in child class")

    def display_running(self):
        """Returns True/False indicating whether display object is still running"""
        raise ValueError("Method should be implemented in child class")

    def draw_slide(self):
        """Call underlying graphics library to draw the slide"""
        raise ValueError("Method should be implemented in child class")

    def cleanup(self):
        """Clean up any resources on Viewer exit"""
        raise ValueError("Method should be implemented in child class")



class TkinterViewer(ViewerBase):
    def __init__(self, manager):
        super().__init__(manager)


    def create_display(self, width, height):
        self.width = width
        self.height = height

        self.root = tk.Tk()  
        canvas = tk.Canvas(self.root, bg='white', highlightthickness=0, width=width, height=height)  
        canvas.pack(fill=tk.BOTH, expand=True) # configure canvas to occupy the whole main window
        root.config(cursor="none")

        # Attach method to exit full screen easily. Attach other keyboard methods here. 
        self.root.bind('<Escape>', self.toggle_fs)

        # Set first blank image
        img = get_image("pictures/black.png")
        self.current_img = ImageTk.PhotoImage(img)  
        self.img_container = canvas.create_image(0,0, anchor=tk.NW, image=self.current_img) 

        # use this to jump to main loop?
        self.root.after(1, ___)

        # TODO - Put this here?
        self.root.mainloop() 


    def close_gui():
        self.root.destroy()
        # TODO - set variables to None and reset states
    
    
    def toggle_fs(self, dummy=None):
        """Toggles the GUI window between fullscreen and 1/4 size"""
        if self.root.attributes('-fullscreen'):
            root.geometry('{}x{}}+100+100'.format(str(self.width/4), str(self.height/4)))
        else:
            self.root.attributes('-fullscreen', true)
        #state = False if self.root.attributes('-fullscreen') else True
        #self.root.attributes('-fullscreen', state)
        #if not state:
        #    root.geometry('{}x{}}+100+100'.format(str(self.width/4), str(self.height/4)))


    def get_next_pic(self):
        """Retrieve the next picture's path from the manager and prepare it for
        display"""
        im, orientation = self.manager.get_next_pic()
        tex = None
        
        orientation = image_utils.get_orientation(im)

        try:
            # Resize image to fit display? TODO - Figure out what this does...
            (w, h) = im.size
            max_dimension = MAX_SIZE # TODO changing MAX_SIZE causes serious crash on linux laptop!
            if not config.AUTO_RESIZE: # turned off for 4K display - will cause issues on RPi before v4
                max_dimension = 3840 # TODO check if mipmapping should be turned off with this setting.
            if w > max_dimension:
                im = im.resize((max_dimension, int(h * max_dimension / w)), resample=Image.BICUBIC)
            elif h > max_dimension:
                im = im.resize((int(w * max_dimension / h), max_dimension), resample=Image.BICUBIC)

            # Fix orientation if needed
            if orientation == 2:
                im = im.transpose(Image.FLIP_LEFT_RIGHT)
            elif orientation == 3:
                im = im.transpose(Image.ROTATE_180) # rotations are clockwise
            elif orientation == 4:
                im = im.transpose(Image.FLIP_TOP_BOTTOM)
            elif orientation == 5:
                im = im.transpose(Image.FLIP_LEFT_RIGHT).transpose(Image.ROTATE_270)
            elif orientation == 6:
                im = im.transpose(Image.ROTATE_270)
            elif orientation == 7:
                im = im.transpose(Image.FLIP_LEFT_RIGHT).transpose(Image.ROTATE_90)
            elif orientation == 8:
                im = im.transpose(Image.ROTATE_90)

            # Fill edges with blurred image if configured
            size = (self.DISPLAY.width, self.DISPLAY.height)
            if config.BLUR_EDGES:
                wh_rat = (size[0] * im.size[1]) / (size[1] * im.size[0])
                if abs(wh_rat - 1.0) > 0.01: # make a blurred background
                    (sc_b, sc_f) = (size[1] / im.size[1], size[0] / im.size[0])
                    if wh_rat > 1.0:
                        (sc_b, sc_f) = (sc_f, sc_b) # swap round
                    (w, h) =  (round(size[0] / sc_b / BLUR_ZOOM), round(size[1] / sc_b / BLUR_ZOOM))
                    (x, y) = (round(0.5 * (im.size[0] - w)), round(0.5 * (im.size[1] - h)))
                    box = (x, y, x + w, y + h)
                    blr_sz = (int(x * 512 / size[0]) for x in size)
                    im_b = im.resize(size, resample=0, box=box).resize(blr_sz)
                    im_b = im_b.filter(ImageFilter.GaussianBlur(BLUR_AMOUNT))
                    im_b = im_b.resize(size, resample=Image.BICUBIC)
                    im_b.putalpha(round(255 * EDGE_ALPHA))  # to apply the same EDGE_ALPHA as the no blur method.
                    im = im.resize((int(x * sc_f) for x in im.size), resample=Image.BICUBIC)
                    im_b.paste(im, box=(round(0.5 * (im_b.size[0] - im.size[0])),
                                        round(0.5 * (im_b.size[1] - im.size[1]))))
                    im = im_b # have to do this as paste applies in place

            # Create pi3D texture object from image object
            tex = pi3d.Texture(im, blend=True, m_repeat=True, automatic_resize=config.AUTO_RESIZE,
                            free_after_load=True)

        except Exception as e:
            if config.VERBOSE:
                print('''Couldn't load file {} giving error: {}'''.format(fname, e))
            tex = None

        

    def viewer_init(self):
        """Run when Viewer enters INIT state"""
        self.get_next_pic()
        if self.sfg is None:
            print("\n\nERROR - sfg is none\n\n")
        self.update_slide(self.sfg)
        self.alpha = 1.0
        self.step_transition()

    def update_slide(self, sfg, sbg=None):
        """Update the display. sfg = Slide foreground, sbg = slide background"""
        pass

    def display_now(self):
        """Force a change of pictures now (i.e. skip transition)"""
        self.start_transition()
        self.alpha=1.0
        self.step_transition()

    def start_transition(self):
        """Prep transition variables to start new transition"""
        self.update_slide(self.sfg, self.sbg)
        self.alpha = 0.0
        self.step_transition()

    def step_transition(self):
        """Step transition by one frame. Return True if transition is over"""
        # Update the alpha value during slide transition
        self.alpha += self.delta_alpha
        if self.alpha > 1.0:
            self.alpha = 1.0
        self.slide.unif[44] = self.alpha * self.alpha * (3.0 - 2.0 * self.alpha)
            
        # Indicate whether transition is over
        if self.alpha == 1.0:
            return True
        else:
            return False

    def display_running(self):
        """Returns True/False indicating whether display object is still running"""
        return self.DISPLAY.loop_running()

    def draw_slide(self):
        """Call underlying graphics library to draw the slide"""
        self.slide.draw()
        # self.text.draw()

    def cleanup(self):
        """Clean up any resources on Viewer exit"""
        self.DISPLAY.destroy()

    
                    



"""
Signals
1. Play/Pause
2. Forward/Backward 1 picture
    - Signal Viewer to transition now
3. To beginning/end of playlist. To next/previous playlist.
    - Update manager. Signal Viewer to transition now
4. Start new playlist (user selects new playlist to play now)
    - Could be manager selects new playlist, sends next playlist signal
5. Inject new picture that interrupts current playlist, and then playlist returns
    - Should this happen in manager? Or do we prefer instant 
6. Transition now.

-->  Start/stop and transition now (after getting next image)

"""