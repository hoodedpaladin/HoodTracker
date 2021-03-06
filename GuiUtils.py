from PySide2.QtWidgets import *

class ScrollSettingsArea(QScrollArea):
    # resize QScrollArea? https://stackoverflow.com/questions/54351997/cannot-automatically-resize-a-qscrollarea
    def __init__(self, widgets):
        super().__init__()

        self._layout = QVBoxLayout()
        self._layout.setSpacing(0)

        self.setNewWidgets(widgets)

        self._widget = QWidget()
        self._widget.setLayout(self._layout)

        self.setWidget(self._widget)
        self.setWidgetResizable(True)

    def setNewWidgets(self, widgets):
        layout = self._layout

        while layout.count():
            child = layout.takeAt(0)
            if isinstance(child, QWidgetItem):
                child.widget().deleteLater()
        for w in widgets:
            layout.addWidget(w, 0)
        layout.addStretch()

class GridScrollSettingsArea(QScrollArea):
    def __init__(self, widgets):
        super().__init__()

        self._layout = QGridLayout()
        self._layout.setSpacing(0)
        self.width = 8

        self.setNewWidgets(widgets)

        self._widget = QWidget()
        self._widget.setLayout(self._layout)

        self.setWidget(self._widget)
        self.setWidgetResizable(True)

    def setNewWidgets(self, widgets):
        layout = self._layout
        while layout.count():
            child = layout.takeAt(0)
            if isinstance(child, QWidgetItem):
                child.widget().deleteLater()

        for count, w in enumerate(widgets):
            layout.addWidget(w, count // self.width, count % self.width)

        # Prevent gaps between buttons by making the last column and row take up the extra space
        layout.setColumnStretch(self.width - 1, 1)
        last_row = (len(widgets) - 1) // self.width
        # IDK why last_row + 1 works
        layout.setRowStretch(last_row + 1, 1)

