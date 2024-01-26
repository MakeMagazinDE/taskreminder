import machine
import time
import ujson
import urequests as requests

# Google Sheets "Apps Script"-URLs für POST:
UPLOAD_URL = 'Hier URL einsetzen'        # Anpassen !!!

# Konfiguration der Spaltenüberschriften im Google-Sheet
# Nicht ändern, da sonst auch das Google-Script angepasst werden muss
# Spaltenüberschriften im Blatt „LED_Status":
HEADER_ICON = "Icon:"
HEADER_TIME = "Um (optional) :"
HEADER_DATE = "Faellig am:"
HEADER_TITEL = "Aufgabenbeschreibung:"
HEADER_COLOR = "Farbe:"
HEADER_ROW_ID = "ROW_ID"
HEADER_EMAIL = "Email address"

# Define the pin number where the sensor is connected
sensor_pin = machine.Pin(39)
adc = machine.ADC(sensor_pin)

# Funktion zur Erstellung einer neuen Aufgabe oder zum Status-update einer bestehenden Aufgabe    
def Today_as_String():

    # Get the current time in seconds
    current_time = time.time()

    # Convert the time to a tuple representing local time
    current_local_time = time.localtime(current_time)

    # Extract the date components
    year = current_local_time[0]
    month = current_local_time[1]
    day = current_local_time[2]

    # Create the date string in the format "dd/mm/yyyy"
    date_string = "{:02d}/{:02d}/{:04d}".format(day, month, year)

    # Print the date string
    return date_string

def call_google_apps_script(data):
    # Convert the JSON data to a string
    data_str = ujson.dumps(data)

    # Make a POST request
    response = requests.request("POST", UPLOAD_URL , data=data_str)
    return response

# Function to read soil moisture data from the sensor
def read_soil_moisture():
    # Read analog value from the sensor
    sensor_value = adc.read()
    
    # Convert the analog value to a percentage (0-100%)
    moisture_percentage = 100 - ((sensor_value / 1023) * 100)
    
    return moisture_percentage

# Main loop
while True:
    # Read soil moisture
    moisture = read_soil_moisture()
   
    # Print the moisture value
    print("Soil Moisture: {:.2f}%".format(moisture))
    if (moisture > 50):
        # Erstelle neue Aufgabe in Aufgabenliste mit folgenden Werten:
        WriteResponse = call_google_apps_script({ HEADER_ICON: "3-Giessen", HEADER_TITEL: "Rosen giessen",
                                                  HEADER_DATE: Today_as_String(), HEADER_EMAIL: "ESP32@Rosen", HEADER_COLOR: "blue"})  
        print(WriteResponse.text)
        time.sleep(60*60*12) # Aufgabe wurde erstellt, warte 12h vor der nächsten Messung
     
    # Delay for 3 seconds
    time.sleep(3)
