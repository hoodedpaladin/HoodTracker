from PySide2.QtWidgets import *

class ScrollSettingsArea(QScrollArea):
    # resize QScrollArea? https://stackoverflow.com/questions/54351997/cannot-automatically-resize-a-qscrollarea
    def __init__(self, widgets):
        super().__init__()

        self._layout = QVBoxLayout()
        self._layout.setSpacing(10)

        self.collection_of_widgets = []
        self.setNewWidgets(widgets)

        self._widget = QWidget()
        self._widget.setLayout(self._layout)

        self.setWidget(self._widget)
        self.setWidgetResizable(True)

    def setNewWidgets(self, widgets):
        layout = self._layout
        for x in self.collection_of_widgets:
            x.setParent(None)
        while layout.count():
            layout.takeAt(0)
        for w in widgets:
            layout.addWidget(w, 0)
        self.collection_of_widgets = widgets
        layout.addStretch()
