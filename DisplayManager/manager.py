
import pi3d
import config
import time

import math

import os
from PIL import Image, ExifTags, ImageFilter # these are needed for getting exif data from images


class Manager:
    def __init__(self):
        self.alive = True
        self.ready = False
    
    def run(self):
      self.ready = True # TODO - move this to init function
        while self.alive:
            time.sleep(0.5)
            #print("Manager")

    @staticmethod
    def get_files(root):

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


    def get_exif_info(self, file_path_name, im=None):
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
Behavior:
1. Do an initial scan of the filesystem if (1) there is not an existing file 
with database information or (2) if there is a new filesystem

2. Do an initial update of filesystems if an initial scan wasn't done. Delete
any entries in database that weren't found during scan (ie set a flag to false 
for each entry, and then update flag as items are found.)

3. Every xx sec, do another update. Have mechanism for user to request immediate
update.

4. Need behavior to manage playlist selection. 

5. Need method to share resource with viewer (Database object that is shared 
by both viewer and manager?)

6. Need method to communicate with viewer (manager is ready to start, viewer 
wants the next picture/playlist, viewer wants the previous picture/playlist, etc)

* May just be easier to hand viewer an entire playlist at a time. "Playlist" 
consists of filenames/path and some data such as rotation, date, etc

* Can just give viewer/manager handles of each other. That way they can call each
other's functions and check variable values. 

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
      mod_tm = os.stat(root).st_mtime # time of alteration in a directory
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
