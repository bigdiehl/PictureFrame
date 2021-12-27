
import config
import time
import math
import numpy as np 
import random
import os
from PIL import Image, ExifTags, ImageFilter # these are needed for getting exif data from images
from collections import namedtuple
import itertools
import bisect
import logging

from database import *

"""Exception Handling:
1. What to do if no media is inserted at all?
2. What to do if database is out of sync - passing invalid picture path to Viewer

"""

def weighted_choice(choices, weights):
    """For Python >= 3.6 there exists the random.choices function to do a
    weighted random choice. For lower versions, do the following """

    # Arrange weights in a cumulative distribution. 
    # E.g. weights [1,3,5] --> cumlist [1,4,9]
    cumdist = list(itertools.accumulate(weights))
    # Pick a random number within the range of cumdist
    x = random.random() * cumdist[-1]
    # Use bisect() to find the index where x would fall if sorted into cumdist
    # E.g. x = 1.3 --> index 1 (falls between 1 and 4 in cumlist)
    return choices[bisect.bisect(cumdist, x)]

def convert_heif(fname):
    """Attempt to open .heif image file and return a PIL image object if 
    successful and None oterwise"""
    try:
        import pyheif

        heif_file = pyheif.read(fname)
        image = Image.frombytes(heif_file.mode, heif_file.size, heif_file.data,
                                "raw", heif_file.mode, heif_file.stride)
        return image
    except ImportError as e:
        logger.error("Cannot handle .heif file. pyheif not installed.")
        raise ValueError("pyheif not installed")



