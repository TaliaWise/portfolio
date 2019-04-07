# TileExtractor
This module generates tiles from slide images or from slide images with bmp label files. It allows you to save tile coordinates or images of:
<li>tiles from an unlabeled slide image</li>
<li>tiles from each label of a bmp file</li>
<li>tiles from each label of a bmp file + tiles from unlabelled tissue</li>
<li>tiles from the borders of tissue</li>
<li>tiles from the borders of labels</li>
<br>
<h3>How to use</h3>
<b>note:</b> because of PIL's limit on .bmp file size you must also download the PatchedPIL.py file. This file allows you to open very large .bmp files using PIL by importing PatchedPIL instead of PIL.
<br></br>
The module allows you to specify:
<li>tile height and width</li>
<li>uniform random selection vs. row by row selection</li>
<li>tile overlap</li>
<li>selection by color threshold or center pixel value or both</li>
<li>number of tiles to check in random selection</li>
<br></br>
It also allows several tile visualization options:
<li>thumbnails showing the locations of tiles on the .bmp and .svs files</li>
<li>tiles from the .bmp file for testing purposes</li>
<li>the number of tiles generated for each label color to stdout</li>
<h4>Example usage</h4>
to generate all possible tiles of width 256 pixels and height 256 pixels from a slide image: <br>
python tileExtractor.py svs_path/234.svs 256 256 
<br></br>
to generate up to 1000 randomly distributed labeled tiles of size 500 by 300 with labeled center pixels:<br>
python bmpTileExtractor.py svs_path/234.svs 500 300 -r -m 1000 -cp 1 
<br></br>
<br></br>

<b>positional arguments:</b><br>
<br>  svs_path  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;   path to svs slide
<br>  tile_width      &nbsp;&nbsp;&nbsp;&nbsp;      width of tiles in pixels
<br>  tile_height     &nbsp;&nbsp;      height of tiles in pixels
<br></br>
<b>optional arguments:</b><br>
<p>  -h, --help  <br>         show this help message and exit</p>
<p>  -b BMP_PATH, --bmp_path BMP_PATH <br>          
                        path to bmp label file</p>
<p>  -out OUTPUT_DIR, --output_dir OUTPUT_DIR <br>
                        path to a directory in which the generated tiles will be saved</p>
<p>  -th THRESHOLD, --threshold THRESHOLD <br>
                        fraction of labeled pixels per resulting tile.
                        Defaults to 0.5. For a different percentage enter a
                        float value between 0 and 1: e.g. '-th 0.6' generates
                        tiles that have at least 60 percent of pixels labeled.</p>
<p> -mpp MPP, --mpp MPP   <br>
                        specifies the resolution of the generates tiles.
                        default is the slide's original resolution. for
                        standardized 20X tiles use -mpp 0.45 and for
                        standardized 10X tiles use -mpp 0.9 etc...
 <p> -cp CENTER_PIXEL, --center_pixel CENTER_PIXEL<br>
                        selects tiles by the value of their center pixel: '-cp
                        1' to generate tiles with labeled center pixel
                        (without checking the tile --threshold). '-cp 2' for
                        tiles with labeled center pixel and label threshold as
                        specified by -th option. If -cp is omitted (default),
                        the center pixel is ignored.</p>
<p> -si, --save_tile_images<br>
                        in order to save images of the tiles instead of
                        getting tile coordinates in a csv file use this
                        command. each category of tile will be saved to a
                        seperate folder in the output directory</p>
<p> -r, --random_selection<br>
                        selects tiles from random locations in a uniform
                        distribution, the default number of tiles checked is
                        (width/tile_width * height/tile_height * 10) and by
                        default tiles are selected with no overlap. To specify
                        number of tiles checked and overlap use -m and -o
                        parameters</p>
<p> -m MAX_TILE_CANDIDATES, --max_tile_candidates MAX_TILE_CANDIDATES <br>
                        specifies the number of tile candidates in random
                        selection. E.g. -m 300 will generate 300 random tiles
                        and save all the tiles that fit the selection
                        criteria. Defaults to (width/tile_width *
                        height/tile_height * 10)</p>
<p> -ms MAX_TILES_SELECTED, --max_tiles_selected MAX_TILES_SELECTED<br>
                        maximum number of tiles that will be generated per
                        slide (only works on random tile selection) E.g. -ms
                        100 will generate up to 100 tiles, default is no
                        maximum</p>
<p>  -o OVERLAP, --overlap OVERLAP<br>
                        For row-by-row selection (default): number of pixels
                        by which tiles should overlap side to side. E.g. '-o
                        50' will generate tiles with overlap by 50 pixels on
                        each side. For random selection: A number between 0.0
                        and 1.0 where '-o 0.0' means that 0 percent of pixel
                        overlap is allowed between accepted tiles, and '-o
                        1.0' means that entire tile overlap is allowed.
                        Defaults to no overlap ('-o 0').</p>
<p> -bti, --background_tiles<br>
                        saves tiles from unlabeled tissue region to a folder
                        in the output folder. Background detection is done
                        with otsu_thresholding and pixel color thresholding.
                        By default this option is off</p>
<p> -bth BACKGROUND_THRESHOLD, --background_threshold BACKGROUND_THRESHOLD <br>
                        float between 0.0 and 1.0 specifying the minimum
                        percentage of background in each tile. note: with no
                        label file this will give tiles on the edge of
                        borders, and with a label file it will give tiles on
                        the edge of labels</p>
<p>  -sb, --show_bmp_tiles<br>
                        for testing: saves tiles from the bmp file as well as
                        from the svs file to the output folder</p>
<p>  -t THUMBNAIL, --thumbnail THUMBNAIL<br>
                        shows thumbnails with tile locations in output folder:
                        this will show one thumbnail of the slide image, one
                        of the label image and one with the labels overlayed
                        on the slide</p>
<p> -j, --jpeg_tiles <br>      
                        by default tiles will be saved as png images, to save
                        the tiles in jpeg format select this option</p>
 <p> -sr, --show_rejected_tiles<br>
                        displays locations of rejected tiles in thumbnails</p>
 <p> -v, --verbose         <br>show progress and output information</p>
 
 <h3>Usage examples</h3>
 <p>To generate all tiles from a slide image (saving coordinates to a csv file) call: python tileExtractor.py input/p390508.svs 300 300<br> 
 To do this but also standardize tile resolution and generate a thumbnail showing tile locations call: python tileExtractor.py input/p390508.svs 300 300 -mpp 0.45 -t</p>
 <p>To get all labeled tiles from a slide image with a bmp label file: python tileExtractor.py input/394221.svs 600 600 -b input/394221.svs_data/labels.bmp -t </p>
 <p>To generate all labeled tiles (as above) but also get tiles from the unlabeled parts of a slide: python tileExtractor.py input/394217.svs 300 300 -b input/394217.svs_data/labels.bmp -bti -r -t</p>
 <p>To get tiles from the borders of labels use: python tileExtractor.py input/394221.svs 300 300 -b input/394221.svs_data/labels.bmp -bth 0.1 -t -r. -bth sets the background threshold so when both -th and -bth are greater than 0, only tiles with labeled sections and unlabeled sections will be chosen. note: for good coverage of border areas random tile selection or row-by-row selection with overlap (-o ) works better)</p>
 <p>To get tiles from the border of tissue use -th and -bth as above, but don't include the (-b) label file argument.</p>
 
 
