import config
import time

import math
import numpy as np 

import os
from PIL import Image, ExifTags, ImageFilter # these are needed for getting exif data from images
from collections import namedtuple


"""
Data Structures:
* List of directory trees - one element for each root directory
* Directory tree - Tree of directories. Implemented as dictionary. Key = unique
value, value = directory name?? Also contain image lists with image names, and
available EXIF info
* Playlist order = circular list of directory references. Point to item in
directory tree.

How to order Playlists?
1. Random playlists
2. Alphabetical order - stepping down and up tree in sequence
3. By date - Not by individual image dates. Keep playlists together. Compute
average date for playlist images and use that date. 
4. By user-defined sequence. Useful? Seems difficult to implement, and not sure
it would be that useful. 

In general, keep playlists images together. 

Is it desirable to play photos completely randomly? Randomly within a playlist? 
By date within a playlist?


Directory_Name : [ Parent_Name, Parent_Path, [ Children_Names ], [ (Image Tuples) ], Date_Score ]

Where (Image Tuple) = (Filename, Rotation, Date, etc) (Maybe a named tuple)

* Randomize playlist order = get list of keys and randomize
* In tree order = Start at root, get children and recursively traverse tree
* By date = Return list of (Directory_Name, Date_Score) and sort by Date_Score
* Within a playlist, can sort Image tuples according to filename, date, or randomize
* Completely randomize images = randomly select playlist, randomly select image.

Issue - How to get full path name? Have parent name consist of the full path to 
that point? Additional element with path to parent? Construct path by following 
up to root?


Notes on image formats:
* JPEG: Best supported format. JPEG is very common, well supported, and contains
  exif data (thus containing date information)
* PNG: Supported. Generally doesn't come with exif data, so date information
  is not extracted. May have metadata, but reading of this is not implemented.
* HEIC: Newer format. Images are typically converted to JPEG when downloaded from
  phones/iCloud/Google Photos, so dealing with these images will likely not be 
  encountered unless connecting directly to these services. Pretty sure this
  format comes with lots of exif/metadata, but not sure how to read it.



  TODO - How to supplement Image_Database to handle SmugMug pictures???
  More generic interface???
  TODO - See if I can implement iterator(s) for Image_Database object
"""


# Global variables to make handling exif data easier
EXIF_DATE = None 
EXIF_ORIENTATION = None
for k in ExifTags.TAGS:
  if ExifTags.TAGS[k] == 'DateTimeOriginal':
    EXIF_DATE = k
  elif ExifTags.TAGS[k] == 'Orientation':
    EXIF_ORIENTATION = k


def isnan(num):
    """If an item does not equal itself, then it is a NaN"""
    return num != num

def list_subdirs(path):
    """Returns a list of full paths to all subdirectories in the given path"""
    return [os.path.join(path,d) for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))]

def list_images(path):
    """Return a list of filenames for all images in the given directory."""

    extensions = ['.png','.jpg','.jpeg','.heif','.heic']
    
    files = os.listdir(path)
    pics = []
    for filename in files:
        ext = os.path.splitext(filename)[1].lower()
        if ext in extensions and not filename.startswith('.'):
            pics.append(filename)
    return pics


class Image_Database(dict):
    """Main data structure to hold all information relating to available images
    to play. Implemented as a dictionary that holds a collection of Image_Directory
    objects, which act as nodes of branching tree structures. Image_Database
    can hold multiple data trees, and tree roots are stored in self.roots. Each
    tree represent a different image filesystem (e.g. local Pictures directory, 
    external storage directory, directory tied to cloud storage, etc)"""
    def __init__(self):
        self.roots = []

    def add_directory(self, directory):
        """Given a full directory path, create a new Image_Directory object 
        and add it to the dict. If a directory has no images, Image_Directory 
        object will have zero length images list"""

        # Make sure we have been given a real directory
        if os.path.isdir(directory):
            img_dir = Image_Directory(directory)

            # Only add the directory to the database if it has images in it (???)
            #if img_dir.images_present:

            # To ensure that all keys are unique, use the full path as the key
            self.__setitem__(directory, img_dir)
        else:
            #TODO - Work on better error handling than this
            raise ValueError("Not a directory: " + directory)

    def remove_directory(self, directory):
        """Remove the given directory and all child directories from the database"""
        pass

    def load_database(self, fname):
        """Load a database from a file."""

    def __repr__(self):
        rep = "============ Image Database ============\n"
        rep += "- Number of roots in db: {}\n".format(len(self.roots))
        rep += "- Folders in db: {}\n\n".format(self.__len__())

        for i in range(len(self.roots)):
            root = self.roots[i]
            rep += "Root {} at: {}\n".format(i+1, self.__getitem__(root).path)
            num_pics, num_folders = self.stats(root)
            rep += "Num folders: {}, Num Pictures: {}\n".format(num_folders,num_pics)
            rep += ("-"*30 + "\n")
            rep += self.repr(root, level=0)

            if i != (len(self.roots)-1):
                rep += "\n\n"

        rep += "="*40
        return rep

    def repr(self, dir_name, level):
        """Recursive representation function to support __repr__"""
        rep = "   "*level
        rep += (self.__getitem__(dir_name).__repr__() + "\n")
        for sub in self.__getitem__(dir_name).child_names:
            rep += self.repr(sub, level+1)
        return rep

    def stats(self, dir_name):
        """Recursively traverse tree to get basic stats"""
        num_pics = len(self.__getitem__(dir_name).images)
        num_folders = 1
        for sub in self.__getitem__(dir_name).child_names:
            np, nf = self.stats(sub)
            num_pics += np
            num_folders += nf
        
        return num_pics, num_folders


