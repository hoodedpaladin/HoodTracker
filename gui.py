import logging

try:
    import PySide2.QtWidgets as QtWidgets
    import PySide2.QtGui as QtGui
except ModuleNotFoundError as e:
    logging.error("This needs the PySide2 library; please run \'pip install PySide2\'")
    raise e

import sys
import InventoryManager
import ExploreManager
import LocationManager
import HoodTracker
import ItemPool
import FindPath
import MQManager

class DisplayWindow(QtWidgets.QMainWindow):
    def __init__(self, invManager, exploreManager, locManager, world, mqmanager, find_path_dialog:FindPath.FindPathDialog):
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

        # Add the MQ bar at the bottom
        prevwidget = QtWidgets.QWidget()
        prevwidget.setLayout(split)
        mqsplit = QtWidgets.QVBoxLayout()
        mqsplit.addWidget(prevwidget)
        mqsplit.addWidget(mqmanager.widget)

        fullcanvas = QtWidgets.QWidget()
        fullcanvas.setLayout(mqsplit)
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
    if world.settings.shuffle_scrubs == 'off' and not world.settings.shuffle_grotto_entrances:
        if loc.filter_tags and 'Deku Scrub' in loc.filter_tags and 'Deku Scrub Upgrades' not in loc.filter_tags:
            return False
    # Don't bother with shuffled grotto chests; assume they are taken immediately
    if world.settings.shuffle_grotto_entrances:
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
        self.init_world()

    def run(self):
        inv_list = InventoryManager.makeInventory(max_starting=self.override_inventory, world=self.world)
        self.invManager = InventoryManager.InventoryManager(inventory=inv_list, parent=self)
        if not self.override_inventory:
            for item in self.input_data['equipment']:
                self.invManager.collectItem(item)
        self.world.state.prog_items = self.invManager.getProgItems(world=self.world)

        self.output_data = HoodTracker.solve(self.world)

        self.locManager = LocationManager.LocationManager(self.world)
        self.populate_locations()


        self.exploreManager = ExploreManager.ExploreManager(self.world, parent=self, please_explore=self.output_data['please_explore'], known_exits=self.output_known_exits)
        self.mqmanager = MQManager.MQManager(world=self.world, parent=self)

        self.find_path_dialog = FindPath.FindPathDialog(all_regions=[x.name for x in self.world.regions], parent=self)
        window = DisplayWindow(invManager=self.invManager, exploreManager=self.exploreManager, locManager=self.locManager, world=self.world, find_path_dialog=self.find_path_dialog, mqmanager=self.mqmanager)
        window.find_path_action.triggered.connect(self.launch_pathfind_dialog)
        window.show()

        self.app.exec_()

        self.input_data['equipment'] = self.invManager.getOutputFormat()
        self.input_data['checked_off'] = self.locManager.getOutputFormat()
        if self.save_enabled:
            HoodTracker.writeResultsToFile(world=self.world,
                                           input_data=self.input_data,
                                           output_data=self.output_data,
                                           output_known_exits=self.output_known_exits,
                                           filename=self.filename,
                                           output_known_exit_pairs=self.output_known_exit_pairs)

    def addKnownExit(self, exit_name, destination_name):
        self.output_known_exits[exit_name] = destination_name

    def forgetKnownExit(self, exit_name):
        logging.info("Forgetting exit {}".format(exit_name))
        del self.output_known_exits[exit_name]
        self.exploreManager.reshuffle_exit(exit_name)

        # The other exit in a pair
        if exit_name in self.output_known_exit_pairs:
            exit_name2 = self.output_known_exit_pairs[exit_name]
            logging.info("Forgetting paired exit {}".format(exit_name2))
            self.exploreManager.reshuffle_exit(exit_name2)
            del self.output_known_exits[exit_name2]
            del self.output_known_exit_pairs[exit_name]
            del self.output_known_exit_pairs[exit_name2]

    def addKnownExitPairs(self, exit, paired_exit):
        self.output_known_exits[exit.name] = ExploreManager.getDestinationForPairedExit(paired_exit.name)
        self.output_known_exits[paired_exit.name] = ExploreManager.getDestinationForPairedExit(exit.name)
        self.output_known_exit_pairs[exit.name] = paired_exit.name
        self.output_known_exit_pairs[paired_exit.name] = exit.name

    def updateLogic(self):
        # Reset inventory to the state of the invManager
        self.world.state.prog_items = self.invManager.getProgItems(world=self.world)
        self.output_data = HoodTracker.solve(self.world)
        self.locManager.updateLocationPossible(self.output_data['possible_locations'])
        self.locManager.updateLocationsIgnored(self.world)
        self.exploreManager.show_these(self.output_data['please_explore'], self.output_known_exits)

    def launch_pathfind_dialog(self):
        self.find_path_dialog.show()

    def init_world(self):
        self.world, self.output_known_exits, self.output_known_exit_pairs = HoodTracker.startWorldBasedOnData(self.input_data, gui_dialog=True)

    def populate_locations(self):
        for loc in self.world.get_locations():
            if not doWeWantThisLoc(loc, self.world):
                continue
            possible = loc in self.output_data['possible_locations']
            checked = loc.name in self.input_data['checked_off']
            ignored = LocationManager.locationIsIgnored(self.world, loc)
            locationEntry = LocationManager.LocationEntry(loc_name=loc.name, possible=possible, checked=checked, parent_region=loc.parent_region.name, ignored=ignored, parent=self.locManager)
            self.locManager.insertLocation(locationEntry)

    def update_world(self, world):
        self.world.state.prog_items = self.invManager.getProgItems(world=self.world)
        self.output_data = HoodTracker.solve(self.world)
        self.locManager.update_world(world)
        self.populate_locations()
        self.exploreManager.show_widgets()
        self.invManager.update_world(self.world)

    def update_mqs(self, dungeon_mqs):
        # Route the "output" information to the input again so it isn't lost
        self.input_data['checked_off'] = sorted(self.locManager.getOutputFormat())
        self.input_data['dungeon_mqs'] = [name for name in dungeon_mqs if dungeon_mqs[name]]
        all_exits = [x for region in self.world.regions for x in region.exits]
        self.input_data |= HoodTracker.exit_information_to_text(all_exits=all_exits, known_exits=self.output_known_exits, known_exit_pairs=self.output_known_exit_pairs)
        # Regenerate the world again with new settings and send it to the GUI elements
        self.init_world()
        self.update_world(self.world)

# Pyside2 will consume exceptions unless we replace sys.excepthook with this
# Also prints exceptions to the log
def exception_hook(exctype, value, traceback):
    logging.error("Uncaught exception:", exc_info=(exctype, value, traceback))
    # Pyside2 will continue unless we do this
    sys.exit(1)

def main(filename):
    sys.excepthook = exception_hook

    hoodgui = HoodTrackerGui(filename)
    hoodgui.run()
