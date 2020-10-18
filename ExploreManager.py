import GuiUtils
import PySide2.QtWidgets as QtWidgets
import HoodTracker
from CommonUtils import *
import EntranceShuffle
import AutoGrotto
from collections import Counter

# This is the intended number of overworld entrances to a certain region
overworld_destinations = {
    "Castle Grounds": 1,
    "DMC Lower Local": 1,
    "DMC Upper Local": 1,
    "Death Mountain": 2,
    "Death Mountain Summit": 1,
    "Desert Colossus": 1,
    "GC Darunias Chamber": 1,
    "GC Woods Warp": 1,
    "GF Outside Gate": 1,
    "GV Fortress Side": 1,
    "Gerudo Fortress": 1,
    "Gerudo Valley": 1,
    "Goron City": 1,
    "Graveyard": 1,
    "Hyrule Field": 7,
    "Kak Behind Gate": 1,
    "Kakariko Village": 2,
    "Kokiri Forest": 2,
    "LW Beyond Mido": 1,
    "LW Bridge": 1,
    "LW Bridge From Forest": 1,
    "Lake Hylia": 2,
    "Lon Lon Ranch": 1,
    "Lost Woods": 3,
    "Market": 3,
    "Market Entrance": 2,
    "SFM Entryway": 1,
    "ToT Entrance": 1,
    "Wasteland Near Colossus": 1,
    "Wasteland Near Fortress": 1,
    "ZD Behind King Zora": 1,
    "ZR Behind Waterfall": 1,
    "ZR Front": 1,
    "Zora River": 1,
    "Zoras Domain": 2,
    "Zoras Fountain": 1
}

owl_destinations = list(overworld_destinations.keys()) + ['Kak Impas Ledge']

class ExploreBox(QtWidgets.QWidget):
    def __init__(self, text, options, parent=None):
        super().__init__()
        self.parent = parent
        a = QtWidgets.QLabel(text)
        b = QtWidgets.QComboBox()
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(a)
        layout.addWidget(b)
        b.addItem("?")
        for x in options:
            b.addItem(x)
        b.currentIndexChanged.connect(lambda x:self.combo_select_event(x))
        self.setLayout(layout)
        self.text = text
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        self.combo = b

    def combo_select_event(self, x):
        if self.combo.currentText == "?":
            return
        self.setParent(None)
        self.parent.setKnownExit(self.text, self.combo.currentText())

substitute_regions = {}
substitute_regions['Auto Generic Grotto'] = AutoGrotto.allGrottoRegionsWithTypes([0x3f])
substitute_regions['Auto Scrub Grotto'] = AutoGrotto.allGrottoRegionsWithTypes([0x5a4, 0x5bc])
substitute_regions['Auto Fairy Fountain'] = AutoGrotto.allGrottoRegionsWithTypes([0x036D])
substitute_regions['Auto Great Fairy Fountain'] = AutoGrotto.allGreatFairyFountains()

def substitute_helper(name):
    for type in substitute_regions:
        if name in substitute_regions[type]:
            return type
    return name

def getFromListByName(thelist, name):
    return expectOne([x for x in thelist if x.name == name])

