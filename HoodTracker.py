#!/usr/bin/env python3
import logging
import os
import sys
import re
import argparse
from CommonUtils import *
import datetime

# Make OoTR work as a submodule in a dir called ./OoT-Randomizer
try:
    from World import World
except ModuleNotFoundError:
    ootr_path = os.path.join(os.getcwd(), "OoT-Randomizer")
    if ootr_path not in sys.path:
        sys.path.append(ootr_path)
    from World import World
from Utils import data_path
from DungeonList import create_dungeons
import ItemPool
import TextSettings
import EntranceShuffle
import SettingsList
from Item import ItemFactory
from Settings import Settings, ArgumentDefaultsHelpFormatter
import AutoGrotto
from Region import TimeOfDay
import gui

def getSettings(input_data, gui_dialog=None):
    parser = argparse.ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)

    parser.add_argument('--settings_string', help='Provide sharable settings using a settings string. This will override all flags that it specifies.')

    args = parser.parse_args()

    settings = Settings({})
    settings_string = None
    assert not (('settings_string' in input_data) and (args.settings_string))
    if 'settings_string' in input_data:
        settings_string = expectOne(input_data['settings_string'])
    elif args.settings_string is not None:
        settings_string = args.settings_string
    elif gui_dialog:
        settings_string = gui.DialogSettingsManager.get_settings_string()
    if settings_string is None:
        raise Exception("Please provide settings_string as an argument or in the text file")

    assert settings_string
    settings.update_with_settings_string(settings_string)
    return settings

def generate(input_data, gui_dialog):
    settings = getSettings(input_data, gui_dialog=gui_dialog)

    for trick in SettingsList.logic_tricks.values():
        settings.__dict__[trick['name']] = trick['name'] in settings.allowed_tricks

    worlds = []
    for i in range(0, settings.world_count):
        worlds.append(World(i, settings))
        worlds[-1].ensure_tod_access = False

    for id, world in enumerate(worlds):
        if settings.logic_rules == 'glitched':
            overworld_data = os.path.join(data_path('Glitched World'), 'Overworld.json')
        else:
            overworld_data = os.path.join(data_path('World'), 'Overworld.json')

        # Compile the json rules based on settings
        world.ensure_tod_access=True
        world.load_regions_from_json(overworld_data)
        create_dungeons(world)
        world.create_internal_locations()

        # Populate drop items
        drop_locations = list(filter(lambda loc: loc.type == 'Drop', world.get_locations()))
        for drop_location in drop_locations:
            item = ItemPool.droplocations[drop_location.name]
            world.push_item(drop_location, ItemFactory(item, world))
            drop_location.locked = True

        return world

# This is very similar to Search._expand_regions()
# Try to access all exits we have not been able to access yet
# Output a number of changes and a list of failed exits to potentially re-try again
# Also add any reached_regions to the list and any exits that need exploring to the list
def filterRegions(exit_queue, world, age, reached_regions, please_explore):
    failed = []
    changes = 0

    for exit in exit_queue:
        if exit.shuffled:
            if exit.access_rule(world.state, spot=exit, age=age):
                please_explore.append(exit.name)
                changes += 1
            else:
                failed.append(exit)
            continue

        destination = world.get_region(exit.connected_region)
        if destination in reached_regions:
            continue
        if exit.access_rule(world.state, spot=exit, age=age):
            changes += 1
            reached_regions[destination] = destination.provides_time
            reached_regions[world.get_region('Root')] |= destination.provides_time
            exit_queue.extend(destination.exits)
        else:
            failed.append(exit)
    return changes, failed

item_events = {
    'Stop GC Rolling Goron as Adult from Goron City': 'Stop GC Rolling Goron as Adult',
}

def doWeWantThisLoc(loc, world):
    # Deku scrubs that don't have upgrades can be ignored, but not if scrub shuffle or grotto shuffle is on
    if world.shuffle_scrubs == 'off' and not world.shuffle_grotto_entrances:
        if loc.filter_tags and 'Deku Scrub' in loc.filter_tags and 'Deku Scrub Upgrades' not in loc.filter_tags:
            return False
    # Generic grottos with chests are assumed to be looted immediately when you find a grotto, so ignore them
    if world.shuffle_grotto_entrances:
        if loc.filter_tags and 'Grottos' in loc.filter_tags and loc.rule_string == 'True':
            return False
    return True

