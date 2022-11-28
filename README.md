# HoodTracker
A tracker for OoT-Randomizer which uses its logic and handles entrance shuffling

### How To Run
You need Python 3.8+ installed, and the PySide2 library ("pip install PySide2" will do this.)
Then run
```shell
python HoodTracker.py
```

The save file is called output.txt, and if you don't have one, running the tracker will first prompt you for a settings string. This should come from the same version of OoT-Randomizer which is found in this folder. It doesn't need to be the exact same settings - more tricks enabled or more shuffle settings turned on will still be solveable.

There are three main sections of the window:
![Example Screenshot](https://github.com/hoodedpaladin/HoodTracker/raw/master/images/example_screenshot.png?raw=true)

### Inventory
The lower-right corner shows your inventory. Left-click to add an item to your inventory, and right-click to decrease the amount.

### Locations
The left side of the window shows all locations where progression items can be found. After the name of the location, in parentheses is the "neighborhood" of this location, which is the suggestion of the major region that this will be found near to (experimental feature). To help find your way to locations, the "Find Path" dialog box can show you a possible path from your current region to the region containing your location. If you want to check off locations that are out of logic (items that are merely visible, or that are collected using a trick that is not in the settings string) you can check them off from the "Not Possible" section.

### Entrance Shuffle
If you have entrance shuffle on, the upper-right corner will prompt when there are unknown exits. When you take the exit from <first region> to <second region>, note in the dropdown where you actually end up. Knowing the precise OoT-Randomizer name can make a difference - for example, Zora River lets you float downriver to ZR Front, but you can't always reach Zora River from ZR Front.
  
### Master Quest, Dungeon Shortcuts, Empty Dungeons, and Ganon's Trials Selections
The checkboxes for these features show up along the bottom of the screen if the settings string doesn't explicitly state what they are.

# Features Support
Supports:
  - OoTR release 7.0
  - Entrance shuffle
  - Master Quest dungeons
  - Ganon's trials, dungeon shortcuts and empty dungeons
  - Changing settings string on the fly (not sure how stable this is)
  
Probably does not support glitched logic. The settings string should be generated using OoTR v7.0, otherwise it may not be valid. If there are randomized settings in your settings string, you should fill out the settings as they actually got decided; I'm not sure what will happen otherwise.