class ExploreManager:
    def __init__(self, world):
        self.explorations = []
        self.widget = GuiUtils.ScrollSettingsArea(widgets = self.explorations)
        self.widget.setVisible(len(self.explorations) > 0)
        self.world = world
        self.parent = None

        all_exits = [x for region in world.regions for x in region.exits]
        all_destination_names = set(x.parent_region.name for x in all_exits)

        est = EntranceShuffle.entrance_shuffle_table
        overworld_to_interior_names = [x[1][0] for x in est if x[0] in ('Interior', 'SpecialInterior')]
        interior_to_overworld_names = [x[2][0] for x in est if x[0] in ('Interior', 'SpecialInterior')]
        self.overworld_to_interior = [getFromListByName(all_exits, name) for name in overworld_to_interior_names]
        self.interior_to_overworld = [getFromListByName(all_exits, name) for name in interior_to_overworld_names]

        overworld_to_overworld_names = [x[1][0] for x in est if x[0] == 'Overworld'] + [x[2][0] for x in est if x[0] == 'Overworld']
        self.overworld_to_overworld = [getFromListByName(all_exits, name) for name in overworld_to_overworld_names]

        overworld_to_grotto_names = [x[1][0] for x in est if x[0] in ('Grotto', 'Grave', 'SpecialGrave')]
        self.overworld_to_grotto = [getFromListByName(all_exits, name) for name in overworld_to_grotto_names]
        grotto_to_overworld_names = [x[2][0] for x in est if x[0] in ('Grotto', 'Grave', 'SpecialGrave')]
        self.grotto_to_overworld = [getFromListByName(all_exits, name) for name in grotto_to_overworld_names]

        overworld_to_dungeon_names = [x[1][0] for x in est if x[0] == 'Dungeon']
        self.overworld_to_dungeon = [x for x in all_exits if x.name in overworld_to_dungeon_names]
        self.overworld_to_dungeon = [getFromListByName(all_exits, name) for name in overworld_to_dungeon_names]
        dungeon_to_overworld_names = [x[2][0] for x in est if x[0] == 'Dungeon']
        self.dungeon_to_overworld = [x for x in all_exits if x.name in dungeon_to_overworld_names]
        self.dungeon_to_overworld = [getFromListByName(all_exits, name) for name in dungeon_to_overworld_names]

        owl_flight_names = [x[1][0] for x in est if x[0] == 'OwlDrop']
        self.owl_flight = [x for x in all_exits if x.name in owl_flight_names]

        # substitute_helper() does a lookup from exit name -> auto name
        # save this in backwards form
        self.backwards_substitute = {}
        for destination in all_destination_names:
            sub_name = substitute_helper(destination)
            if sub_name not in self.backwards_substitute:
                self.backwards_substitute[sub_name] = []
            self.backwards_substitute[sub_name].append(destination)

    def showThese(self, please_explore, world):
        # Sort the exit names
        please_explore = sorted(please_explore, key=str.casefold)

        all_exits = [x for region in world.regions for x in region.exits]

        new_widgets = []
        for exit_name in please_explore:
            exit = expectOne([x for x in all_exits if x.name == exit_name])
            assert exit.shuffled

            # Find the list of possible destinations based on rules for various types of exit
            possible = None
            if exit in self.interior_to_overworld:
                possible = [str(x.parent_region) for x in self.overworld_to_interior if x.shuffled]
            elif exit in self.overworld_to_interior:
                check_these = [x for x in self.overworld_to_interior if not x.shuffled]
                interiors = [x.parent_region.name for x in self.interior_to_overworld]
                for x in check_these:
                    interiors.remove(x.connected_region)
                possible = interiors
            elif exit in self.overworld_to_overworld:
                check_these = [x for x in self.overworld_to_overworld if not x.shuffled]
                leading_to = Counter()
                for x in check_these:
                    leading_to[x.connected_region] += 1
                possible = [dest for dest in overworld_destinations if leading_to[dest] < overworld_destinations[dest]]
                possible = [dest for dest in possible if dest != exit.parent_region.name]
            elif exit in self.owl_flight:
                possible = owl_destinations
            elif exit in self.overworld_to_grotto:
                possible = [str(x.parent_region) for x in self.grotto_to_overworld if x.shuffled]
            elif exit in self.overworld_to_dungeon:
                possible = [str(x.parent_region) for x in self.dungeon_to_overworld if x.shuffled]

            assert possible is not None

            # Replace destination names with automatic substitute keywords
            possible = [substitute_helper(x) for x in possible]
            # Remove duplicates + alphabetize
            possible = sorted(list(set(possible)))

            widget = ExploreBox(text=exit_name, options=possible, parent=self)
            new_widgets.append(widget)

        self.widget.setNewWidgets(new_widgets)
        self.explorations = new_widgets
        self.widget.setVisible(len(self.explorations) > 0)

    def setKnownExit(self, exit, destination_name):
        # Find the object version of the exit
        all_exits = [x for region in self.world.regions for x in region.exits]
        exit = expectOne([x for x in all_exits if x.name == exit])

        # One-entrance places
        one_entrance_places = self.overworld_to_grotto + self.overworld_to_interior + self.overworld_to_dungeon

        # If this is set at the end of the function, we will connect the reverse
        reverse_exit = None

        # Sanity checks based on what kind of connection this is
        if exit in self.overworld_to_overworld:
            # The overworld to overworld connections must not be all accounted for for this destination
            check_these = self.overworld_to_overworld
            leading_to = [x for x in check_these if not x.shuffled and x.connected_region == destination_name]
            assert len(leading_to) < overworld_destinations[destination_name]
        elif exit in one_entrance_places:
            # Find the matching destination that has no exit leading to it yet.
            # If destination_name is an automatic substitute, backwards_substitute will return a list of all such
            # destinations
            possibilities = self.backwards_substitute[destination_name]
            found = None
            check_these = [x for x in one_entrance_places if not x.shuffled]
            for possible_dest in possibilities:
                leading_to = [x for x in check_these if x.connected_region == possible_dest]
                if len(leading_to) == 0:
                    found = possible_dest
                    break
            assert found is not None
            if found != destination_name:
                print("{} chose {}".format(destination_name, found))
                destination_name = found

            reverse_exits = self.grotto_to_overworld + self.interior_to_overworld + self.dungeon_to_overworld
            reverse_exit = expectOne([x for x in reverse_exits if x.parent_region.name == destination_name])
        elif exit in self.owl_flight:
            assert destination_name in owl_destinations
        elif exit in self.interior_to_overworld:
            # Let's assume this is good ...
            pass
        else:
            raise Exception("Unknown connection type")

        # Success
        self.makeConnection(exit, destination_name)
        if reverse_exit is not None:
            self.makeConnection(reverse_exit, exit.parent_region.name, redundant_okay=True)
        # Update the display with new logic
        self.parent.updateLogic()

    def makeConnection(self, exit, destination_name, redundant_okay=False):
        if not exit.shuffled:
            assert redundant_okay
            assert exit.connected_region == destination_name
            return
        exit.shuffled = False
        exit.connected_region = destination_name
        print("exit {} goesto {}".format(str(exit), destination_name))
        self.parent.addKnownExit(exit.name, destination_name)

