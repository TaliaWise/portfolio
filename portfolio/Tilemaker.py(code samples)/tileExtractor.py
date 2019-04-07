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
import tile_maker_methods 
from tile_maker_methods import rec, tile_by_label_threshold_nb, tile_by_threshold_on_thumbnail, get_center_pixel, tile_value, check_tiles

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

import skimage
from skimage.filters import threshold_otsu
from skimage.segmentation import clear_border
from skimage.measure import label, regionprops
from skimage.morphology import closing, square
from skimage.color import label2rgb, rgb2gray
from skimage.util import invert

import cv2
import warnings


parser = argparse.ArgumentParser( description = 
	"""
	Generate tiles from slide images or from slide images with bmp label file.
	Options are: tiles from tissue, tiles from labeled areas only, tiles from both labeled areas and unlabeled areas, tiles only from tissue border or tiles only from label borders.
	for example, to generate all possible labeled tiles of width 256 pixels and height 256 pixels write: 	
	python tileExtractor.py svs_path/234.svs output_path/folder 256 256 -b bmp_path/123.bmp
	""")
parser.add_argument('svs_path', help = 'path to svs slide')
parser.add_argument('tile_width', help = 'width of tiles in pixels', type = int)
parser.add_argument('tile_height', help = 'height of tiles in pixels', type = int)
parser.add_argument('-out', '--output_dir', default = 'output', help = 'path to a directory in which the generated tiles will be saved')
parser.add_argument('-b', '--bmp_path', type = str, help = 'path to bmp label file')
parser.add_argument('-mpp', '--mpp', type = float, help = 'specifies the resolution of the generates tiles. default is the slide\'s original resolution. for standardized 20X tiles use -mpp 0.45 and for standardized 10X tiles use -mpp 0.9 etc...')
parser.add_argument('-th', '--threshold', type = float, default = 0.5, help = "fraction of labeled pixels per resulting tile. Defaults to 0.5. For a different percentage enter a float value between 0 and 1: e.g. '-th 0.6' generates tiles that have at least 60 percent of pixels labeled.")
parser.add_argument('-cp', '--center_pixel', type = int, help = "selects tiles by the value of their center pixel: '-cp 1' to generate tiles with labeled center pixel (without checking the tile --threshold). '-cp 2' for tiles with labeled center pixel and label threshold as specified by -th option. If -cp is omitted (default), the center pixel is ignored.")
parser.add_argument('-r', '--random_selection', action = "store_true", help = "selects tiles from random locations with uniform distribution. The default number of tile candidates is (width/tile_width * height/tile_height * 10), and by default tiles are selected with no overlap. To specify the number of tile candidates and overlap use -m and -o parameters.")
parser.add_argument('-m', '--max_tile_candidates', type = int, default = 0, help = "specifies the number of tile candidates in random selection. E.g. -m 300 will generate 300 random tiles and save all the tiles that fit the selection criteria. Defaults to (width/tile_width * height/tile_height * 10)")
parser.add_argument('-ms', '--max_tiles_selected', type = int, help = "maximum number of tiles that will be generated per slide (only works on random tile selection) E.g. -ms 100 will generate up to 100 tiles, default is no maximum")
parser.add_argument('-o', '--overlap', type = float, default = 0, help = "For row-by-row selection (default): number of pixels by which tiles should overlap side to side. E.g. '-o 50' will generate tiles with overlap by 50 pixels on each side. For random selection: A number between 0.0 and 1.0 where '-o 0.0' means that 0 percent of pixel overlap is allowed between accepted tiles, and '-o 1.0' means that entire tile overlap is allowed. Defaults to no overlap ('-o 0').")
parser.add_argument('-bti', '--background_tiles', action = 'store_true', help = 'saves tiles from unlabeled tissue region to a folder in the output folder. Background detection is done with otsu_thresholding and pixel color thresholding. By default this option is off')
parser.add_argument('-bth', '--background_threshold', type = float, default = 0.0, help = 'float between 0.0 and 1.0 specifying the minimum percentage of background in each tile. note: with no label file this will give tiles on the edge of borders, and with a label file it will give tiles on the edge of labels')
parser.add_argument('-sb', '--show_bmp_tiles', action = "store_true", help = "for testing: saves tiles from the bmp file as well as from the svs file to the output folder")
parser.add_argument('-j', '--jpeg_tiles', action = "store_true", help = "by default tiles will be saved as png images, to save the tiles in jpeg format select this option")
parser.add_argument('-si', '--save_tile_images', action = "store_true", help = "in order to save images of the tiles instead of getting tile coordinates in a csv file use this command. each category of tile will be saved to a seperate folder in the output directory")
parser.add_argument('-t', '--thumbnail', action = "store_true", help = "shows thumbnails with tile locations in output folder: this will show one thumbnail of the slide image, one of the label image and one with the labels overlayed on the slide")
parser.add_argument('-sr', '--show_rejected_tiles', action = "store_true", help = "displays locations of rejected tiles in thumbnails")
parser.add_argument('-v', '--verbose', action = "store_true", help = "show progress and output information")
args = parser.parse_args()

