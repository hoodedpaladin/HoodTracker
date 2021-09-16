from collections import Counter
import ItemPool
import GuiUtils
from CommonUtils import *
from ImageInvButton import ImageInvButton
from itertools import chain

total_equipment = ItemPool.item_groups['ProgressItem'] + ItemPool.item_groups['Song'] + ItemPool.item_groups['DungeonReward'] + [
    'Deku Stick Capacity',
    'Deku Shield',
    'Hylian Shield',
    'Progressive Hookshot',
    'Progressive Strength Upgrade',
    'Progressive Strength Upgrade',
    'Progressive Scale',
    'Progressive Wallet',
    'Blue Fire',
    'Deku Nut',
]

gui_ignore_items = [
    'Bottle with Milk',
    'Deliver Letter',
    'Eyedrops',
    'Ice Arrows',
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
    'Small Key (Gerudo Fortress)',

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
]

child_trade = [
    'Weird Egg',
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
    'Claim Check',
]

item_limits = Counter()
for name, item in chain(ItemPool.vanillaSK.items(), ItemPool.vanillaBK.items()):
    if "MQ" in name:
        continue
    item_limits[item] += 1

for item in total_equipment:
    item_limits[item] += 1
item_limits['Gold Skulltula Token'] += 100
item_limits['Boss Key (Ganons Castle)'] += 1
item_limits['Small Key (Gerudo Fortress)'] += 4

class InventoryEntry:
    def __init__(self, name, max, current=0):
        self.name = name
        self.max = max
        self.current = current

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

    def getProgItems(self, free_scarecrow, free_epona):
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
            if x.name == 'Deku Shield':
                results['Buy Deku Shield'] += x.current
            elif x.name == 'Deku Stick Capacity':
                results['Deku Stick Drop'] += x.current
            elif x.name == 'Hylian Shield':
                results['Buy Hylian Shield'] += x.current
            elif x.name == 'Deku Nut':
                results['Buy Deku Nut (5)'] += x.current
                results['Deku Nut Drop'] += x.current
            elif x.name == 'Bombchus':
                results['Bombchu Drop'] += x.current

        # Hardcoded items
        if free_scarecrow:
            results['Scarecrow Song'] += 1
        if free_epona:
            results['Epona'] += 1

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

def makeInventory(max_starting=False):
    global item_limits

    result = []
    # Each item name is a normal widget, except for the Adult Trade items which are their own special widget
    for item, count in item_limits.items():
        if item in adult_trade or item in child_trade:
            continue
        result.append(InventoryEntry(name=item, max=count, current=0))
    result.append(InventoryEntry(name='Adult Trade', max=len(adult_trade), current = 0))
    result.append(InventoryEntry(name='Child Trade', max=len(child_trade), current = 0))

    if max_starting:
        for x in result:
            x.current = x.max
    return result
