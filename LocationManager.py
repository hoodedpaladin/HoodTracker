
from PySide2.QtWidgets import *
from PySide2.QtGui import *
import EntranceShuffle
import re
from CommonUtils import *
import logging

class LocationManager:
    def __init__(self, world):
        self.world = world
        self.widget = QTreeView()
        self.widget = self.widget
        self.widget.setHeaderHidden(True)

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

    def updateLocationPossible(self, possible_locations):
        possible_names = set(x.name for x in possible_locations)
        for x in self.allLocations:
            possible = x.loc_name in possible_names
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

def itemMaxed(world, itemname):
    if itemname not in world.max_progressions:
        itemname = itemname + " Drop"
        assert itemname in world.max_progressions

    current = world.state.prog_items[itemname]
    maximum = world.max_progressions[itemname]
    return current >= maximum

def locationIsIgnored(world, location):
    if location.name in world.disabled_locations:
        return True
    if getattr(location, 'shop_non_progression', False):
        return True
    if location.item is not None:
        if itemMaxed(world, location.item.name):
            return True
    if not world.shuffle_medigoron_carpet_salesman:
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
    def __init__(self, loc_name, possible, parent_region, checked=False, ignored=False, parent=None):
        super().__init__()

        self.setEditable(False)
        self.setForeground(QColor(0, 0, 0))
        self.setFont(QFont('Open Sans', 10))

        self.loc_name = loc_name
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
        if possible:
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
        if self.possible:
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


def originOfExit(exit_name):
    match = re.fullmatch("(.*) -> (.*)", exit_name)
    assert match
    return match.group(1)

def nthOfEST(types, n):
    est = EntranceShuffle.entrance_shuffle_table
    return [x[n][0] for x in est if x[0] in types]

interior_regions = {}
for exit in nthOfEST(['Interior', 'SpecialInterior', 'Grotto', 'Grave', 'SpecialGrave'], 2):
    region = originOfExit(exit)
    interior_regions[region] = exit


overworld_neighborhoods = {
    'Hyrule Field': ['Hyrule Field'],
    'No Location': ['Root'],
    'Kokiri Forest': ['Kokiri Forest'],
    'LW Bridge': ['LW Bridge From Forest'],
    'Gerudo Valley': ['GV Stream', 'GV Crate Ledge', 'GV Fortress Side', 'Gerudo Valley'],
    'Kakariko Village': ['Kakariko Village', 'Kak Rooftop', 'Kak Backyard', 'Kak Impas Ledge', 'Kak Impas Rooftop', 'Kak Odd Medicine Rooftop'],
    'Lost Woods': ['Lost Woods', 'LW Beyond Mido'],
    'Sacred Forest Meadow': ['Sacred Forest Meadow', 'SFM Entryway'],
    'Hyrule Castle': ['Hyrule Castle Grounds', 'HC Garden'],
    'Death Mountain Cavern': ['DMC Ladder Area Nearby', 'DMC Upper Local', 'DMC Central Nearby', 'DMC Lower Local', 'DMC Central Local'],
    'Gerudo Fortress': ['Gerudo Fortress'],
    'Death Mountain': ['Death Mountain', 'Death Mountain Summit'],
    'Graveyard': ['Graveyard'],
    'Ganon\'s Castle': ['Ganons Castle Grounds'],
    'Market': ['Market', 'Market Dog Lady House', 'Market Back Alley'],
    'Market Entrance': ['Market Entrance'],
    'Lon Lon Ranch': ['Lon Lon Ranch'],
    'Lake Hylia': ['Lake Hylia', 'LH Fishing Island'],
    'Goron City': ['Goron City', 'GC Darunias Chamber'],
    'ToT Entrance': ['ToT Entrance'],
    'Zora\'s Domain': ['Zoras Domain'],
    'Zora\'s Fountain': ['Zoras Fountain'],
    'Zora River': ['Zora River', 'ZR Front'],
    'Castle Grounds': ['Castle Grounds', 'HC Garden Locations'],
    'Desert Colossus': ['Desert Colossus'],
    'Haunted Wasteland': ['Haunted Wasteland'],
    'Ice Cavern': ['Ice Cavern'],
    'Ganon\'s Castle Grounds': ['Ganons Castle Grounds'],
    'Gerudo Valley': ['Gerudo Valley', 'GV Upper Stream', 'GV Crate Ledge', 'GV Fortress Side',],

    'Deku Tree': ['Deku Tree Slingshot Room', 'Deku Tree Lobby', 'Deku Tree Boss Room', 'Deku Tree Basement Backroom'],
    'Dodongo\'s Cavern': ['Dodongos Cavern Climb', 'Dodongos Cavern Lobby', 'Dodongos Cavern Far Bridge', 'Dodongos Cavern Boss Area', 'Dodongos Cavern Staircase Room'],
    'Jabu Jabu\'s Belly': ['Jabu Jabus Belly Boss Area', 'Jabu Jabus Belly Depths', 'Jabu Jabus Belly Main'],
    'Bottom of the Well': ['Bottom of the Well Main Area'],
    'Forest Temple': ['Forest Temple Lobby', 'Forest Temple NW Outdoors', 'Forest Temple NE Outdoors', 'Forest Temple Outdoors High Balconies', 'Forest Temple Block Push Room', 'Forest Temple Boss Region', 'Forest Temple Bow Region', 'Forest Temple Falling Room', 'Forest Temple Outside Upper Ledge', 'Forest Temple Straightened Hall'],
    'Fire Temple': ['Fire Temple Lower', 'Fire Temple Big Lava Room', 'Fire Temple Middle', 'Fire Temple Upper'],
    'Water Temple': ['Water Temple Dive', 'Water Temple Cracked Wall', 'Water Temple Dragon Statue', 'Water Temple Middle Water Level', 'Water Temple Dark Link Region', 'Water Temple Highest Water Level', 'Water Temple North Basement', 'Water Temple Falling Platform Room',],
    'Shadow Temple': ['Shadow Temple Beginning', 'Shadow Temple Beyond Boat', 'Shadow Temple First Beamos', 'Shadow Temple Huge Pit', 'Shadow Temple Wind Tunnel',],
    'Spirit Temple': ['Child Spirit Temple', 'Early Adult Spirit Temple', 'Child Spirit Temple Climb', 'Spirit Temple Beyond Central Locked Door', 'Spirit Temple Beyond Final Locked Door', 'Spirit Temple Central Chamber', 'Spirit Temple Outdoor Hands', 'Desert Colossus From Spirit Lobby',],
    'Gerudo Training Grounds': ['Gerudo Training Grounds Lobby', 'Gerudo Training Grounds Central Maze Right', 'Gerudo Training Grounds Eye Statue Lower', 'Gerudo Training Grounds Eye Statue Upper', 'Gerudo Training Grounds Hammer Room', 'Gerudo Training Grounds Heavy Block Room', 'Gerudo Training Grounds Lava Room', 'Gerudo Training Grounds Like Like Room', 'Gerudo Training Grounds Central Maze'],
    'Ganon\'s Castle': ['Ganons Castle Water Trial', 'Ganons Castle Deku Scrubs', 'Ganons Castle Forest Trial', 'Ganons Castle Light Trial', 'Ganons Castle Shadow Trial', 'Ganons Castle Spirit Trial', 'Ganons Castle Tower',],
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
    if region in interior_regions:
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
