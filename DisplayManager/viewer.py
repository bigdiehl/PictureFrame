import time

import pi3d
import config

import math
import os
from PIL import Image, ExifTags, ImageFilter # these are needed for getting exif data from images
import pyheif

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


config.PIC_DIR = r'/home/diehl/Pictures'


class ViewerBase:
    """Base class for picture frame viewer. Derived class can implement specific 
    methods (e.g. Pi3D libary objects and methods go in ViewerPi3D subclass)"""

    def __init__(self, manager):
        self.manager = manager #Handle to manager instance

        self.alive = True
        self.state = view_state.INIT
        self.last_state = None

        self.t_next_frame = 0
        self.t_next_pic = 0

    def run(self):
        """Main event loop. Implements a state machine. """
        
        index = 1
        next_pic_ready = False
        
        if self.state == view_state.INIT:
            self.wait_for_manager_ready():
            self.get_next_pic()
            self.viewer_init()

            self.state = view_state.DISPLAY
            self.t_next_pic = time.time() + config.TIME_DELAY

        while self.alive and self.display_running():

            t = time.time()
        
            # Check signal from other thread/processes.
            signal = None #Temporary TODO clean this up
            if 0: #Signal is received
                if signal == view_signal.PLAY:
                    self.state = self.last_state

                elif signal == view_signal.PAUSE:
                    self.last_state = self.state
                    self.state = view_state.PAUSED

                elif signal == view_signal.TRANSITION_NOW:
                    self.get_next_pic()
                    self.display_now()
                    self.state = view_state.DISPLAY
                    self.t_next_pic = t + config.TIME_DELAY
            else:
                time.sleep(0.1) # Go to sleep to reduce CPU load (?)


            if self.state == view_state.DISPLAY:
                # Note - Try to do any extra things during the display time. Try to not
                # do anything computationally expensive during transition time.
                
                # If it is time to transition, prepare variables and change state
                if t > self.t_next_pic:
                    self.start_transition()
                    self.state = view_state.TRANSITION
                    self.t_next_frame = t + 1.0/config.FPS

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
                        next_pic_ready = False
                        self.t_next_pic = t + config.TIME_DELAY
                        index += 1
                    
            elif self.state == view_state.PAUSED:
                pass
                

            self.draw_slide()
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

    
    
    