class Manager:
    def __init__(self):
        self.alive = True
        self.ready = False
        
        self.settings = self.load_settings()

        # Can maintain multiple image storage locations 
        self.root_dirs = config.PIC_DIRS
        self.pic_db = Image_Database()

        # If no database can be loaded, start from scratch
        if self.settings['Image DB'] is None:
            self.load_all_dirs(config.PIC_DIRS)
            logging.info("\n" + self.pic_db.__repr__())
        # Otherwise prepare at least the first directory before Viewer starts
        else:
            self.prepare_first_playlist()

        self.current_playlist = None  # Image_Directory object
        self.current_pic = None       # Int index of current image

        # --- Variables to support play methods ---
        self.counter = 0
        self.pic_idxs = []
        self.now_imgs = []
        self.return_playlist = None
        self.return_pic = None
        self.return_play_method = None
        # -----------------------------------------

        #self.set_play_method(self.play_randomly)
        #self.set_play_method(self.play_random_playlist)
        self.set_play_method(self.play_random_playlist_randomly)

        # 1/0 mask to instruct play modes which subset of playlists are available
        self.dirs_to_play = {img_dir : 1 for img_dir in self.pic_db.keys()}

        # Testing 
        self.dirs_to_play['/home/diehl/Pictures'] = 0
        self.dirs_to_play['/home/diehl/Pictures/Sub1'] = 0

    
    def run(self):
        """Manager is primarily in charge of keeping pic database up to date, 
        and in handling logic of which image to hand off next to Viewer. The run
        function handles the first part of those responsibilities"""

        self.ready = True # TODO - move this to init function
        while self.alive:
            time.sleep(0.5)

    def get_next_pic(self):
        """Main method called by Viewer to get the next picture to be played. 
        Attempts for 1/2 frame delay time to find an image that can be opened 
        as a PIL image object. If an image object cannot be created in that time,
        then the default error image is passed to the viewer.
        
        TODO: Must be thread safe."""

        t_timeout = time.time() + config.TIME_DELAY/2

        while time.time() < t_timeout:
            try:
                self.play_method()
                img_tuple = self.current_playlist.images[self.current_pic]
                pic_path = os.path.join(self.current_playlist.path, img_tuple.fname)

                if os.path.isfile(pic_path):
                    ext = os.path.splitext(pic_path)[1].lower()
                    if ext in ('.heif','.heic'):
                        im = self.convert_heif(pic_path)
                    else:
                        im = Image.open(pic_path)

                    logging.info("Now playing: {}, pic: {} ({})".format(self.current_playlist.path, 
                        img_tuple.fname, self.current_pic ))

                    return im, img_tuple.orientation

                else: 
                    logging.error("manager.get_next_pic() - Could not find " + pic_path)

            except Exception as e:
                    logging.error("Error obtaining image file: ", e)

        return {"path" : "PictureFrame2020img.jpg", "orientation" : 1 }


    def load_all_dirs(self, root_dirs):
        """Method to recursively search from give root directories and add all 
        directories to the database"""
        for root_dir in root_dirs:
            t_start = time.time()
            self.pic_db.add_directory(root_dir)

            # Keep track of root names
            if root_dir not in self.pic_db.roots:
                self.pic_db.roots.append(root_dir)

            # Recursively add all subdirectories to pic_db
            for root, dirnames, filenames in os.walk(root_dir):
                for directory in dirnames:
                    self.pic_db.add_directory(os.path.join(root, directory))

            logging.info("Image root {:} loaded in {:.1f} sec: ".format(root_dir, time.time()-t_start))

    def load_settings(self):
        return ({'Image DB' : None, 
                 '1' : 0})

    def load_database(self):
        return None

    def prepare_first_playlist(self):
        return None

    def set_play_method(self, method):
        """Expect method to be a callback function"""
        self.play_method = method

        self.current_playlist = None
        self.current_pic = None

    def play_mask(self, playlists): 
        """Applies the dirs_to_play mask to return a subset of playlists available
        to play. Expect all play methods to call this function"""
        return [x for x in playlists if self.dirs_to_play[x]]

    # *************** PLAY MODES *********************************************

    #TODO - Perhaos we should shuffle playlists and play them instead of random 
    #selection. That way each playlist will run at least once before a repeat
    #happens
    def play_randomly(self):
        """Play method to play images completely randomly"""
        # Pick a random playlist. Weight playlist probability by number of 
        # pictures in playlist

        # TODO - Make sure we don't play the same picture twice in a row

        # To ensure a uniform probability over all pictures, must select playlists
        # using weighted distribution since not all playlists have same size.
        # This also neatly removes the chance of selecting playlist with zero pics.
        playlists = self.play_mask(self.pic_db.keys())
        weights = [len(self.pic_db[img_dir].images) for img_dir in playlists]
        self.current_playlist = self.pic_db[weighted_choice(playlists, weights)]

        # Pick a random image tuple index using a uniform distribution
        self.current_pic = random.randint(0,len(self.current_playlist.images)-1)

    def play_random_playlist(self):
        """Selects a playlist at random and then sequentially plays the images
        within that playlist"""

        # Load a new playlist when starting play method, or when we have reached
        # the end of the image list
        load_new = False
        if self.current_playlist is None or self.current_pic is None:
            load_new = True
        elif self.current_pic >= (len(self.current_playlist.images)-1):
            load_new = True

        if load_new:
            # Select directories that have images
            playlists = [x for x in self.pic_db.keys() if len(self.pic_db[x].images) > 0 ]
            playlists = self.play_mask(playlists)
            
            # Remove current playlist from list so we don't play the same 
            # playlist twice in a row. Unless there is only a single playlist.
            if self.current_playlist is not None:
                if self.current_playlist.path in playlists and len(playlists) > 1:
                    idx = playlists.index(self.current_playlist.path)
                    playlists.pop(idx)

            # Select playlist using uniform distribution
            self.current_playlist = self.pic_db[playlists[random.randint(0, len(playlists)-1)]]
            self.current_pic = 0

        else:
            self.current_pic += 1

        
    def play_random_playlist_randomly(self):
        """Selects a playlist at random, and then randomly plays the images
        within that playlist"""

        # TODO - Add ability to play up to N photos, and then switch

        load_new = False
        if self.current_playlist is None or self.current_pic is None:
            load_new = True
        elif self.counter >= (len(self.current_playlist.images)-1):
            load_new = True

        if load_new:
            # Select directories that have images
            playlists = [x for x in self.pic_db.keys() if len(self.pic_db[x].images) > 0 ]
            playlists = self.play_mask(playlists)

            # Remove current playlist from list so we don't play the same 
            # playlist twice in a row. Unless there is only a single playlist.
            if self.current_playlist is not None:
                if self.current_playlist.path in playlists and len(playlists) > 1:
                    idx = playlists.index(self.current_playlist.path)
                    playlists.pop(idx)

            # Select playlist using uniform distribution
            self.current_playlist = self.pic_db[playlists[random.randint(0, len(playlists)-1)]]
            
            self.pic_idxs = list(range(len(self.current_playlist.images)))
            random.shuffle(self.pic_idxs)
            
            self.counter = 0
        else:
            self.counter += 1

        self.current_pic = self.pic_idxs[self.counter]
        

    def play_sequentially(self):
        """Plays images and playlists in order. Order = alphabetical, recursively
        goes traverses the directory tree in a depth first fashion"""
        # playlists = self.play_mask(playlists)
        pass

    def play_date_range(self):
        """Plays all images within a specified date range"""
        # playlists = self.play_mask(playlists)
        pass

    def set_play_now(self, img_dir, imgs=None):
        """Set up play mode that interrupts the current play mode to play a 
        given set of images."""

        if not os.path.isdir(img_dir):
            raise ValueError("Invalid directory path given to set_play_now()")

        # Save current play state so we can return 
        self.return_playlist = self.current_playlist
        self.return_pic = self.current_pic
        self.return_play_method = self.play_method

        self.set_play_method(self.play_now)

        # Since imgs may be a subset of all the images in img_dir, create a 
        # temporary Image_Directory object to hold play information
        self.current_playlist = Image_Directory(img_dir)
        self.current_pic = 0

        if imgs is not None:
            if len(imgs) == 0:
                raise ValueError("Zero length play now list")
            self.current_playlist.images = imgs        

    def play_now(self):
        """Play mode that interrupts the current play mode to play a given set
        of images. When images have played, play returns to previous play control"""
        
        if self.current_pic is None:
            self.current_pic = 0
        elif self.current_pic < (len(self.current_playlist.images) - 1):
            self.current_pic += 1
        else:
            # Restore and run previous play state
            self.set_play_method(self.return_play_method)
            self.current_pic = self.return_pic
            self.current_playlist = self.return_playlist
            self.play_method()



    # *************** END PLAY MODES ******************************************
    

    @staticmethod
    def get_files(root):
        """Return a list of paths for all images in the given directory."""

        extensions = ['.png','.jpg','.jpeg','.heif','.heic']
        # os.stat(path).st_mtime gives time directory was last modified
        # by 'modified', we mean last time a file was added/removed, not modified
        # or when the directory file itself was modified. 

        files = os.listdir(root)
        pics = []
        for filename in files:
            ext = os.path.splitext(filename)[1].lower()
            if ext in extensions and not filename.startswith('.'):
                file_path_name = os.path.join(root, filename)
                orientation = 1 # this is default - unrotated
                dt = None # if exif data DISPLAYDISPLAYnot read - used for checking in tex_load
                pics.append(file_path_name)
        return pics



