from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.textinput import TextInput
from kivy.lang import Builder
import rsa
import socket
from threading import Thread
from functools import partial
from kivy.clock import Clock


from math import *
from kivy.graphics import Color, Line
from kivy.graphics.context_instructions import Translate, Scale
from kivy_garden.mapview.utils import clamp
from kivy_garden.mapview.view import MapLayer, MIN_LONGITUDE, MIN_LATITUDE, MAX_LATITUDE, MAX_LONGITUDE, MapSource


SERVERIP = '127.0.0.1'
PORTNUM = 8888
MAP_LAYERS = []

##################################
Builder.load_string('''
#:import MapSource kivy.garden.mapview.MapSource

<Login>:
    BoxLayout
        id: login
        orientation: 'vertical'
        
        spacing: 20

        Label:
            text: 'Welcome!'
            font_size: 32
		Label:
            text: 'Please enter your driver number'
            font_size: 24
		
		BoxLayout:
            orientation: 'vertical'

            Label:
                text: 'Driver Number'
                font_size: 18
                halign: 'left'
                text_size: root.width-20, 20

            TextInput:
                id: driverNumber
                multiline:False
                font_size: 28
				
        
		Button:
            text: 'Connection'
            font_size: 24
            on_press: root.do_login(driverNumber.text)
			
<Connected>:
    PageLayout: 
        FloatLayout: 
            MapView:
                id: mapscreen
                zoom: 13
                lat: 31.251738
                lon: 34.79342
                map_source:
                
                MapMarkerPopup:
                    id: start_marker
                    lat: 
                    lon: 
                    popup_size: dp(230), dp(130)
                    Bubble:
                        Label:
                            text: "[b]START POINT[/b]"
                            markup: True
                            halign: "center"
                MapMarkerPopup:
                    id: end_marker
                    lat: 
                    lon: 
                    popup_size: dp(100), dp(100)
                    Bubble:
                        Label:
                            text: "[b]END POINT[/b]"
                            markup: True
                            halign: "center"
            StackLayout:
                orientation: 'lr-tb'
                Button:
                    size_hint: None, None
                    font_size: 17
                    text: "CONNECT"
                    background_color: (0, 1, 0, 1)
                    pos_hint: {"left":1 , "top":1}
                    on_press: root.start_threading()
                Button:
                    size_hint: None, None
                    font_size: 17
                    text: "Refresh"
                    pos_hint: {"left":1 , "top":1}
                    on_press: root.refresh_map()
                Button:
                    size_hint: None, None
                    font_size: 17
                    text: "Finish"
                    pos_hint: {"left":1 , "top":1}
                    on_press: root.finish_route()
            Label:
                id: route_label
                size_hint_y: None
                markup: True
                font_size: 25
                text: ""
                    
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

#this is the main app loop class
class Bus_Land_App_Driver(App):
    def on_start(self):
        print("The app is running!")

    def stop(self):
        try:
            client.sendall(("CLOSE - Diver number " + str(dNumber) + " has left :( ").encode('utf-8'))
        except:
            pass
        print("The app is closed!")

    def build(self):
        self.screen_manager = ScreenManager()

        self.screen_manager.add_widget(Login(name='login'))
        self.screen_manager.add_widget(Connected(name='connected'))
        self.screen_manager.add_widget(Retry(name='retry'))

        return self.screen_manager

#this class is responsible for the LOGIN screen and for proper connection with the server
class Login(Screen):

    #the function connect to server
    def do_login(self, driverNumber):
        self.resetForm()

        global client
        client = socket.socket()
        client.connect((SERVERIP, PORTNUM))

        global dNumber
        dNumber = driverNumber

        self.manager.transition = SlideTransition(direction="left")

        if self.check_work_number():
            self.manager.current = 'connected'

        else:
            dNumber = 0
            self.manager.current = 'retry'

    def resetForm(self):
        self.ids['driverNumber'].text = ""

    def getDriverNumber(self):
        global dNumber
        return dNumber

    #the funftion return true if the driver number is correct and return false if the driver number is incorrect (if the driver is allready connected, the func will also return false)
    def check_work_number(self):
        data_send = ("Number D " + dNumber).encode()
        client.sendall(data_send)
        client_input = client.recv(1024)
        decoded_input = client_input.decode()
        if decoded_input == 'True':
            return True
        else:
            return False

#class for the chat screen
class ChatText(TextInput):
    def insert_text(self, substring, from_undo=False):
        return super(ChatText, self).insert_text("", from_undo=from_undo)

#this class is the heart of the program. responsible for the chat/map screen
class Connected(Screen):
    def __init__(self, **kwargs):
        super(Connected, self).__init__(**kwargs)
        self.f = False
        self.k = False

    #the func main purpose is to start threading and request a route from random manager that online now- worked when the worker click "CONNECT" button
    def start_threading(self):
        Connected.scrolling(self)
        client.sendall(("ROUTE REQUEST - Driver number: " + Login.getDriverNumber(self)).encode('utf-8'))
        if not self.k:
            t = Thread(target=Connected.get_message_thread, args=(self, client))
            t.daemon = True
            t.start()
        self.k = True

    #when the driver finish his route, the func delete all layers from the previous line and request new route- worked when the worker click "Finish" button
    def finish_route(self):
        try:
            self.ids.mapscreen.remove_layer(MAP_LAYERS[0])
            del MAP_LAYERS[:]
        except:
            pass
        self.ids.start_marker.lon = 20.251738
        self.ids.start_marker.lat = 20.251738
        self.ids.end_marker.lon = 20.251738
        self.ids.end_marker.lat = 20.251738
        client.sendall(("ROUTE REQUEST - Driver number: " + Login.getDriverNumber(self)).encode('utf-8'))
        route_shirshur = '[b]' + '[color=000080]WAITING FOR NEXT ROUTE[/color]' + '[/b]'
        self.ids['route_label'].text = route_shirshur
        self.refresh_map()

    #refreshing the map - worked when the worker click "Refresh" button
    def refresh_map(self):
        self.ids.mapscreen.map_source = MapSource()

    #The following 3 functions are responsible for the scroll wiget
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

    #message send - worked when the worker click "SEND" button
    def send(self, text_input):
        self.ids['text_input'].text = ""

        to_send = ("Driver " + Login.getDriverNumber(self) + " : " + text_input).encode()

        client.sendall(to_send)

        massage = ChatText(text=to_send, size_hint_y=None, height=52, font_size=30, background_color=(0, 0, 0, 0),
                           cursor_color=(1, 1, 1, 1), foreground_color=(0, 1, 0, 1))
        massage.text_size = (massage.size)
        self.ids.layout2.add_widget(massage)

    #this func is allways works (because of the thread). this func receives messages from the server
    #if the server send data the strats with "Route" so the function causes the line to appear on the map
    #if the server send data the are not strats with "Route" so this func add the message to the chatbox
    def get_message_thread(self, client):
        while True:
            client_input = client.recv(9000000)
            decoded_input = client_input.decode("utf-8")
            print("Received message:", decoded_input)
            Clock.schedule_once(partial(self.update_ui, decoded_input))

    def update_ui(self, decoded_input, *args):
        if decoded_input[:5] == 'Route':
            line = LineMapLayer(decoded_input)
            start_coor, end_coor = line.first_last_coordinate()
            MAP_LAYERS.append(line)
            splited_input = decoded_input.split(" ")
            route_shirshur = '[b]' + '[color=000080]Route number: ' + splited_input[2] + ", Bus number: " + splited_input[3] + ", Hour: " + splited_input[4][0:5] + '[/color]' + '[/b]'
            self.ids['route_label'].text = route_shirshur
            massage_text = "Route has setted, refresh your map, good work!"
            massage = ChatText(text=massage_text, size_hint_y=None, height=50, font_size=30, background_color=(0, 0, 0, 0), cursor_color=(255, 255, 255, 255), foreground_color=(0, 0, 1, 1))
            massage.text_size = (massage.size)
            self.ids.layout2.add_widget(massage)
            self.ids.mapscreen.add_layer(line, mode="scatter")
            self.ids.start_marker.lon = start_coor[1]
            self.ids.start_marker.lat = start_coor[0]
            self.ids.end_marker.lon = end_coor[1]
            self.ids.end_marker.lat = end_coor[0]
        else:
            if decoded_input == 'MANNAGER IS CONNECTED':
                route_shirshur = '[b]' + '[color=000080]WAITING FOR NEXT ROUTE [/color]' + '[/b]'
                self.ids['route_label'].text = route_shirshur
            else:
                massage = ChatText(text=decoded_input, size_hint_y=None, height=50, font_size=30, background_color=(0, 0, 0, 0), cursor_color=(255, 255, 255, 255), foreground_color=(0, 0, 1, 1))
                massage.text_size = (massage.size)
                self.ids.layout2.add_widget(massage)



#this class is responsible for the try again screen if the worker number didnt correct
class Retry(Screen):
    def do_retry(self):
        self.manager.transition = SlideTransition(direction="right")
        self.manager.current = 'login'

#this class is causes the line to appear on the map
class LineMapLayer(MapLayer):
    def __init__(self, coordinates_file_string, **kwargs):
        super(LineMapLayer, self).__init__(**kwargs)
        self._coordinates = []
        self.zoom = 0

        splited = coordinates_file_string.split('\n')
        coordinates = []

        for i in splited:
            splited_text = i.split(',')
            try:
                cooridnate1 = []
                cooridnate1.append(float(splited_text[1]))
                cooridnate1.append(float(splited_text[2]))
                coordinates.append(cooridnate1)
            except:
                pass

        self.coordinates = coordinates

    @property
    def coordinates(self):
        return self._coordinates

    @coordinates.setter
    def coordinates(self, coordinates):
        self._coordinates = coordinates

        #: Since lat is not a linear transform we must compute manually
        self.line_points = [(self.get_x(lon), self.get_y(lat)) for lat, lon in coordinates]

    # self.line_points = [mapview.get_window_xy_from(lat, lon, mapview.zoom) for lat, lon in coordinates]

    def first_last_coordinate(self):
        length = len(self._coordinates)
        return self._coordinates[0], self._coordinates[length-1]

    def reposition(self):
        mapview = self.parent

        #: Must redraw when the zoom changes
        #: as the scatter transform resets for the new tiles
        if (self.zoom != mapview.zoom):
            self.draw_line()

    def get_x(self, lon):
        '''Get the x position on the map using this map source's projection
        (0, 0) is located at the top left.
        '''
        return clamp(lon, MIN_LONGITUDE, MAX_LONGITUDE) / 180.

    def get_y(self, lat):
        '''Get the y position on the map using this map source's projection
        (0, 0) is located at the top left.
        '''
        lat = clamp(-lat, MIN_LATITUDE, MAX_LATITUDE)
        lat = lat * pi / 180.
        return ((1.0 - log(tan(lat) + 1.0 / cos(lat)) / pi))

    def draw_line(self, *args):
        mapview = self.parent
        self.zoom = mapview.zoom

        # When zooming we must undo the current scatter transform
        # or the animation distorts it
        scatter = mapview._scatter
        map_source = mapview.map_source
        sx, sy, ss = scatter.x, scatter.y, scatter.scale
        vx, vy, vs = mapview.viewport_pos[0], mapview.viewport_pos[1], mapview.scale

        # Account for map source tile size and mapview zoom
        ms = pow(2.0, mapview.zoom) * map_source.dp_tile_size

        with self.canvas:
            # Clear old line
            self.canvas.clear()

            # Undo the scatter animation transform
            Scale(1 / ss, 1 / ss, 1)
            Translate(-sx, -sy)

            # Apply the get window xy from transforms
            Scale(vs, vs, 1)
            Translate(-vx, -vy)

            # Apply the what we can factor out
            # of the mapsource long, lat to x, y conversion
            Scale(ms / 2.0, ms / 2.0, 1)
            Translate(1, 0)

            # Draw new
            Color(0, 0.2, 0.7, 0.25)
            Line(points=self.line_points, width=6.5 / ms)
            Color(0, 0.2, 0.7, 1)
            Line(points=self.line_points, width=6 / ms)
            Color(0, 0.3, 1, 1)
            Line(points=self.line_points, width=4 / ms)


if __name__ == '__main__':
    Bus_Land_App_Driver().run()
