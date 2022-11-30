import logging
from collections import Counter

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
import FindPath
from MQManager import MQManager
import DungeonShortcutsManager
from SkippedTrialsManager import SkippedTrialsManager
from EmptyDungeonsManager import EmptyDungeonsManager

class DisplayWindow(QtWidgets.QMainWindow):
    def __init__(self, invManager, exploreManager, locManager, world, mqmanager, dungeon_shortcuts_manager,
                 skipped_trials_manager, empty_dungeons_manager, find_path_dialog:FindPath.FindPathDialog):
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
        mqsplit.addWidget(dungeon_shortcuts_manager.widget)
        mqsplit.addWidget(skipped_trials_manager.widget)
        mqsplit.addWidget(empty_dungeons_manager.widget)

        fullcanvas = QtWidgets.QWidget()
        fullcanvas.setLayout(mqsplit)
        self.setCentralWidget(fullcanvas)
        self.fullcanvas_widget = fullcanvas

        actions = []
        self.find_path_action = QtWidgets.QAction("&Find Path", self)
        self.find_path_action.setShortcut('Ctrl+F')
        actions.append(self.find_path_action)
        self.change_settings_action = QtWidgets.QAction("Change &Settings String", self)
        self.change_settings_action.setShortcut('Ctrl+S')
        actions.append(self.change_settings_action)
        for action in actions:
            self.menuBar().addAction(action)

    def closeEvent(self, event:QtGui.QCloseEvent):
        self.find_path_dialog.close()