# Very similar to Search.iter_reachable_locations
# Go through the list of locked_locations and move them to the possible_locations list if accessible
def filterLocations(locked_locations, possible_locations, reachable_regions, state, age, world):
    changes = 0

    # Filter the list without removing from locked_locations
    reach_these = []
    for loc in locked_locations:
        if loc.parent_region not in reachable_regions:
            continue
        if not loc.access_rule(state, spot=loc, age=age):
            continue
        changes += 1
        if loc.name in item_events:
            state.prog_items[item_events[loc.name]] += 1
        reach_these.append(loc)

    # Now move items from one list to the other
    for loc in reach_these:
        locked_locations.remove(loc)
        if doWeWantThisLoc(loc, world):
            possible_locations.append(loc)

    return changes

# If the item type is an event, fixed location, or drop, collect it automatically
def autocollect(possible_locations, collected_locations, state):
    collect_items = []
    move_locs = []

    for loc in possible_locations:
        if loc.name in ItemPool.fixedlocations:
            collect_items.append(ItemPool.fixedlocations[loc.name])
            move_locs.append(loc)
            continue
        if loc.type == 'Event':
            collect_items.append(loc.item.name)
            move_locs.append(loc)
            continue
        if loc.type in ('HintStone', 'Drop'):
            if loc.item:
                collect_items.append(loc.item.name)
            move_locs.append(loc)
            continue

    for item in collect_items:
        state.prog_items[item] += 1
    for loc in move_locs:
        possible_locations.remove(loc)
        collected_locations.append(loc)

    return len(move_locs)

def solve(world, starting_region='Root'):
    root_region = world.get_region(starting_region)
    reached_regions = {'child': {root_region:TimeOfDay.NONE},
                       'adult': {root_region:TimeOfDay.NONE}}
    all_locations = [x for region in world.regions for x in region.locations]
    locked_locations=all_locations[:]
    possible_locations=[]
    collected_locations=[]
    queues = {'child': [exit for exit in root_region.exits],
              'adult': [exit for exit in root_region.exits]}
    please_explore = []

    # Provide an implementation of world.state.search.can_reach
    world.state.search = SearchClass(world, reached_regions)

    # Map traversal
    changes = 1
    while changes:
        changes = 0

        for age in ['adult', 'child']:
            add_changes, queues[age] = filterRegions(queues[age], world, age, reached_regions[age], please_explore)
            changes += add_changes
            changes += filterLocations(locked_locations, possible_locations, reached_regions[age], world.state, age, world)

        changes += autocollect(possible_locations, collected_locations, world.state)

    return {'please_explore':list(set(please_explore)), 'possible_locations':possible_locations, 'adult_reached':reached_regions['adult'], 'child_reached':reached_regions['child']}

# Mark all exits shuffled that would be shuffled according to the settings
def shuffleExits(world):
    settings_to_types_dict = {
        'shuffle_dungeon_entrances': ['Dungeon'],
        'shuffle_interior_entrances': ['Interior'],
        'shuffle_grotto_entrances': ['Grotto', 'Grave'],
        'shuffle_overworld_entrances': ['Overworld'],
        'owl_drops': ['OwlDrop'],
        'warp_songs': ['WarpSong'],
        'spawn_positions': ['Spawn'],
        'shuffle_special_interior_entrances': ['SpecialInterior'],
    }
    shuffled_types = []

    for setting, types in settings_to_types_dict.items():
        if getattr(world, setting):
            shuffled_types.extend(types)

    # Complex exceptions
    if world.shuffle_grotto_entrances and world.shuffle_special_interior_entrances:
        types.append('SpecialGrave')

    shuffle_these = set()
    for x in EntranceShuffle.entrance_shuffle_table:
        if x[0] not in shuffled_types:
            continue
        assert len(x) >= 2
        assert len(x) <= 3
        shuffle_these.add(x[1][0])
        if len(x) > 2:
            shuffle_these.add(x[2][0])

    all_exits = [x for region in world.regions for x in region.exits]
    for x in all_exits:
        if x.name in shuffle_these:
            x.shuffled = True

# Fill known exits that the player has explored
# Simple interiors/grottos/dungeons with only one connection to the overworld will be assisted
def fillKnownExits(world, known_exits):
    # This will be the output data (static regions substituted for keywords)
    # Dictionary of exit_name -> destination
    output_known_exits = {}

    # Help fill in auto_* destinations
    helper = AutoGrotto.AutoGrotto()

    all_exits = [x for region in world.regions for x in region.exits]

    # List all of the simply paired connections
    simple_pairs = {}
    for x in EntranceShuffle.entrance_shuffle_table:
        if x[0] not in ['Grotto', 'Grave', 'SpecialGrave', 'Interior', 'Dungeon']:
            continue
        simple_pairs[x[1][0]] = x[2][0]

    # These are not auto-generated, so we know them for sure
    concrete_destinations = [x[1] for x in known_exits if "auto" not in x[1]]
    helper.removeRegions(concrete_destinations)

    # Fill in explored exits
    for name, dest_name in known_exits:
        # Here's where we substitute a previously unused region name for the auto keyword
        if "auto" in dest_name:
            dest_name = helper.serveRegion(dest_name)

        # Fill in the one-way information
        exit = expectOne([x for x in all_exits if x.name == name])
        dest_region = world.get_region(dest_name)
        if exit.shuffled:
            exit.connected_region = dest_region.name
            exit.shuffled = False
            output_known_exits[str(exit)] = str(dest_region)
        else:
            assert exit.connected_region == dest_region.name
    return output_known_exits