class ViewerPi3D(ViewerBase):
    def __init__(self, manager):
        super.__init__(manager)

        # pi3d main display elements
        self.DISPLAY = pi3d.Display.create(x=config.DISPLAY_X, y=config.DISPLAY_Y,
              w=config.DISPLAY_W, h=config.DISPLAY_H, frames_per_second=config.FPS,
              display_config=pi3d.DISPLAY_CONFIG_HIDE_CURSOR, background=config.BACKGROUND)
        self.CAMERA = pi3d.Camera(is_3d=False)

        self.shader = pi3d.Shader(config.SHADER)
        self.slide = pi3d.Sprite(camera=self.CAMERA, w=self.DISPLAY.width, h=self.DISPLAY.height, z=5.0)
        self.slide.set_shader(self.shader)

        # Set select slide parameters
        self.slide.unif[47] = config.EDGE_ALPHA
        self.slide.unif[54] = config.BLEND_TYPE

        # PointText and TextBlock. If SHOW_TEXT_TM <= 0 then this is just used for no images message
        grid_size = math.ceil(len(config.CODEPOINTS) ** 0.5)
        font = pi3d.Font(config.FONT_FILE, codepoints=config.CODEPOINTS, grid_size=grid_size)
        self.text = pi3d.PointText(font, self.CAMERA, max_chars=200, point_size=config.SHOW_TEXT_SZ)
        textblock = pi3d.TextBlock(x=-self.DISPLAY.width * 0.5 + 50, y=-self.DISPLAY.height * 0.4,
                                z=0.1, rot=0.0, char_count=199,
                                text_format="{}".format(" "), size=0.99,
                                spacing="F", space=0.02, colour=(1.0, 1.0, 1.0, 1.0))
        self.text.add_text_block(textblock)
        
        back_shader = pi3d.Shader("mat_flat")
        self.text_bkg = pi3d.Sprite(w=self.DISPLAY.width, h=90, y=-self.DISPLAY.height * 0.4 - 20, z=4.0)
        self.text_bkg.set_shader(back_shader)
        self.text_bkg.set_material((0, 0, 0))

        # Additional variables
        self.next_pic = None
        self.alpha = 0.0
        self.delta_alpha = 1.0 / (config.FPS * config.FADE_TIME)
        self.sfg = None
        self.sbg = None

    def get_next_pic(self):
        """Retrieve the next picture's path from the manager and prepare it for
        display"""


    def viewer_init(self):
        """Run when Viewer enters INIT state"""
        self.sfg = self.get_tex(files[0])
        self.update_slide(self.sfg)
        
        self.alpha = 1.0
        self.update_transition_alpha()

    def display_now(self):
        """Force a change of pictures now (i.e. skip transition)"""
        raise ValueError("Method should be implemented in child class")

    def start_transition(self):
        """Prep transition variables to start new transition"""
        self.update_slide(self.sfg, self.sbg)

        self.alpha = 0.0
        self.update_transition_alpha()

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
        self.DISPLAY.destroy()








    def update_slide(self, sfg, sbg=None):
        """Update the display. sfg = Slide foreground, sbg = slide background"""

        if sbg is None: # No transition
            sbg = sfg

        self.slide.set_textures([sfg, sbg])
        self.slide.unif[45:47] = self.slide.unif[42:44] # transfer front width and height factors to back
        self.slide.unif[51:53] = self.slide.unif[48:50] # transfer front width and height offsets

        # Set display ratios
        wh_rat = (self.DISPLAY.width * sfg.iy) / (self.DISPLAY.height * sfg.ix) #wh_rat = width to height ratio
        if (wh_rat > 1.0 and config.FIT) or (wh_rat <= 1.0 and not config.FIT):
            sz1, sz2, os1, os2 = 42, 43, 48, 49
        else:
            sz1, sz2, os1, os2 = 43, 42, 49, 48
            wh_rat = 1.0 / wh_rat
        self.slide.unif[sz1] = wh_rat
        self.slide.unif[sz2] = 1.0
        self.slide.unif[os1] = (wh_rat - 1.0) * 0.5
        self.slide.unif[os2] = 0.0

    def update_transition_alpha(self):
        """Update the alpha value during slide transition"""
        self.alpha += self.delta_alpha
        if self.alpha > 1.0:
            self.alpha = 1.0
        self.slide.unif[44] = self.alpha * self.alpha * (3.0 - 2.0 * self.alpha)
            
        # Indicate whether transition is over
        if self.alpha == 1.0:
            return True
        else:
            return False


    def get_tex(self, fname):
        """Get pi3d texture - i.e. a texture object derived from the given
        image file. Returns None if image cannot be loaded. """
        im = None
        tex = None

        try:
            ext = os.path.splitext(fname)[1].lower()
            if ext in ('.heif','.heic'):
                im = self.convert_heif(fname)
            else:
                im = Image.open(fname)

            tex = pi3d.Texture(im, blend=True, m_repeat=True, automatic_resize=config.AUTO_RESIZE,
                            free_after_load=True)

        except Exception as e:
            if config.VERBOSE:
                print('''Couldn't load file {} giving error: {}'''.format(fname, e))
            tex = None

        return tex

    @staticmethod
    def convert_heif(fname):
        try:

            heif_file = pyheif.read(fname)
            image = Image.frombytes(heif_file.mode, heif_file.size, heif_file.data,
                                    "raw", heif_file.mode, heif_file.stride)
            return image
        except Exception as e:
            print(e)
            return None


"""
===== ========================================== ==== ==
    vec3  description                                python
    ----- ------------------------------------------ -------
    index                                            from to
    ===== ========================================== ==== ==
       0  location                                     0   2
       1  rotation                                     3   5
       2  scale                                        6   8
       3  offset                                       9  11
       4  fog shade                                   12  14
       5  fog distance, fog alpha, shape alpha        15  17
       6  camera position                             18  20
       7  point light if 1: light0, light1, unused    21  23
       8  light0 position, direction vector           24  26
       9  light0 strength per shade                   27  29
      10  light0 ambient values                       30  32
      11  light1 position, direction vector           33  35
      12  light1 strength per shade                   36  38
      13  light1 ambient values                       39  41
      14  defocus dist_from, dist_to, amount          42  44 # also 2D x, y
      15  defocus frame width, height (only 2 used)   45  46 # also 2D w, h, tot_ht
      16  custom data space                           48  50
      17  custom data space                           51  53
      18  custom data space                           54  56
      19  custom data space                           57  59
    ===== ========================================== ==== ==
    """


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