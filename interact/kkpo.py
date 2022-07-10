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
    
    def save_regions(self, save_vol = False, save_max = True, step = 8, overwrite = False):
        ''' 
        Saves the regions as individual files.
        Parameters: save_vol (bool) - whether or not to save the volume as a single file
                    save_max (bool) - whether or not to save the max projection as a single file    
                    step (int) - the step size to use when saving the volume (step=8 will be <10% of original file size)
                    overwrite (bool) - whether or not to overwrite existing files
        Returns: None
        '''
        if not save_vol and not save_max:
            print('*****'*9)
            print('I can\'t save nothing!')
            print('*****'*9)
            sys.exit()

        for region_num, region_name in enumerate(self.region_names):
            print(f'Saving region {region_num + 1}/{len(self.region_names)}')
            print(f'Collecting information about region {region_name}')

            interval, timepoint_names, channel_names, illum_names, plane_names = self.get_region_info(region_name)

            # create a folder to save the max projections and volume arrays for this region
            region_save_path = self.file_path / f'{region_name}_processed'

            if os.path.exists(region_save_path) and not overwrite:
                print(f'{region_save_path} already exists. Pass overwrite=True to overwrite.')
                continue
            
            elif os.path.exists(region_save_path) and overwrite:
                print(f'{region_save_path} already exists. Overwriting file!')
    
            else:
                print('Creating directories...')
                Path.mkdir(region_save_path, parents=True, exist_ok=True)
    
            for ch_num, ch_name in enumerate(channel_names):
                print(f'Saving channel {ch_num+1}/{len(channel_names)}')
                if len(illum_names) > 1:
                    print('Two-sided illumination detected')
                    channel_array_left = dask_read(self.file_path / f'*{region_name}*{ch_name}_I0*.tif')
                    channel_array_right = dask_read(self.file_path / f'*{region_name}*{ch_name}_I1*.tif')

                    # if one side has fewer time points, trim the other side
                    numtp1 = channel_array_left.shape[0]
                    numtp2 = channel_array_right.shape[0]
                    if numtp1 < numtp2:
                        channel_array_right = channel_array_right[:numtp1]
                    elif numtp2 < numtp1:
                        channel_array_left = channel_array_left[:numtp2]
                    assert channel_array_left.shape == channel_array_right.shape, 'something is wrong... I0 and I1 arrays are not the same shape'


                else:
                    channel_array = dask_read(self.file_path /  f'*{region_name}*{ch_name}*.tif')

                # save the downsampled channel volume, if requested
                if save_vol:

                    chan_path = region_save_path / f'{region_name}_{ch_name}_volume.zarr'

                    if len(illum_names) > 1:
                        with yaspin() as sp:
                            sp.text = f'Fusing two-sided illumination and converting full volume for {ch_name} to zarr, please be patient...'
                            start = time.time()
                            fused = da.maximum(channel_array_left, channel_array_right)
                            da.to_zarr(fused[:,:,::step,::step], chan_path, overwrite=True)
                            end = time.time()
                            print(f'Saved channel {ch_name} in {round(end - start, 3)} seconds')

                    else:
                        with yaspin() as sp:
                            sp.text = f'Converting full volume for {ch_name} to zarr, please be patient...'
                            start = time.time()
                            da.to_zarr(channel_array[:,:,::step,::step], chan_path, overwrite=True)
                            end = time.time()
                            print(f'Saved channel {ch_name} in {round(end - start, 3)} seconds')

                # save the max projections for this channel (getting ~16-20s/it which is about as fast as I can do it using fiji)
                if save_max:
                    with tqdm(total=len(timepoint_names)) as max_pbar:
                        max_pbar.set_description('Saving max projections')
                        for tp, tp_name in enumerate(timepoint_names):
                            if len(illum_names) > 1:
                                tiff_write(region_save_path / f'{region_name}_{ch_name}_{tp_name}_Max.tiff', np.maximum(np.max(channel_array_left[tp,:,:,:], axis=0), np.max(channel_array_right[tp,:,:,:], axis=0)))
                            else:
                                tiff_write(region_save_path / f'{region_name}_{ch_name}_{tp_name}_Max.tiff', np.max(channel_array[tp,:,:,:], axis=0))
                            max_pbar.update(1)

        print(f'done saving regions')


    def view_volumes(self, region):
        ''' 
        Dask/Napari interactive workflow
        '''
        # check for volume data
        region_save_path = self.file_path / f'{region}_processed'
        interval, timepoint_names, channel_names, illum_names, plane_names = self.get_region_info(region)
        volume_names = [f'{region}_{ch}_volume.zarr' for ch in channel_names]
        if not all(os.path.exists(region_save_path / volume_name) for volume_name in volume_names):
            print(f'One or more channels for region {region} have not been processed. Please run save_regions(save_vol = True) before trying to interact with saved volumes.')

        channels = [da.from_zarr(region_save_path / f'{region}_{ch}_volume.zarr') for ch in channel_names]

        with napari.gui_qt():
            viewer = napari.Viewer(title="Interactive Kkpo Viewer")
            for chan_num, channel in enumerate(channels):
                viewer.add_image(channel, name=f'Region {region}, Ch {chan_num+1}', contrast_limits=[0, 20000], blending='additive') # T, Z, X, Y)