Img_Tup = namedtuple("Img_Tup", ['fname', 'date', 'orientation'])

class Image_Directory():
    """Holds the data relating to a given directory - images present, parent
    directory, child directories, etc. Acts as a node in a branching tree data 
    structure"""
    def __init__(self, path):
        
        if os.path.isdir(path):
            self.path = path
            self.name = os.path.basename(path)
            self.parent_name = os.path.dirname(path)
            self.child_names = list_subdirs(path)
            
            self.images = []
            img_names = list_images(path) 
            # TODO - is sort order here the same as the sort order the filesystem does?  I.e. does filesystem do a different lexigraphical ordering?
            # Sort image names by alphabetical order
            img_names.sort(key=lambda x: x.lower())
            for img_name in img_names:
                img_tuple = self.get_image_tuple(img_name, path)
                if img_tuple is not None:
                    self.images.append(self.get_image_tuple(img_name, path))
            
            self.date_score = self.compute_date_score()

            # Set flags indicating state of directory
            self.images_present = (len(self.images) > 0)
            self.subdirs_present = (len(self.child_names) > 0)
            self.image_reads_failed = len(img_names) - len(self.images)

            self.updated = True
            self.update_time = time.time()
        else:
            raise ValueError("Not a directory: " + directory)
            # TODO - Provide exception handling for this case
        
    def get_image_tuple(self, image_name, path):
        """Given an image name, produce a tuple containing 
        (Filename, Rotation, Date)
        TODO - Perhaps add other elements such as geotag"""

        # Default values
        date = float("nan")
        orientation = 1 # No orientation fix needed

        # EXIF data only for JPEG images
        ext = os.path.splitext(image_name)[1].lower()
        if ext == ".jpg" or ext == '.jpeg':
            try:
                im = None #Image.open(os.path.join(path, image_name))
                exif_data = None# im._getexif()

                if exif_data is not None:
                    if EXIF_DATE in exif_data:
                        # Convert date string to time.struct_time object
                        exif_date = time.strptime(exif_data[EXIF_DATE], r'%Y:%m:%d %H:%M:%S') 
                        # Converts struct_time object to total seconds since epoch
                        date = time.mktime(exif_date)

                    if EXIF_ORIENTATION in exif_data:
                        orientation = int(exif_data[EXIF_ORIENTATION])
               
                    #if config.LOAD_GEOLOC and geo.EXIF_GPSINFO in exif_data:
                    #    location = geo.get_location(exif_data[geo.EXIF_GPSINFO])
                    
                    # Convert time to date string of specified format. For display purposes
                    # Perhaps move to viewer functionality
                    #fdt = time.strftime(config.SHOW_TEXT_FM, time.localtime(dt))

            except Exception as e:
                # TODO - Just print exception, or log occurence? Setup logging?
                print("Error reading image: ", os.path.join(path, image_name))
                print("Received: ", e)
                return None

        return Img_Tup(image_name, date, orientation)

    def compute_date_score(self):
        """Take an average of the image dates to compute an average date score"""
        n = 0
        dt = 0
        for img in self.images:
            if not isnan(img.date):
                dt += img.date
                n += 1

        if dt > 0:
            return dt/n

        return float("nan")

    def __repr__(self):
        rep = ("{}, Pics: {}, Date Score: {:e} ".format(self.name, len(self.images), 
            self.date_score))
        return rep
    
