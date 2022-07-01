from ast import Continue
import enum
import os
import sys
import napari
import numpy as np
from tqdm import tqdm
from pathlib import Path
from datetime import datetime
from tifffile import imread as tiff_read
from tifffile import imwrite as tiff_write
from dask_image.imread import imread as dask_read
import dask.array as da
from dask import distributed
import time
from yaspin import yaspin

class Kkpo:

    def __init__(self, file_path=None):
        if not file_path:
            print('*****'*9)
            print("I can't make a Kakapo without a file path!")
            print('*****'*9)
            sys.exit()
        self.file_path = Path(file_path)
        self.files = [file for file in os.listdir(self.file_path) if all([file.endswith('.tif')]) and not any([file.startswith('.'),
                                                                                                              'MP' in file,
                                                                                                              'max' in file])]
        self.region_names = np.unique([file.split('_')[3] for file in self.files])
        self.metadata = [line.rstrip() for line in open(self.file_path / 'FlamingoMetaData.txt', "r")]
        self.objmag = int([line for line in self.metadata if 'Name = ' in line][0][-3:-1])

    def get_region_info(self, region_name: str):
        '''
        Identifies the number of timepoints, channels, slices, and illumination sources for a given
        region. Also pulls timestamps from the first and last timepoint to calculate the interval.
        Parameters: region_name (str) - the name of the region to get the interval for
        Returns: 
         - interval (float) - the interval between timepoints in seconds
         - num_timepoints (int) - the number of timepoints in the region
         - num_channels (int) - the number of channels in the region
         - num_slices (int) - the number of slices in the region
         - num_illum (int) - the number of illumination sources in the region
        '''
        # get the image parameters for the region
        region_files = [file for file in self.files if region_name in file]
        timepoint_names = np.unique([file.split('_')[1] for file in region_files])
        channel_names =   np.unique([file.split('_')[6] for file in self.files])
        illum_names =     np.unique([file.split('_')[7] for file in self.files])
        plane_names =     np.unique([file.split('_')[9] for file in self.files])
        num_timepoints =  len(timepoint_names)

        # pick out the first and lasat settings files
        setting_files = [file for file in os.listdir(self.file_path) if "Settings.txt" in file and region_name in file and not file.startswith('.')]
        first_timepoint_name = [file for file in setting_files if all(match in file for match in [timepoint_names[0], channel_names[0], illum_names[0]])]
        last_timepoint_name = [file for file in setting_files if all(match in file for match in [timepoint_names[-1], channel_names[0], illum_names[0]])]

        # quality control
        if len(first_timepoint_name) != 1 or len(last_timepoint_name) != 1:
            print('*****'*9)
            print(f'EEROR:Problem with the settings file!\n{len(first_timepoint_name)} first and {len(last_timepoint_name)} last timepoint names found.\n',
                  f'Expected 1 first and 1 last timepoint name. Exiting...')
            print('*****'*9)
            sys.exit()
        
        def get_datetime(settings_file: np.ndarray):
            '''
            Extracts the date and time from a settings file.
            Accepts: settings file for a given timepoint as an ndarray
            Returns: datetime object
            '''
            timestamp_line = [line for line in settings_file if 'Date time stamp' in line][0]
            timestamp_val = timestamp_line.split('=')[-1]
            timestamp_date = timestamp_val.split('_')[0]
            timestamp_time = timestamp_val.split('_')[1]
            start_year = int(timestamp_date[0:5])
            start_month = int(timestamp_date[5:7])
            start_day = int(timestamp_date[7:9])
            start_hour = int(timestamp_time[0:2])
            start_minute = int(timestamp_time[2:4])
            start_second = int(timestamp_time[4:6])
            return datetime(start_year, start_month, start_day, start_hour, start_minute, start_second)

        # read the settings file, get the start and end times
        first_timepoint_file = np.loadtxt(self.file_path / first_timepoint_name[0], dtype='str', delimiter = '/n')
        start_datetime = get_datetime(first_timepoint_file)
        last_timepoint_file = np.loadtxt(self.file_path / last_timepoint_name[0], dtype='str', delimiter = '/n')
        end_datetime = get_datetime(last_timepoint_file)
        total_seconds = (end_datetime - start_datetime).total_seconds()
        interval = total_seconds / (num_timepoints - 1)
        return interval, timepoint_names, channel_names, illum_names, plane_names
    
    '''
    A better way to do this may be to iterate through the regions and for each region
    calculate the number of channels, slices, and timepoints. Then I don't have to worry
    about different regions using different numbers of channels and slices.
    '''
    
    def save_regions(self, save_vol = False, step = 8, overwrite = False):
        ''' 
        '''

        for region_num, region_name in enumerate(self.region_names):
            print(f'Saving region {region_num + 1}/{len(self.region_names)}')
            print(f'Collecting information about region {region_name}')

            interval, timepoint_names, channel_names, illum_names, plane_names = self.get_region_info(region_name)

            # create a folder to save the max projections and volume arrays for this region
            region_save_path = self.file_path / f'{region_name}_processed'

            if os.path.exists(region_save_path) and not overwrite:
                print(f'{region_save_path} already exists. Pass overwrite=True to overwrite.')
                continue
            
            else:
                if os.path.exists(region_save_path) and overwrite:
                    print(f'{region_save_path} already exists. Overwriting file!')
                    
                Path.mkdir(region_save_path, parents=True, exist_ok=True)
    
                for ch_num, ch_name in enumerate(channel_names):
                    print(f'Saving channel {ch_num+1}/{len(channel_names)}')
                    channel_array = dask_read(self.file_path /  (f'*{region_name}*{ch_name}*.tif'))

                    # save the downsampled channel volume, if requested
                    if save_vol:
                        with yaspin() as sp:
                            sp.text = f'Converting full volume for {ch_name} to zarr. This takes 1-2 seconds per time point, please be patient...'
                            chan_path = self.file_path / f'{region_name}_{ch_name}_volume.zarr'
                            start = time.time()
                            da.to_zarr(channel_array[:,:,::step,::step], chan_path, overwrite=True)
                            end = time.time()
                            print(f'Saved channel {ch_name} in {round(end - start, 3)} seconds')

                    # save the max projections for this channel (getting ~16-20s/it which is about as fast as I can do it using fiji)
                    with tqdm(total=len(timepoint_names)) as max_pbar:
                        max_pbar.set_description('Saving max projections')
                        for tp, tp_name in enumerate(timepoint_names):
                            tiff_write(region_save_path / f'{region_name}_{ch_name}_{tp_name}_Max.tiff', np.max(channel_array[:,tp,:,:], axis=0))
                            max_pbar.update(1)

        print(f'done saving regions')


    def view_volumes(self, region):
        ''' 
        Dask/Napari interactive workflow
        '''
        if not self.downsampled:
            print('Please run save_regions() before trying to interact with saved volumes.')

        channels = [dask_read(self.file_path /  ('*'+region+'*'+channel+'*.tif')) for channel in self.channel_names]
        channels = [da.from_zarr(self.file_path / f'region_{region}_{chan_num+1}_volume.zarr') for chan_num in range(self.num_channels)]

        with napari.gui_qt():
            viewer = napari.Viewer(title="Interactive Kkpo Viewer")
            for chan_num, channel in enumerate(channels):
                viewer.add_image(channel, name=f'Region {region}, Ch {chan_num+1}', contrast_limits=[0, 20000], blending='additive') # T, Z, X, Y)