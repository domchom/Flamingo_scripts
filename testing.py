from interact.kkpo import Kkpo

kkpo = Kkpo('/Volumes/bigData/kkpo_test/song')
#kkpo.interact('R0003')
kkpo.save_regions(region='R0001', overwrite=True)
#kkpo.view_volumes(region='R0001')
'''
good start!
next, separate out separate channels, and add each as a separate layer in the viewer.
bind keys to move forward and backward in time/z to make it easier for the computer to keep up.

Other things to add:
 - aspect ratio
 - could I write a widget with typable fields for the timepoint, sample, etc?
'''

'''
I think I need to do something like this:
1) get the desired dask array for each view
2) save the array as a zarr file
3) project the array onto a max projection and save the projection as a tif file
'''

'''
I'm running into huge problems. take a big step back and use a jupyter notebook so that you can visualize the array and chunk sizes
Make sure you can use a workflow that can concatenate multiple channels to create a single array and save that as zarr
'''