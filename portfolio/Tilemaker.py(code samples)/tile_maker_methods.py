#!/usr/bin/python

import openslide
from openslide import OpenSlide, OpenSlideError
import os
import sys
import PatchedPIL
from PatchedPIL import Image, ImageFile, BmpImagePlugin, ImagePalette, ImageDraw
import random
import time
import argparse
import csv
import cv2



#draws a rectangle around each tile in thumbnail
def rec(image, x, y, x1, y1, color):
	x1 = int(x1 - 1)
	y1 = int(y1 - 1)
	x = int(x)
	y = int(y)
	for X in range(x, x1):
		image.putpixel((X,y), color)
		image.putpixel((X,y1), color)
	for Y in range(y, y1):
		image.putpixel((x,Y), color)
		image.putpixel((x1,Y), color)
	image.putpixel((x1,y1), color)



#gets tile coordinates and returns 0 if there is no color labeled over the threshold, or the value of the label
#this works on a full size bmp label file and has no tissue/background detection
def tile_by_label_threshold_nb(img, coordinates, tile_x, tile_y, threshold, background_threshold):	
	left = coordinates[0]
	upper = coordinates[1]
	right = coordinates[0] + tile_x
	lower = coordinates[1] + tile_y

	tile = img.crop((left, upper, right, lower))
	tile_colors = tile.getcolors()
	total = tile_x*tile_y
	label_color = 0
	for i in tile_colors: 
		if (i[0] >= threshold*total):
			label_color = i[1]
	if background_threshold > 0.0:
		if (len(tile_colors) == 1) or (tile_colors[0][0] < background_threshold*total and tile_colors[len(tile_colors)-1][0] < background_threshold*total):
			label_color = 0
	return label_color




#similar to above but checks the thumbnail instead of the fullsize label image in order to get information about tissue location. works for background threshold but not for label/unlabeled threshold
def tile_by_threshold_on_thumbnail(img, coordinates, tile_x, tile_y, threshold, background_threshold, ratio):
	tile_x = int(tile_x*ratio)
	tile_y = int(tile_y*ratio)
	left = int(coordinates[0]*ratio)
	upper = int(coordinates[1]*ratio)
	right = (left+tile_x)
	lower = (upper+tile_y)

	tile = img.crop((left, upper, right, lower))

	tile_colors = tile.getcolors()
	total = tile_x*tile_y

	label_color = 0
	for i in tile_colors[:-1]: 
		if (i[0] >= threshold*total):
			label_color = i[1]
	#if there is no acceptable label color see if background threshold fits
	if label_color == 0:
		if (tile_colors[len(tile_colors)-1][0] >= threshold*total):
			label_color = tile_colors[len(tile_colors)-1][1]
	if background_threshold > 0.0:
		if (tile_colors[0][1] == 1) or (tile_colors[0][0] < background_threshold*total):
			label_color = 0
	return label_color




def get_center_pixel(img, x, y, tile_x, tile_y, b_ratio, ineedbackground):
	if not ineedbackground:
		label = img.getpixel( (x+(tile_x/2), y+(tile_y/2)) )
	else:
		label = img.getpixel( (int((x+(tile_x/2))*b_ratio), int((y+(tile_y/2))*b_ratio)) )
	return label




#checks to see if tile passes selection criteria
def tile_value(img, x, y, b_ratio, ineedbackground, cp, tile_x, tile_y, threshold, background_threshold):
	#if selection criteria is center pixel check just the center pixel
	if (cp == 1) and (background_threshold == 0.0):
		l = get_center_pixel(img, x, y, tile_x, tile_y, b_ratio, ineedbackground) 
	#if it is center pixel and threshold check both
	elif (cp == 2):
		label_c = get_center_pixel(img, x, y, tile_x, tile_y, b_ratio, ineedbackground) 
		if ineedbackground:
			label_t = tile_by_threshold_on_thumbnail(img, (x,y), tile_x, tile_y, threshold, background_threshold, b_ratio)
		else:
			label_t = tile_by_label_threshold_nb(img, (x,y), tile_x, tile_y, threshold, background_threshold)
		#makes sure they are both the same label color
		if (label_c == label_t):
			l = label_c
		else:
			l = 0
	#if it is just threshold check threshold
	else:
		if ineedbackground:
			l = tile_by_threshold_on_thumbnail(img, (x,y), tile_x, tile_y, threshold, background_threshold, b_ratio)
		else:
			l = tile_by_label_threshold_nb(img, (x,y), tile_x, tile_y, threshold, background_threshold)

	return l




#allows you to adjust the ratio of background tiles to labeled tiles
def can_i_save(max_background_tiles, num_labels):
	tiles_s = 0
	num_background = num_labels[len(num_labels)-1]
	for i in num_labels[:-1]:
		tiles_s = tiles_s + i
	if (num_background <= tiles_s*max_background_tiles):
		return True
	else:
		return False




#checks the number of tiles saved/checked to cap off random tile selection
def check_tiles(tiles_c, tiles_f, max_tiles_selected, max_tiles):
	if not max_tiles_selected:
		if (tiles_c < max_tiles):
			return True
		else:
			return False
	else:
		if (tiles_c < max_tiles) and (tiles_f < max_tiles_selected):
			return True
		else:
			return False



