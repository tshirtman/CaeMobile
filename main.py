from kivy.app import App
from kivy.uix.screenmanager import Screen

__version__ = '0.01'


class NdfApp(App):
    pass


class FirstScreen(Screen):
    pass


class MenuScreen(Screen):
    pass


class AddScreen(Screen):
    pass


class BacklogScreen(Screen):
    pass


if __name__ == '__main__':
    NdfApp().run()
