
from PySide2.QtWidgets import *
from PySide2.QtGui import *
import EntranceShuffle
import re
from CommonUtils import *
import logging

class LocationManager:
    def __init__(self, world, parent_gui):
        self.world = world
        self.widget = QTreeView()
        self.widget = self.widget
        self.widget.setHeaderHidden(True)
        self.parent_gui = parent_gui

        self.model = QStandardItemModel()
        rootNode = self.model.invisibleRootItem()

        self._unchecked = NeighborhoodCategory("Unchecked", parent = self)
        self._checked = LocationCategory("Checked", font_size=12)
        self._not_possible = LocationCategory("Not Possible", font_size=12)
        self._ignored = LocationCategory("Ignored", font_size=12)
        rootNode.appendRow(self._unchecked)
        rootNode.appendRow(self._checked)
        rootNode.appendRow(self._not_possible)
        rootNode.appendRow(self._ignored)

        self.allCategories = [self._unchecked, self._checked, self._not_possible, self._ignored]
        self.allLocations = set()

        self.widget.setModel(self.model)
        self.expandThisItem(self._unchecked)

        self.model.itemChanged.connect(lambda x: x.processCheck())
        self.widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.widget.customContextMenuRequested.connect(self.openMenu)

    def insertLocation(self, location, first=False):
        # Make sure it's in the set
        if location not in self.allLocations:
            self.allLocations.add(location)

        # Make sure it's removed from all categories
        for category in self.allCategories:
            category.removeLoc(location)

        # Find the subtree to place it in
        if location.ignored:
            destination = self._ignored
        elif location.currently_checked:
            destination = self._checked
        elif not location.possible:
            destination = self._not_possible
        else:
            destination = self._unchecked

        destination.addLoc(location)

    def updateLocationPossible(self, possible_locations, allkeys_possible_locations):
        possible_names = set(x.name for x in possible_locations)
        allkeys_names = set(x.name for x in allkeys_possible_locations)
        for x in self.allLocations:
            possible = x.loc_name in possible_names
            if not possible and x.loc_name in allkeys_names:
                possible = 2
            x.setPossible(possible)

    def updateLocationsIgnored(self, world):
        for x in self.allLocations:
            ignored = locationIsIgnored(world, world.get_location(x.loc_name))
            x.setIgnored(ignored)

    def getOutputFormat(self):
        results = []
        for x in self.allLocations:
            if x.currently_checked:
                results.append(x.loc_name)
        return results

    def expandThisItem(self, item):
        self.widget.expand(self.model.indexFromItem(item))

    def clear_locations(self):
        for location in self.allLocations:
            for category in self.allCategories:
                category.removeLoc(location)
        self.allLocations = set()

    def update_world(self, world):
        self.world = world
        self.clear_locations()

    def openMenu(self, position):
        indexes = self.widget.selectedIndexes()
        assert len(indexes) == 1
        index = indexes[0]
        data = index.data(role=Qt.UserRole)
        if not data:
            return
        data.openMenu(parent=self, position=position)



def itemMaxed(world, itemname):
    if itemname not in world.max_progressions:
        itemname = itemname + " Drop"
        assert itemname in world.max_progressions

    current = world.state.prog_items[itemname]
    maximum = world.max_progressions[itemname]
    return current >= maximum

def locationIsIgnored(world, location):
    if location.name in world.settings.disabled_locations:
        return True
    if getattr(location, 'shop_non_progression', False):
        return True
    if location.item is not None:
        if itemMaxed(world, location.item.name):
            return True
    if not world.settings.shuffle_medigoron_carpet_salesman:
        if location.name == "GC Medigoron":
            return True
    return False

class LocationCategory(QStandardItem):
    def __init__(self, txt, font_size=10, color=QColor(0,0,0)):
        super().__init__()
        self.setEditable(False)
        self.setForeground(color)
        self.setFont(QFont('Open Sans', font_size))
        self.setText(txt)
        self.locs = set()

    def addLoc(self, loc):
        assert loc not in self.locs
        self.locs.add(loc)

        found = False
        for i in range(self.rowCount()):
            if loc < self.child(i,0):
                self.insertRow(i,loc)
                found = True
                break
        if not found:
            self.appendRow(loc)

    def removeLoc(self, loc):
        if loc not in self.locs:
            return
        self.locs.remove(loc)
        self.takeRow(loc.row())

