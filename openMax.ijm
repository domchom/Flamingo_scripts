



//path = getDirectory("Select a folder");
path = "/Volumes/bigData/kkpo_test/1_region_2i/R0000_processed/";

// Get a list of file names to parse through
list_files = getFileList(path);
list_stacks = newArray;
count_stacks = 0;
for (a = 0; a < list_files.length; a++) {
	filename = list_files[a];
	if (lengthOf(filename) == 26) {
		if (endsWith(filename, ".tiff")) {
			list_stacks[count_stacks] = filename;
			count_stacks++;
		}
	}
}

// parse file names to find the number of channels present
// NOTE a lot of this can be deleted
channels_used = newArray(false, false, false, false, false);
channel_names = newArray("C00", "C01", "C02", "C03", "C04")
numb_frames = newArray(0, 0, 0, 0, 0);
C00 = false;
C01 = false;
C02 = false;
C03 = false;
C04 = false;

tif_channel = newArray(lengthOf(list_stacks));
for (a = 0; a<lengthOf(list_stacks); a++) {
	sub = substring(list_stacks[a],7,9);
	tif_channel[a] = parseInt(sub);

	if (tif_channel[a] == 0) {
		channels_used[0] = true;
		C00 = true;
	}
	if (tif_channel[a] == 1) {
		channels_used[1] = true;
		C01 = true;
	}
	if (tif_channel[a] == 2) {
		channels_used[2] = true;
		C02 = true;
	}
	if (tif_channel[a] == 3) {
		channels_used[3] = true;
		C03 = true;
	}
	if (tif_channel[a] == 4) {
		channels_used[4] = true;
		C04 = true;
	}	

}

// import image sequences, rename by channel, and record the number of frames
for (i=0; i<5; i++) {
	if (channels_used[i] == true) {
		 File.openSequence(path, "filter=" + channel_names[i]);
		 rename(channel_names[i]);
		 getDimensions(width, height, channels, slices, frames);
		 numb_frames[i] = slices;	// see if you can fix this on the Python side of things
	}
}

// find the channels with the fewest and largest number of frames
nonzero_frames = Array.deleteValue(numb_frames, 0);
Array.getStatistics(nonzero_frames, min_frames, max_frames, _, _);

// loop back through the channels and trim the long ones
for (i=0; i<5; i++) {
	if (channels_used[i] == true) {
		 selectWindow(channel_names[i]);
		 getDimensions(width, height, channels, slices, frames);
		 if (slices > min_frames) {
		 	diff = max_frames - slices;
		 	Stack.setSlice(slices);
		 	for (j = 0; j <= diff; j++) {
		 		run("Delete Slice");
		 		print("slice deleted from the end of " + channel_names[i]);
		 	}
		 }
	}
}