if args.verbose:
	print "\n---    Tile Extractor. For help: python bmpTileExtractor.py -h    ---\n"


if (args.background_threshold + args.threshold > 1.0):
	print 'there are no tiles with', args.background_threshold*100, 'percent background and,', args.threshold*100, 'percent tissue. please fix your thresholds'
	sys.exit(1)


overlap = args.overlap

#find/make output directory
output_dir = args.output_dir
if not os.path.exists(output_dir):
	os.makedirs(output_dir)
starttime = time.time()

#get tile size
tile_x = args.tile_width
tile_y = args.tile_height


#open slide image
try:
	svs = openslide.OpenSlide(args.svs_path)
	lx, ly = svs.dimensions
except Exception, e:
	print >> sys.stderr, "Exception can not open", args.svs_path, "%s. note: this may be an issue with openslide in your environment and switching to a different python environment might help" % str(e)
	sys.exit(1)


#get slide resolution
mpp_x = float(svs.properties[openslide.PROPERTY_NAME_MPP_X])
mpp_y = float(svs.properties[openslide.PROPERTY_NAME_MPP_Y])
resolution = (mpp_x + mpp_y)/2


#get tile size and overlap for specifies resolution
if args.mpp:
	tile_x = int(tile_x*args.mpp/mpp_x)
	tile_y = int(tile_y*args.mpp/mpp_y)
	if not args.random_selection:
		overlap = args.overlap*args.mpp/resolution


#open BMP label file
if args.bmp_path:
	try:
		label_img = Image.open(args.bmp_path)
	except Exception, e:
		print >> sys.stderr, "Exception can not open", args.bmp_path, "%s" % str(e)
		sys.exit(1)

	#get dimensions of image
	if (svs.dimensions != (label_img.size[0], label_img.size[1]) ):
		print 'Slide', svs.dimensions, 'and BMP (', lx, ',', ly, ') have different dimensions'
		sys.exit(1)


#check if background detection is needed
ineedbackground = False
if (not args.bmp_path) or args.background_tiles or (args.background_threshold and not args.bmp_path):
	ineedbackground = True



#find maximum tiles to check in random selection and if none is specified set to default value
if (args.max_tile_candidates == 0):
	max_tiles = int((float(lx)/float(tile_x))*(float(ly)/float(tile_y))*10*(1+args.overlap))
else:
	max_tiles = args.max_tile_candidates



#if row by row get the number tiles that will be checked
if not args.random_selection:
	max_tiles = int(float(lx)/float(tile_x-overlap)*float(ly)/float(tile_y-overlap))



