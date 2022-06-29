import os
import numpy as np 
from pathlib import Path
from tifffile import imread
from tifffile import imsave
from tifffile import imwrite
from timeit import default_timer as time

file_folder = Path('/Volumes/Song_8TB/20220415_143603_GFPwGBDE01T01')

max_dir = file_folder / ('0_max_projections')
max_dir.mkdir(exist_ok=True, parents=True)
vol_dir = file_folder / ('0_vol_downsample')
vol_dir.mkdir(exist_ok=True, parents=True)

name = input('enter channel name:')
magnification = 10

files = [item for item in os.listdir(file_folder) if item.endswith('.tif') and name in item and not item.startswith('.') and not 'MP' in item]

files.sort()

i0_C00_files = [item for item in files if 'I0' in item]
i1_C00_files = [item for item in files if 'I1' in item]
i0_C00_files.sort()
i1_C00_files.sort()
sample_image = imread(file_folder / i0_C00_files[0])
slices = sample_image.shape[0]
pixels = sample_image.shape[1]

xy_scale_factor = 8
z_scale_factor = 2
xy_scaled_pixels = int(pixels / xy_scale_factor)
z_scaled_pixels = int(slices / z_scale_factor)

frames = len(i0_C00_files)

full_shape = slices, pixels, pixels
max_shape = pixels, pixels

save_dict = {}

for index in range(frames):
    start = time()
    i0_C00 = np.zeros(full_shape, dtype = 'uint16')
    i1_C00 = np.zeros(full_shape, dtype = 'uint16')
    c00 = np.zeros(full_shape, dtype = 'uint16')
    c00_Max = np.zeros(max_shape, dtype='uint16')
    print('finished creating empty arrays')
    print(f'starting to load time point {index} of channel {name}')
    i0_C00 = imread(file_folder / i0_C00_files[index])
    print('finished loading left side illumination')
    i1_C00 = imread(file_folder / i1_C00_files[index])
    print('finished loading right side illumination')
    c00 = np.maximum(i0_C00, i1_C00)
    
    print('finished merging left and right sided illumination')
    c00_Max = np.max(c00, axis=0)
    print('finished calculating max projection')
    c00 = c00[::z_scale_factor,::xy_scale_factor,::xy_scale_factor]
    print('finished downsampling volume')

    px_xy = (6.4/magnification)*xy_scale_factor
    px_z = 2.5 * z_scale_factor

    imwrite(vol_dir / (name + '_' + str(index) + '.tif'), c00, imagej=True, resolution=(1./px_xy, 1./px_xy), metadata={'spacing': px_z, 'unit': 'um', 'axes': 'ZYX', 'finterval': 16})
    imwrite(max_dir / (name + '_' + str(index) + '.tif'), c00_Max, imagej=True, resolution=(1./(6.4/magnification), 1./(6.4/magnification)), metadata={'unit': 'um', 'axes': 'YX', 'finterval': 16})
    end = time()
    save_dict[str(index)] = end-start
    print(f'finished processing frame {index} in {round((end-start), 4)} seconds')
    print(f'{round((index+1)/frames*100, 2)}% finished downsampling all frames')