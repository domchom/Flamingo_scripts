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
#from dask.array.image import imread as dask_read 
import dask.array as da

class Kkpo:

    def __init__(self, file_path=None):
        if file_path == None:
            print('*****'*9)
            print("I can't make a Kakapo without a file path!")
            print('*****'*9)
            sys.exit()
        self.file_path = Path(file_path)
        self.files = [file for file in os.listdir(self.file_path) if all([file.endswith('.tif')]) and not any([file.startswith('.'),
                                                                                                              'MP' in file,
                                                                                                              'max' in file])]

        self.sample_names =    np.unique([file.split('_')[0] for file in self.files])
        self.timepoint_names = np.unique([file.split('_')[1] for file in self.files])
        self.view_names =      np.unique([file.split('_')[2] for file in self.files])
        self.region_names =    np.unique([file.split('_')[3] for file in self.files])
        self.tileX_names =     np.unique([file.split('_')[4] for file in self.files])
        self.tileY_names =     np.unique([file.split('_')[5] for file in self.files])
        self.channel_names =   np.unique([file.split('_')[6] for file in self.files])
        self.illum_names =     np.unique([file.split('_')[7] for file in self.files])
        self.camera_names =    np.unique([file.split('_')[8] for file in self.files])
        self.planes =          np.unique([file.split('_')[9] for file in self.files])

        self.num_samples = len(self.sample_names)
        self.num_timepoints = len(self.timepoint_names)
        self.num_views = len(self.view_names)
        self.num_regions = len(self.region_names)
        self.num_tilesX = len(self.tileX_names)
        self.num_tilesY = len(self.tileY_names)
        self.num_channels = len(self.channel_names)
        self.num_illum = len(self.illum_names)
        self.num_cameras = len(self.camera_names)

    def get_interval(self):
        '''
        Identifies first and last settings file in the kkpo directory. Pulls timestamps from these files
        to determine the exact startina and end time. Calculates the total number of seconds elapsed
        and the frame interval from the number of time points.
        Returns: frame interval in seconds/frame.
        '''
        setting_files = [file for file in os.listdir(self.file_path) if "Settings.txt" in file and not file.startswith('.')]
        first_timepoint_name = [file for file in setting_files if all(match in file for match in [self.timepoint_names[0], self.region_names[0], self.channel_names[0], self.illum_names[0]])]
        last_timepoint_name = [file for file in setting_files if all(match in file for match in [self.timepoint_names[-1], self.region_names[0], self.channel_names[0], self.illum_names[0]])]
        
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
        self.start_datetime = get_datetime(first_timepoint_file)
        last_timepoint_file = np.loadtxt(self.file_path / last_timepoint_name[0], dtype='str', delimiter = '/n')
        self.end_datetime = get_datetime(last_timepoint_file)
        self.total_seconds = (self.end_datetime - self.start_datetime).total_seconds()
        self.interval = self.total_seconds / (self.num_timepoints - 1)
        return self.interval

    def save_max_project(self, save_vol = False, downsample = False):
        '''
        Loads each timepoint, channel, stage position, etc (still working out the deets), calculates a max projection,
        and saves the projection to file.
        Accepts: 
         - save_vol (bool) - whether or not to also save the full volume to file.
         - downsample - whether or not to downsample the volume.
        Returns:
         not sure yet.
        '''
        # create a folder to save the max projections
        self.max_proj_path = self.file_path / 'max_projections'
        if not os.path.exists(self.max_proj_path):
            os.mkdir(self.max_proj_path)
        
        max_projection = np.zeros((2048,2048))
        its = self.num_samples*self.num_timepoints*self.num_views*self.num_regions*self.num_tilesX*self.num_tilesY*self.num_channels*self.num_illum*self.num_cameras
        with tqdm(total = its, miniters=its/100) as pbar:
            pbar.set_description('Calculating max projections')
            for samp in range(self.num_samples):
                for time in range(self.num_timepoints):
                    for view in range(self.num_views):
                        for reg in range(self.num_regions):
                            for tileX in range(self.num_tilesX):
                                for tileY in range(self.num_tilesY):
                                    for chan in range(self.num_channels):
                                        for illum in range(self.num_illum):
                                            for cam in range(self.num_cameras):
                                                file_name = [file for file in self.files if all([match in file for match in [ self.sample_names[samp], 
                                                                                                                              self.timepoint_names[time], 
                                                                                                                              self.view_names[view], 
                                                                                                                              self.region_names[reg], 
                                                                                                                              self.tileX_names[tileX], 
                                                                                                                              self.tileY_names[tileY], 
                                                                                                                              self.channel_names[chan], 
                                                                                                                              self.illum_names[illum], 
                                                                                                                              self.camera_names[cam]]])][0]
                                                img = tiff_read(self.file_path / file_name)
                                                max_projection = np.max(img, axis=0)
                                                tiff_write(self.max_proj_path /  f'{self.sample_names[samp]}_{self.timepoint_names[time]}_{self.view_names[view]}_{self.region_names[reg]}_{self.tileX_names[tileX]}_{self.tileY_names[tileY]}_{self.channel_names[chan]}_{self.illum_names[illum]}_{self.camera_names[cam]}_max_projection.tif', max_projection)
                                                pbar.update(1)
    def interact(self, region):
        ''' 
        Dask/Napari interactive workflow
        '''
            
        ims = dask_read(self.file_path /  ('*'+region+'*.tif')) #S000_t000011_V000_R0003_X000_Y000_C02_I0_D0_P00190

        with napari.gui_qt():
            viewer = napari.Viewer(title="Interactive Kkpo Viewer")
            viewer.add_image(ims, name=f'Region {region}')

        
