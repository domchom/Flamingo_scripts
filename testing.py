from interact.kkpo import Kkpo

kkpo = Kkpo('/Volumes/bigData/kkpo_test/song')
kkpo.interact('R0003')

'''
good start!
next, separate out separate channels, and add each as a separate layer in the viewer.
bind keys to move forward and backward in time/z to make it easier for the computer to keep up.

Other things to add:
 - aspect ratio
 - could I write a widget with typable fields for the timepoint, sample, etc?
'''