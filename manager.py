from kivy.app import App
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.button import *
from kivy.lang import Builder
import rsa
import socket
import os
import subprocess
from threading import Thread
from functools import partial

SERVERIP = '127.0.0.1'
PORTNUM = 8888

##################################
Builder.load_string('''
<Login>:
    BoxLayout
        id: login
        orientation: 'vertical'
        
        spacing: 20

        Label:
            text: 'Welcome!'
            font_size: 32
		Label:
            text: 'Please enter your manager number'
            font_size: 24
		
		BoxLayout:
            orientation: 'vertical'

            Label:
                text: 'Manager Number'
                font_size: 18
                halign: 'left'
                text_size: root.width-20, 20

            TextInput:
                id: mangerNumber
                multiline:False
                font_size: 28
                on_text_validate: root.do_login(mangerNumber.text)
				
        
		Button:
            text: 'Connection'
            font_size: 24
            on_press: root.do_login(mangerNumber.text)
			
<Connected>:
    PageLayout:
        FloatLayout
            Button:
                background_normal: 'my_background.jpg'
                font_size: 36
                on_press: root.managerPopup()
            Button:
                size_hint: None, None
                font_size: 17
                text: "CONNECT"
                background_color: (0, 1, 0, 1)
                pos_hint: {"left":1 , "top":1}
                on_press: root.start_threading()
                
		BoxLayout:
			orientation: 'vertical'
			
			StackLayout:
                canvas:
                    Color:
                        rgb: 1, 0, 0
                    Rectangle:
                        size: self.size
                        pos: self.pos
				orientation: 'lr-bt'

				ScrollView:
					id: scrlv
					size_hint: (0.9, 0.95)

					BoxLayout:
						id: layout2
						orientation: 'vertical'
						spacing: -20
						size_hint_y: None
	
				Slider:
					id: s
					min: 0
					max: 1
					value: 25
					orientation: 'vertical'
					step: 0.01
					size_hint: (0.1, 0.95)

			BoxLayout: 
				orientation: 'horizontal'
				size_hint_y: 0.2
				
				TextInput:
					id: text_input 
					multiline: False
					font_size: 30
					on_text_validate: root.send(text_input.text)

				Button: 
					text: 'SEND'
					font_size: 25
					background_color: (.07, 2.1, 2.1, 1)
					size_hint_x: 0.2
					on_press: root.send(text_input.text)
				

<Retry>:
    BoxLayout:
        orientation: 'vertical'

        Label:
            text: "ERROR, WRONG WORKER NUMBER, PLEASE TRY AGAIN"
            font_size: 32
        Button:
            text: "TRY AGAIN"
            font_size: 24
			on_press: root.do_retry()
''')


class Bus_Land_App_Manager(App):
    def on_start(self):
        print("The app is running!")

    def stop(self):
        try:
            client.sendall(("CLOSE - Manager number " + str(mNumber) + " has left :(").encode('utf-8'))
        except:
            pass
        print("The app is closing!")

    def build(self):
        self.screen_manager = ScreenManager()

        self.screen_manager.add_widget(Login(name='login'))
        self.screen_manager.add_widget(Connected(name='connected'))
        self.screen_manager.add_widget(Retry(name='retry'))

        return self.screen_manager


class Login(Screen):
    def do_login(self, mangerNumber):
        self.resetForm()

        global client
        client = socket.socket()
        client.connect((SERVERIP, PORTNUM))

        global mNumber
        mNumber = mangerNumber

        self.manager.transition = SlideTransition(direction="left")

        if self.check_work_number():
            self.manager.current = 'connected'
        else:
            mNumber = 0
            self.manager.current = 'retry'

    def resetForm(self):
        self.ids['mangerNumber'].text = ""

    def getManagerNumber(self):
        global mNumber
        return mNumber

    def setManagerNumber(self, x):
        global mNumber
        mNumber = x

    def check_work_number(self):
        data_send = ("Number M " + mNumber).encode()
        client.sendall(data_send)
        client_input = client.recv(1024)
        decoded_input = client_input.decode()
        if decoded_input == 'True':
            return True
        else:
            return False


class Retry(Screen):
    def do_retry(self):
        self.manager.transition = SlideTransition(direction="right")
        self.manager.current = 'login'


class ChatText(TextInput):

    def insert_text(self, substring, from_undo=False):
        return super(ChatText, self).insert_text("", from_undo=from_undo)


