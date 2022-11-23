#!/usr/bin/env python3
import logging
import os
import sys
import re
import argparse
import LocationList
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
from Dungeon import create_dungeons
import ItemPool
import TextSettings
import EntranceShuffle
import SettingsList
from Item import ItemFactory
from Settings import Settings, ArgumentDefaultsHelpFormatter
from Region import TimeOfDay
import gui
import LocationLogic
import InventoryManager

class BadSettingsStringException(Exception):
    pass

def validate_settings_string(settings_string):
    s = Settings({})
    try:
        s.update_with_settings_string(settings_string)
    except Exception:
        return False
    return True

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
    try:
        settings.update_with_settings_string(settings_string)
    except Exception:
        raise BadSettingsStringException("{} is not a valid settings string".format(settings_string))
    return settings

def determine_mq_dungeons(world, input_data):
    if 'dungeon_mqs' not in input_data:
        # No data about MQs yet; what do we know?
        # Start with all 12 as vanilla unless it's non-random all-MQ
        if world.settings.mq_dungeons_mode == 'mq' or (world.settings.mq_dungeons_mode == 'count' and world.settings.mq_dungeons_count == 12):
            input_data['dungeon_mqs'] = world.dungeon_mq.keys()[:]
        else:
            input_data['dungeon_mqs'] = []

    for name in world.dungeon_mq:
        world.dungeon_mq[name] = True if name in input_data['dungeon_mqs'] else False

def determine_trials(world):
    if not world.settings.trials_random and world.settings.trials == 0:
        for x in world.skipped_trials:
            world.skipped_trials[x] = True
    elif not world.settings.trials_random and world.settings.trials == 6:
        # All trials enabled is the default setting
        pass
    else:
        # TODO: support selecting which trials are active
        pass

def generate(input_data, gui_dialog):
    settings = getSettings(input_data, gui_dialog=gui_dialog)

    for trick in SettingsList.logic_tricks.values():
        settings.__dict__[trick['name']] = trick['name'] in settings.allowed_tricks

    worlds = []
    for i in range(0, settings.world_count):
        worlds.append(World(i, settings, resolveRandomizedSettings=False))
        worlds[-1].ensure_tod_access = False

    for id, world in enumerate(worlds):
        determine_mq_dungeons(world, input_data)
        determine_trials(world)
        dungeons = ['Deku Tree', 'Dodongos Cavern', 'Jabu Jabus Belly', 'Forest Temple', 'Fire Temple', 'Water Temple', 'Shadow Temple', 'Spirit Temple']
        if (settings.dungeon_shortcuts_choice == 'all'):
            settings.dungeon_shortcuts = dungeons

        # Compile the json rules based on settings
        world.ensure_tod_access=True

        # Load common json rule files (those used regardless of MQ status)
        if settings.logic_rules == 'glitched':
            path = 'Glitched World'
        else:
            path = 'World'
        path = data_path(path)

        for filename in ('Overworld.json', 'Bosses.json'):
            world.load_regions_from_json(os.path.join(path, filename))

        create_dungeons(world)
        world.create_internal_locations()

        # Populate drop items
        drop_locations = list(filter(lambda loc: loc.type == 'Drop', world.get_locations()))
        for drop_location in drop_locations:
            world.push_item(drop_location, ItemFactory(drop_location.vanilla_item, world))
            drop_location.locked = True
        # Populate fixed location items
        ItemPool.junk_pool[:] = list(ItemPool.junk_pool_base)
        if world.settings.junk_ice_traps == 'on':
            ItemPool.junk_pool.append(('Ice Trap', 10))
        elif world.settings.junk_ice_traps in ['mayhem', 'onslaught']:
            ItemPool.junk_pool[:] = [('Ice Trap', 1)]
        (pool, placed_items) = ItemPool.get_pool_core(world)
        placed_items_count = {}
        #world.itempool = ItemFactory(pool, world)
        placed_locations = list(filter(lambda loc: loc.name in placed_items, world.get_locations()))
        for location in placed_locations:
            item = placed_items[location.name]
            placed_items_count[item] = placed_items_count.get(item, 0) + 1
            world.push_item(location, ItemFactory(item, world))
            world.get_location(location).locked = True
        a = LocationList.location_table

        if settings.empty_dungeons_mode == 'specific':
            for k,v in LocationList.location_table.items():
                empty = False
                for dungeon in settings.empty_dungeons_specific:
                    if v[5] and dungeon in v[5]:
                        empty = True
                        break
                if empty:
                    try:
                        location = world.get_location(k)
                        world.push_item(location, ItemFactory('Recovery Heart', world))
                        location.locked = True
                    except KeyError:
                        pass

        return world

