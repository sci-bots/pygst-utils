#!/bin/bash
gst-launch-0.10 v4l2src device=/dev/video1 num-buffers=90 ! video/x-raw-yuv,width=640,height=480,framerate=10/1 ! queue ! videorate ! video/x-raw-yuv,framerate=10/1 ! queue ! ffmpegcolorspace ! ffenc_mpeg4 bitrate=1200000 ! avimux ! filesink location=temp.avi
