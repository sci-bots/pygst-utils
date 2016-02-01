from pygtkhelpers.utils import gsignal
from pygtkhelpers.delegates import SlaveView
import gtk
import pandas as pd

from ..video_source import get_available_video_modes, DeviceNotFound


class VideoModeSelector(SlaveView):
    gsignal('video-config-selected', object)

    def __init__(self, configs=None):
        if configs is None:
            try:
                self.configs = pd.DataFrame(get_available_video_modes())
            except DeviceNotFound:
                self.configs = pd.DataFrame(None)
        else:
            self.configs = configs
        super(VideoModeSelector, self).__init__()

    def set_configs(self, configs):
        f_config_str = (lambda c: '[{device}] {width}x{height}\t'
                        '{framerate:.0f}fps'.format(**c))

        self.config_store.clear()
        self.config_store.append([-1, None, 'None'])
        for i, config_i in configs.iterrows():
            self.config_store.append([i, config_i, f_config_str(config_i)])

    def create_ui(self):
        self.config_store = gtk.ListStore(int, object, str)
        self.set_configs(self.configs)

        self.config_combo = gtk.ComboBox(model=self.config_store)
        renderer_text = gtk.CellRendererText()
        self.config_combo.pack_start(renderer_text, True)
        self.config_combo.add_attribute(renderer_text, "text", 2)
        self.config_combo.connect("changed", self.on_config_combo_changed)
        self.widget.pack_start(self.config_combo, False, False, 0)

    def on_config_combo_changed(self, combo):
        tree_iter = combo.get_active_iter()
        if tree_iter is not None:
            model = combo.get_model()
            config = model[tree_iter][1]
            self.emit('video-config-selected', config)
