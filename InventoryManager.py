from collections import Counter
import ItemPool
from PySide2.QtWidgets import *
import GuiUtils
from CommonUtils import *
import logging

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
] + list(ItemPool.tradeitems)

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

class InventoryBox(QWidget):
    def __init__(self, name, max, current, parent):
        super().__init__()
        self.parent = parent
        self.name = name
        self.current = current
        self.max = max

        self.label = QLabel()
        self.plusbox = QPushButton("+")
        self.plusbox.setFixedWidth(40)
        self.plusbox.clicked.connect(lambda x: self.plusEvent(x))
        self.plusspacer = QLabel("")
        self.plusspacer.setFixedWidth(40)
        self.minusbox = QPushButton("-")
        self.minusbox.setFixedWidth(40)
        self.minusbox.clicked.connect(lambda x: self.minusEvent(x))
        self.minusspacer = QLabel("")
        self.minusspacer.setFixedWidth(40)
        self.layout = QHBoxLayout()
        self.layout.addWidget(self.label)
        self.layout.addStretch()
        self.layout.addWidget(self.plusbox)
        self.layout.addWidget(self.plusspacer)
        self.layout.addWidget(self.minusbox)
        self.layout.addWidget(self.minusspacer)

        self.setLayout(self.layout)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.setFixedHeight(50)

        self.updateWidgets()

    def plusEvent(self, x):
        if (self.current >= self.max):
            return
        self.current = self.current + 1
        logging.info("User has increased {} to {}".format(self.name, self.current))
        self.updateWidgets()
        self.parent.update(self)

    def minusEvent(self, x):
        if (self.current < 1):
            return
        self.current = self.current - 1
        logging.info("User has decreased {} to {}".format(self.name, self.current))
        self.updateWidgets()
        self.parent.update(self)

    def updateWidgets(self):
        self.label.setText("{}: {}".format(self.name, self.current))
        self.plusbox.setVisible(self.current < self.max)
        self.plusspacer.setVisible(not(self.current < self.max))
        self.minusbox.setVisible(self.current > 0)
        self.minusspacer.setVisible(not(self.current > 0))

class InventoryManager:
    def __init__(self, inventory, parent):
        self.inv_widgets = [InventoryBox(name=x.name, max=x.max, current=x.current, parent=self) for x in inventory]
        self.widget = GuiUtils.ScrollSettingsArea(widgets=self.inv_widgets)
        self.parent = parent

    def collectItem(self, name, count=1):
        item = expectOne([x for x in self.inv_widgets if x.name == name])
        item.current += count
        assert item.current <= item.max and item.current >= 0
        item.updateWidgets()

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
