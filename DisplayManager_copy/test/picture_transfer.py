"""DESCRIPTION: Recursively transfer the contents of src_dir to dst_dir. 
Specifically transfer only image files, and resize the image file to fit 
the 1920x1080 resolution of the picture frame display (to save memory). """

import os
import sys

import subprocess

def run_command(command_str):
    subprocess.check_call(command_str, shell=True)

# TODO - Provide dst and src as command line inputs
src_dir = sys.argv[1]
dst_dir = sys.argv[2]

src_dir = os.path.abspath(src_dir)
dst_dir = os.path.abspath(dst_dir)

answer = input("You have selected\n\t{}\nas the source directory and \n\t{}\nas the \
destination directory. Continue?: ".format(src_dir, dst_dir))

if 'y' not in answer.lower():
    print("\nAborting...\n")
    quit()
else:
    print("\nCommencing file transfer...\n")
#src_dir = r'Source'
#dst_dir = r'Dest'

file_types = ['.jpg', '.jpeg', '.png']


types_found  = {}

log_file = open('Log', 'w')

for root, dirs, files in os.walk(src_dir):
    #print(root, dirs, files)
    dest = root.replace(src_dir, dst_dir)
    #print("\t", dest)
    #for directory in dirs:
    #    os.mkdir(os.path.join(dest, directory))

    # Ignore exception that is raised if file exists
    try:
        os.mkdir(dest)
    except FileExistsError:
        pass

    dest_files = os.listdir(dest)

    for f in files:
        ext = os.path.splitext(f)[-1].lower()
        if f not in dest_files and ext in file_types:
            #print("Image found: ", f)
            try:
                run_command(r'convert "{}" -resize 1920x1080 "{}"'.format(os.path.join(root, f), os.path.join(dest,f)))
            except Exception as e:
                log_file.write(os.path.join(root, f) + '\n')
        # Keep track of file types found. Just for giggles
        types_found[ext]=0

print("\nFound the following file types: ")
print(types_found.keys())
#run_command("convert {} -resize 1920x1080 {}")

log_file.close()
print("\nScript Complete!\n")