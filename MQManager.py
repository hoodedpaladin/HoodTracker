from CheckboxGui import CheckboxGui

class MQManager(CheckboxGui):
    gui_title = "MQ"
    key = 'dungeon_mqs'

    def get_names(self, world, input_data):
        return list(world.dungeon_mq.keys())

    def get_checked(self, name, world, input_data):
        return name in input_data[self.key]

    def get_visibility(self, world, input_data):
        if world.settings.mq_dungeons_mode == 'mq' or (world.settings.mq_dungeons_mode == 'count' and world.settings.mq_dungeons_count == 12):
            return False
        elif world.settings.mq_dungeons_mode == 'vanilla' or (world.settings.mq_dungeons_mode == 'count' and world.settings.mq_dungeons_count == 0):
            return False
        elif world.settings.mq_dungeons_mode == 'specific':
            return False
        return True

    def update_world_from_gui(self):
        new_data = [x for x in self.checkboxes if self.checkboxes[x].isChecked()]
        self.parent.update_input_information(key=self.key, data=new_data)