#print variables for user debugging purposes
if (args.verbose):
	print 'Slide path is', args.svs_path
	if (args.bmp_path):
		print 'Label image path is', args.bmp_path
	print 'Output directory is', output_dir
	print 'Image dimensions are:', svs.dimensions
	if (args.bmp_path):
		print 'Label image dimensions are: (', lx,',', ly, ')'
	print 'The slide\'s objective power is', svs.properties[openslide.PROPERTY_NAME_OBJECTIVE_POWER]
	print 'The slide\'s resolution is', resolution
	print 'Tile width is:', args.tile_width, ', tile height is:', args.tile_height
	if (args.center_pixel == 1):
		print 'Tiles are selected by the value of their center pixel'
	elif (args.center_pixel == 2):
		print 'Tiles are saved if they are more than', int(args.threshold*100), 'percent labeled and if the center pixel is labeled'
	else:
		print 'Tiles are saved if they are more than', int(args.threshold*100), 'percent labeled'
	if (args.random_selection):
		print 'Tiles are checked in a uniform random distribution with an overlap of', int(args.overlap*100), 'percent and a maximum of', max_tiles,'tiles checked' 
	else:
		print 'Tiles are checked row-by-row with an overlap of', int(args.overlap),'pixels, and a maximum of', max_tiles, 'tiles checked'
	if (args.jpeg_tiles):
		print 'Tiles will be saved in jpeg format'
	else:
		print 'Tiles will be saved in png format'
	if (args.background_tiles):
		print 'Tiles from unlabeled areas of tissue will also be saved'
	else:
		print 'Tiles from unlabeled areas of tissue will not be saved'
	if (args.show_bmp_tiles):
		print 'Bmp tiles will also be saved in output folders'
	if (args.thumbnail):
		print 'Thumbnails showing tile locations will be saved in the output folder'
	else:
		print 'No thumbnails will be saved'
	if (args.show_rejected_tiles):
		print 'The locations of rejected tiles will be shown in the thumbnails'
	else:
		print 'The locations of rejected tiles will not be shown in the thumbnails'


if (args.verbose):
	sys.stdout.write('---   all files opened successfully   ---')
	sys.stdout.flush()


#bmp thumbnail
if args.thumbnail:
	if args.verbose:
		sys.stdout.write('\r---        creating thumbnails        ---')
		sys.stdout.flush()


	
#create thumbnail of slide image, record size and ratio to slide
svs_thumbnail = svs.get_thumbnail((2000,2000))
b_width, b_height = svs_thumbnail.size
b_ratio = float(svs_thumbnail.size[0])/float(lx)


#if there is a label file for the image create a thumbnail and find a new color for bakckground
if args.bmp_path:
	bmp_thumbnail = label_img.copy()
	bmp_thumbnail.thumbnail((2000,2000))

	#find an unused color for the unlabeled tissue
	b_color = len(bmp_thumbnail.getcolors())

#if there is no label image create a blank thumbnail and find color for background
else:
	bmp_thumbnail = Image.new('1', svs_thumbnail.size, 0)
	b_color = 1



#create thumbnails
if args.thumbnail:
	#convert thumbnails to RGBA in order to create composites
	svs_th = svs_thumbnail.convert("RGBA")

	#create composite thumbnail
	#this removes opacity from the white sections of the bmp file and then superimposes the labels on the .svs slide for the thumbnail
	if args.bmp_path:
		bmp_th = bmp_thumbnail.convert("RGBA")
		bmp_t = list(bmp_th.getdata())
		for i,pixel in enumerate(bmp_t):
			a,b,c = pixel[:3]
			if (pixel[:3] == (255,255,255)):
				bmp_t[i] = (255,255,255,0)
			else:
				bmp_t[i] = ((a,b,c,120))
		bmp_th.putdata(bmp_t)
		#sometimes this function does not work for whatever strange reason
		try:
			composite_thumbnail = Image.alpha_composite(svs_th, bmp_th)
		except Exception, e:
			composite_thumbnail = svs_thumbnail



#for more information on how this works please refer to http://scikit-image.org/docs/dev/auto_examples/segmentation/plot_label.html
#def get_background(bmp_thumbnail):
if ineedbackground:
	if args.verbose:
		sys.stdout.write('\r---        detecting image background        ---')
		sys.stdout.flush()

	for_seg = Image.new('RGB', ((svs_thumbnail.size[0]+ 15), (svs_thumbnail.size[1]+15)), (255, 255, 255)) 
	for_seg.paste(svs_thumbnail, (5,5))
	for_seg.save('th.jpg')

	img = cv2.imread('th.jpg', 0)
	blur = cv2.GaussianBlur(img,(25,25),0)
	ret1, th1=cv2.threshold(blur,0,255,cv2.THRESH_OTSU)

	img_GRAY = rgb2gray(invert(th1))
	svs_arr = np.where(img_GRAY > np.mean(img_GRAY),1,0)
	thresh = threshold_otsu(svs_arr)
	bw = closing(svs_arr > thresh, square(3))
	cleared = clear_border(bw)
	label_image = label(cleared)
	with warnings.catch_warnings():
		warnings.simplefilter("ignore")
		image_label_overlay = label2rgb(label_image, image=svs_arr)
	fig, ax = plt.subplots(figsize=(10, 6))
	ax.imshow(image_label_overlay)
	boxes = []
	check_area = []
	for region in regionprops(label_image):
		if region.area < 600:
			#remove region from label_image
			for coord in region.coords:
				label_image[coord[0]][coord[1]] = 0

		#if desired: for row-by-row selection get bbox of tissue areas
		else:
			if not args.random_selection:
				if region.area >= 600:
					miny, minx, maxy, maxx = region.bbox
					minx, miny, maxx, maxy = int(minx/b_ratio), int(miny/b_ratio), int(maxx/b_ratio), int(maxy/b_ratio)
					check_area.append([(minx, maxx),(miny, maxy)])
		

	os.remove('th.jpg')
	#end segmentation

	#cover background of bmp with last number
	for x in range(b_width):
		for y in range(b_height):
			if label_image[y+5][x+5] != 0 and bmp_thumbnail.getpixel((x,y)) == 0:
				bmp_thumbnail.putpixel((x,y), b_color)