class Connected(Screen):
    def __init__(self, **kwargs):
        super(Connected, self).__init__(**kwargs)
        self.f = False

    def start_threading(self):
        Connected.scrolling(self)
        if not self.f:
            t = Thread(target=Connected.get_message_thread, args=(self, client))
            t.daemon = True
            t.start()
        self.f = True

    def scrolling(self):
        self.ids.scrlv.bind(scroll_y=partial(self.slider_change, self.ids.s))
        self.ids.s.bind(value=partial(self.scroll_change, self.ids.scrlv))
        self.ids.layout2.bind(minimum_height=self.ids.layout2.setter('height'))
        self.scroll_change(self.ids.scrlv, None, 0)

    def scroll_change(self, scrlv, instance, value):
        scrlv.scroll_y = value

    def slider_change(self, s, instance, value):
        if value >= 0:
            # this to avoid 'maximum recursion depth exceeded' error
            s.value = value

    def send(self, text_input):

        self.ids['text_input'].text = ""

        to_send = ("Manager " + Login.getManagerNumber(self) + " : " + text_input).encode('utf-8')

        client.sendall(to_send)

        massage = ChatText(text=to_send, size_hint_y=None, height=52, font_size=30, background_color=(0, 0, 0, 0),
                           cursor_color=(1, 1, 1, 1), foreground_color=(0, 1, 0, 1))
        massage.text_size = (massage.size)
        self.ids.layout2.add_widget(massage)

    def get_message_thread(self, client):
        while True:
            try:
                client_input = client.recv(1024)
                decoded_input = client_input.decode("utf-8")
                massage = ChatText(text=decoded_input, size_hint_y=None, height=50, font_size=30,
                                   background_color=(0, 0, 0, 0), cursor_color=(1, 1, 1, 1),
                                   foreground_color=(255, 255, 255, 255))
                massage.text_size = (massage.size)
                self.ids.layout2.add_widget(massage)
            except:
                pass

    def managerPopup(self):

        box = BoxLayout(orientation="vertical", spacing=10)
        box_horizon_Route = BoxLayout(orientation="horizontal")
        box_horizon_Driver = BoxLayout(orientation="horizontal")
        box_horizon_Hour = BoxLayout(orientation="horizontal")
        box_horizon_Bus = BoxLayout(orientation="horizontal")

        box.add_widget(Label(text='Press 4 parameters : Driver number, Bus number ,Route number and Hour'))

        box_horizon_Driver.add_widget(Label(text='DRIVER NUMBER'))
        self.driver_text_input = TextInput(font_size=24, multiline=False)
        box_horizon_Driver.add_widget(self.driver_text_input)

        box_horizon_Bus.add_widget(Label(text='BUS NUMBER'))
        self.bus_text_input = TextInput(font_size=24, multiline=False)
        box_horizon_Bus.add_widget(self.bus_text_input)

        box_horizon_Route.add_widget(Label(text='ROUTE NUMBER'))
        self.route_text_input = TextInput(font_size=24, multiline=False)
        box_horizon_Route.add_widget(self.route_text_input)

        box_horizon_Hour.add_widget(Label(text='HOUR'))
        self.hour_text_input = TextInput(font_size=24, multiline=False)
        box_horizon_Hour.add_widget(self.hour_text_input)

        box.add_widget(box_horizon_Driver)
        box.add_widget(box_horizon_Route)
        box.add_widget(box_horizon_Bus)
        box.add_widget(box_horizon_Hour)

        set_button = Button(text="SET", font_size=25, background_color=(.07, 2.1, 2.1, 1))

        box.add_widget(set_button)

        popupWindow = Popup(title="Route Setting", content=box, size_hint=(None, None), size=(500, 500))

        set_button.bind(on_press=partial(self.settings))

        popupWindow.open()

    def settings(self, instance):
        # the message will be "Route _drivernumber_ _routenumber_ _busnumber_ _hour_"_
        print('route sending')

        client.sendall((
                "Route " + self.driver_text_input.text + " " + self.route_text_input.text + " " + self.bus_text_input.text + " " + self.hour_text_input.text).encode(
            'utf-8'))

        self.bus_text_input.text = ""
        self.hour_text_input.text = ""
        self.driver_text_input.text = ""
        self.route_text_input.text = ""


if __name__ == '__main__':
    Bus_Land_App_Manager().run()
