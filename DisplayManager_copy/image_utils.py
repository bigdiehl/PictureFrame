from PIL import Image  

# -------------------------------------------------
# NOTE - For all functions, size = (width, height)
# -------------------------------------------------

def get_frame_image(filename, size):
    """Opens the specified file, resizes to specified size while maintaining
    aspect ratio, and then adds a black background of specified size. """
    img = open_image(filename)
    img = resize_image(img, size)
    img = add_black_background(img, size)
    return img

def open_image(filename):
    # open raises a number of exceptions if an error occurs - https://pillow.readthedocs.io/en/stable/reference/Image.html
    # TODO - handles exceptions here?
    img = Image.open(filename)
    return img

def resize_image(img, size):
    """Resizes img to specified size while maintaining aspect ratio."""
    img.thumbnail(size,Image.ANTIALIAS)
    img = img.convert("RGBA")
    return img

def add_black_background(img, size):
    """Pastes img onto the middle of a black background of the specified size."""
    bg = Image.new("RGBA", size, (0, 0, 0, 255))
    bg.paste(img, (int((bg.size[0]-img.size[0])/2), 
                   int((bg.size[1]-img.size[1])/2)) )
    return bg


def get_orientation(img):
    """Read exif data to get orientation. Returns an oriention of 1 if no exif
    data is found. """
    orientation = 1
    try:
        exif_data = img._getexif()
        if database.EXIF_ORIENTATION in exif_data:
            orientation = int(exif_data[database.EXIF_ORIENTATION])
    except Exception: # Should really check error here but it's almost certainly due to lack of exif data
        pass
    
    return orientation


def get_exif_info(filename, img=None):
    """Expects img to be PIL Image object. More efficient to pass in already opened
    image since this function will discard any image it opens.
        - Returns None if no exif data is found."""
    if img is None: 
        img = open_image(filename)

    try: 
        exif_data = img._getexif()
    except: # should really check error here but it's almost certainly due to lack of exif data
        return None

    dt = os.path.getmtime(filename) # so use file last modified date
    orientation = 1
    location = ""

    if EXIF_DATID in exif_data:
        exif_dt = time.strptime(exif_data[EXIF_DATID], '%Y:%m:%d %H:%M:%S')
        dt = time.mktime(exif_dt)
    if EXIF_ORIENTATION in exif_data:
        orientation = int(exif_data[EXIF_ORIENTATION])
    #if config.LOAD_GEOLOC and geo.EXIF_GPSINFO in exif_data:
    #    location = geo.get_location(exif_data[geo.EXIF_GPSINFO])

    return (orientation, dt)


"""


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