def doWeWantThisLoc(loc, world):
    # Events / drops / gossipstones / fixed locations are auto-collected
    if loc.name == 'Ganon':
        return True
    if loc.type in ('Event', 'HintStone', 'Drop', 'Hint'):
        return False
    if loc.locked and loc.item.name not in HoodTracker.drops_we_are_interested_in:
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
        inv_list = InventoryManager.makeInventory(world=self.world, max_starting=self.override_inventory)
        self.invManager = InventoryManager.InventoryManager(inventory=inv_list, parent=self)
        if not self.override_inventory:
            equipment_items = Counter()
            for item in self.input_data['equipment']:
                equipment_items[item] += 1
            for item, count in equipment_items.items():
                self.invManager.collectItem(item, count=count)
        self.invManager.update_world(self.world)
        prog_items = self.invManager.getProgItems(world=self.world)

        # Init ExploreManager now to use its logic for filling in known exits
        self.exploreManager = ExploreManager.ExploreManager(self.world, parent=self, input_data=self.input_data)

        self.output_data = HoodTracker.solve(self.world, prog_items=prog_items)

        # Update ExploreManager widgets with the solve data
        self.exploreManager.show_widgets()
        self.locManager = LocationManager.LocationManager(self.world, parent_gui=self)
        self.populate_locations()


        self.mqmanager = MQManager(world=self.world, parent=self, input_data=self.input_data)
        self.dungeon_shortcuts_manager = DungeonShortcutsManager.DungeonShortcutsManager(world=self.world, parent=self, input_data=self.input_data)
        self.skipped_trials_manager = SkippedTrialsManager(world=self.world, parent=self, input_data=self.input_data)
        self.empty_dungeons_manager = EmptyDungeonsManager(world=self.world, parent=self, input_data=self.input_data)

        self.find_path_dialog = FindPath.FindPathDialog(all_regions=[x.name for x in self.world.regions], parent=self)
        window = DisplayWindow(invManager=self.invManager,
                               exploreManager=self.exploreManager,
                               locManager=self.locManager,
                               world=self.world,
                               find_path_dialog=self.find_path_dialog,
                               mqmanager=self.mqmanager,
                               dungeon_shortcuts_manager=self.dungeon_shortcuts_manager,
                               skipped_trials_manager=self.skipped_trials_manager,
                               empty_dungeons_manager=self.empty_dungeons_manager)
        self.window = window
        window.find_path_action.triggered.connect(self.launch_pathfind_dialog)
        window.change_settings_action.triggered.connect(self.launch_settingsstring_dialog)
        window.show()

        self.app.exec_()

        self.input_data['equipment'] = self.invManager.getOutputFormat()
        self.input_data['checked_off'] = self.locManager.getOutputFormat()
        output_known_exits, output_known_exit_pairs = self.exploreManager.get_output()
        if self.save_enabled:
            HoodTracker.writeResultsToFile(world=self.world,
                                           input_data=self.input_data,
                                           output_data=self.output_data,
                                           output_known_exits=output_known_exits,
                                           filename=self.filename,
                                           output_known_exit_pairs=output_known_exit_pairs)

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
        prog_items = self.invManager.getProgItems(world=self.world)
        for exit in self.exploreManager.all_shuffled_exits:
            exit.please_explore = False
        self.output_data = HoodTracker.solve(self.world, prog_items=prog_items)
        self.locManager.updateLocationPossible(self.output_data['possible_locations'], self.output_data['allkeys_possible_locations'])
        self.locManager.updateLocationsIgnored(self.world)
        self.skipped_trials_manager.update_visibility(world=self.world, input_data=self.input_data)
        self.exploreManager.show_widgets()

    def launch_pathfind_dialog(self):
        self.find_path_dialog.show()

    def init_world(self):
        self.world = HoodTracker.startWorldBasedOnData(self.input_data, gui_dialog=True)

    # Fill the LocationManager gui with the current set and state of locations
    def populate_locations(self):
        for loc in self.world.get_locations():
            if not doWeWantThisLoc(loc, self.world):
                continue
            possible = loc in self.output_data['possible_locations']
            if not possible and loc in self.output_data['allkeys_possible_locations']:
                possible = 2
            checked = loc.name in self.input_data['checked_off']
            ignored = LocationManager.locationIsIgnored(self.world, loc)
            locationEntry = LocationManager.LocationEntry(loc_name=loc.name, type=loc.type, possible=possible, checked=checked, parent_region=loc.parent_region.name, ignored=ignored, parent=self.locManager)
            self.locManager.insertLocation(locationEntry)

    # Refresh all gui managers with the new self.world
    def update_world(self):
        # Get inventory and known exits before solving the logic
        self.world.state.prog_items = self.invManager.getProgItems(world=self.world)
        self.exploreManager.update_world(world=self.world, input_data=self.input_data)
        self.output_data = HoodTracker.solve(self.world, prog_items=self.world.state.prog_items)
        self.locManager.update_world(self.world)
        # Update GUIs
        self.populate_locations()
        self.exploreManager.show_widgets()
        self.invManager.update_world(self.world)
        self.mqmanager.update_gui_from_world(world=self.world, input_data=self.input_data)
        self.dungeon_shortcuts_manager.update_gui_from_world(world=self.world, input_data=self.input_data)
        self.skipped_trials_manager.update_gui_from_world(world=self.world, input_data=self.input_data)
        self.empty_dungeons_manager.update_gui_from_world(world=self.world, input_data=self.input_data)

    # Save the current state of the world / gui managers into input_data
    def save_current_data_to_input_data(self):
        self.input_data['checked_off'] = sorted(self.locManager.getOutputFormat())
        self.input_data['dungeon_mqs'] = [name for name in self.world.dungeon_mq if self.world.dungeon_mq[name]]
        output_known_exits, output_known_exit_pairs = self.exploreManager.get_output()
        self.input_data['known_exits'] = output_known_exits
        self.input_data['paired_exits'] = output_known_exit_pairs

    def update_input_information(self, key, data):
        # TODO: not all of these really need the world to be regenerated, if you handle the settings changes better
        # Route the "output" information to the input again so it isn't lost
        self.save_current_data_to_input_data()
        # Apply changes to the input data
        self.input_data[key] = data
        # Regenerate the world again with new settings and send it to the GUI elements
        self.init_world()
        self.update_world()

    def update_settings_string(self, new_settings_string):
        self.save_current_data_to_input_data()
        old_settings_string = self.world.settings.settings_string
        # Regenerate the world again with new settings and send it to the GUI elements
        self.input_data['settings_string'] = [new_settings_string]
        try:
            self.init_world()
        except HoodTracker.BadSettingsStringException as e:
            logging.error("Invalid settings string: {}".format(e))
            self.input_data['settings_string'] = [old_settings_string]
            self.init_world()
        self.update_world()

    def updateLocationWallets(self, locname, numwallets):
        # Route the "output" information to the input again so it isn't lost
        self.save_current_data_to_input_data()

        # Add to wallet list it should be in, and remove from any wallet lists it shouldn't be in
        wallet_lists = { 1: self.input_data['one_wallet'], 2: self.input_data['two_wallets']}
        for num,walletlist in wallet_lists.items():
            while locname in walletlist:
                walletlist.remove(locname)
            if numwallets == num:
                walletlist.append(locname)

        # Regenerate the world again with new settings and send it to the GUI elements
        self.init_world()
        self.update_world()

    def launch_settingsstring_dialog(self):
        old_settings_string = self.world.settings.settings_string
        new_string, ok = QtWidgets.QInputDialog.getText(self.window.fullcanvas_widget,
                                                        "Change Settings String",
                                                        "Enter new settings string:\n{}".format(old_settings_string),
                                                        QtWidgets.QLineEdit.Normal,
                                                        old_settings_string)
        if not ok:
            return
        # Attempt to quit early if the settings string is invalid
        if not HoodTracker.validate_settings_string(new_string):
            logging.error("Invalid settings string: " + new_string)
            show_warning_popup("Invalid settings string: " + new_string)
            return
        logging.info("Updating settings string to " + new_string)
        self.update_settings_string(new_string)

def show_warning_popup(message):
    msgBox = QtWidgets.QMessageBox()
    msgBox.setIcon(QtWidgets.QMessageBox.Information)
    msgBox.setWindowTitle("Error")
    msgBox.setText(message)
    msgBox.exec()

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
