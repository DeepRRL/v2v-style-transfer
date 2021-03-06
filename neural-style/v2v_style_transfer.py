## Video2video style transfer using merged styles with sliding window
##
## Input: multiple keyframes from style video (e.g., movie trailer)
## Output: stylized frames for target video
##       Each frame is stylized using blended multiple style keyframes.

import sys, os, re, argparse
from subprocess import call

def style_transfer_avg(input_frames, style_frames, 
                input_dir, style_dir, output_dir, niter=1000, gpu=0):
    """
    input_frames: file names of original frame images
    style_frames: file names of the keyframes as styles
    input_dir: directory for input frames
    style_dir: directory for style frames
    output_dir: directory for output stylized frames
    """

    for input_frame in input_frames:
        style_frames = map(lambda file: style_dir+"/"+file, style_frames)
        print "Style transfer for", input_dir+"/"+input_frame, \
                "from styles", ",".join(style_frames)

        call(" ".join(["th neural_style.lua", 
            "-content_image", input_dir+"/"+input_frame, 
            "-init image",
            "-style_image", ",".join(style_frames),
            "-output_image", output_dir+"/avg-stylized-"+input_frame,
            "-num_iterations", str(niter),
            "-save_iter", str(0), 
            "-gpu", str(gpu)]), shell=True)


def style_transfer_sw(matched, input_dir, style_dir, output_dir, niter=1000, gpu=0):
    """
    matched: a dictionary: key=input_frames, 
        value=(list of style frames to use for it, weights for diff styles)
    input_dir: directory for input frames
    style_dir: directory for style frames
    output_dir: directory for output stylized frames
    """

    for input_frame in matched:
        (style_frames, weights) = matched[input_frame]
        style_frames = map(lambda file: style_dir+"/"+file, style_frames)
        print "Style transfer for", input_frame, "from styles", ",".join(style_frames), \
                "using weights", weights

        call(" ".join(["th neural_style.lua", 
            "-content_image", input_dir+"/"+input_frame, 
            "-init image",
            "-style_image", ",".join(style_frames),
            "-style_blend_weights", ",".join(map(str, weights)),
            "-output_image", output_dir+"/stylized-"+input_frame,
            "-num_iterations", str(niter),
            "-save_iter", str(0), 
            "-gpu", str(gpu)]), shell=True)


def match_frames(input_frames, style_frames, window=2):
    """
    Deside which style frames to use for each input frames,
    such that the temporal transitioning is maintained.
    Note: the only digits in the filename must be the frame number

    window: how many style frames to use at a time
    return a dictionary: key=input_frames, 
        value=list of style frames to use for it
    """

    input_times = map(lambda file: float(re.sub("\D", "", file)), input_frames)
    style_times = map(lambda file: float(re.sub("\D", "", file)), style_frames)

    ## transform such that both times are within [0, 1]
    input_times = [time / input_times[-1] for time in input_times]
    style_times = [time / style_times[-1] for time in style_times]

    matched = dict()
    start, end = 0, window
    mid = (start + end) / 2
    for i in range(len(input_frames)):
        ## move to next group of styles
        if input_times[i] > style_times[mid] and end < len(style_times):
            start += 1
            end += 1
            mid = (start + end) / 2

        ## weight different styles according to their distance to input_time
        weights = [0] * window
        for k in range(window):
            weights[k] = 1.0 / max(abs(input_times[i] - style_times[start+k]), 1e-2)
        ## normalize to sum to 10
        weights = [10 * w / sum(weights) for w in weights]
        matched[input_frames[i]] = (style_frames[start:end], weights)

        # print input_frames[i], (start, end-1), weights 

    return matched


def images_in_dir(input_dir, ext="jpg"):
    """
    List all names of the images under a directory;
    images are ordered according to frame number.
    Note: the only digits in the filename must be the frame number
    """
    images = [file for file in os.listdir(input_dir) if ext in file]
    ## sort image files according to frame number (the only digits)
    images.sort(key=lambda file: int(re.sub("\D", "", file)))
    return images


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-input_dir", "--input_frame_dir", default="../data/pig/frames")
    parser.add_argument("-style_dir", "--style_frame_dir", default="../trailers/5m/frames_5m")
    parser.add_argument("-output_dir", "--output_dir", default="../data/pig/5m_frames")
    parser.add_argument("-method", "--method", default="sw")
    parser.add_argument("-niter", "--niter", default=1000)
    parser.add_argument("-gpu", "--gpu", default=0)
    parser.add_argument("-window", "--window", default=2)
    args = parser.parse_args()

    input_frames = images_in_dir(args.input_frame_dir)
    style_frames = images_in_dir(args.style_frame_dir)

    ## sliding window
    if args.method == "sw":
        ## match which style files to use for which input frame
        matched = match_frames(input_frames, style_frames, args.window)
        style_transfer_sw(matched, args.input_frame_dir, args.style_frame_dir, 
                        args.output_dir, args.niter, args.gpu)
        
    ## average style
    elif args.method == "avg":
        style_transfer_avg(input_frames, style_frames, 
            args.input_frame_dir, args.style_frame_dir, args.output_dir, args.niter, args.gpu)

