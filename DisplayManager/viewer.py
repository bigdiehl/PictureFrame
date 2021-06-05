import time

import pi3d
import config
import math
import os

from PIL import Image, ExifTags, ImageFilter # these are needed for getting exif data from images
from pi3d.Texture import MAX_SIZE

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
            self.wait_for_manager_ready()
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
                        index += 1
                    
            elif self.state == view_state.PAUSED:
                pass
            
            self.draw_slide()

            # Sleep to reduce CPU load? Maybe make this more sophisticated?
            # Sleep different depending on the state?
            self.sleep = True
            if self.sleep:
                if self.state == view_state.TRANSITION:
                    time.sleep(1.0/config.FPS/2) 
                else:
                    time.sleep(0.1) 
                self.sleep = False

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
        super().__init__(manager)

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
        pic_info = self.manager.get_next_pic()

        fname = pic_info['path']
        orientation = pic_info['orientation']

        # Get pi3d texture - i.e. a texture object derived from the given
        # image file. Returns None if image cannot be loaded. 
        im = None
        tex = None

        # TODO - Figure out some better error handling than this
        try:
            # Create image object from image file
            ext = os.path.splitext(fname)[1].lower()
            if ext in ('.heif','.heic'):
                im = self.convert_heif(fname)
            else:
                im = Image.open(fname)

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

        # TODO - what to do if tex is None?
        self.sbg = self.sfg
        self.sfg = tex

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

        if self.sbg is None: # No transition
            self.sbg = sfg

        self.slide.set_textures([self.sfg, self.sbg])
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

    def display_now(self):
        """Force a change of pictures now (i.e. skip transition)"""
        raise ValueError("Method not implemented yet")

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








    

    @staticmethod
    def convert_heif(fname):
        try:
            import pyheif
            from PIL import Image

            heif_file = pyheif.read(fname)
            image = Image.frombytes(heif_file.mode, heif_file.size, heif_file.data,
                                    "raw", heif_file.mode, heif_file.stride)
            return image
        except Exception as e:
            print("have you installed pyheif?")
            print(e)
            return None

    @staticmethod
    def get_exif_info(file_path_name, im=None):
        dt = os.path.getmtime(file_path_name) # so use file last modified date
        orientation = 1
        location = ""
        try:
            if im is None:
                im = Image.open(file_path_name) # lazy operation so shouldn't load (better test though)
            exif_data = im._getexif() # TODO check if/when this becomes proper function
            if EXIF_DATID in exif_data:
                exif_dt = time.strptime(exif_data[EXIF_DATID], '%Y:%m:%d %H:%M:%S')
                dt = time.mktime(exif_dt)
            if EXIF_ORIENTATION in exif_data:
                orientation = int(exif_data[EXIF_ORIENTATION])
            if config.LOAD_GEOLOC and geo.EXIF_GPSINFO in exif_data:
                location = geo.get_location(exif_data[geo.EXIF_GPSINFO])
        except Exception as e: # NB should really check error here but it's almost certainly due to lack of exif data
            if config.VERBOSE:
                print('trying to read exif', e)
        fdt = time.strftime(config.SHOW_TEXT_FM, time.localtime(dt))
        return (orientation, dt, fdt, location)


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