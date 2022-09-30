from interact.kkpo import Kkpo
import time
from dask.distributed import Client
import os
from tqdm import tqdm


if __name__ == '__main__':
    client = Client()
    print(client.dashboard_link)
    dirs = os.walk('/Volumes/zs2tb/stims/')
    dirs = [d[0] for d in dirs]
    dirs.sort()
    dirs.pop(0)
    with tqdm(total=len(dirs)) as pbar:
        for dir in dirs:
            kkpo = Kkpo(dir)

            start = time.time()
            kkpo.save_regions(save_vol=True, save_max=True, overwrite=True)
            end = time.time()
            print(f'Saved regions in {round(end - start, 3)} seconds')
            pbar.update(1)

    #kkpo.view_volumes('R0000')
