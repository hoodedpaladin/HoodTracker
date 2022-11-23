import GuiUtils
import PySide2.QtWidgets as QtWidgets
import PySide2.QtCore as QtCore
import PySide2.QtGui as QtGui
import HoodTracker
from CommonUtils import *
import EntranceShuffle
import AutoGrotto
import logging
import re
from collections import Counter

# Break the exit name into [ source_name, dest_name ]
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

# Find the opposite exit of the pairs defined by the EntranceShuffleTable
def getOppositeExitName(name):
    for x in EntranceShuffle.entrance_shuffle_table:
        if len(x) != 3:
            continue
        if x[1][0] == name:
            return x[2][0]
        if x[2][0] == name:
            return x[1][0]
    raise Exception("Opposite exit not found!")

# The obvious place for an exit to lead would be the source region of its paired exit
# But this breaks the logic of some exits with special logic, e.g. LW Bridge From Forest,
# Colossus from Spirit Temple, and DMC
# The solution is to lead to the DESTINATION region of the OPPOSITE exit according to the EntranceShuffleTable
def getDestinationForPairedExit(paired_exit_name):
    return parseExitName(getOppositeExitName(paired_exit_name))[1]

owl_destinations = set(getDestinationsOfTypes(['WarpSong', 'OwlDrop', 'Overworld', 'Extra']))
spawn_warp_destinations = set(getDestinationsOfTypes(['Spawn', 'WarpSong', 'OwlDrop', 'Overworld', 'Interior', 'SpecialInterior', 'Extra']))

# Custom combo box that does not allow mouse wheel events until clicked
class MyComboBox(QtWidgets.QComboBox):
    def __init__(self):
        super().__init__()
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

    def wheelEvent(self, e:QtGui.QWheelEvent) -> None:
        if self.hasFocus():
            super().wheelEvent()
        else:
            pass

class ExploreBox(QtWidgets.QWidget):
    def __init__(self, text, options, parent=None):
        super().__init__()
        self.parent = parent
        a = QtWidgets.QLabel(text)
        b = MyComboBox()
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
        self.deleteLater()

        exit = self.text
        destination = self.combo.currentText()
        logging.info("User has indicated that {} goesto {}".format(exit, destination))
        self.parent.setKnownExit(exit, destination)

class KnownExploreBox(QtWidgets.QWidget):
    def __init__(self, text, parent):
        super().__init__()
        self.parent = parent
        self.text = text

        a = QtWidgets.QLabel(text)
        b = QtWidgets.QPushButton("x")
        b.setMaximumWidth(20)
        b.setMaximumHeight(20)
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(a, stretch=1)
        layout.addWidget(b, stretch=0)
        b.clicked.connect(self.close_button_clicked)
        self.setLayout(layout)
        self.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Fixed)
        layout.setMargin(0)

    def close_button_clicked(self):
        logging.info("User clicked x button on {}".format(self.text))
        self.parent.delete_connection_button_clicked(self.text)
        return

substitute_regions = {}
substitute_regions['Auto Generic Grotto'] = AutoGrotto.allGrottoRegionsWithTypes([0x3f])
if AutoGrotto.combine_scrub_numbers:
    substitute_regions['Auto Scrub Grotto'] = AutoGrotto.allGrottoRegionsWithTypes([0x5a4, 0x5bc, 0x5b0, 0x59c])
else:
    substitute_regions['Auto 1-Scrub Grotto'] = AutoGrotto.allGrottoRegionsWithTypes([0x59c])
    substitute_regions['Auto 2-Scrub Grotto'] = AutoGrotto.allGrottoRegionsWithTypes([0x5b0, 0x5bc])
    substitute_regions['Auto 3-Scrub Grotto'] = AutoGrotto.allGrottoRegionsWithTypes([0x5a4])
substitute_regions['Auto Fairy Fountain'] = AutoGrotto.allGrottoRegionsWithTypes([0x036D])
substitute_regions['Auto Great Fairy Fountain'] = AutoGrotto.allGreatFairyFountains()