"""
TODO - Fun to add new pictures, and see them on the picture frame right away.
With Meural pic frame, you add pics and then the system resets with the new 
pics on the top

* Need to modify random select so it doesn't select the same thing twice in a row.
* Need to do an overview of error handling
* Need to make things thread safe
* Need to implement manager database updating loop. Figure out how to do this intelligently.

Behavior:
1. Do an initial scan of the filesystem if (1) there is not an existing file 
with database information or (2) if there is a new filesystem

2. Do an initial update of filesystems if an initial scan wasn't done. Delete
any entries in database that weren't found during scan (ie set a flag to false 
for each entry, and then update flag as items are found.)

3. Every xx sec, do another update. Have mechanism for user to request immediate
update.

4. Need behavior to manage playlist selection. 

6. Need method to communicate with viewer (manager is ready to start, viewer 
wants the next picture/playlist, viewer wants the previous picture/playlist, etc)


Settings
------------------------
* 

PLAY METHODS:
1. Play images randomly - Random directory selection, random image selection
2. Play playlists randomly - Random directory selection, play images in order
    - What is "in order"? By name? Probably. Sequential pictures should have 
    sequential names
3. Play in order - Recursively step through directories and play in order
    - What is "in order"? By name would be most straightforward. Only other real 
    option would be to have interface to select play order. Probably more complicated
    than is worthwhile for this application
4. Play by date range - Search for all images in a date range. Play in order 
    - Can only play pictures with date information (ie JPEGS)
    - Play by date order? Or randomly?
5. Dwell on picture - stay on injected image(s) for a certain period of time. Used
   when emailing pictures in.

If we got really fancy, we could do stuff like make a schedule. Play a specific
date range on a specific day, or play a specific set of playlists on a specific day
    - Could be fun for birthdays, Sundays, anniversaries, etc.
    - For example, play wedding pictures on anniversary.
    - Would probably be easiest to set this up in a configuration file. Don't 
    introduce to web interface

So we need to have general method for:
1. Play method
    - Callback function? Every time get_pic is called the currently registered
    callback function is run?
2. Playlist selection (Which subset of playlists are available to the play method)
    - dirs_to_play = {dirname : 0/1} - Flags to indicate if a playlist should
      be played
    - Create generic method to set flags? 

How to set up a schedule? Basically just sets dirs_to_play and other settings 
when a certain date occurs. If we want to add this, this shouldn't be too hard I think
















"""


