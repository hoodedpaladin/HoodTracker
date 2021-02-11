import PySide2.QtWidgets as QtWidgets
import PySide2.QtGui as QtGui
import sys
import InventoryManager
import ExploreManager
import LocationManager
import HoodTracker
import ItemPool
import FindPath
import logging
import datetime
import os

class DisplayWindow(QtWidgets.QMainWindow):
    def __init__(self, invManager, exploreManager, locManager, world, find_path_dialog:FindPath.FindPathDialog):
        super().__init__()
        self.world = world
        self.find_path_dialog = find_path_dialog

        self.setWindowTitle('HoodTracker')
        self.resize(1500, 1200)

        # Left and right side split - Locations widget is on the left
        rightside_widget=QtWidgets.QWidget()
        split = QtWidgets.QHBoxLayout()
        split.setSpacing(10)
        split.addWidget(locManager.widget, 1)
        split.addWidget(rightside_widget, 1)

        # Rightside upper = Explore widget
        # Rightside lower = Inventory widget
        rightside_layout = QtWidgets.QVBoxLayout()
        rightside_layout.addWidget(exploreManager.widget, 1)
        rightside_layout.addWidget(invManager.widget, 1)
        rightside_widget.setLayout(rightside_layout)

        fullcanvas = QtWidgets.QWidget()
        fullcanvas.setLayout(split)
        self.setCentralWidget(fullcanvas)

        self.find_path_action = QtWidgets.QAction("&Find Path", self)
        self.find_path_action.setShortcut('Ctrl+F')
        self.menuBar().addAction(self.find_path_action)

    def closeEvent(self, event:QtGui.QCloseEvent):
        self.find_path_dialog.close()

def doWeWantThisLoc(loc, world):
    # Events / drops / gossipstones / fixed locations are auto-collected
    if loc.type in ('Event', 'HintStone', 'Drop'):
        return False
    if loc.name in ItemPool.fixedlocations:
        return False
    # We do not need non-progression deku scrubs unless scrubsanity or grotto shuffle is on
    if world.shuffle_scrubs == 'off' and not world.shuffle_grotto_entrances:
        if loc.filter_tags and 'Deku Scrub' in loc.filter_tags and 'Deku Scrub Upgrades' not in loc.filter_tags:
            return False
    # Don't bother with shuffled grotto chests; assume they are taken immediately
    if world.shuffle_grotto_entrances:
        if loc.filter_tags and 'Grottos' in loc.filter_tags and loc.rule_string == 'True':
            return False
    return True

class DialogSettingsManager(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
    @staticmethod
    def get_settings_string():
        dialog = DialogSettingsManager()
        dialog.show()
        text, ok = QtWidgets.QInputDialog.getText(dialog, "Please input a settings string", "Settings string:");
        if not ok:
            text = None
        return text

class HoodTrackerGui:
    def __init__(self, filename, save_enabled=True, override_inventory=False):
        self.save_enabled = save_enabled
        self.override_inventory = override_inventory
        self.filename = filename
        self.input_data = HoodTracker.getInputData(filename)
        self.app = QtWidgets.QApplication(sys.argv)
        self.world, self.output_known_exits = HoodTracker.startWorldBasedOnData(self.input_data, gui_dialog=True)

    def run(self):

        self.invManager = InventoryManager.InventoryManager(inventory=InventoryManager.makeInventory(max_starting=self.override_inventory), parent=self)
        if not self.override_inventory:
            for item in self.input_data['equipment']:
                self.invManager.collectItem(item)
        self.world.state.prog_items = self.invManager.getProgItems(free_scarecrow=self.world.free_scarecrow, free_epona=self.world.no_epona_race)

        self.output_data = HoodTracker.solve(self.world)

        locations_from_tracker = []
        for loc in self.world.get_locations():
            if not doWeWantThisLoc(loc, self.world):
                continue
            name = LocationManager.possibleLocToString(loc, self.world, self.output_data['child_reached'], self.output_data['adult_reached'])
            possible = loc in self.output_data['possible_locations']
            checked = loc.name in self.input_data['checked_off']
            locations_from_tracker.append(LocationManager.LocationEntry(loc_name=loc.name, txt=name, possible=possible, checked=checked, parent_region=loc.parent_region.name, ignored=LocationManager.locationIsIgnored(self.world, loc)))
        self.locManager = LocationManager.LocationManager(locations=locations_from_tracker, world=self.world)


        self.exploreManager = ExploreManager.ExploreManager(self.world, parent=self)
        self.exploreManager.showThese(self.output_data['please_explore'], self.world, self.output_known_exits)

        self.find_path_dialog = FindPath.FindPathDialog(all_regions=[x.name for x in self.world.regions], parent=self)
        window = DisplayWindow(invManager=self.invManager, exploreManager=self.exploreManager, locManager=self.locManager, world=self.world, find_path_dialog=self.find_path_dialog)
        window.find_path_action.triggered.connect(self.launch_pathfind_dialog)
        window.show()

        self.app.exec_()

        self.input_data['equipment'] = self.invManager.getOutputFormat()
        self.input_data['checked_off'] = self.locManager.getOutputFormat()
        if self.save_enabled:
            HoodTracker.writeResultsToFile(self.world, self.input_data, self.output_data, self.output_known_exits, self.filename)

    def addKnownExit(self, exit_name, destination_name):
        self.output_known_exits[exit_name] = destination_name

    def updateLogic(self):
        # Reset inventory to the state of the invManager
        self.world.state.prog_items = self.invManager.getProgItems(free_scarecrow=self.world.free_scarecrow, free_epona=self.world.no_epona_race)
        self.output_data = HoodTracker.solve(self.world)
        self.locManager.updateLocationPossible(self.output_data['possible_locations'])
        self.locManager.updateLocationsIgnored(self.world)
        self.exploreManager.showThese(self.output_data['please_explore'], self.world, self.output_known_exits)

    def launch_pathfind_dialog(self):
        self.find_path_dialog.show()

def main(filename):
    log_dir = 'Logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    logfile_name = datetime.datetime.now().strftime('logfile_%Y-%m-%d %H-%M-%S.log')
    logging.basicConfig(filename=os.path.join(log_dir, logfile_name), level=logging.INFO)
    hoodgui = HoodTrackerGui(filename)
    hoodgui.run()