# This is very similar to Search._expand_regions()
# Try to access all exits we have not been able to access yet
# Output a number of changes and a list of failed exits to potentially re-try again
# Also add any reached_regions to the list and any exits that need exploring to the list
def filterRegions(exit_queue, world, age, reached_regions, please_explore=True):
    failed = []
    changes = 0

    for exit in exit_queue:
        if exit.shuffled:
            if please_explore and exit.access_rule(world.state, spot=exit, age=age):
                exit.please_explore = True
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
    'Odd Mushroom Access from Lost Woods' : 'Odd Mushroom Access',
    'Poachers Saw Access from Lost Woods' : 'Poachers Saw Access',
    'Eyedrops Access from LH Lab' : 'Eyedrops Access',
    'Broken Sword Access from GV Fortress Side' : 'Broken Sword Access',
    'Cojiro Access from Kakariko Village' : 'Cojiro Access',
    'Odd Potion Access from Kak Odd Medicine Building' : 'Odd Potion Access',
    'Prescription Access from Death Mountain Summit' : 'Prescription Access',
    'Eyeball Frog Access from Zoras Domain' : 'Eyeball Frog Access',
}

def doWeWantThisLoc(loc, world):
    # Deku scrubs that don't have upgrades can be ignored, but not if scrub shuffle or grotto shuffle is on
    if world.settings.shuffle_scrubs == 'off' and not world.settings.shuffle_grotto_entrances:
        if loc.filter_tags and 'Deku Scrub' in loc.filter_tags and 'Deku Scrub Upgrades' not in loc.filter_tags:
            return False
    # Generic grottos with chests are assumed to be looted immediately when you find a grotto, so ignore them
    if world.settings.shuffle_grotto_entrances:
        if loc.filter_tags and 'Grottos' in loc.filter_tags and loc.rule_string == 'True':
            return False
    # Ignore cows if cowsanity is off
    if not world.settings.shuffle_cows:
        if loc.filter_tags and 'Cow' in loc.filter_tags:
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
        if loc.name == 'Ganon':
            # Don't hide the wincon!
            continue
        if loc.locked:
            collect_items.append(loc.item.name)
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

def solve(world, prog_items, starting_region='Root'):
    root_region = world.get_region(starting_region)
    reached_regions = {'child': {root_region:TimeOfDay.NONE},
                       'adult': {root_region:TimeOfDay.NONE}}
    all_locations = [x for region in world.regions for x in region.locations]
    locked_locations=all_locations[:]
    possible_locations=[]
    collected_locations=[]
    allkeys_possible_locations = []
    queues = {'child': [exit for exit in root_region.exits],
              'adult': [exit for exit in root_region.exits]}

    # Provide an implementation of world.state.search.can_reach
    world.state.search = SearchClass(world, reached_regions)

    world.state.prog_items = prog_items.copy()
    InventoryManager.add_free_items(world, world.state.prog_items)

    # Map traversal
    changes = 1
    while changes:
        changes = 0

        for age in ['adult', 'child']:
            add_changes, queues[age] = filterRegions(queues[age], world, age, reached_regions[age], please_explore=True)
            changes += add_changes
            changes += filterLocations(locked_locations, possible_locations, reached_regions[age], world.state, age, world)

        changes += autocollect(possible_locations, collected_locations, world.state)

    if world.settings.shuffle_smallkeys in ['vanilla', 'dungeon']:
        # Give max small keys and try again, to see which locations are "ignore small key logic" possible
        allkeys_possible_locations = possible_locations.copy()
        allkeys_reached_regions = { 'child':reached_regions['child'].copy(),
                                    'adult':reached_regions['adult'].copy()}
        key_amounts = InventoryManager.get_small_key_limits(world)
        # Free keys are given to fix the logic sometimes. So instead of comparing the current prog items,
        # Compare the base prog items amount with expected
        for key, amount in key_amounts.items():
            difference = amount - prog_items[key]
            if difference > 0:
                world.state.prog_items[key] += difference
        changes = 1
        while changes:
            changes = 0

            for age in ['adult', 'child']:
                add_changes, queues[age] = filterRegions(queues[age], world, age, allkeys_reached_regions[age], please_explore=False)
                changes += add_changes
                changes += filterLocations(locked_locations, allkeys_possible_locations, allkeys_reached_regions[age], world.state, age, world)

            changes += autocollect(allkeys_possible_locations, collected_locations, world.state)

    return {'possible_locations':possible_locations, 'adult_reached':reached_regions['adult'], 'child_reached':reached_regions['child'], 'allkeys_possible_locations':allkeys_possible_locations}

def get_shuffled_exits(settings):
    settings_to_types_dict = {
        'shuffle_grotto_entrances': ['Grotto', 'Grave'],
        'shuffle_overworld_entrances': ['Overworld'],
        'owl_drops': ['OwlDrop'],
        'warp_songs': ['WarpSong'],
        'spawn_positions': ['Spawn'],
    }
    shuffled_types = []

    for setting, types in settings_to_types_dict.items():
        if getattr(settings, setting):
            shuffled_types.extend(types)

    interior_options_dict = {
        'off': [],
        'simple': ['Interior'],
        'all': ['Interior', 'SpecialInterior'],
    }
    shuffled_types.extend(interior_options_dict[settings.shuffle_interior_entrances])

    # Complex exceptions
    if 'Grave' in shuffled_types and 'SpecialInterior' in shuffled_types:
        shuffled_types.append('SpecialGrave')

    if settings.shuffle_bosses != 'off':
        shuffled_types.extend(['ChildBoss', 'AdultBoss'])
    if settings.shuffle_dungeon_entrances in ['simple', 'all']:
        shuffled_types.append('Dungeon')
    if settings.shuffle_dungeon_entrances in ['all']:
        shuffled_types.append('DungeonSpecial')

    shuffle_these = set()
    for x in EntranceShuffle.entrance_shuffle_table:
        if x[0] not in shuffled_types:
            continue
        assert len(x) >= 2
        assert len(x) <= 3
        if len(x) == 2 and x[0] == 'Overworld' and not getattr(settings, 'decouple_entrances', False):
            # The GV Lower Stream -> Lake Hylia exit isn't shuffled unless the exits are decoupled
            continue
        shuffle_these.add(x[1][0])
        if len(x) > 2:
            shuffle_these.add(x[2][0])

    return shuffle_these

