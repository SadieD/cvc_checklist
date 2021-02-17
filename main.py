import kivy
kivy.require('2.0.0')

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.properties import ObjectProperty, NumericProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.core.window import Window
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.config import Config
from kivy.utils import platform
from kivy.base import runTouchApp

from plyer import gps
from functools import partial
import time, os, json, csv, pickle, shutil
import tempfile

from apiclient import discovery
from apiclient.http import MediaFileUpload

#Define the device home folder
DATA_FOLDER = os.getenv('EXTERNAL_STORAGE') if platform == 'android' \
    else os.path.expanduser("~")

#Resize window to simulate mobile device - for development
if platform not in ('android', 'ios'):
    Config.set('graphics', 'resizable', '0')
    Window.size = (450, 800)
else:
    Window.softinput_mode = 'below_target'

#Get control values from json file
with open('control_values.json','r') as stream:
    control_values = json.loads(stream.read())

with open('settings.json','r') as stream:
    settings = json.loads(stream.read())
'''
#Google Drive credentials
def credentials_from_file():
    from google.oauth2 import service_account
    import googleapiclient.discovery

    SCOPES = [
    "https://spreadsheets.google.com/feeds",
    'https://www.googleapis.com/auth/spreadsheets',
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"]

    SERVICE_ACCOUNT_FILE = './cvcpitnotes-eda84c977ac9.json'

    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)

    return credentials

userEmail = 'cvc-pit-notes@cvc-pit-notes.iam.gserviceaccount.com'
credentials = credentials_from_file()
service = discovery.build('drive', 'v3', credentials=credentials)

folder_metadata = {
    'name': 'Pit Notes Data',
    'mimeType': 'application/vnd.google-apps.folder'
}
cloudFolder = service.files().create(body=folder_metadata).execute()
'''
#Depth, Site, and Report classes hold our soil pit Report data
class EquipmentValues():
    def __init__(self, id):
        self.id = id
        self.oil= ''

class Equipment():
    def __init__(self, id):
        self.id = id
        self.values = EquipmentValues(id)

class Report():
    def __init__(self,equipment_type='vehicle',equipment_id='',description=''):
        self.equipment_type = equipment_type
        self.equipment = Equipment(equipment_type)
        self.name = settings['name']
        self.datetime = '' #Add get date/time
        self.filepath = ''
        self.filename = ''

class Settings():
    def __init__(self,name='',language=''):
        self.name = settings['name']
        self.language = settings['language']

class HomeScreen(Screen):
    #Widget Values
    equipment_type = control_values['equipment_type'][0]['english']

class SettingsScreen(Screen):
    #Widget Values
    settings_name = settings['name']
    language_values = control_values['language']
    pass

class EquipmentScreen(Screen):
    equipment_type = control_values['equipment_type'][0]['english']
    pass

class VehicleScreen(Screen):
    #Widget Values
    vehicle_id = control_values['vehicle_id'][0]
    oil_engine = control_values['oil_engine'][0]
    oil_trans = control_values['oil_trans'][0]
    tire_condition = control_values['tire_condition'][0]
    tire_spare = control_values['tire_spare'][0]
    tire_iron = control_values['tire_iron'][0]

class AtvScreen(Screen):
    #Widget Values
    pass

class TractorScreen(Screen):
    #Widget Values
    pass

class ImplementScreen(Screen):
    #Widget Values
    pass

class ToolScreen(Screen):
    #Widget Values
    pass

class CameraScreen(Screen):
    def capture(self, Report):
        '''
        Function to capture the images and give them the names
        according to their captured time and date.
        '''
        camera = self.ids['camera']
        timestr = time.strftime("%Y%m%d_%H%M%S")
        camera.export_to_png("{0}/{1}_{2}_{3}_{4}.png".format(
            Report.filepath,
            Report.client_name,
            Report.ranch_name,
            Report.current_site.siteno,
            timestr
            ))
        print("Captured")

class SendReportScreen(Screen):
    path = DATA_FOLDER + '/Checklist'
    text_input = ObjectProperty(None)

    def save_file(self, path, filename):
        print('File Save: {0}'.format(filename))
        if not filename:
            print('No file')
            self.manager.current ='homescreen'
        else:
            new_dir = path + "/" + self.text_input.text
            try:
                os.mkdir(new_dir)
            except:
                self.manager.current ='homescreen'
                return False
            with open(os.path.join(new_dir, filename), 'w') as stream:
                stream.write(self.text_input.text)
            self.manager.current ='homescreen'
            return True
    pass

class Manager(ScreenManager):
    home = ObjectProperty(None)
    settings = ObjectProperty(None)
    equipment = ObjectProperty(None)
    vehicle = ObjectProperty(None)
    atv = ObjectProperty(None)
    tractor = ObjectProperty(None)
    implement = ObjectProperty(None)
    tool = ObjectProperty(None)
    send_report = ObjectProperty(None)

