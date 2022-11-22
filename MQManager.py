import PySide2.QtWidgets as QtWidgets
import PySide2.QtGui as QtGui
import logging


class MQManager:
    def __init__(self, world, parent):
        self.names = world.dungeon_mq.keys()
        self.widget = QtWidgets.QWidget()
        self.parent = parent

        horiz_split = QtWidgets.QHBoxLayout()
        self.checkboxes = {}
        for name in self.names:
            # Widget and layout to hold the label and checkbox
            w = QtWidgets.QWidget()
            l = QtWidgets.QVBoxLayout()
            label = QtWidgets.QLabel(name)
            #checkbox = QtWidgets.QCheckBox()
            checkbox = MQDungeonCheckbox(parent=self, name=name)
            l.addWidget(label)
            l.addWidget(checkbox)
            w.setLayout(l)
            self.checkboxes[name] = checkbox
            horiz_split.addWidget(w)
        self.widget.setLayout(horiz_split)
        self.update_world(world)

        # Don't allow interaction if MQ dungeons are determined
        if world.settings.mq_dungeons_mode in ['vanilla', 'mq'] or (world.settings.mq_dungeons_mode == 'count' and world.settings.mq_dungeons_count in [0,12]):
            self.widget.hide()

    def clicked(self, checkbox):
        changed = checkbox.name
        dungeon_mq = {}
        for name, checkbox in self.checkboxes.items():
            dungeon_mq[name] = True if checkbox.isChecked() else False
        logging.info("User has indicated that {} is{} MQ".format(changed, "" if dungeon_mq[changed] else " not"))
        self.parent.update_mqs(dungeon_mq)

    def update_world(self, world):
        for name in self.names:
            is_mq = world.dungeon_mq[name]
            self.checkboxes[name].updateWithoutClick(is_mq)

class MQDungeonCheckbox(QtWidgets.QCheckBox):
    def __init__(self, parent, name):
        super().__init__()
        self.parent = parent
        self.name = name
        self.stateChanged.connect(self.notify)
        self.ignore_update = False

    def notify(self):
        if not self.ignore_update:
            self.parent.clicked(self)

    def updateWithoutClick(self, state):
        self.ignore_update = True
        self.setChecked(state)
        self.ignore_update = False