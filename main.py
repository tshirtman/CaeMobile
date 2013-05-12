from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.uix.listview import ListItemButton
from kivy.adapters.simplelistadapter import SimpleListAdapter
from kivy.properties import ObjectProperty, ListProperty, StringProperty
from kivy.metrics import sp


class NdfApp(App):
    datalist_adapter = ObjectProperty(None)
    datalist = ListProperty()

    def __init__(self, **kwargs):
        super (NdfApp, self).__init__(**kwargs)
        self.datalist_adapter = SimpleListAdapter(
                data=self.datalist[:],
                cls=ListItemButton,
                args_converter=self.data_converter,
                )

    def build(self):
        return super(NdfApp, self).build()

    def on_datalist(self, *args):
        self.datalist_adapter.data = self.datalist[:]

    def data_converter(self, row_index, element):
        return {
            'text': element['title'],
            'size_hint_y': None,
            'height': sp(30)
            }

class MenuScreen(Screen):
    pass


class AddScreen(Screen):
    ndf_type = StringProperty('')

    def on_ndf_type(self, *args):
        print 'type changed: %s' % str(args)


class BacklogScreen(Screen):
    pass


if __name__ == '__main__':
    NdfApp().run()
