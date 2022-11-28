from CheckboxGui import CheckboxGui
import itertools

class SkippedTrialsManager(CheckboxGui):
    gui_title = "Skipped Trials"
    key = 'skipped_trials'

    def get_names(self, world, input_data):
        return list(world.skipped_trials.keys())

    def get_checked(self, name, world, input_data):
        return name in input_data[self.key]

    def get_visibility(self, world, input_data):
        if not world.settings.trials_random and world.settings.trials == 0:
            return False
        elif not world.settings.trials_random and world.settings.trials == 6:
            return False

        # Also hide if we can't get to Ganon's Castle
        reach_lobby = False
        output_data = self.parent.output_data
        for x in itertools.chain(output_data['adult_reached'], output_data['child_reached']):
            if x.name == 'Ganons Castle Lobby':
                reach_lobby = True
                break
        if not reach_lobby:
            return False
        return True

    def update_world_from_gui(self):
        new_data = [x for x in self.checkboxes if self.checkboxes[x].isChecked()]
        self.parent.update_input_information(key=self.key, data=new_data)
