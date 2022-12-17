from collections import Counter
import ItemPool
import GuiUtils
from CommonUtils import *
from ImageInvButton import ImageInvButton
from itertools import chain
import ItemList
import LocationList

total_equipment = ItemPool.item_groups['ProgressItem'] + ItemPool.item_groups['Song'] + ItemPool.item_groups['DungeonReward'] + [
    'Deku Stick Capacity',
    'Deku Shield',
    'Hylian Shield',
    'Progressive Hookshot',
    'Progressive Strength Upgrade',
    'Progressive Strength Upgrade',
    'Progressive Scale',
    'Progressive Wallet',
    'Progressive Wallet',
    'Blue Fire',
    'Deku Nut',
    'Biggoron Sword'
]

gui_ignore_items = [
    'Bottle with Milk',
    'Deliver Letter',
    'Eyedrops',
    'Bombchus (5)',
    'Bombchus (10)',
    'Bombchus (20)',
    'Bombchu Drop',
    'Bottle with Red Potion',
    'Bottle with Green Potion',
    'Bottle with Blue Potion',
    'Bottle with Fairy',
    'Bottle with Fish',
    'Bottle with Blue Fire',
    'Bottle with Bugs',
    'Bottle with Poe',
    'Double Defense',
    'Triforce Piece',
    'Giants Knife',
    'Magic Bean Pack',
    'Pocket Cucco',
    'Sell Big Poe',
    'Bottle with Big Poe',
]

gui_positions = [
    'Deku Stick Capacity',
    'Deku Nut',
    'Bomb Bag',
    'Bow',
    'Fire Arrows',
    'Dins Fire',
    'Kokiri Sword',
    'Biggoron Sword',

    'Slingshot',
    'Ocarina',
    'Bombchus',
    'Progressive Hookshot',
    'Light Arrows',
    'Farores Wind',
    'Deku Shield',
    'Hylian Shield',

    'Boomerang',
    'Lens of Truth',
    'Magic Bean',
    'Megaton Hammer',
    'Bottle',
    'Nayrus Love',
    'Mirror Shield',
    'Progressive Strength Upgrade',

    'Zeldas Lullaby',
    'Eponas Song',
    'Suns Song',
    'Sarias Song',
    'Song of Time',
    'Song of Storms',
    'Goron Tunic',
    'Zora Tunic',

    'Minuet of Forest',
    'Prelude of Light',
    'Bolero of Fire',
    'Serenade of Water',
    'Nocturne of Shadow',
    'Requiem of Spirit',
    'Progressive Scale',
    'Magic Meter',

    'Forest Medallion',
    'Fire Medallion',
    'Water Medallion',
    'Shadow Medallion',
    'Spirit Medallion',
    'Light Medallion',
    'Iron Boots',
    'Hover Boots',

    'Kokiri Emerald',
    'Goron Ruby',
    'Zora Sapphire',
    'Progressive Wallet',
    'Rutos Letter',
    'Child Trade',
    'Adult Trade',
    'Gold Skulltula Token',

    'Small Key (Forest Temple)',
    'Small Key (Fire Temple)',
    'Small Key (Water Temple)',
    'Small Key (Shadow Temple)',
    'Small Key (Spirit Temple)',
    'Small Key (Gerudo Training Ground)',
    'Small Key (Bottom of the Well)',
    'Small Key (Thieves Hideout)',

    'Boss Key (Forest Temple)',
    'Boss Key (Fire Temple)',
    'Boss Key (Water Temple)',
    'Boss Key (Shadow Temple)',
    'Boss Key (Spirit Temple)',
    'Boss Key (Ganons Castle)',
    'Small Key (Ganons Castle)',
    'Gerudo Membership Card',

    'Stone of Agony',
    'Blue Fire',
    'Ice Arrows',
    'Heart Container',
]

child_trade = [
    'Weird Egg',
    'Pocket Cucco',
    'Zeldas Letter',
]

adult_trade = [
    'Pocket Egg',
    'Cojiro',
    'Odd Mushroom',
    'Odd Potion',
    'Poachers Saw',
    'Broken Sword',
    'Prescription',
    'Eyeball Frog',
    'Eyedrops',
    'Claim Check',
]

item_limits = None
mq_item_limits = None

class InventoryEntry:
    def __init__(self, name, max, current=0):
        self.name = name
        self.max = max
        self.current = current
    def __repr__(self):
        return f"{self.name} inventory ({self.current} out of {self.max})"

def orderGuiWidgets(inputwidgets):
    results = []
    widgets = [x for x in inputwidgets if x.name not in gui_ignore_items]

    for item_name in gui_positions:
        match = expectOne([x for x in widgets if x.name == item_name])
        widgets.remove(match)
        results.append(match)
    results.extend(widgets)
    return results