#if thumbnail update label thumbnail to include background 
if args.thumbnail:
	label_thumbnail = bmp_thumbnail
	label_thumbnail = label_thumbnail.convert('RGBA')




if (args.verbose):
	sys.stdout.write('\r---        beginning tile extraction         ---')
	sys.stdout.flush()




#get slide number for saving images
s_path = args.svs_path.replace('/', '.').replace("\\", '.').split('.')
slide_num = s_path[len(s_path)-2]




#get label colors from slide and make a folder for each label color
folder_names = []
#make list of names of possible tile locations
if args.bmp_path:
	label_colors = range(1, len(label_img.getcolors()), 1)
	for color in label_colors:
		folder_names.append(color)
else:
	label_colors = ()

if args.background_tiles or (args.background_threshold and not args.bmp_path) or (not args.bmp_path):
	folder_names.append('unlabeled_tissue')

#if not csv then make folders for tiles
if args.save_tile_images:
	for folder in folder_names:
		newpath = newpath = os.path.join(args.output_dir, '{0}'.format(folder))
		if not os.path.exists(newpath):
			os.makedirs(newpath)


#num_labels counts the number of tiles for each label color. note: the last one is unlabeled tissue
num_labels = [0 for l in label_colors]
if (args.background_tiles or not args.bmp_path):
	num_labels.append(0)


#creates array for accepted tile coordinates
if not args.save_tile_images:
	csv_arr = [[] for l in folder_names]


#get thumbnail to image ratio
s_x = float(lx)/float(svs_thumbnail.size[0])
s_y = float(ly)/float(svs_thumbnail.size[1])


threshold = args.threshold


#saves tile at coordinate (x,y)
def save_tile(x, y, label):
	if not args.save_tile_images:
		csv_arr[label-1].append((slide_num,(x,y),label))
	else:
		if not args.bmp_path:
			label = 'unlabeled_tissue'

		tile = svs.read_region( (x, y) ,0 , (tile_x, tile_y) )
		if (args.jpeg_tiles):
			name = '{0}.{1}_{2}.jpeg'.format(slide_num,x,y)
			tile = tile.convert('RGB')
			if args.mpp:
				tile.thumbnail((args.tile_width, args.tile_height))
			tile.save(os.path.join(args.output_dir, '{0}'.format(label), name), 'JPEG')
		else:
			name = '{0}.{1}_{2}.png'.format(slide_num,x,y)
			if args.mpp:
				tile.thumbnail((args.tile_width, args.tile_height))
			tile.save(os.path.join(args.output_dir, '{0}'.format(label), name), 'PNG')

		if (args.show_bmp_tiles):
			tilebmp = label_img.crop((x,y,x+tile_x,y+tile_y))
			name = '{0}.{1}_{2}.bmp'.format(slide_num,x,y)
			if args.mpp:
				tile.thumbnail((args.tile_width, args.tile_height))
			tilebmp.save(os.path.join(args.output_dir, '{0}'.format(label), name), 'BMP')
		


if (args.verbose):
	#to erase previous line
	sys.stdout.write('\r                                                                        ')
	sys.stdout.flush()
	sys.stdout.write('\r')
	sys.stdout.flush()





#tile counter in order to cap off random tile search
tiles_found = 0
tiles_checked = 0




