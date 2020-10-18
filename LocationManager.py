
from PySide2.QtWidgets import *
from PySide2.QtGui import *

class LocationManager:
    def __init__(self, locations):
        treeWidget = QTreeView()
        self.widget = treeWidget
        treeWidget.setHeaderHidden(True)

        treeModel = QStandardItemModel()
        rootNode = treeModel.invisibleRootItem()

        self._unchecked = TableEntry("Unchecked", font_size=12)
        self._checked = TableEntry("Checked", font_size=12)
        self._not_possible = TableEntry("Not Possible", font_size=12)
        rootNode.appendRow(self._unchecked)
        rootNode.appendRow(self._checked)
        rootNode.appendRow(self._not_possible)

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

        if location.currently_checked:
            destination = self._checked
        elif not location.possible:
            destination = self._not_possible
        else:
            destination = self._unchecked
        if first:
            destination.insertRow(0, location)
        else:
            destination.appendRow(location)
    def updateLocationPossible(self, possible_locations):
        possible_names = set(x.name for x in possible_locations)
        for x in self.allLocations:
            possible = x.loc_name in possible_names
            x.setPossible(possible)
    def getOutputFormat(self):
        results = []
        for x in self.allLocations:
            if x.currently_checked:
                results.append(x.loc_name)
        return results

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
    def __init__(self, loc_name, txt, possible, checked=False):
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
        if checked:
            self.setCheckState(Qt.CheckState.Checked)
        else:
            self.setCheckState(Qt.CheckState.Unchecked)
        #self.currently_checked = self.isChecked()
        self.possible = possible

    def isChecked(self):
        return self.checkState() == Qt.CheckState.Checked

    def processCheck(self):
        if not self.isCheckable():
            return
        new_checked = self.isChecked()
        if self.currently_checked == new_checked:
            return
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