class NeighborhoodGroup(QStandardItem):
    def __init__(self, name):
        super().__init__()
        self.setEditable(False)
        self.setForeground(QColor(0, 0, 0))
        self.setFont(QFont('Open Sans', 10))

        self.name = name
        self.locs = set()
        self.updateText()

    def updateText(self):
        self.setText("{} ({})".format(self.name, len(self.locs)))

    def addLoc(self, loc):
        assert loc not in self.locs
        self.locs.add(loc)

        found = False
        for i in range(self.rowCount()):
            if loc < self.child(i, 0):
                self.insertRow(i, loc)
                found = True
                break
        if not found:
            self.appendRow(loc)
        self.updateText()

    def removeLoc(self, loc):
        if loc not in self.locs:
            return
        self.locs.remove(loc)
        self.takeRow(loc.row())
        self.updateText()

    def processCheck(self):
        pass
    def __lt__(self, other):
        return self.name.lower() < other.name.lower()


class NeighborhoodCategory(QStandardItem):
    def __init__(self, txt, parent):
        super().__init__()

        self.setEditable(False)
        self.setForeground(QColor(0, 0, 0))
        self.setFont(QFont('Open Sans', 10))
        self.setText(txt)
        self.parent = parent
        self.locs = set()
        self.neighborhoods={}

    # Get or create+insert neighborhood
    def getNeighborhood(self, neighborhood_name):
        if neighborhood_name in self.neighborhoods:
            return self.neighborhoods[neighborhood_name]

        # Create it
        neighborhood = NeighborhoodGroup(neighborhood_name)
        self.neighborhoods[neighborhood_name] = neighborhood

        # Insert it in order
        found = False
        for i in range(self.rowCount()):
            if neighborhood < self.child(i, 0):
                self.insertRow(i, neighborhood)
                found = True
                break
        if not found:
            self.appendRow(neighborhood)

        self.parent.expandThisItem(neighborhood)
        return neighborhood

    def addLoc(self, loc):
        assert loc not in self.locs
        self.locs.add(loc)

        neighborhood = self.getNeighborhood(loc.neighborhood)
        neighborhood.addLoc(loc)

    def removeLoc(self, loc):
        if loc not in self.locs:
            return
        self.locs.remove(loc)

        # Check all neighborhoods for removal (the neighborhood name can change)
        for name in list(self.neighborhoods.keys()):
            neighborhood = self.neighborhoods[name]
            neighborhood.removeLoc(loc)
            # Clear out this neighborhood if it is now empty
            if len(neighborhood.locs) == 0:
                self.removeRow(neighborhood.row())
                del self.neighborhoods[name]



class LocationEntry(QStandardItem):
    def __init__(self, loc_name, type, possible, parent_region, checked=False, ignored=False, parent=None):
        super().__init__()

        self.setEditable(False)
        self.setForeground(QColor(0, 0, 0))
        self.setFont(QFont('Open Sans', 10))

        self.loc_name = loc_name
        self.type = type
        self.setCheckable(True)
        self._parent = parent
        self.currently_checked = checked
        self.parent_region = parent_region
        if checked:
            self.setCheckState(Qt.CheckState.Checked)
        else:
            self.setCheckState(Qt.CheckState.Unchecked)
        self.possible = possible
        self.ignored = ignored

        self.known_item = None
        loc = self._parent.world.get_location(self.loc_name)
        if loc.item is not None and not getattr(loc, 'unshuffled_gs_token', False):
            self.known_item = loc.item.name

        self.updateText()
        if self.type == 'Shop':
            self.setData(self, role=Qt.UserRole)

    def isChecked(self):
        return self.checkState() == Qt.CheckState.Checked

    def processCheck(self):
        if not self.isCheckable():
            return
        new_checked = self.isChecked()
        if self.currently_checked == new_checked:
            return
        logging.info("User has {}checked {}".format("" if new_checked else "un", self.loc_name))
        self.currently_checked = new_checked
        self.updateText()
        self._parent.insertLocation(self)

    def setPossible(self, possible):
        if possible == self.possible:
            return
        if possible == 2:
            color = QColor(20, 20, 255)
        elif possible:
                color = QColor(0,0,0)
        else:
            color = QColor(255,0,0)
        self.setForeground(color)
        self.possible = possible
        self.updateText()
        self._parent.insertLocation(self)
    def setIgnored(self, ignored):
        if ignored == self.ignored:
            return
        self.ignored = ignored
        self.updateText()
        self._parent.insertLocation(self)

    def updateText(self):
        if self.possible == 2:
            color = QColor(20, 20, 255)
            self.neighborhood = getNeighborhood(self.parent_region, self._parent.world)
        elif self.possible:
            color = QColor(0,0,0)
            self.neighborhood = getNeighborhood(self.parent_region, self._parent.world)
        else:
            color = QColor(255,0,0)
            self.neighborhood = self.parent_region

        text = self.loc_name + " ("
        if self.known_item:
            text += self.known_item
            text += ") ("
        text += self.neighborhood
        text += ")"

        self.setForeground(color)
        self.setText(text)

    def __eq__(self, other):
        return self.loc_name == other.loc_name
    def __hash__(self):
        return hash(self.loc_name)
    def __lt__(self, other):
        if self.neighborhood.lower() < other.neighborhood.lower():
            return True
        if self.neighborhood.lower() == other.neighborhood.lower():
            if self.loc_name.lower() < other.loc_name.lower():
                return True
        return False

    def openMenu(self, parent, position):
        if self.type == 'Shop':
            menu = QMenu(parent.widget)
            entries = []
            entries.append(menu.addAction("0-99 Rupees"))
            entries.append(menu.addAction("100-200 Rupees"))
            entries.append(menu.addAction("201-500 Rupees"))
            chosen_action = menu.exec_(parent.widget.mapToGlobal(position))
            if chosen_action is None:
                return
            chosen = entries.index(chosen_action)
            logging.info("User has indicated that {} needs {} wallets".format(self.loc_name, chosen))
            parent.parent_gui.updateLocationWallets(self.loc_name, chosen)
            return
        else:
            raise Exception("Unknown location type for context menu")