#random selection
if args.random_selection:
	#makes a black image and fills tiles in white in order to measure tile overlap
	tile_tracker = Image.new('1', (lx, ly), 0)
	tile = Image.new('1', (tile_x , tile_y), 1)

	#check to make sure overlap is not bigger than 100 %
	if (overlap > 1.0):
		print ("for random selection the -o paramater should have a number between 0.0 and 1.0 indicating the maximum percent of pixel overlap between tiles")
		sys.exit(1)

	max_overlap = overlap


	random.seed(1)

	while(tiles_checked < max_tiles):
		tiles_checked = tiles_checked + 1

		x = random.randint(0, lx-tile_x)
		y = random.randint(0, ly-tile_y)

		#if tile is checking background then tile is checked on bmp_thumbnail, otherwise the tile is checked on the label_img
		if ineedbackground:				
			label = tile_value(bmp_thumbnail, x, y, b_ratio, ineedbackground, args.center_pixel, tile_x, tile_y, threshold, args.background_threshold)
		else:
			label = tile_value(label_img, x, y, b_ratio, ineedbackground, args.center_pixel, tile_x, tile_y, threshold, args.background_threshold)
		

		#if label is colored save tile, update tile count, update the tile_tracker image, and update num_labels
		if (label != 0 and tile_by_label_threshold_nb(tile_tracker, (x, y), tile_x, tile_y, max_overlap, 0.0) == 0):
			tile_tracker.paste(tile, (x,y))

			#if background is involved check to see if foldername should be renamed to tissue (ie. if it is an unlabeled slide it should not have a label number)
			if args.background_tiles or (args.background_threshold and not args.bmp_path):
				#if it is background call it unlabeled tissue
				if (label == len(num_labels)) and args.save_tile_images:
					foldername = 'unlabeled_tissue'
				#otherwise call it its label number (this is necessary for csv because of csv_arr)
				else: 
					foldername = label
				save_tile(x,y, foldername)
			#if only label tiles are produced save with label number
			else:
				save_tile(x,y,label)
			#update numlabels and tiles found
			num_labels[label-1] = num_labels[label-1] + 1 
			tiles_found = tiles_found + 1

			#write out tiles found to stdout
			if args.verbose:
				prog = (tiles_checked*100)/max_tiles
				sys.stdout.write('\r--- {0} tiles extracted. {1} percent of tiles checked ---'.format(tiles_found, prog))
				sys.stdout.flush()


			#show tiles in the requested thumbnails
			if args.thumbnail:
				rec(svs_thumbnail, (x)/s_x, (y)/s_y, (x+tile_x)/s_x, (y+tile_y)/s_y, (0,0,0))
				if args.bmp_path or args.background_threshold:
					rec(label_thumbnail, (x)/s_x, (y)/s_y, (x+tile_x)/s_x, (y+tile_y)/s_y, (0,0,0))
				if args.bmp_path:
					rec(composite_thumbnail, (x)/s_x, (y)/s_y, (x+tile_x)/s_x, (y+tile_y)/s_y, (0,0,0))
		
		#this allows the thumbnails to show rejected tiles as well
		else:
			if args.show_rejected_tiles:
				if args.thumbnail:
					rec(svs_thumbnail, (x)/s_x, (y)/s_y, (x+tile_x)/s_x, (y+tile_y)/s_y, (40,180,40))
					if args.bmp_path or args.background_threshold:
						rec(label_thumbnail, (x)/s_x, (y)/s_y, (x+tile_x)/s_x, (y+tile_y)/s_y, (40,180,40))
					if args.bmp_path:
						rec(composite_thumbnail, (x)/s_x, (y)/s_y, (x+tile_x)/s_x, (y+tile_y)/s_y, (40,180,40))
			