def attemptLookup(name, dictionary):
    if name in dictionary:
        return dictionary[name]
    return name

def getFromListByName(thelist, name):
    return expectOne([x for x in thelist if x.name == name])

class ExploreManager:
    def __init__(self, world, parent, input_data):
        self.explorations = []
        self.widget = GuiUtils.ScrollSettingsArea(widgets=self.explorations)
        self.widget.setVisible(len(self.explorations) > 0)
        self.parent = parent

        self.set_up_world(world, input_data)
        self.show_widgets()

    def show_widgets(self):
        # Sort the exit names
        please_explore = [str(exit) for exit in self.all_shuffled_exits if getattr(exit, "please_explore", False)]
        please_explore = sorted(please_explore, key=str.casefold)
        known_labels = sorted([str(exit) + " goesto " + exit.connected_region for exit in self.all_shuffled_exits if getattr(exit, "marked_known", False)], key=str.casefold)

        new_widgets = []
        for exit_name in please_explore:
            possible = self.getPossibilities(exit_name)
            widget = ExploreBox(text=exit_name, options=possible, parent=self)
            new_widgets.append(widget)

        for known in known_labels:
            new_widgets.append(KnownExploreBox(text=known, parent=self))

        old_slider_position = self.widget.verticalScrollBar().sliderPosition()
        self.widget.setNewWidgets(new_widgets)
        self.widget.verticalScrollBar().setSliderPosition(old_slider_position)
        self.explorations = new_widgets
        self.widget.setVisible(len(self.explorations) > 0)

    def getPossibilities(self, exit_name):
        exit = self.exits_dict[exit_name]
        assert exit.shuffled

        # Find the list of possible destinations based on rules for various types of exit
        self.update_consumed_flag()
        if exit in self.owl_flight:
            possible = owl_destinations
        elif exit in self.owl_flight:
            possible = owl_destinations
        elif exit in self.spawn_warp_exits:
            possible = spawn_warp_destinations
        elif getattr(self.world.settings, 'mix_entrance_pools', 'off') != 'off':
            opposite_exit = self.exits_dict[getOppositeExitName(exit_name)]
            possible = [str(x) for x in self.nonwarp_shuffled_exits if not x.consumed and x != opposite_exit]
        else:
            type_list = expectOne([x for x in self.type_lists if exit in x])
            opposite_exit = self.exits_dict[getOppositeExitName(exit_name)]
            possible = [str(x) for x in type_list if not x.consumed and x != opposite_exit]
        assert possible is not None

        # Simplify to a region name if there is only one entrance to that region
        possible = [attemptLookup(x, self.oneentrance_to_region) for x in possible]

        # Replace destination names with automatic substitute keywords
        possible = [self.substitute_helper(x, self.world) for x in possible]

        # Remove duplicates
        possible = list(set(possible))

        # Reformat the names from X -> Y to Y (from X)
        for i in range(len(possible)):
            if " -> " in possible[i]:
                match = re.match("(.+) -> (.+)", possible[i])
                assert match
                possible[i] = "{} (from {})".format(match.group(2), match.group(1))

        # Alphabetize
        return sorted(possible)

    def setKnownExit(self, exit, destination_name):
        # Find the object version of the exit
        all_exits = [x for region in self.world.regions for x in region.exits]
        exit = expectOne([x for x in all_exits if x.name == exit])

        # One-entrance places
        one_entrance_places = self.overworld_to_grotto + self.overworld_to_interior + self.overworld_to_dungeon

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

        # Sanity checks based on what kind of connection this is
        if exit in self.owl_flight:
            assert destination_name in owl_destinations
            self.makeConnection(exit, destination_name, consumed_exit=None)
        elif exit in self.spawn_warp_exits:
            assert destination_name in spawn_warp_destinations
            self.makeConnection(exit, destination_name, consumed_exit=None)
        else:
            # Either the destination is one word, which came from the oneentrance table
            # Or it's been turned into the form X (from Y)
            # Either way, we just need a destination name and a consumed exit from it
            if destination_name in self.region_to_oneentrance:
                exit_name = self.region_to_oneentrance[destination_name]
                match = re.match("(.+) -> (.+)", exit_name)
                assert match
                destination_name = match.group(2)
                consumed_exit = self.exits_dict[exit_name]
            else:
                match = re.match("(.+) \(from (.+)\)", destination_name)
                assert match
                destination_name = match.group(1)
                exit_name = "{} -> {}".format(match.group(2), match.group(1))
                consumed_exit = self.exits_dict[exit_name]

            if getattr(self.world.settings, 'decouple_entrances', False):
                self.makeConnection(exit, destination_name, consumed_exit=consumed_exit)
            else:
                # The decoupled pattern is: (exit a->b) consumed (exit c->d) and goes to d
                # If it's coupled, then the reverse path is: (exit d->c) consumed (exit b->a) and goes to a
                # B and C are irrelevant except to know which doorway it is, but make sure that c->d and b->a are consumed
                #
                # There is enough info if we say that (exit a->b) is paired with (exit d->c),
                # and this is symmetrical to save in text (i.e. (d->c) pairswith (a->b) is the same)
                # So we will follow this in code too
                paired_exit_name = getOppositeExitName(str(consumed_exit))
                paired_exit = self.exits_dict[paired_exit_name]
                self.makeCoupledConnection(exit, paired_exit)

        # Success
        # Update the display with new logic
        self.parent.updateLogic()

    # Make a single connection
    def makeConnection(self, exit, destination_name, redundant_okay=False, consumed_exit=None):
        if not exit.shuffled:
            assert redundant_okay
            assert exit.connected_region == destination_name
            return
        exit.shuffled = False
        exit.marked_known = True
        exit.connected_region = destination_name
        if exit in self.boss_door_to_room:
            # Mark the boss room hint once we've connected it to a dungeon
            other_exit = self.exits_dict[destination_name]
            other_exit.parent_region.dungeon = exit.parent_region.dungeon

        exit.please_explore = False
        if consumed_exit:
            logging.info("Consuming exit {} for this".format(consumed_exit))
            exit.consumed_exit = consumed_exit
            self.consumed_flag_dirty = True

    def makeCoupledConnection(self, exit1, exit2):
        exits = [exit1, exit2]
        consumed_exits = [self.exits_dict[getOppositeExitName(str(x))] for x in exits]
        self.consumed_flag_dirty = True
        for i,x in enumerate(exits):
            other_index = (i+1)%2
            other_exit = exits[other_index]
            consumed_exit = consumed_exits[other_index]
            x.shuffled = False
            x.please_explore = False
            x.marked_known = True
            x.coupled_exit = other_exit
            x.consumed_exit = consumed_exit
            if x in self.boss_door_to_room:
                # Mark the boss room hint once we've connected it to a dungeon
                other_exit.parent_region.dungeon = x.parent_region.dungeon
            # Destination = destination of the consumed exit
            # (but use the name, i.e. the canonical destination, not the struct)
            match = re.match("(.+) -> (.+)", str(x.consumed_exit))
            assert match
            x.connected_region = match.group(2)

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

    # Called from the GUI button click; send to HoodTrackerGui to forget and unlink exits
    def delete_connection_button_clicked(self, connection_string):
        exit_name, destination = connection_string.split(" goesto ")
        self.reshuffle_exit(exit_name)
        self.parent.updateLogic()

    # Called from the HoodTrackerGui for each exit that we unlink
    def reshuffle_exit(self, exit_name):
        exit = self.exits_dict[exit_name]

        assert not exit.shuffled

        region = self.world.get_region(exit.connected_region)
        if 'Boss Room' in region.name:
            # No more dungeon hint for an unconnected boss room
            region.dungeon = None
        exit.shuffled = True
        exit.connected_region = None
        exit.marked_known = False
        exit.consumed_exit = None
        exit.please_explore = False
        self.consumed_flag_dirty = True
        if hasattr(exit, "coupled_exit"):
            coupled_exit = exit.coupled_exit
            del exit.coupled_exit
            del coupled_exit.coupled_exit
            self.reshuffle_exit(str(coupled_exit))

    def update_consumed_flag(self):
        if not self.consumed_flag_dirty:
            return
        for x in self.all_shuffled_exits:
            x.consumed = False
        for x in self.all_shuffled_exits:
            consumed_exit = getattr(x, "consumed_exit", None)
            if consumed_exit:
                consumed_exit.consumed = True
        self.consumed_flag_dirty = False

    def input_saved_data(self, input_data):
        # Get the shuffled exits according to the world settings
        # so that we can ignore/discard anything that isn't shuffled
        shuffled_exits = HoodTracker.get_shuffled_exits(self.world.settings)
        discard = []

        for line in input_data['known_exits']:
            match = re.match("(.+) goesto (.+) \(Consumes (.+)\)", line)
            if match:
                exit, destination_region, consumed_exit = match.groups()
                consumed_exit = self.exits_dict[consumed_exit]
            else:
                match = re.match("(.+) goesto (.+)", line)
                assert match
                exit, destination_region = match.groups()
                consumed_exit = None
            if exit not in shuffled_exits:
                # A shuffled exit is not un-shuffled due to settings change
                discard.append(line)
                continue
            exit = self.exits_dict[exit]
            self.makeConnection(exit, destination_region, consumed_exit=consumed_exit, redundant_okay=True)
        for line in discard:
            input_data['known_exits'].remove(line)

        discard = []
        for line in input_data['paired_exits']:
            match = re.match("(.*) pairswith (.*)", line)
            assert match
            exit1, exit2 = match.groups()
            if not exit1 in shuffled_exits:
                # A shuffled exit is not un-shuffled due to settings change
                assert exit2 not in shuffled_exits
                discard.append(line)
                continue
            exit1 = self.exits_dict[exit1]
            exit2 = self.exits_dict[exit2]
            self.makeCoupledConnection(exit1, exit2)
        for line in discard:
            input_data['paired_exits'].remove(line)

    def get_output(self):
        output_known_exits = []
        output_known_paired_exits = []
        do_these = [x for x in self.all_shuffled_exits if getattr(x, "marked_known", False)]
        while len(do_these):
            exit = do_these.pop()
            assert not exit.shuffled
            if not getattr(exit, "coupled_exit", None):
                consumed_exit = getattr(exit, "consumed_exit", None)
                if not consumed_exit:
                    output_known_exits.append("{} goesto {}".format(exit, exit.connected_region))
                else:
                    output_known_exits.append("{} goesto {} (Consumes {})".format(exit, exit.connected_region, consumed_exit))
            else:
                output_known_paired_exits.append("{} pairswith {}".format(exit, exit.coupled_exit))
                do_these.remove(exit.coupled_exit)
        return output_known_exits, output_known_paired_exits

    def set_up_world(self, world, input_data):
        self.world = world
        self.consumed_flag_dirty = True

        all_exits = [x for region in world.regions for x in region.exits]
        all_destination_names = set(x.parent_region.name for x in all_exits)

        est = EntranceShuffle.entrance_shuffle_table
        overworld_to_interior_names = [x[1][0] for x in est if x[0] in ('Interior', 'SpecialInterior')]
        interior_to_overworld_names = [x[2][0] for x in est if x[0] in ('Interior', 'SpecialInterior')]
        self.overworld_to_interior = [getFromListByName(all_exits, name) for name in overworld_to_interior_names]
        self.interior_to_overworld = [getFromListByName(all_exits, name) for name in interior_to_overworld_names]

        overworld_to_overworld_names = []
        for x in [x for x in est if x[0] == 'Overworld']:
            if len(x) < 3 and not getattr(self.world.settings, 'decouple_entrances', False):
                # The GV Lower Stream -> Lake Hylia exit is not shuffled if decoupled entrances is off
                continue
            for i in range(1, len(x)):
                overworld_to_overworld_names.append(x[i][0])
        self.overworld_to_overworld = [getFromListByName(all_exits, name) for name in overworld_to_overworld_names]

        overworld_to_grotto_names = [x[1][0] for x in est if x[0] in ('Grotto', 'Grave', 'SpecialGrave')]
        self.overworld_to_grotto = [getFromListByName(all_exits, name) for name in overworld_to_grotto_names]
        grotto_to_overworld_names = [x[2][0] for x in est if x[0] in ('Grotto', 'Grave', 'SpecialGrave')]
        self.grotto_to_overworld = [getFromListByName(all_exits, name) for name in grotto_to_overworld_names]

        overworld_to_dungeon_names = [x[1][0] for x in est if x[0] in ['Dungeon', 'DungeonSpecial']]
        self.overworld_to_dungeon = [getFromListByName(all_exits, name) for name in overworld_to_dungeon_names]
        dungeon_to_overworld_names = [x[2][0] for x in est if x[0] in ['Dungeon', 'DungeonSpecial']]
        self.dungeon_to_overworld = [getFromListByName(all_exits, name) for name in dungeon_to_overworld_names]

        boss_door_to_room_names = [x[1][0] for x in est if x[0] in ['ChildBoss', 'AdultBoss']]
        self.boss_door_to_room = [getFromListByName(all_exits, name) for name in boss_door_to_room_names]
        boss_room_to_door_names = [x[2][0] for x in est if x[0] in ['ChildBoss', 'AdultBoss']]
        self.boss_room_to_door = [getFromListByName(all_exits, name) for name in boss_room_to_door_names]

        owl_flight_names = [x[1][0] for x in est if x[0] == 'OwlDrop']
        self.owl_flight = [x for x in all_exits if x.name in owl_flight_names]

        spawn_warp_names = [x[1][0] for x in est if x[0] in ['WarpSong', 'Spawn']]
        self.spawn_warp_exits = [x for x in all_exits if x.name in spawn_warp_names]

        self.all_shuffled_exits = self.overworld_to_interior + self.interior_to_overworld + self.overworld_to_overworld + self.overworld_to_grotto + self.grotto_to_overworld + self.overworld_to_dungeon + self.dungeon_to_overworld + self.owl_flight + self.spawn_warp_exits + self.boss_door_to_room + self.boss_room_to_door
        self.nonwarp_shuffled_exits = self.overworld_to_interior + self.interior_to_overworld + self.overworld_to_overworld + self.overworld_to_grotto + self.grotto_to_overworld + self.overworld_to_dungeon + self.dungeon_to_overworld
        self.type_lists = [self.overworld_to_overworld,
                           self.overworld_to_grotto,
                           self.grotto_to_overworld,
                           self.overworld_to_dungeon,
                           self.dungeon_to_overworld,
                           self.overworld_to_interior,
                           self.interior_to_overworld,
                           self.boss_door_to_room,]

        self.all_exits = [x for region in world.regions for x in region.exits]
        self.exits_dict = {}
        for x in self.all_exits:
            assert x.name not in self.exits_dict
            self.exits_dict[x.name] = x

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

        one_entrance_places = self.overworld_to_grotto + self.overworld_to_interior + self.overworld_to_dungeon
        self.region_to_oneentrance = {}
        self.oneentrance_to_region = {}
        for exit in one_entrance_places:
            exit_name = str(exit)
            source, dest = exit_name.split(" -> ")
            self.region_to_oneentrance[dest] = exit_name
            self.oneentrance_to_region[exit_name] = dest
        self.input_saved_data(input_data)

    def update_world(self, world, input_data):
        self.set_up_world(world, input_data)
        self.show_widgets()
