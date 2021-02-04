from collections import Counter
import ItemPool
import GuiUtils
from CommonUtils import *
from ImageInvButton import ImageInvButton

total_equipment = ItemPool.item_groups['ProgressItem'] + ItemPool.item_groups['Song'] + ItemPool.item_groups['DungeonReward'] + [
    'Bombchu Drop',
    'Zeldas Letter',
    'Weird Egg',
    'Rutos Letter',
    'Gerudo Membership Card',
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
    'Bombchus (20)',
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
]

item_limits = Counter()
for name, item in ItemPool.vanillaSK.items():
    if "MQ" in name:
        continue
    item_limits[item] += 1
for name, item in ItemPool.vanillaBK.items():
    if "MQ" in name:
        continue
    item_limits[item] += 1
for item in total_equipment:
    item_limits[item] += 1
item_limits['Gold Skulltula Token'] += 100

class InventoryEntry:
    def __init__(self, name, max, current=0):
        self.name = name
        self.max = max
        self.current = current

class InventoryManager:
    def __init__(self, inventory, parent):
        self.inv_widgets = [ImageInvButton(name=x.name, max=x.max, current=x.current, parent=self) for x in inventory]
        self.shown_widgets = [x for x in self.inv_widgets if x.name not in gui_ignore_items]
        self.widget = GuiUtils.GridScrollSettingsArea(widgets=self.shown_widgets)
        self.parent = parent

    def collectItem(self, name, count=1):
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
            results += [item.name] * item.current
        return results

def makeInventory(max_starting=False):
    global item_limits

    result = [InventoryEntry(name=item, max=count, current=0) for item, count in item_limits.items()]
    if max_starting:
        for x in result:
            x.current = x.max
    return result
