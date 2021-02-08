
from PySide2.QtWidgets import *
from PySide2.QtGui import *
import EntranceShuffle
import re
from CommonUtils import *
import logging

class LocationManager:
    def __init__(self, locations, world):
        self.world = world
        treeWidget = QTreeView()
        self.widget = treeWidget
        treeWidget.setHeaderHidden(True)

        treeModel = QStandardItemModel()
        rootNode = treeModel.invisibleRootItem()

        self._unchecked = TableEntry("Unchecked", font_size=12)
        self._checked = TableEntry("Checked", font_size=12)
        self._not_possible = TableEntry("Not Possible", font_size=12)
        self._ignored = TableEntry("Ignored", font_size=12)
        rootNode.appendRow(self._unchecked)
        rootNode.appendRow(self._checked)
        rootNode.appendRow(self._not_possible)
        rootNode.appendRow(self._ignored)

        self.allLocations = []

        for x in locations:
           self.addLocation(x)

        treeWidget.setModel(treeModel)
        treeWidget.expand(treeModel.indexFromItem(self._unchecked))

        treeModel.itemChanged.connect(lambda x: x.processCheck())

    def addLocation(self, location, first=False):
        location._parent = self
        # Make sure it's in the set
        if location not in self.allLocations:
            self.allLocations.append(location)

        if location.ignored:
            destination = self._ignored
        elif location.currently_checked:
            destination = self._checked
        elif not location.possible:
            destination = self._not_possible
        else:
            destination = self._unchecked
            neighborhood = getNeighborhood(location.parent_region, self.world)
            location.setText("{} ({})".format(location.loc_name, neighborhood))
        if first:
            destination.insertRow(0, location)
        else:
            destination.appendRow(location)
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


def locationIsIgnored(world, location):
    if location.filter_tags is not None and 'Skulltulas' in location.filter_tags:
        if world.state.prog_items['Gold Skulltula Token'] >= world.max_progressions['Gold Skulltula Token']:
            if world.tokensanity == 'off' or (
                    world.tokensanity == 'dungeons' and location.scene >= 0xA) or (
                    world.tokensanity == 'overworld' and location.scene < 0xA):
                return True
    if location.name in world.disabled_locations:
        return True
    return False


class TableEntry(QStandardItem):
    def __init__(self, txt='', font_size=10, color=QColor(0,0,0)):
        super().__init__()

        fnt = QFont('Open Sans', font_size)

        self.setEditable(False)
        self.setForeground(color)
        self.setFont(fnt)
        self.setText(txt)

def possibleLocToString(loc, world, child_reached, adult_reached):
    child = loc.parent_region in child_reached and loc.access_rule(world.state, spot=loc, age='child')
    adult = loc.parent_region in adult_reached and loc.access_rule(world.state, spot=loc, age='adult')

    message = "{} (in {})".format(loc, loc.parent_region)

    if child and adult:
        message += " (child or adult)"
    elif child:
        message += " (child)"
    elif adult:
        message += " (adult)"

    return message

class LocationEntry(TableEntry):
    def __init__(self, loc_name, txt, possible, parent_region, checked=False, ignored=False):
        if possible:
            color = QColor(0,0,0)
        else:
            color = QColor(255,0,0)
        super().__init__(txt=txt, color=color)
        self.loc_name = loc_name
        self.name = txt
        self.setCheckable(True)
        self._parent = None
        self.currently_checked = checked
        self.parent_region = parent_region
        if checked:
            self.setCheckState(Qt.CheckState.Checked)
        else:
            self.setCheckState(Qt.CheckState.Unchecked)
        self.possible = possible
        self.ignored = ignored

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
        self.parent().takeRow(self.row())
        self._parent.addLocation(self, first=True)
    def setPossible(self, possible):
        if possible == self.possible:
            return
        if possible:
            color = QColor(0,0,0)
        else:
            color = QColor(255,0,0)
        self.setForeground(color)
        self.possible = possible
        self.parent().takeRow(self.row())
        self._parent.addLocation(self, first=True)
    def setIgnored(self, ignored):
        if ignored == self.ignored:
            return
        self.ignored = ignored
        self.parent().takeRow(self.row())
        self._parent.addLocation(self, first=True)

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