#What to display to the user as un-collected items
total_equipment = ItemPool.item_groups['ProgressItem'] + ItemPool.item_groups['Song'] + ItemPool.item_groups['DungeonReward'] + [
'Small Key (Bottom of the Well)',
'Small Key (Forest Temple)',
'Small Key (Fire Temple)',
'Small Key (Water Temple)',
'Small Key (Shadow Temple)',
'Small Key (Spirit Temple)',
'Small Key (Gerudo Fortress)',
'Small Key (Gerudo Training Grounds)',
'Small Key (Ganons Castle)',
'Boss Key (Forest Temple)',
'Boss Key (Fire Temple)',
'Boss Key (Water Temple)',
'Boss Key (Shadow Temple)',
'Boss Key (Spirit Temple)',
'Boss Key (Ganons Castle)',
'Bombchu Drop',
'Zeldas Letter',
'Weird Egg',
'Rutos Letter',
'Gerudo Membership Card',
'Deku Stick Capacity',
'Deku Shield',
'Gold Skulltula Token',
'Hylian Shield',
] + list(ItemPool.tradeitems)

def parseKnownExits(lines):
    result = []
    for line in lines:
        match = re.fullmatch("(.*) goesto (.*)", line)
        assert match
        result.append((match.group(1), match.group(2)))
    return result

def getInputData(filename):
    try:
        input_data = TextSettings.readFromFile(filename)
    except FileNotFoundError:
        input_data = {}

    # Make some input data empty lists if they are not present
    for key in ['equipment', 'checked_off', 'one_wallet', 'two_wallets', 'known_exits']:
        if key not in input_data:
            input_data[key] = []

    # Remove trailing whitespace and any parentheses
    for key in ['checked_off', 'one_wallet', 'two_wallets']:
        input_data[key] = [re.sub("\s*(\(.*)*$", "", x) for x in input_data[key]]

    # If any of the exits in please_explore have had their "?" replaced with a name, consider them a known_exits instead
    if 'please_explore' in input_data:
        migrate_these = [x for x in input_data['please_explore'] if not x.endswith("?")]
        for x in migrate_these:
            input_data['please_explore'].remove(x)
            input_data['known_exits'].append(x)
    return input_data

class SearchClass():
    def __init__(self, world, reached_regions):
        self.world = world
        self.reached_regions = reached_regions

    def can_reach(self, region, age, tod):
        assert tod in [TimeOfDay.DAY, TimeOfDay.DAMPE]

        if self.reached_regions[age][region] & tod:
            return True

        return self.propagate_tod(self.reached_regions[age], age, tod, goal_region=region)

    def propagate_tod(self, regions, age, tod, goal_region):
        exit_queue = []
        for region in regions:
            if not regions[region] & tod:
                continue
            exit_queue.extend(region.exits)

        while len(exit_queue):
            exit = exit_queue.pop(0)

            if exit.shuffled:
                continue
            destination = self.world.get_region(exit.connected_region)
            if destination not in regions:
                continue
            if regions[destination] & tod:
                continue
            if exit.access_rule(self.world.state, spot=exit, age=age, tod=tod):
                regions[destination] |= tod
                if destination == goal_region:
                    return True
                exit_queue.extend(destination.exits)
        return False

