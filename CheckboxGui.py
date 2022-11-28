import PySide2.QtWidgets as QtWidgets
import logging

short_names = {
    'Deku Tree': 'Deku',
    'Dodongos Cavern': 'Dodongo',
    'Jabu Jabus Belly': 'Jabu',
    'Bottom of the Well': 'BOTW',
    'Ice Cavern': 'IceCav',
    'Gerudo Training Ground': 'GTG',
    'Forest Temple': 'Forest',
    'Fire Temple': 'Fire',
    'Water Temple': 'Water',
    'Spirit Temple': 'Spirit',
    'Shadow Temple': 'Shadow',
    'Ganons Castle': 'GC',
}

class CheckboxGui:
    gui_title = "CheckboxGui, Please Replace"

    def __init__(self, world, parent, input_data):
        self.widget = QtWidgets.QWidget()
        self.parent = parent

        horiz_split = QtWidgets.QHBoxLayout()
        self.checkboxes = {}
        title = QtWidgets.QLabel(self.gui_title)
        horiz_split.addWidget(title)
        horiz_split.setMargin(0)

        for name in self.get_names(world=world, input_data=input_data):
            # Widget and layout to hold the label and checkbox
            w = QtWidgets.QWidget()
            l = QtWidgets.QVBoxLayout()
            l.setMargin(0)
            short_name = short_names.get(name, name)
            label = QtWidgets.QLabel(short_name)
            checkbox = CheckboxWidget(parent=self, name=name)
            l.addWidget(label)
            l.addWidget(checkbox)
            w.setLayout(l)
            self.checkboxes[name] = checkbox
            horiz_split.addWidget(w)
        self.widget.setLayout(horiz_split)
        self.update_gui_from_world(world=world, input_data=input_data)

        # Don't allow interaction if MQ dungeons are determined
        self.update_visibility(world=world, input_data=None)

    def update_visibility(self, world, input_data):
        visible = self.get_visibility(world=world, input_data=input_data)
        if visible:
            self.widget.show()
        else:
            self.widget.hide()

    def clicked(self, checkbox):
        changed = checkbox.name
        boxes_checked = {}
        for name, checkbox in self.checkboxes.items():
            boxes_checked[name] = True if checkbox.isChecked() else False
        logging.info("User has indicated that {}:{} is {}".format(self.gui_title, changed, "True" if boxes_checked[changed] else "False"))
        self.update_world_from_gui()

    def update_gui_from_world(self, world, input_data):
        for name in self.checkboxes.keys():
            checked = self.get_checked(name=name, world=world, input_data=input_data)
            self.checkboxes[name].updateWithoutClick(checked)
        self.update_visibility(world=world, input_data=input_data)

    def get_names(self, world, input_data):
        raise Exception()

    def get_checked(self, name, world, input_data):
        raise Exception()

    def get_visibility(self, world, input_data):
        raise Exception()

    def update_world_from_gui(self):
        raise Exception()


class CheckboxWidget(QtWidgets.QCheckBox):
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