def get_files(dt_from=None, dt_to=None):
  # dt_from and dt_to are either None or tuples (2016,12,25)
  if dt_from is not None:
    dt_from = time.mktime(dt_from + (0, 0, 0, 0, 0, 0))
  if dt_to is not None:
    dt_to = time.mktime(dt_to + (0, 0, 0, 0, 0, 0))
  global shuffle, EXIF_DATID, last_file_change
  file_list = []
  extensions = ['.png','.jpg','.jpeg','.heif','.heic'] # can add to these
  picture_dir = os.path.join(config.PIC_DIR, subdirectory)
  for root, _dirnames, filenames in os.walk(picture_dir):
      # Time of alteration in a directory. Updates when file added/removed.
      # Not updated when a file is modified.
      mod_tm = os.stat(root).st_mtime
      if mod_tm > last_file_change:
        last_file_change = mod_tm
      for filename in filenames:
          ext = os.path.splitext(filename)[1].lower()
          if ext in extensions and not '.AppleDouble' in root and not filename.startswith('.'):
              file_path_name = os.path.join(root, filename)
              include_flag = True
              orientation = 1 # this is default - unrotated
              dt = None # if exif data not read - used for checking in tex_load
              fdt = None
              location = ""
              if not config.DELAY_EXIF and EXIF_DATID is not None and EXIF_ORIENTATION is not None:
                (orientation, dt, fdt, location) = get_exif_info(file_path_name)
                if (dt_from is not None and dt < dt_from) or (dt_to is not None and dt > dt_to):
                  include_flag = False
              if include_flag:
                # iFiles now list of lists [file_name, orientation, file_changed_date, exif_date, exif_formatted_date]
                file_list.append([file_path_name,
                                  orientation,
                                  os.path.getmtime(file_path_name),
                                  dt,
                                  fdt,
                                  location])
  if shuffle:
    file_list.sort(key=lambda x: x[2]) # will be later files last
    temp_list_first = file_list[-config.RECENT_N:]
    temp_list_last = file_list[:-config.RECENT_N]
    random.seed()
    random.shuffle(temp_list_first)
    random.shuffle(temp_list_last)
    file_list = temp_list_first + temp_list_last
  else:
    file_list.sort() # if not suffled; sort by name
  return file_list, len(file_list) # tuple of file list, number of pictures
