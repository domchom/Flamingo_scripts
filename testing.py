from interact.kkpo import Kkpo
import time

kkpo = Kkpo('/Volumes/bigData/kkpo_test/1_region_2i')

start = time.time()
kkpo.save_regions(save_vol=False, overwrite=True)
end = time.time()
print(f'Saved regions in {round(end - start, 3)} seconds')

#kkpo.view_volumes('R0000')