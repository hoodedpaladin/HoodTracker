import HoodTracker
from CommonUtils import *
import PySide2.QtWidgets as QtWidgets

class Visit:
    def __init__(self, age, region, steps, string, previous):
        self.age = age
        self.region = region
        self.steps = steps
        self.string = string
        self.previous = previous
    def getHistory(self):
        if not self.previous:
            return self.string
        previous_string = self.previous.getHistory()
        if previous_string:
            previous_string += ", "
        return previous_string + self.string

def findPath(world, equipment, start_region, start_age, destination, destination_ages=['adult' , 'child'], reboot_as_last_resort=True):
    # To traverse the world, we need drop and event items, so run a full solve step to get those
    world.state.prog_items = equipment
    HoodTracker.solve(world)

    # Keep tuples of region,age that have been visited
    already_visited = {'child':set(), 'adult':set()}
    queue = []
    last_resort = []

    prog_items = world.state.prog_items
    first = Visit(age=start_age, region=start_region, steps=0, string="", previous=None)

    if start_region == destination and start_age in destination_ages:
        return "Already there"

    already_visited[start_age].add(first)
    queue.append(first)

    root_exits = world.get_region("Root Exits").exits[:]
    if reboot_as_last_resort:
        child_reboot = expectOne([x for x in root_exits if x.name == "Root Exits -> Child Spawn"])
        adult_reboot = expectOne([x for x in root_exits if x.name == "Root Exits -> Adult Spawn"])
        root_exits.remove(child_reboot)
        root_exits.remove(adult_reboot)
        last_resort.append(Visit(age=start_age, region="Root Exits", steps=0, string="Reboot, ", previous=None))
        already_visited[start_age].add("Root Exits")

    while len(queue) or len(last_resort):
        visit = queue.pop(0) if len(queue) else last_resort.pop()
        region = world.get_region(visit.region)
        age = visit.age

        if (visit.region == destination and visit.age in destination_ages):
            return visit.getHistory()

        # Exits
        try_these_exits = region.exits + root_exits
        for exit in try_these_exits:
            if exit.shuffled:
                continue
            if not exit.access_rule(world.state, spot=exit, age=age):
                continue
            if exit.connected_region in already_visited[age]:
                continue
            next_visit = Visit(age=age, region=exit.connected_region, string = "take exit "+ str(exit), steps=visit.steps + 1, previous=visit)
            if (next_visit.region == destination and next_visit.age in destination_ages):
                # Success
                return next_visit.getHistory()
            already_visited[next_visit.age].add(next_visit.region)
            queue.append(next_visit)


        # Age change
        if region.name == "Beyond Door of Time" and prog_items['Time Travel'] >= 1:
            other_age = 'adult'
            if age == 'adult':
                other_age = 'child'
            if region.name in already_visited[other_age]:
                continue
            next_visit = Visit(age=other_age, region=region.name,
                               string="age change to " + other_age, steps=visit.steps + 1, previous=visit)
            if (next_visit.region == destination and next_visit.age in destination_ages):
                # Success
                return next_visit.getHistory()
            already_visited[next_visit.age].add(next_visit.region)
            queue.append(next_visit)

            if reboot_as_last_resort:
                last_resort.append(Visit(age=other_age, region="Root Exits", steps=0, string="Reboot", previous=None))
                already_visited[other_age].add("Root Exits")

    # We have looped through all possible routes
    return None

class FindPathDialog(QtWidgets.QDialog):
    def __init__(self, all_regions, parent):
        super().__init__()

        self.parent = parent

        all_regions.sort(key=str.casefold)
        self.setWindowTitle("Find Path")
        layout = QtWidgets.QVBoxLayout()

        # Start widgets
        start_label = QtWidgets.QLabel("Current region:")
        self.start_combobox = QtWidgets.QComboBox()
        for x in all_regions:
            self.start_combobox.addItem(x)
        start_age_label = QtWidgets.QLabel("Current age:")
        self.start_age_combobox = QtWidgets.QComboBox()
        self.start_age_combobox.addItem("child")
        self.start_age_combobox.addItem("adult")

        # End widgets
        end_label = QtWidgets.QLabel("Ending region:")
        self.end_combobox = QtWidgets.QComboBox()
        for x in all_regions:
            self.end_combobox.addItem(x)
        end_age_label = QtWidgets.QLabel("Ending age:")
        self.end_age_combobox = QtWidgets.QComboBox()
        self.end_age_combobox.addItem("either")
        self.end_age_combobox.addItem("child")
        self.end_age_combobox.addItem("adult")

        # Checkbox
        self.checkbox = QtWidgets.QCheckBox()
        check_layout = QtWidgets.QHBoxLayout()
        check_layout.addWidget(QtWidgets.QLabel("Reboots OK:"))
        check_layout.addWidget(self.checkbox)

        # 2 rows lots of columns
        horiz = QtWidgets.QHBoxLayout()
        col1 = QtWidgets.QVBoxLayout()
        col1.addWidget(start_label)
        col1.addWidget(end_label)
        col2 = QtWidgets.QVBoxLayout()
        col2.addWidget(self.start_combobox)
        col2.addWidget(self.end_combobox)
        col3 = QtWidgets.QVBoxLayout()
        col3.addWidget(start_age_label)
        col3.addWidget(end_age_label)
        col4 = QtWidgets.QVBoxLayout()
        col4.addWidget(self.start_age_combobox)
        col4.addWidget(self.end_age_combobox)
        col5 = QtWidgets.QVBoxLayout()
        col5.addStretch(1)
        col5.addLayout(check_layout)
        horiz.addLayout(col1)
        horiz.addLayout(col2)
        horiz.addLayout(col3)
        horiz.addLayout(col4)
        horiz.addLayout(col5)
        layout.addLayout(horiz)

        # Full row button, label, and text box
        find_button = QtWidgets.QPushButton("Find Route")
        find_button.clicked.connect(self.findSolution)
        layout.addWidget(find_button)

        self.solution = QtWidgets.QLabel("Solution:")
        layout.addWidget(self.solution)

        self.solution_display = QtWidgets.QPlainTextEdit()
        layout.addWidget(self.solution_display)

        self.setLayout(layout)

    def findSolution(self):
        both_ages = ['child', 'adult']
        start_region = self.start_combobox.currentText()
        start_age = self.start_age_combobox.currentText()
        dest_region = self.end_combobox.currentText()
        dest_age_selection = self.end_age_combobox.currentText()
        if dest_age_selection == "either":
            dest_ages = both_ages
        elif dest_age_selection in both_ages:
            dest_ages = [dest_age_selection]
        else:
            raise Exception()
        reboot_as_last_resort = not self.checkbox.isChecked()

        if start_region == dest_region and start_age in dest_ages:
            answer = "Already there"
        else:
            answer = findPath(self.parent.world, self.parent.world.state.prog_items, start_region, start_age, dest_region, destination_ages=dest_ages, reboot_as_last_resort=reboot_as_last_resort)
            if answer is None:
                answer = "Failure"
        self.solution_display.setPlainText(answer)
