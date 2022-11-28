from CheckboxGui import CheckboxGui

class DungeonShortcutsManager(CheckboxGui):
    gui_title = "Dungeon Shortcuts"
    key = 'dungeon_shortcuts'

    def get_names(self, world, input_data):
        return list(world.dungeon_mq.keys())

    def get_checked(self, name, world, input_data):
        return name in input_data[self.key]

    def get_visibility(self, world, input_data):
        return world.settings.dungeon_shortcuts_choice not in ['off', 'choice', 'all']

    def update_world_from_gui(self):
        new_data = [x for x in self.checkboxes if self.checkboxes[x].isChecked()]
        self.parent.update_input_information(key=self.key, data=new_data)