class ExitPopup(Popup):
    def __init__(self, **kwargs):
        super(ExitPopup, self).__init__(**kwargs)
        self.register_event_type('on_confirm')

    def on_confirm(self):
        pass

    def on_button_yes(self):
        self.dispatch('on_confirm')

class ChecklistApp(App):
    manager = ObjectProperty()
    my_report = Report() #The Report object
    settings = Settings()
    gps_location = ['','']
    gps_status = False

    def request_android_permissions(self):
        from android.permissions import request_permissions, Permission

        def callback(permissions, results):
            if all([res for res in results]):
                print("callback. All permissions granted.")
            else:
                print("callback. Some permissions refused.")

        request_permissions([Permission.ACCESS_COARSE_LOCATION,
                             Permission.ACCESS_FINE_LOCATION,
                             Permission.INTERNET,
                             Permission.CAMERA,
                             Permission.READ_EXTERNAL_STORAGE,
                             Permission.WRITE_EXTERNAL_STORAGE], callback)

    def build(self):
        try:
            gps.configure(on_location=self.gps_on_location, on_status=None)
            self.gps_status = True
        except NotImplementedError:
            import traceback
            traceback.print_exc()
            self.gps_status = False

        if platform == "android":
            self.request_android_permissions()

        if not os.path.isdir(DATA_FOLDER + '/Checklist'):
            os.mkdir(DATA_FOLDER + '/Checklist')
        if not os.path.isdir(DATA_FOLDER + '/Checklist/temp'):
            os.mkdir(DATA_FOLDER + '/Checklist/temp')
        sm = Manager()
        self.manager = sm
        self.bind(on_start=self.post_build_init)
        return sm

    def post_build_init(self, *args):
        Window.bind(on_keyboard=self.onBackBtn)

    def gps_start(self, min_time, min_distance):
        if self.gps_status:
            print("GPS Started")
            gps.start(min_time,min_distance)

    def gps_stop(self):
        if self.gps_status:
            gps.stop()

    def gps_on_location(self, **kwargs):
        if self.gps_status:
            self.gps_location[0] = str(kwargs['lat'])
            self.gps_location[1] = str(kwargs['lon'])
            print(f"\n GPS Coordinates: {self.gps_location}\n")

    def save_report(self, Report):
        with open(os.path.join(Report.filepath,Report.filename), 'wb') as report_file:
                pickle.dump(Report, report_file)
        print("Report Saved \n")
        return

    def send_report(self, Report):
        #Compress current Report directory
        print(Report.filepath)
        shutil.make_archive(base_dir='./', root_dir=Report.filepath, format='zip', base_name=os.path.join(DATA_FOLDER + '/Checklist/temp/temp'))
        #send to gsheets
        #send alert data to Dylan
        return

    #Add: dump json then save to file
    def save_settings(self, Settings)
        pass

    #Add: Update this after forms are complete
    def save_csv(self, Report):
        with open(os.path.join(Report.filepath,Report.filename + '.csv') , 'w') as csv_file:
            report_writer = csv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            report_writer.writerow([
                            'growername',
                            'ranchname',
                            'siteno',
                            'depth',
                            'texture',
                            'color',
                            'boundary',
                            'structure',
                            'consistence',
                            'rootimpair',
                            'comments',
                            'pitdepth',
                            'rootdepth',
                            'lat',
                            'lon'
                            ])
            for site in Report.sites:
                for depth in site.depths:
                    report_writer.writerow([
                                Report.client_name,
                                Report.ranch_name,
                                site.siteno,
                                depth.depth_min + '-' + depth.depth_max,
                                depth.texture + '-' + depth.fragments,
                                depth.color[0] + '-' + depth.color[1] + '-' + depth.color[2],
                                depth.boundary,
                                depth.structure,
                                depth.consis,
                                depth.root_imp,
                                depth.comments,
                                site.pitdepth,
                                site.rootdepth,
                                site.location[0],
                                site.location[1]
                    ])

    def onBackBtn(self, window, key, *args):
        """ To be called whenever user presses Back/Esc Key
        If user presses Back/Esc Key, switch screens"""
        if key == 27:
            if self.manager.current == 'homescreen':
                self.stop()
            elif self.manager.current == 'equipmentscreen':
                self.manager.current='homescreen'
            elif self.manager.current == 'vehiclescreen':
                self.manager.current='equipmentscreen'
            elif self.manager.current == 'atvscreen':
                self.manager.current='equipmentscreen'
            elif self.manager.current=='tractorscreen':
                self.manager.current='equipmentscreen'
            elif self.manager.current=='gearscreen':
                self.manager.current='equipmentscreen'
            else:
                self.manager.current='equipmentscreen'
            return True

    def on_start(self):
        self.gps_start(1000,0)

    def on_stop(self):
        self.gps_stop()

    def stop(self, *largs):
        popup = ExitPopup(title="Exit Checklist?")
        popup.bind(on_confirm=partial(self.close_app, *largs))
        popup.open()

    def close_app(self, *largs):
        super(ChecklistApp, self).stop(*largs)

if __name__ == '__main__':
    pitnotes_app = ChecklistApp()
    pitnotes_app.run()