# Mark all exits shuffled that would be shuffled according to the settings
def shuffleExits(world):
    shuffle_these = get_shuffled_exits(world.settings)
    all_exits = [x for region in world.regions for x in region.exits]
    for x in all_exits:
        if x.name in shuffle_these:
            x.shuffled = True
        if 'Boss Room' in x.connected_region and not x.shuffled:
            # Unshuffled boss rooms need their hint areas marked
            other_region = world.get_region(x.connected_region)
            other_region.dungeon = x.parent_region.dungeon

#What to display to the user as un-collected items
total_equipment = ItemPool.item_groups['ProgressItem'] + ItemPool.item_groups['Song'] + ItemPool.item_groups['DungeonReward'] + [
'Small Key (Bottom of the Well)',
'Small Key (Forest Temple)',
'Small Key (Fire Temple)',
'Small Key (Water Temple)',
'Small Key (Shadow Temple)',
'Small Key (Spirit Temple)',
'Small Key (Gerudo Fortress)',
'Small Key (Gerudo Training Ground)',
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
] + list(ItemPool.trade_items)

def getInputData(filename):
    try:
        input_data = TextSettings.readFromFile(filename)
    except FileNotFoundError:
        input_data = {}

    # Make some input data empty lists if they are not present
    for key in ['equipment', 'checked_off', 'one_wallet', 'two_wallets', 'known_exits', 'paired_exits']:
        if key not in input_data:
            input_data[key] = []

    # Remove trailing whitespace
    for key in ['checked_off', 'one_wallet', 'two_wallets']:
        input_data[key] = [re.sub("\s*$", "", x) for x in input_data[key]]

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

    LocationLogic.populateKnownUnshuffled(world)

    # Fix the bug in World.py code
    max_tokens = 0
    if world.settings.bridge == 'tokens':
        max_tokens = max(max_tokens, world.settings.bridge_tokens)
    if world.settings.lacs_condition == 'tokens':
        max_tokens = max(max_tokens, world.settings.lacs_tokens)
    tokens = [50, 40, 30, 20, 10]
    for t in tokens:
        if f'Kak {t} Gold Skulltula Reward' not in world.settings.disabled_locations:
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

    # Set price rules that we have enabled
    for name in input_data['one_wallet']:
        loc = world.get_location(name)
        wallet1 = world.parser.parse_rule('(Progressive_Wallet, 1)')
        loc.add_rule(wallet1)
    for name in input_data['two_wallets']:
        loc = world.get_location(name)
        wallet2 = world.parser.parse_rule('(Progressive_Wallet, 2)')
        loc.add_rule(wallet2)

    return world

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

def writeResultsToFile(world, input_data, output_data, output_known_exits, filename, output_known_exit_pairs, priorities=None):
    # Propagate input data to output
    for key in ['equipment', 'checked_off', 'one_wallet', 'two_wallets', 'dungeon_mqs']:
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

    # Turn the known_exits data into formatted text
    #output_data = output_data | exit_information_to_text(all_exits, output_known_exits, output_known_exit_pairs)
    # TODO: clean this up later
    output_data['known_exits'] = output_known_exits
    output_data['paired_exits'] = output_known_exit_pairs

    # Output data that we don't want
    del output_data['child_reached']
    del output_data['adult_reached']

    if priorities is None:
        priorities = ["settings_string", "possible_locations", "known_exits", "other_shuffled_exits"]
    TextSettings.writeToFile(output_data, filename, priorities)

def formatPairedExits(known_exit_twins):
    items = list(known_exit_twins.keys())
    assert len(items) % 2 == 0

    result = []
    while len(items):
        item1 = items.pop(0)
        item2 = known_exit_twins[item1]
        items.remove(item2)
        result.append("{} pairswith {}".format(item1, item2))

    return result

# Turn the known-exit dictionaries into text
def exit_information_to_text(all_exits, known_exits, known_exit_pairs):
    known_exits = ["{} goesto {}".format(exit.name, known_exits[exit.name]) for exit in all_exits if exit.name in known_exits and exit.name not in known_exit_pairs]
    paired_exits = formatPairedExits(known_exit_pairs)
    return {'known_exits':known_exits, 'paired_exits':paired_exits}


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
