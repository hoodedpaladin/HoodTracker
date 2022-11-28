import PySide2.QtWidgets as QtWidgets
import PySide2.QtGui as QtGui
import logging

class MQManager:
    def __init__(self, world, parent, input_data):
        self.names = world.dungeon_mq.keys()
        self.widget = QtWidgets.QWidget()
        self.parent = parent

        horiz_split = QtWidgets.QHBoxLayout()
        self.checkboxes = {}
        title = QtWidgets.QLabel("MQ:")
        horiz_split.addWidget(title)
        for name in self.names:
            # Widget and layout to hold the label and checkbox
            w = QtWidgets.QWidget()
            l = QtWidgets.QVBoxLayout()
            label = QtWidgets.QLabel(name)
            checkbox = MQDungeonCheckbox(parent=self, name=name)
            l.addWidget(label)
            l.addWidget(checkbox)
            w.setLayout(l)
            self.checkboxes[name] = checkbox
            horiz_split.addWidget(w)
        self.widget.setLayout(horiz_split)
        self.update_world(world, input_data=input_data)

        # Don't allow interaction if MQ dungeons are determined
        self.update_visibility(world=world, input_data=None)

    def get_visibility(self, world, input_data):
        return not (world.settings.mq_dungeons_mode in ['vanilla', 'mq', 'specific'] or (world.settings.mq_dungeons_mode == 'count' and world.settings.mq_dungeons_count in [0,12]))

    def update_visibility(self, world, input_data):
        visible = self.get_visibility(world=world, input_data=input_data)
        if visible:
            self.widget.show()
        else:
            self.widget.hide()

    def clicked(self, checkbox):
        changed = checkbox.name
        dungeon_mq = {}
        for name, checkbox in self.checkboxes.items():
            dungeon_mq[name] = True if checkbox.isChecked() else False
        logging.info("User has indicated that {} is{} MQ".format(changed, "" if dungeon_mq[changed] else " not"))
        self.parent.update_mqs(dungeon_mq)

    def update_world(self, world, input_data):
        for name in self.names:
            is_mq = world.dungeon_mq[name]
            self.checkboxes[name].updateWithoutClick(is_mq)
        self.update_visibility(world=world, input_data=input_data)

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