class InventoryManager:
    def __init__(self, inventory, parent):
        self.inv_widgets = [ImageInvButton(name=x.name, max=x.max, current=x.current, parent=self) for x in inventory]
        self.shown_widgets = orderGuiWidgets(self.inv_widgets)
        self.widget = GuiUtils.GridScrollSettingsArea(widgets=self.shown_widgets)
        self.parent = parent
        self.widgets_dict = dict()
        for x in self.inv_widgets:
            self.widgets_dict[x.name] = x

    def collectItem(self, name, count=1):
        # If we have an adult trade item, assume we have all the preceding trade items
        if name in adult_trade:
            item = expectOne([x for x in self.inv_widgets if x.name == 'Adult Trade'])
            index = adult_trade.index(name) + 1
            item.current = max(item.current, index)
            assert item.current <= item.max and item.current >= 0
            item.update()
            return
        elif name in child_trade:
            item = expectOne([x for x in self.inv_widgets if x.name == 'Child Trade'])
            index = child_trade.index(name) + 1
            item.current = max(item.current, index)
            assert item.current <= item.max and item.current >= 0
            item.update()
            return
        item = expectOne([x for x in self.inv_widgets if x.name == name])
        item.current += count
        assert item.current <= item.max and item.current >= 0
        item.update()

    # Other aliases for buyable / replaceable items
    item_aliases = {
        'Deku Shield': 'Buy Deku Shield',
        'Deku Stick Capacity': 'Deku Stick Drop',
        'Hylian Shield': 'Buy Hylian Shield',
        'Deku Nut': 'Deku Nut Drop',
        'Bombchus': 'Bombchu Drop',
    }

    def getProgItems(self, world):
        results = Counter()
        for x in self.inv_widgets:
            assert x.current >= 0
            if x.current == 0:
                continue

            # Adult trade items mean we have all preceding trade items
            if x.name == 'Adult Trade':
                for item in adult_trade[:x.current]:
                    results[item] += 1
                continue
            elif x.name == 'Child Trade':
                for item in child_trade[:x.current]:
                    results[item] += 1
                continue

            results[x.name] += x.current
            # Fixes for buyable + replaceable items
            if x.name in self.item_aliases:
                results[self.item_aliases[x.name]] += x.current
        if results['Magic Bean'] >= 1:
            results['Magic Bean'] = 10
        if 'Heart Container' in results:
            results['Piece of Heart'] = results['Heart Container'] * 4
        return results

    def update(self, child_item):
        self.parent.updateLogic()

    def getOutputFormat(self):
        results = []
        for item in self.inv_widgets:
            if item.name == 'Adult Trade':
                # Adult trade items mean we have all preceding trade items
                results.extend(adult_trade[:item.current])
                continue
            elif item.name == 'Child Trade':
                # Child trade items mean we have all preceding trade items
                results.extend(child_trade[:item.current])
                continue
            results += [item.name] * item.current
        return results

    # Redo the small key amounts for vanilla/MQ
    def update_world(self, world):
        mq_items = get_mq_items(world)
        key_names = ["Small Key ({})".format(name) for name in world.dungeon_mq]
        for key_name in key_names:
            if key_name not in self.widgets_dict:
                continue
            widget = self.widgets_dict[key_name]
            amount = get_item_limit(key_name, mq_items)
            widget.update_limit(amount)
            if world.settings.shuffle_smallkeys in ['remove']:
                widget.current = amount
                widget.update()

        if world.settings.shuffle_bosskeys in ['remove']:
            key_names = [x for x,y in ItemList.item_table.items() if 'BossKey' in y[0] and x != 'Boss Key']
            for key_name in key_names:
                widget = self.widgets_dict[key_name]
                widget.current = 1
                widget.update()

# Determine which small key counts are vanilla or MQ
# Returns an empty list for vanilla
def get_mq_items(world):
    results = set()
    for dungeon_name, is_mq in world.dungeon_mq.items():
        if not is_mq:
            continue
        smallkeyname = "Small Key ({})".format(dungeon_name)
        results.add(smallkeyname)
    return results

# Picks either the regular item limit or the MQ item limit
def get_item_limit(item_name, mq_items):
    if item_name in mq_items:
        return mq_item_limits[item_name]
    else:
        return item_limits[item_name]

def get_small_key_limits(world):
    mq_items = get_mq_items(world)
    results = dict()
    for item in gui_positions:
        if 'Small Key' not in item:
            continue
        results[item] = get_item_limit(item, mq_items)
    return results

def initItemLimits(world):
    global item_limits
    global mq_item_limits

    item_limits = Counter()
    mq_item_limits = Counter()
    keys_dict = {k:v for k,v in LocationList.location_table.items() if v[4] and 'Key' in v[4]}
    for value in keys_dict.values():
        if "Master Quest" in value[5]:
            mq_item_limits[value[4]] += 1
        if "Vanilla" in value[5] or "Master Quest" not in value[5]:
            item_limits[value[4]] += 1

    for item in total_equipment:
        skip = False
        for banned_word in ["Bombchus (", "Bottle with", "Piece of Heart"]:
            if banned_word in item:
                skip = True
                break
        if item in ["Buy Magic Bean", "Deliver Letter", "Heart Container", "Piece Of Heart", "Triforce Piece"]:
            skip = True
        if not skip:
            item_limits[item] += 1
    item_limits['Gold Skulltula Token'] += 100
    item_limits['Heart Container'] += 17


def getItemLimits(world):
    global item_limits

    if not item_limits:
        initItemLimits(world)
    return item_limits


def makeInventory(world, max_starting=False):
    item_limits = getItemLimits(world)

    result = []
    mq_items = get_mq_items(world)
    # Each item name is a normal widget, except for the Adult Trade items which are their own special widget
    for item in item_limits:
        if item in adult_trade or item in child_trade:
            continue
        count = get_item_limit(item, mq_items)
        result.append(InventoryEntry(name=item, max=count, current=0))
    result.append(InventoryEntry(name='Adult Trade', max=len(adult_trade), current = 0))
    result.append(InventoryEntry(name='Child Trade', max=len(child_trade), current = 0))

    if max_starting:
        for x in result:
            x.current = x.max
    return result

def add_free_items(world, prog_items):
    # Hardcoded items
    if world.settings.free_scarecrow:
        prog_items['Scarecrow Song'] += 1
    if world.settings.no_epona_race:
        prog_items['Epona'] += 1
    if not world.keysanity and not world.dungeon_mq['Fire Temple']:
        prog_items['Small Key (Fire Temple)'] += 1
    if world.settings.shuffle_smallkeys == 'vanilla' and world.dungeon_mq['Spirit Temple']:
        prog_items['Small Key (Spirit Temple)'] += 3