def originOfExit(exit_name):
    match = re.fullmatch("(.*) -> (.*)", exit_name)
    assert match
    return match.group(1)

def nthOfEST(types, n):
    est = EntranceShuffle.entrance_shuffle_table
    return [x[n][0] for x in est if x[0] in types]

interior_regions = {}
for exit in nthOfEST(['Interior', 'SpecialInterior', 'Grotto', 'Grave', 'SpecialGrave', 'ChildBoss', 'AdultBoss'], 2):
    region = originOfExit(exit)
    interior_regions[region] = exit


overworld_neighborhoods = {
    'Hyrule Field': ['Hyrule Field'],
    'No Location': ['Root'],
    'Kokiri Forest': ['Kokiri Forest'],
    'LW Bridge': ['LW Bridge From Forest'],
    'Gerudo Valley': ['GV Stream', 'GV Crate Ledge', 'GV Fortress Side', 'Gerudo Valley'],
    'Kakariko Village': ['Kakariko Village', 'Kak Rooftop', 'Kak Backyard', 'Kak Impas Ledge', 'Kak Impas Rooftop', 'Kak Odd Medicine Rooftop'],
    'Lost Woods': ['Lost Woods', 'LW Beyond Mido', 'LW Underwater Entrance',],
    'Sacred Forest Meadow': ['Sacred Forest Meadow', 'SFM Entryway'],
    'Hyrule Castle': ['Hyrule Castle Grounds', 'HC Garden'],
    'Death Mountain Cavern': ['DMC Ladder Area Nearby', 'DMC Upper Local', 'DMC Central Nearby', 'DMC Lower Local', 'DMC Central Local', 'DMC Lower Nearby', 'DMC Pierre Platform',],
    'Gerudo Fortress': ['Gerudo Fortress', 'GF Chest Roof', 'GF Balcony', 'GF Roof Gold Skulltula', 'Hideout 1 Torch Jail', 'Hideout 2 Torches Jail', 'Hideout 3 Torches Jail', 'Hideout 4 Torches Jail', 'Hideout Hall to Balcony Lower', 'Hideout Kitchen Hallway', 'Hideout Kitchen Pots',],
    'Death Mountain': ['Death Mountain', 'Death Mountain Summit'],
    'Graveyard': ['Graveyard'],
    'Ganon\'s Castle': ['Ganons Castle Grounds'],
    'Market': ['Market', 'Market Dog Lady House', 'Market Back Alley'],
    'Market Entrance': ['Market Entrance'],
    'Lon Lon Ranch': ['Lon Lon Ranch'],
    'Lake Hylia': ['Lake Hylia', 'LH Fishing Island'],
    'Goron City': ['Goron City', 'GC Darunias Chamber', 'GC Grotto Platform', 'GC Spinning Pot',],
    'ToT Entrance': ['ToT Entrance'],
    'Zora\'s Domain': ['Zoras Domain', 'ZD Behind King Zora',],
    'Zora\'s Fountain': ['Zoras Fountain', 'ZF Underwater', 'ZF Hidden Cave',],
    'Zora River': ['Zora River', 'ZR Front'],
    'Castle Grounds': ['Castle Grounds', 'HC Garden Locations'],
    'Desert Colossus': ['Desert Colossus'],
    'Haunted Wasteland': ['Haunted Wasteland', 'Wasteland Near Crate', 'Wasteland Near Fortress',],
    'Ice Cavern': ['Ice Cavern', 'Ice Cavern Map Room', 'Ice Cavern Iron Boots Region', 'Ice Cavern Compass Room', 'Ice Cavern Behind Ice Walls', 'Ice Cavern Beginning', 'Ice Cavern Spinning Blades',],
    'Ganon\'s Castle Grounds': ['Ganons Castle Grounds'],
    'Gerudo Valley': ['Gerudo Valley', 'GV Upper Stream', 'GV Crate Ledge', 'GV Fortress Side', 'GV Grotto Ledge',],

    'Deku Tree': ['Deku Tree Slingshot Room', 'Deku Tree Lobby', 'Deku Tree Boss Room', 'Deku Tree Basement Backroom', 'Deku Tree Compass Room', 'Deku Tree Basement Water Room Front', 'Deku Tree Basement Ledge', 'Deku Tree Basement Ledge', 'Deku Tree Basement Water Room Back', 'Deku Tree Basement Back Room', 'Deku Tree Basement', 'Deku Tree Boss Door', 'Deku Tree Before Boss',],
    'Dodongo\'s Cavern': ['Dodongos Cavern Climb', 'Dodongos Cavern Lobby', 'Dodongos Cavern Far Bridge', 'Dodongos Cavern Boss Area', 'Dodongos Cavern Staircase Room', 'Dodongos Cavern Bomb Bag Area', 'Dodongos Cavern Lower Right Side', 'Dodongos Cavern Boss Door', 'Dodongos Cavern Before Boss', 'Dodongos Cavern Before Upper Lizalfos', 'Dodongos Cavern Torch Room', 'Dodongos Cavern Upper Lizalfos',],
    'Jabu Jabu\'s Belly': ['Jabu Jabus Belly Boss Area', 'Jabu Jabus Belly Depths', 'Jabu Jabus Belly Main', 'Jabu Jabus Belly Beginning', 'Jabu Jabus Belly Boss Door', 'Jabu Jabus Belly Before Boss', 'Jabu Jabus Belly Past Big Octo',],
    'Bottom of the Well': ['Bottom of the Well Main Area', 'Bottom of the Well Perimeter', 'Bottom of the Well Middle', 'Bottom of the Well Behind Fake Walls', 'Bottom of the Well Behind Locked Doors',],
    'Forest Temple': ['Forest Temple Lobby', 'Forest Temple NW Outdoors', 'Forest Temple NE Outdoors', 'Forest Temple Outdoors High Balconies', 'Forest Temple Block Push Room', 'Forest Temple Boss Region', 'Forest Temple Bow Region', 'Forest Temple Falling Room', 'Forest Temple Outside Upper Ledge', 'Forest Temple Straightened Hall', 'Forest Temple After Block Puzzle', 'Forest Temple Central Area', 'Forest Temple NE Outdoors Ledge', 'Forest Temple Outdoor Ledge', 'Forest Temple Outdoors Top Ledges', 'Forest Temple Before Boss', 'Forest Temple Boss Door', 'Forest Temple Frozen Eye Switch Room',],
    'Fire Temple': ['Fire Temple Lower', 'Fire Temple Big Lava Room', 'Fire Temple Middle', 'Fire Temple Upper', 'Fire Big Lava Room', 'Fire Boss Room', 'Fire Lower Locked Door', 'Fire Lower Maze', 'Fire Upper Maze', 'Fire Temple Boulder Maze Lower', 'Fire Temple Boulder Maze Upper', 'Fire Temple Flame Maze', 'Fire Temple Lower Locked Door', 'Fire Temple Narrow Path Room', 'Fire Temple Boss Door', 'Fire Temple Elevator Room',],
    'Water Temple': ['Water Temple Dive', 'Water Temple Cracked Wall', 'Water Temple Dragon Statue', 'Water Temple Middle Water Level', 'Water Temple Dark Link Region', 'Water Temple Highest Water Level', 'Water Temple North Basement', 'Water Temple Falling Platform Room', 'Water Temple Basement Gated Areas', 'Water Temple Lobby', 'Water Temple Lowered Water Levels', 'Water Temple Boss Key Chest Room', 'Water Temple Central Bow Target', 'Water Temple River', 'Water Temple Boss Door',],
    'Shadow Temple': ['Shadow Temple Beginning', 'Shadow Temple Beyond Boat', 'Shadow Temple First Beamos', 'Shadow Temple Huge Pit', 'Shadow Temple Wind Tunnel', 'Shadow Temple Dead Hand Area', 'Shadow Temple Invisible Maze', 'Shadow Temple Lower Huge Pit', 'Shadow Temple Upper Huge Pit', 'Shadow Temple After Wind', 'Shadow Temple Invisible Spikes', 'Shadow Temple Boss Door', 'Shadow Temple 3 Spinning Pots Rupees', 'Shadow Temple Before Boss', 'Shadow Temple Beyond Boat Scarecrow', 'Shadow Temple Beyond Boat SoT Block', 'Shadow Temple Boat',],
    'Spirit Temple': ['Child Spirit Temple', 'Early Adult Spirit Temple', 'Child Spirit Temple Climb', 'Spirit Temple Beyond Central Locked Door', 'Spirit Temple Beyond Final Locked Door', 'Spirit Temple Central Chamber', 'Spirit Temple Outdoor Hands', 'Desert Colossus From Spirit Lobby', 'Spirit Temple Lobby', 'Spirit Temple Shared', 'Adult Spirit Temple', 'Lower Adult Spirit Temple', 'Mirror Shield Hand', 'Silver Gauntlets Hand', 'Spirit Temple Boss Area', 'Adult Spirit Temple Climb', 'Spirit Temple Beyond Anubis Room', 'Spirit Temple Big Mirror Room', 'Spirit Temple Boss Door', 'Child Spirit Before Locked Door', 'Spirit Temple Anubis Room',],
    'Gerudo Training Ground': ['Gerudo Training Ground Lobby', 'Gerudo Training Ground Central Maze Right', 'Gerudo Training Ground Eye Statue Lower', 'Gerudo Training Ground Eye Statue Upper', 'Gerudo Training Ground Hammer Room', 'Gerudo Training Ground Heavy Block Room', 'Gerudo Training Ground Lava Room', 'Gerudo Training Ground Like Like Room', 'Gerudo Training Ground Central Maze', 'Gerudo Training Ground Left Side', 'Gerudo Training Ground Right Side', 'Gerudo Training Ground Back Areas', 'Gerudo Training Ground Stalfos Room', 'Gerudo Training Ground Underwater',],
    'Ganon\'s Castle': ['Ganons Castle Water Trial', 'Ganons Castle Deku Scrubs', 'Ganons Castle Forest Trial', 'Ganons Castle Light Trial', 'Ganons Castle Shadow Trial', 'Ganons Castle Spirit Trial', 'Ganons Castle Tower', 'Ganons Castle Shadow Trial Second Gap', 'Ganons Castle Spirit Trial Second Room Back', 'Ganons Castle Spirit Trial Second Room Front', 'Ganondorf Boss Room', 'Ganons Castle Fire Trial', 'Ganons Castle Fire Trial Ending', 'Ganons Castle Forest Trial Ending', 'Ganons Castle Light Trial Boulder Room', 'Ganons Castle Light Trial Ending', 'Ganons Castle Shadow Trial Ending', 'Ganons Castle Shadow Trial First Gap', 'Ganons Castle Spirit Trial Ending', 'Ganons Castle Tower Below Boss', 'Ganons Castle Water Trial Ending',],
}

redirect_region = {
    'Beyond Door of Time': 'Temple of Time',
    'Kak Impas House Near Cow': 'Kak Impas House Back',
}

region_to_neighborhood = {}
for neighborhood in overworld_neighborhoods:
    for region in overworld_neighborhoods[neighborhood]:
        region_to_neighborhood[region] = neighborhood

unknown_neighborhoods = set()
def getNeighborhood(region, world):
    if region in region_to_neighborhood:
        return region_to_neighborhood[region]
    if region in redirect_region:
        return getNeighborhood(redirect_region[region], world)
    if region in interior_regions and not getattr(world.settings, 'decouple_entrances', False):
        region_obj = world.get_region(region)
        exit_name = interior_regions[region]
        exit = expectOne([x for x in region_obj.exits if x.name == exit_name])
        if exit.shuffled:
            # TODO: if there is a multi-region interior, can we connect it to a different un-shuffled entrance?
            return "Unknown"
        new_region = exit.connected_region
        return getNeighborhood(new_region, world)
    if region not in unknown_neighborhoods:
        unknown_neighborhoods.add(region)

        print("Unknown neighborhoods =")
        for x in sorted(list(unknown_neighborhoods)):
            print(x)
    return region
