# HoodTracker
Simple tracker for OoT-Randomizer which uses its logic

The UI is very rudimentary right now; so far it only communicates to the player by reading and writing to a file called output.txt.

# Usage
The first thing it needs is your settings string, which you can configure using the GUI of OoT-Randomizer itself. If you don't have an output.txt yet you can run

> python HoodTracker.py --settings-string \<yoursettingsstring\>
  
Then it will generate an output.txt at the start of the game, with no equipment and no locations checked off.
For subsequent uses, edit output.txt and run
> python HoodTracker.py

again. After accomplishing one or more things in the game, edit the file and run the tracker again. Repeat until you get the Triforce.

### Equipment
When you collect a piece of equipment, add a line underneath "equipment:" with the name of the item. A list of item names that you have 0 copies of is listed under "possible_equipment:". If you have more than one copy of an item, duplicate the line. 50 gold skulltula tokens is 50 lines of "Gold Skulltule Token". Deal with it.

### Locations
When you are able to collect something from a location, the name of the location will show up under "possible_locations:". If you want to check this location off, cut and paste the line under "checked_off:" so that it will not show up under "possible_locations:" any more. If you want to check off sequence breaking / out-of-logic locations early you'll have to know their name.

### Entrance Shuffle
If you have any kind of entrance shuffle on, when you are able to reach unknown territory, it will ask you where the exit leads under "please_explore:". The line will say "\<exit name\> goesto ?" All exits are named "\<starting region\> -> \<destination region\>" and one of these region names needs to replace the "?". Names of the unknown shuffled exits will be listed in "other_shuffled_exits:" which will help you figure out what the name of the destination region should be.
  
Be careful here; there are more region names in the randomizer than region names in the game, and an imprecise answer can impact the tracker's accuracy.
You don't need to move the line to "known_exits:" yourself; it will move there automatically if you replace the "?" with a region name. Simple regions with only one way in/out will sometimes automatically discover the reverse direction, or you might have to fill the reverse direction out yourself after running the tracker again.
If you find a common type of grotto, you can replace "?" with a keyword instead of a region name:
* auto_generic_grotto for all generic chest + gossip stone grottoes
* auto_scrub_grotto for all 2- and 3-deku scrub grottoes (TODO: put the 1 deku scrub grotto here too)
* auto_fairy_fountain for all fairy fountain grottoes with nothing else in them
* auto_great_fairy_fountain for all great fairy fountains

These keywords will be turned into a specific region name after you run the tracker, so keep that in mind when checking off location names. (If you have grotto shuffle on, the generic grotto chests will not appear in the location list, because the tracker will assume you collect the chest immediately. If you have scrubsanity on, and you use auto_scrub_grotto, don't worry about whether a grotto has 2 or 3 scrubs; just check them all off after buying all of their items.)

### Settings String
After your output.txt contains a value for "settings_string:", a settings string in the arguments won't work. Just edit the text file. I will add some policy to deal with this later.

# Features Support
Does not support any number of Ganon's trials besides 0 and 6. Probably does not support Master Quest dungeons or glitched logic. I am not sure how well the settings string translates from version to version of the randomizer so you may have to recreate certain settings by hand in the randomizer version which is included in this folder. If there are randomized settings in your settings string, you will have to fill out the settings as they actually got decided; I'm not sure what will happen otherwise.

### Final Tips
Vim is good for cutting/pasting lines at a time. Its macros can also help move a line instantly to another keyword. The "please_explore:" region is hard to use but makes entrance shuffle possible. I have been running this with an IDE (PyCharm) so that saving to output.txt is automatically done before running HoodTracker.py (you may lose some of your text edits if you don't save first). Many of the asserts in the Python code are probably unhelpful, so edit carefully. I will try to work on a GUI when I have the chance and some more insight. Please enjoy, but also, deal with it.
