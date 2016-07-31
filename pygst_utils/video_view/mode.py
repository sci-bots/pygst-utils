from pygtkhelpers.utils import gsignal
from pygtkhelpers.delegates import SlaveView
import gtk
import pandas as pd

from redirect_io import nostderr
with nostderr():
    from ..video_source import get_source_capabilities, DeviceNotFound


class VideoModeSelector(SlaveView):
    gsignal('video-config-selected', object)

    def __init__(self, configs=None):
        if configs is None:
            try:
                self.configs = get_source_capabilities()
            except DeviceNotFound:
                self.configs = pd.DataFrame(None)
        else:
            self.configs = configs
        super(VideoModeSelector, self).__init__()

    def create_ui(self):
        self.config_store = gtk.ListStore(int, object, str)
        self.set_configs(self.configs)

        self.config_combo = gtk.ComboBox(model=self.config_store)
        renderer_text = gtk.CellRendererText()
        self.config_combo.pack_start(renderer_text, True)
        self.config_combo.add_attribute(renderer_text, "text", 2)
        self.config_combo.connect("changed", self.on_config_combo_changed)
        self.widget.pack_start(self.config_combo, False, False, 0)

    def set_configs(self, configs):
        f_config_str = (lambda c: '[{device_name}] {width}x{height}\t'
                        '{framerate:.0f}fps'.format(**c))

        self.config_store.clear()
        self.config_store.append([-1, None, 'None'])
        for i, config_i in configs.iterrows():
            label_config_i = config_i.copy()
            if len(label_config_i.device_name) > 30:
                label_config_i.device_name = ('...' +
                                              label_config_i.device_name[:27])
            self.config_store.append([i, config_i,
                                      f_config_str(label_config_i)])

    ###########################################################################
    # Callback methods
    def on_config_combo_changed(self, combo):
        config = self.get_active_config()
        self.emit('video-config-selected', config)

    ###########################################################################
    # Accessor methods
    def get_active_config(self):
        tree_iter = self.config_combo.get_active_iter()
        if tree_iter is not None:
            model = self.config_combo.get_model()
            return model[tree_iter][1]


def video_mode_dialog(df_video_configs=None, title='Select video mode'):
    '''
    Args
    ----

        df_video_configs (pandas.DataFrame) : Table of video configurations in
            format returned by `..video_source.get_source_capabilities`.
        title (str) : Title to display in video selection dialog.

    Returns
    -------

        (pandas.Series) : Row from `df_video_configs` corresponding to selected
            video configuration.  Returns `None` if dialog is cancelled or no
            configuration was selected.
    '''
    mode_selector = VideoModeSelector(df_video_configs)
    dialog = gtk.Dialog(title=title, buttons=(gtk.STOCK_OK, gtk.RESPONSE_OK,
                                              gtk.STOCK_CANCEL,
                                              gtk.RESPONSE_CANCEL))
    dialog.get_content_area().pack_start(mode_selector.widget, True, False, 15)
    mode_selector.widget.show_all()
    response = dialog.run()
    config = mode_selector.get_active_config()
    dialog.destroy()

    if response == gtk.RESPONSE_OK:
        return config
    else:
        raise RuntimeError('Dialog cancelled.')
