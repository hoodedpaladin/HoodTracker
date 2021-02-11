import GuiUtils
import PySide2.QtWidgets as QtWidgets
import HoodTracker
from CommonUtils import *
import EntranceShuffle
import AutoGrotto
from collections import Counter
import logging
import re
from collections import Counter

def parseExitName(name):
    match = re.fullmatch("(.*) -> (.*)", name)
    assert match
    return [match.group(1), match.group(2)]

def getDestinationsOfTypes(types):
    est = EntranceShuffle.entrance_shuffle_table
    exit_names = []
    for x in est:
        if x[0] not in types:
            continue
        exit_names.append(x[1][0])
        if len(x) > 2:
            exit_names.append(x[2][0])
    return [parseExitName(x)[1] for x in exit_names]

def getPairedExitName(name):
    est = EntranceShuffle.entrance_shuffle_table
    for x in est:
        if len(x) != 3:
            continue
        if x[1][0] == name:
            return x[2][0]
        if x[2][0] == name:
            return x[1][0]
    raise Exception("Paired exit not found!")


# This is the intended number of overworld entrances to a certain region
overworld_destinations = Counter(sorted(getDestinationsOfTypes(['Overworld'])))

owl_destinations = set(getDestinationsOfTypes(['WarpSong', 'OwlDrop', 'Overworld', 'Extra']))
spawn_warp_destinations = set(getDestinationsOfTypes(['Spawn', 'WarpSong', 'OwlDrop', 'Overworld', 'Interior', 'SpecialInterior', 'Extra']))

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
        if self.combo.currentText() == "?":
            return
        self.setParent(None)

        exit = self.text
        destination = self.combo.currentText()
        logging.info("User has indicated that {} goesto {}".format(exit, destination))
        self.parent.setKnownExit(exit, destination)

substitute_regions = {}
substitute_regions['Auto Generic Grotto'] = AutoGrotto.allGrottoRegionsWithTypes([0x3f])
substitute_regions['Auto Scrub Grotto'] = AutoGrotto.allGrottoRegionsWithTypes([0x5a4, 0x5bc])
substitute_regions['Auto Fairy Fountain'] = AutoGrotto.allGrottoRegionsWithTypes([0x036D])
substitute_regions['Auto Great Fairy Fountain'] = AutoGrotto.allGreatFairyFountains()

def getFromListByName(thelist, name):
    return expectOne([x for x in thelist if x.name == name])

class ExploreManager:
    def __init__(self, world, parent):
        self.explorations = []
        self.widget = GuiUtils.ScrollSettingsArea(widgets = self.explorations)
        self.widget.setVisible(len(self.explorations) > 0)
        self.world = world
        self.parent = parent

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

        spawn_warp_names = [x[1][0] for x in est if x[0] in ['WarpSong', 'Spawn']]
        self.spawn_warp_exits = [x for x in all_exits if x.name in spawn_warp_names]

        # substitute_helper() does a lookup from exit name -> auto name
        # save this in backwards form
        self.backwards_substitute = {}
        for destination in all_destination_names:
            sub_name = self.substitute_helper(destination)
            if sub_name == destination:
                continue
            if sub_name not in self.backwards_substitute:
                self.backwards_substitute[sub_name] = []
            self.backwards_substitute[sub_name].append(destination)

    def showThese(self, please_explore, world, known_exits):
        # Sort the exit names
        please_explore = sorted(please_explore, key=str.casefold)
        known_labels = sorted([exit + " goesto " + dest for exit,dest in known_exits.items()], key=str.casefold)

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
                # Overworld pool: exclude overworld destinations that are already lead to by their vanilla amount of overworld<->overworld connections
                check_these = [x for x in self.overworld_to_overworld if not x.shuffled]
                leading_to = Counter()
                for x in check_these:
                    leading_to[x.connected_region] += 1
                possible = [dest for dest in overworld_destinations if leading_to[dest] < overworld_destinations[dest]]
                # Exits won't lead to the same region either
                possible = [dest for dest in possible if dest != exit.parent_region.name]
            elif exit in self.owl_flight:
                possible = owl_destinations
            elif exit in self.spawn_warp_exits:
                possible = spawn_warp_destinations
            elif exit in self.overworld_to_grotto:
                possible = [str(x.parent_region) for x in self.grotto_to_overworld if x.shuffled]
            elif exit in self.overworld_to_dungeon:
                possible = [str(x.parent_region) for x in self.dungeon_to_overworld if x.shuffled]

            assert possible is not None

            # Replace destination names with automatic substitute keywords
            possible = [self.substitute_helper(x, world) for x in possible]

            # Remove duplicates + alphabetize
            possible = sorted(list(set(possible)))

            widget = ExploreBox(text=exit_name, options=possible, parent=self)
            new_widgets.append(widget)

        for known in known_labels:
            new_widgets.append(QtWidgets.QLabel(known))
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

            # overworld connections that are unique can have the reverse automatically filled in
            if overworld_destinations[destination_name] == 1:
                check_reverse_exit = [x for x in self.overworld_to_overworld if x.parent_region.name == destination_name]
                if len(check_reverse_exit) != 1:
                    # TODO These exits are imperfectly matched ... can I fix this?
                    assert destination_name in ['LW Bridge From Forest', 'DMC Upper Local', 'DMC Lower Local', 'LW Bridge']
                else:
                    reverse_exit = expectOne(check_reverse_exit)
        elif exit in one_entrance_places:
            # For automatic substitute names, find a region that is not connected to ANYTHING
            if destination_name in self.backwards_substitute:
                possibilities = self.backwards_substitute[destination_name]
                found = None
                for possible_dest in possibilities:
                    leading_to = [x for x in all_exits if not x.shuffled and x.connected_region == possible_dest]
                    if len(leading_to) == 0:
                        found = possible_dest
                        break
                assert found is not None
                if found != destination_name:
                    logging.info("Auto-substitute chose {} for {}".format(found, destination_name))
                    destination_name = found
            else:
                # This is a specific, not automatic, destination
                # Make sure it is unique among one_entrance_places, but other types of connection are OK
                check_these = [x for x in one_entrance_places if not x.shuffled]
                leading_to = [x for x in check_these if x.connected_region == destination_name]
                assert len(leading_to) == 0

            reverse_exits = self.grotto_to_overworld + self.interior_to_overworld + self.dungeon_to_overworld
            reverse_exit = expectOne([x for x in reverse_exits if x.parent_region.name == destination_name])
        elif exit in self.owl_flight:
            assert destination_name in owl_destinations
        elif exit in self.spawn_warp_exits:
            assert destination_name in spawn_warp_destinations
        elif exit in self.interior_to_overworld:
            # Let's assume this is good ...
            pass
        else:
            raise Exception("Unknown connection type")

        # Success
        self.makeConnection(exit, destination_name)
        if reverse_exit is not None:
            paired_exit = getPairedExitName(exit.name)
            reverse_exit_destination = parseExitName(paired_exit)[1]
            self.makeConnection(reverse_exit, reverse_exit_destination, redundant_okay=True)
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

    # Returns the substitute name for a region
    # If the world is supplied and the world has an entrance leading to this region already, don't substitute it
    def substitute_helper(self, name, world=None):
        for type in substitute_regions:
            if name in substitute_regions[type]:
                if world is not None:
                    region_connected = False
                    all_exits = [x for region in world.regions for x in region.exits]
                    for x in all_exits:
                        if not x.shuffled and x.connected_region == name:
                            region_connected = True
                            break
                    if region_connected:
                        return name
                return type
        return name
