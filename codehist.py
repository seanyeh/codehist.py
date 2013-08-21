import argparse
import glob
import json
from math import log10
from os import system, listdir, makedirs, rename
from os.path import isfile, isdir, join
import re
from subprocess import call

GEN_HTML_CMD = "vim %s +TOhtml '+w %s' '+qall!'"
GEN_IMAGES_CMD = "wkhtmltoimage %s %s"
GEN_VIDEO_CMD = "ffmpeg -f image2 -r 1/.2 -pattern_type glob -i \"%s\" \
        -vf \"scale=640:trunc(ow/a/2)*2\" -r 30 %s"

def generate_files(patch_dir, files_dir):
    # get file_ext (from patch_dir/patch.1.file_ext)
    first_patch_glob = join(patch_dir, "patch.1.*")
    first_patch = glob.glob(first_patch_glob)[0]
    file_ext = first_patch[first_patch.rfind('.') + 1:]

    patches = []

    i = 1;
    patch_fp = join(patch_dir, "patch.%d." + file_ext)
    while isfile(patch_fp%i):
        patches.append(patch_fp%i)
        i += 1

    # Copy START -> TMP
    start_fp = join(patch_dir, "START")
    temp_fp = join(patch_dir, "TMP")
    system("cp %s %s" % (start_fp, temp_fp))

    i = 1
    for p in reversed(patches):
        file_fp = join(files_dir, "file.%d.%s" % (i, file_ext))
        system("cp %s %s" % (temp_fp, file_fp))
        system("patch %s < %s" % (temp_fp, p))
        i += 1

    # Add last one
    file_fp = join(files_dir, "file.%d.%s" % (i, file_ext))
    system("cp %s %s" % (temp_fp, file_fp))

    # Now normalize files
    num_files = len(
            [ f for f in listdir(files_dir) if isfile(join(files_dir,f)) ])
    num_digits = int(log10(num_files)) + 1
    print("num digits: %d"%num_digits)
    normalize_files(files_dir, num_digits)


def get_lc(fp):
    return sum(1 for line in open(fp))


def normalize_files(files_dir, num_digits):
    files = [ f for f in listdir(files_dir) if isfile(join(files_dir, f)) ]

    lc_dict = {}
    # first pass: get max lines
    max_lines = 0
    for f in files:
        fp = join(files_dir, f)
        lc = get_lc(fp)

        # Cache results in dict
        lc_dict[fp] = lc

        if lc > max_lines:
            max_lines = lc

    # second pass: add newlines
    for f in files:
        fp = join(files_dir, f)
        with open(fp, "a") as myfile:
            myfile.write( "\n" * (max_lines - lc_dict[fp]))
        

        # Also rename file with padded 0's
        index2 = fp.rfind('.')# search for later one first
        index1 = fp.rfind('.', 0, index2) + 1

        # should probably error check this someday
        num = int(fp[index1:index2])

        new_fp = fp[:index1] + format(num,"0%dd" % num_digits) + fp[index2:]

        rename(fp, new_fp)


# Call with generate_html(....,"vim %s +TOhtml '+w %s' '+qall!')
def generate_html(files_dir, html_dir, cmd = GEN_HTML_CMD):
    files = [ f for f in listdir(files_dir) if isfile(join(files_dir, f)) ]
    for f in files:
        input_fp = join(files_dir, f)
        output_fp = join(html_dir, f + ".html")
        system( cmd%(input_fp, output_fp) )


# Call with ..."wkhtmltoimage %s %s"
def generate_images(html_dir, images_dir, 
        cmd = GEN_IMAGES_CMD, filetype = ".jpg"):

    files = [ f for f in listdir(html_dir) if isfile(join(html_dir, f)) ]
    for f in files:
        input_fp = join(html_dir, f)
        output_fp = join(images_dir, f + filetype)
        system( cmd%(input_fp, output_fp) )


# cmd = "ffmpeg -f image2 -r 1/.5 -i %s -r 30 %s"
def generate_video(images_dir, video_dir, cmd = GEN_VIDEO_CMD):
    images_fp = join(images_dir, "*.jpg")
    video_fp = join(video_dir, "code-the-movie.mp4")
    system(cmd % (images_fp, video_fp))


def create_dir(d):
    try:
        makedirs(d)
    except FileExistsError:
        pass


def file_to_string(fp):
    f = open(fp, 'r')
    lines = f.readlines()
    f.close()

    return ''.join(list(map(lambda x: x.strip(), lines)))


def generate_json(html_dir, json_dir):
    json_dict = {}

    files = [ f for f in listdir(html_dir) if isfile(join(html_dir, f)) ]

    # sort
    files.sort()
    
    i = 0
    for f in files:
        file_contents = file_to_string(join(html_dir, f))
        style = re.search("<style[^>]*>([\w\W]*)<\/style>",file_contents).groups()[0]
        body = re.search("<body>([\w\W]*)<\/body>",file_contents).groups()[0]
        json_dict[i] = {'style': style, 'body': body}
        i += 1

    json_fp = join(json_dir, "data.json")
    with open(json_fp, 'w') as outfile:
        json.dump(json_dict, outfile)


FUNCS = [{'from': 'diffs', 'func': generate_files, 'to': 'files'}, 
        {'from': 'files', 'func': generate_html, 'to': 'html'},
        {'from': 'html', 'func': generate_json, 'to': 'json'}]


def get_func_index(s, key):
    '''Return the index of FUNCS with s == 'from' key'''
    index = 0
    for func_obj in FUNCS:
        if func_obj[key] == s:
            return index
        index += 1
    return -1
    
    


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('input_dir')
    parser.add_argument('output_dir')
    parser.add_argument('--input-type', default='diffs')
    parser.add_argument('--output-type', default='json')

    args = parser.parse_args()

    print(args)
    
    if isfile(args.output_dir) or isdir(args.output_dir):
        print("Output dir already exists: %s" % args.output_dir)
        return

    input_index = get_func_index(args.input_type, 'from')
    output_index = get_func_index(args.output_type, 'to')
    cur_index = input_index

    if (input_index == -1 or output_index == -1):
        print("Invalid input or output type")
        return

    if (input_index > output_index):
        print("Input-type should precede output-type")
        return

    while cur_index <= output_index:
        cur = FUNCS[cur_index]

        # default dir names (stored in .tmp)
        input_dir = join(args.output_dir, '.tmp', cur['from'])
        output_dir = join(args.output_dir, '.tmp', cur['to'])

        # if first step
        if cur_index == input_index:
            input_dir = args.input_dir
        # if last step (not mutually exclusive to above)
        if cur_index == output_index:
            output_dir = args.output_dir

        create_dir(input_dir)
        create_dir(output_dir)

        # debug
        print("input_dir: %s output_dir: %s cur: %s" % (input_dir, output_dir,
            cur))

        # Generate the files!
        cur['func'](input_dir, output_dir)

        cur_index += 1


if __name__ == "__main__":
    main()
