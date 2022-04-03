"""DESCRIPTION: Configuration parser that can interface with both cmd line
options and a seperate python config file. Normal use is to specify a config
file, and provide cmd line options that will override config file options. 

The config file is the main source of configuration, but cmd line options make
it easy to modify configurations on the fly (useful for testing)

The config file is simply another python module, containing the defined variables
listed below. 

To add another configuration variable
1 - Add the entry to the argparser (And fill in help documentation) (optional)
2 - Add the entry to the defined variables (Set to None if not defined in step 1)
3 - Add the entry to the seperate python config files

If any configuration variable is not defined via cmd line or config file, then
an error will be raised
"""

import argparse
import os
import sys
import importlib

def str_to_bool(x):
    """ function needed to convert str representation of bool values"""
    if len(x) == 0:
        return True # i.e. just arg will set to true
    return not (x.lower()[0] in ('0', 'f', 'n')) # i.e. 0,False,false,No,n

def str_to_tuple(x):
    return tuple(float(v) for v in x.replace("(","").replace(")","").split(","))

def parse_show_text(txt):
    show_text = 0
    txt = txt.lower()
    if "name" in txt:
        show_text |= 1
    if "date" in txt:
        show_text |= 2
    if "location" in txt:
        show_text |= 4
    return show_text

def semi_del_list(txt):
    """Converts semicolon delimited string into list of strings"""
    return [x for x in txt.split(';') if len(x) > 0]

def file_path_to_module_path(path):
    """Convert file path with '/' delimiters to module path with '.' delimiters"""
    # Remember to remove the .py
    path = path.split(r'/')
    path[-1] = path[-1].replace(".py","")
    path = ".".join(path)
    print(path)
    return path

parse = argparse.ArgumentParser("PictureFrame")
parse.add_argument("config_file",     type=str, help="Name of python config file (without the .py) Command line args overwrite config file options")
parse.add_argument("--verbose",       type=str_to_bool, help="show try/exception messages")
parse.add_argument("--pic_dirs",      type=semi_del_list, help="Semicolon delimited list of base directories to look for images")
parse.add_argument("--background",    type=str_to_tuple, help="RGBA to fill edges when fitting")
parse.add_argument("--show_text",     type=str_to_bool, help="show text, include combination of words: name, date, location")
parse.add_argument("--show_text_tm",  type=float, help="time to show text over the image")
parse.add_argument("--show_text_sz",  type=int, help="text character size")
parse.add_argument("--text_width",    type=int, help="number of character before breaking into new line")
parse.add_argument("--fit",           type=str_to_bool, help="shrink to fit screen i.e. don't crop")
parse.add_argument("--time_delay",    type=float, help="time between consecutive slide starts")
parse.add_argument("--fade_time",     type=float, help="change time during which slides overlap")
parse.add_argument("--fps",           type=float, help="frames per seconds for transition fade")
parse.add_argument("--display_w",     type=int, help="width of display surface (None will use max returned by hardware)")
parse.add_argument("--display_h",     type=int, help="height of display surface")

#parse.add_argument("--blur_amount",   type=float, help="larger values than 12 will increase processing load quite a bit")
#parse.add_argument("--blur_edges",    type=str_to_bool, help="use blurred version of image to fill edges - will override FIT = False")
args = parse.parse_args()


# --- Defined Configuration Variables/Names ---
VERBOSE         = args.verbose
PIC_DIRS        = args.pic_dirs
BACKGROUND_RGBA = args.background
SHOW_TEXT       = args.show_text
SHOW_TEXT_TIME  = args.show_text_tm
SHOW_TEXT_SIZE  = args.show_text_sz 
TEXT_WIDTH      = args.text_width 
FIT             = args.fit
TIME_DELAY      = args.time_delay 
FADE_TIME       = args.fade_time 
FPS             = args.fps
DISPLAY_W       = args.display_w 
DISPLAY_H       = args.display_h
LOG_PATH        = None              # Where to save log
LIGHT_SENSOR    = None              # T/F - Is there a light sensor
# ----------------------------------------------

# We assume that all valid configuration names are all uppercase, and everything else is not
defined_vars = [x for x in dir() if x.isupper()]

# Overwrite defined_vars with the value from the config file IF the defined_var
# is None (i.e. cmd line option was not specified)
sys.path.append(os.getcwd())
config = importlib.import_module(file_path_to_module_path(args.config_file))

config_vars = [x for x in dir(config) if x[0:2] != '__']
for var in config_vars:
    if getattr(sys.modules[__name__], var) is None:
        if var not in defined_vars:
            raise ValueError("{}: Not a valid configuration variable".format(var))
        else:
            # sys.modules[__name__] refers to current module
            setattr(sys.modules[__name__], var, getattr(config, var))


if VERBOSE:
    print("\nLoading from: {}".format(args.config_file))
    print("\nPictureFrame Configuration:")
    print("-------------------------------------------")
    for var in defined_vars:
        print("{} = {}".format(var, getattr(sys.modules[__name__], var)))


# If any variable has not been defined (i.e. is still None) then raise an error
for var in defined_vars:
    if getattr(sys.modules[__name__], var) is None:
        raise ValueError("Value for {} not specified".format(var))
        # TODO - More appropriate error handling? Suppress traceback at least