#row-by-row selection
else:
	#get bbox coordinates and find all tile locations to check:
	coords = []
	if ineedbackground:
		for bbox in check_area:
			for x in range(bbox[0][0], bbox[0][1], tile_x-int(overlap)):
				for y in range(bbox[1][0], bbox[1][1], tile_x-int(overlap)):
					coords.append((x,y))
	else:
		for x in range(0, lx-tile_x, tile_x-int(overlap)):
			for y in range(0, ly-tile_y, tile_y-int(overlap)):
				coords.append((x,y))

	for coord in coords:
		x = coord[0]
		y = coord[1]
		tiles_checked = tiles_checked + 1

		#if tile is checking background then tile is checked on bmp_thumbnail, otherwise the tile is checked on the label_img
		if ineedbackground:				
			label = tile_value(bmp_thumbnail, x,y, b_ratio, ineedbackground, args.center_pixel, tile_x, tile_y, threshold, args.background_threshold)
		else:
			label = tile_value(label_img, x, y, b_ratio, ineedbackground, args.center_pixel, tile_x, tile_y, threshold, args.background_threshold)


		#if label is colored save tile and update tile count and if verbose option is on print number of tiles
		if (label != 0):
			#if background is involved check to see if foldername should be renamed to tissue (ie. if it is an unlabeled slide it should not have a label number)
			if args.background_tiles or (args.background_threshold and not args.bmp_path):
				#if it is background call it unlabeled tissue
				if (label == len(num_labels)) and args.save_tile_images:
					foldername = 'unlabeled_tissue'
				#otherwise call it its label number (this is necessary for csv because of csv_arr)
				else: 
					foldername = label
				save_tile(x,y, foldername)
			#if only label tiles are produced save with label number
			else:
				save_tile(x,y,label)
			#update numlabels and tiles found
			num_labels[label-1] = num_labels[label-1] + 1 
			tiles_found = tiles_found + 1



			if (args.verbose):
				prog = tiles_checked*100/max_tiles
				sys.stdout.write('\r--- {0} tiles extracted. {1} percent of tiles checked ---'.format(tiles_found, prog))
				sys.stdout.flush()

			
			# show tiles in thumbnail (this generates random colors for tiles in order to show tile overlap effectively in thumbnails)
			a = random.randint(0, 120)
			b = random.randint(0, 120)
			c = random.randint(0, 120)

			if args.thumbnail:
				rec(svs_thumbnail, (x)/s_x, (y )/s_y, (x+tile_x)/s_x, (y+tile_y)/s_y, (a,b,c))
				if args.bmp_path or args.background_threshold:
					rec(label_thumbnail, (x)/s_x, (y )/s_y, (x+tile_x)/s_x, (y+tile_y)/s_y, (a,b,c))
				if args.bmp_path:
					rec(composite_thumbnail, (x)/s_x, (y )/s_y, (x+tile_x)/s_x, (y+tile_y)/s_y, (a,b,c))	

		#allows program to show rejected tiles in thumbnail
		else:
			a = random.randint(190, 255)
			b = random.randint(190, 255)
			c = random.randint(190, 255)
			if args.show_rejected_tiles:
				if args.thumbnail:
					rec(svs_thumbnail, (x)/s_x, (y )/s_y, (x+tile_x)/s_x, (y+tile_y)/s_y, (a,b,c))
					if args.bmp_path or args.background_threshold:
						rec(label_thumbnail, (x)/s_x, (y )/s_y, (x+tile_x)/s_x, (y+tile_y)/s_y, (a,b,c))
					if args.bmp_path:
						rec(composite_thumbnail, (x)/s_x, (y )/s_y, (x+tile_x)/s_x, (y+tile_y)/s_y, (a,b,c))
			


#save thumbnails
if args.thumbnail:
	svs_thumbnail.save(os.path.join(args.output_dir, slide_num + '_slide_thumbnail.png'), 'PNG')
	if args.bmp_path:
		composite_thumbnail.save(os.path.join(args.output_dir, slide_num + '_composite_thumbnail.png'), 'PNG')	
	if args.bmp_path and (args.background_threshold or args.background_tiles) or not args.bmp_path:
		label_thumbnail.save(os.path.join(args.output_dir, slide_num + '_bmp_thumbnail.png'), 'PNG')
	


#if csv then output csv
if not args.save_tile_images:
	n = 0
	for folder in folder_names:
		with open(os.path.join(output_dir, '{0}.csv'.format(folder)), "a+") as f:
			writer = csv.writer(f)
			for coordinates in csv_arr[n]:
				writer.writerow(coordinates)
		n = n + 1



#write information to stdout
if args.verbose:

	if ineedbackground:
		num_background = num_labels[len(num_labels)-1]
		num_labels = num_labels[:(len(num_labels)-1)]

	sys.stdout.write("\r--- {0} total tiles found in {1} seconds ---\n".format(tiles_found, time.time() - starttime))
	#print number of tiles per label found
	i = 1
	for l in num_labels:
		print ('{0} tiles for label {1}'.format(l,i))
		i = i+1
	if (args.background_tiles):
		print num_background, 'tiles for unlabeled tissue'







 







