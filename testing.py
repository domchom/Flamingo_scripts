from interact.kkpo import Kkpo
import time

kkpo = Kkpo('/Volumes/bigData/kkpo_test/song')

start = time.time()
kkpo.save_regions(save_vol=True, overwrite=True)
end = time.time()
print(f'Saved regions in {round(end - start, 3)} seconds')