def startWorldBasedOnData(input_data, gui_dialog):
    world = generate(input_data, gui_dialog=gui_dialog)

    # Fix the bug in World.py code
    max_tokens = 0
    if world.bridge == 'tokens':
        max_tokens = max(max_tokens, world.bridge_tokens)
    if world.lacs_condition == 'tokens':
        max_tokens = max(max_tokens, world.lacs_tokens)
    tokens = [50, 40, 30, 20, 10]
    for t in tokens:
        if f'Kak {t} Gold Skulltula Reward' not in world.disabled_locations:
            max_tokens = max(max_tokens, t)
    world.max_progressions['Gold Skulltula Token'] = max_tokens

    # Populate starting equipment into state.prog_items
    for x in input_data['equipment']:
        world.state.prog_items[x] += 1
        if x == 'Deku Shield':
            world.state.prog_items['Buy Deku Shield'] += 1
        elif x == 'Deku Stick Capacity':
            world.state.prog_items['Deku Stick Drop'] += 1
        elif x == 'Hylian Shield':
            world.state.prog_items['Buy Hylian Shield'] += 1

    # Shuffle any shuffled exits, and fill in any explored exits
    shuffleExits(world)
    output_known_exits = fillKnownExits(world, parseKnownExits(input_data['known_exits']))

    # Set price rules that we have enabled
    for name in input_data['one_wallet']:
        loc = world.get_location(name)
        wallet1 = world.parser.parse_rule('(Progressive_Wallet, 1)')
        loc.add_rule(wallet1)
    for name in input_data['two_wallets']:
        loc = world.get_location(name)
        wallet2 = world.parser.parse_rule('(Progressive_Wallet, 2)')
        loc.add_rule(wallet2)

    return world, output_known_exits

def possibleLocToString(loc, world, child_reached, adult_reached):
    # TODO: see if using the subrules can be refined here?
    child = loc.parent_region in child_reached and loc.access_rule(world.state, spot=loc, age='child')
    adult = loc.parent_region in adult_reached and loc.access_rule(world.state, spot=loc, age='adult')
    assert child or adult

    if child and adult:
        message = "(child or adult)"
    elif child:
        message = "(child)"
    else:
        message = "(adult)"
    return "{} (in {}) {}".format(loc, loc.parent_region, message)

def writeResultsToFile(world, input_data, output_data, output_known_exits, filename, priorities=None):
    # Propagate input data to output
    for key in ['equipment', 'checked_off', 'one_wallet', 'two_wallets']:
        output_data[key] = input_data[key]
    output_data['settings_string'] = [world.settings.settings_string]

    # Build possible equipment list as a suggestion for items which have not been collected yet
    possible_equipment = total_equipment[:]
    for x in output_data['equipment']:
        try:
            possible_equipment.remove(x)
        except ValueError:
            pass
    output_data['possible_equipment'] = possible_equipment

    # Find the names of the possible locations (minus the checked off ones)
    # Then reconstruct their order using the master list
    p = set([x.name for x in output_data['possible_locations']])
    for name in input_data['checked_off']:
        try:
            p.remove(name)
        except KeyError:
            pass
    locs = [x for x in world.get_locations() if x.name in p]
    output_data['possible_locations'] = [possibleLocToString(x, world, output_data['child_reached'], output_data['adult_reached']) for x in locs]

    # For help with exploring exits, print out all shuffled unreachable exits
    all_exits = [x for region in world.regions for x in region.exits]
    shuffled_exits = [x.name for x in all_exits if x.shuffled]
    output_data['other_shuffled_exits'] = [x for x in shuffled_exits if x not in output_data['please_explore']]

    # Format the known_exits data as "<exit> goesto <destination>", sorted the way all_exits is.
    # This will replace the automatic keywords with real region names.
    output_data['known_exits'] = ["{} goesto {}".format(exit.name, output_known_exits[exit.name]) for exit in all_exits if exit.name in output_known_exits]

    # Format the please_explore area as "<exit> goesto ?" to make it easier on the player
    please_explore_locs = [str(x) for x in all_exits if str(x) in output_data['please_explore']]
    output_data['please_explore'] = [x + " goesto ?" for x in please_explore_locs]

    # Output data that we don't want
    del output_data['child_reached']
    del output_data['adult_reached']
    if output_data['please_explore'] == []:
        del output_data['please_explore']

    if priorities is None:
        priorities = ["please_explore", "possible_locations", "known_exits", "other_shuffled_exits"]
    TextSettings.writeToFile(output_data, filename, priorities)

def textmode(filename):
    input_data = getInputData(filename)
    world, output_known_exits = startWorldBasedOnData(input_data)
    output_data = solve(world)
    writeResultsToFile(world, input_data, output_data, output_known_exits, filename)

if __name__ == "__main__":
    # Log to stderr and file
    log_dir = 'Logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    logfile_name = datetime.datetime.now().strftime('logfile_%Y-%m-%d %H-%M-%S.log')
    logfile_name = os.path.join(log_dir, logfile_name)
    logging.basicConfig(handlers=[logging.FileHandler(logfile_name), logging.StreamHandler()], level=logging.INFO)

    # Parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--textmode', action="store_true")
    parser.add_argument('--filename', type=str, default="output.txt")
    args = parser.parse_args()

    # Launch gui or text mode
    if args.textmode:
        textmode(args.filename)
    else:
        gui.main(args.filename)
