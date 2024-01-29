import machine
import time
import urequests as requests
import neopixel
import utime
import ujson
import _thread
try:
    import usocket as socket
except:
    import socket

# Google Sheets "Apps Script"-URLs für POST and GET Aufruf:
# Kopiere die "Apps Script"-URLs in die folgenden beiden Zeilen
UPLOAD_URL = 'Hier URL einsetzen'        # Anpassen !!!
DOWNLOAD_URL = 'Hier URL einsetzen'     # Anpassen !!!

# Konfiguration der ESP32 IO-Pins zum Anschluss der Taster
BUTTON_PINS = [2, 34, 4, 14, 32] #entspricht SW1, SW2, SW3, SW4, SW5
 
# Konfiguration der Spaltenüberschriften im Google-Sheet
# Nicht ändern, da sonst auch das Google-Script angepasst werden muss
# Spaltenüberschriften im Blatt „LED_Status":
HEADER_ICON = "ICON"
HEADER_TIME = "DUE_TIME"
HEADER_TITEL = "TITEL"
HEADER_STATUS = "STATUS"
HEADER_COLOR = "COLOR"
HEADER_ROW_ID = "ROW_ID"

# Spaltenüberschriften und spezielle Werte im Blatt „Aufgabenliste":
HEADER_WATCHDOG = "WatchDog"       #Wird benötigt um eine Status-Neuberechnung im Google Sheet zu erzwingen
HEADER_TASK_STATUS = "Task_Status" #In dieser Spalte wird der Wert "done" eingetragen, wenn die Aufgabe erledigt wurde
VALUE_COMPLETED = "done"           #Wert der in obige Spalte eingetragen werden soll

# Neopixel Konfiguration
NUM_PIXELS = 10    #Anzahl der LEDs im NeoPixel-Streifen
NEOPIXEL_PIN = 33  #ESP32-IO-Pin, an dem der NeoPixel-Streifen angeschlossen ist
UPDATE_CYCLE = 60  #Zeitintervall in Sekunden zwischen den Abfragen des neuen Status im Google Sheet

# Configure the pin for NeoPixel data
pin = machine.Pin(NEOPIXEL_PIN, machine.Pin.OUT)

# Create a NeoPixel object
pixels = neopixel.NeoPixel(pin, NUM_PIXELS)

led_states = []  # List to store the state and color of each LED
LED_UPDATE_NEEDED = True
PIN_PRESSED = -1
LAST_STATE = False
last_update = time.mktime((0, 0, 0, 0, 0, 0, 0, 0, -1))


# Funktion für die Webseite zur Umbennenung von deutschen Umlauten, die sonst falsch dargestellt würden.
def replace_german_chars(text):
    replacements = {
        "ü": "&uuml;",
        "ö": "&ouml;",
        "ä": "&auml;",
        "Ö": "&Ouml;",
        "Ä": "&Auml;",
        "Ü": "&Uuml;",
        # Add more character replacements as needed
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    return text

# Funktion für die Webseite um neben dem Icon auch die Fälligkeitszeit anzuzeigen  
def AddTimeToIcon(TimeString):
    if TimeString > "00:00":
        TimeString = ' @ ' + TimeString
    else:
        TimeString = ''
    return TimeString

# Webseite, die die anstehenden Aufgaben in tabellarischer Form darstellt
def web_page():
    html = """<!DOCTYPE HTML><html>
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
    html { font-family: Arial; display: inline-block; margin: 0px auto; text-align: left;    }
    h2 { font-size: 1.5rem; } p { font-size: 1.5rem; }
    .units { font-size: 2.0rem; }
    .dht-labels{ font-size: 1.0rem; vertical-align:bottom; padding-bottom: 0px; }
  </style>
</head>
<body>
  <h2>Family Reminder</h2>
  <p>
    <span><strong>""" + replace_german_chars(led_status[0][HEADER_ICON]) + AddTimeToIcon(led_status[0][HEADER_TIME]) + """</strong></span>
  </p>
  <p>
    <span>""" + replace_german_chars(led_status[0][HEADER_TITEL]) + """</span>
  </p>
  <p>
    <span><strong>""" + replace_german_chars(led_status[1][HEADER_ICON]) + AddTimeToIcon(led_status[1][HEADER_TIME]) + """</strong></span>
  </p>
  <p>
    <span>""" + replace_german_chars(led_status[1][HEADER_TITEL]) + """</span>
  </p>
  <p>
    <span><strong>""" + replace_german_chars(led_status[2][HEADER_ICON]) + AddTimeToIcon(led_status[2][HEADER_TIME]) + """</strong></span>
  </p>
  <p>
    <span>""" + replace_german_chars(led_status[2][HEADER_TITEL]) + """</span>
  </p>
  <p>
    <span><strong>""" + replace_german_chars(led_status[3][HEADER_ICON]) + AddTimeToIcon(led_status[3][HEADER_TIME]) + """</strong></span>
  </p>
  <p>
    <span>""" + replace_german_chars(led_status[3][HEADER_TITEL]) + """</span>
  </p>
  <p>
    <span><strong>""" + replace_german_chars(led_status[4][HEADER_ICON]) + AddTimeToIcon(led_status[4][HEADER_TIME]) + """</strong></span>
  </p>
  <p>
    <span>""" + replace_german_chars(led_status[4][HEADER_TITEL]) + """</span>
  </p>

</body>
</html>"""
    
    return html


        
# Funktion zur Erstellung einer neuen Aufgabe oder zum Status-Update einer bestehenden Aufgabe    
def call_google_apps_script(data):
    # Convert the JSON data to a string
    data_str = ujson.dumps(data)

    # Make a POST request
    response = requests.request("POST", UPLOAD_URL , data=data_str)
    return response

# Funktion zur Abfrage des LED-Status in im Google Sheet "LED_Status"    
def fetch_led_status():
    response = ujson.loads(requests.get(DOWNLOAD_URL).text)
    return response 



# Funktion zur Ansteuerung der NeoPixel, für jedes Icon werden zwei aufeinander folgende Pixel angesteuert
def set_neopixel_colors(json_data):
    data = json_data #ujson.loads(json_data)

    for i in range(len(data)):
        if data[i][HEADER_STATUS] == "on":
            color = data[i][HEADER_COLOR]
            pixel_index = i * 2  # Two pixels per ID

            # Set color for the first pixel
            pixels[pixel_index] = parse_color(color)

            # Set color for the second pixel
            pixels[pixel_index + 1] = parse_color(color)
        elif data[i][HEADER_STATUS] == "off":
            pixel_index = i * 2  # Two pixels per ID

            # Switch off the first pixel
            pixels[pixel_index] = (0, 0, 0)

            # Switch off the second pixel
            pixels[pixel_index + 1] = (0, 0, 0)

    # Update NeoPixel strip
    pixels.write()


def parse_color(color):
    color_mapping = {
        "red": (255, 0, 0),
        "green": (0, 255, 0),
        "blue": (0, 0, 255),
        "yellow": (255, 255, 0)
        # Add more color mappings as needed
    }
    return color_mapping.get(color, (0, 0, 0))  # Default to (0, 0, 0) if color is not found in the mapping



# Function to handle incoming connections
def handle_connection(conn):
    request = conn.recv(1024)
    response = web_page()
    conn.sendall(response)
    conn.close()

# Interrupt-Funktion um die aktiven LEDs blinken zu lassen
def LED_timer_interrupt(timer1):
    global LAST_STATE
    global led_status
    if LAST_STATE:
        LAST_STATE = False
        for i in range(len(led_status)):
            if led_status[i][HEADER_STATUS] == "on" :
                pixels[i*2] = parse_color(led_status[i][HEADER_COLOR])
                pixels[i*2+1] = parse_color(led_status[i][HEADER_COLOR])
            else:
                pixels[i*2] = (0, 0, 0)
                pixels[i*2+1] = (0, 0, 0)
    else:
        LAST_STATE = True
        for i in range(NUM_PIXELS):
            pixels[i] = (0, 0, 0)
    pixels.write()
    return []        

def button_interrupt(pin):
    def handle_interrupt(p):
        global PIN_PRESSED
        PIN_PRESSED = pin
    return handle_interrupt

buttons = []
for pin in BUTTON_PINS:
    button = machine.Pin(pin, machine.Pin.IN, machine.Pin.PULL_UP)
    buttons.append(button)
    button.irq(trigger=machine.Pin.IRQ_RISING, handler=button_interrupt(pin))

led_status = fetch_led_status()

# Interrupt-Konfiguration zum Blinkenlassen der LEDs. Die Raute vor den folgenden zwei Zeilen entfernen,
# wenn die LEDsblinken sollen
#timer1 = machine.Timer(0)
#timer1.init(period=1000, mode=machine.Timer.PERIODIC, callback=LED_timer_interrupt)

# Initialisierung der Webseite
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(('', 80))
s.listen(5)
s.setblocking(False)  # Set the socket to non-blocking mode
  


TICK = True
while True:
    # Wurde ein Taster gedrückt, wird die entsprechende Tasternummer (0-4) in der Variablen PIN_PRESSED gespeichert
    if (PIN_PRESSED > -1):
        #Gibt einen VALUE_COMPLETED zwischen 0 und 4 zurück, der die gedrückte Taste representiert
        button_index = BUTTON_PINS.index(PIN_PRESSED)
        print("ButtonIndex:", button_index )
        
        #In der Spalte „Row_ID“ im Blatt „LED_STATUS“ wird die Zeile der Aufgabe aus der Aufgabenliste gespeichert
        #Die folgende Zeile ruft das Google Apps-Skript auf, um in der Spalte COLUMN_COMPLETED den Status der oben genannten Aufgabe in „done“ zu ändern.
        WriteResponse = call_google_apps_script({HEADER_ROW_ID: led_status[button_index][HEADER_ROW_ID],HEADER_TASK_STATUS:VALUE_COMPLETED})
        print(WriteResponse.text)
        LED_UPDATE_NEEDED = True
        PIN_PRESSED = -1
        print(WriteResponse)

    # Abfrage des aktuellen Status aus dem Google Sheet "LED_Status" nach Ablauf der Zeit UPDATE_CYCLE. Damit Formelwerte neu berechnet werden, wird abwechselnd der
    # Wert Tick oder Tack in den Spalte Watchdog geschrieben. 
    if (time.time() - last_update) > UPDATE_CYCLE or LED_UPDATE_NEEDED:
        if TICK:
            str_tick = "TICK"
        else:
            str_tick = "TACK"
        WriteResponse = call_google_apps_script({HEADER_ROW_ID: "2",HEADER_WATCHDOG:str_tick})  #Call only needed to trigger data update in Google Sheet
        print(WriteResponse.text)
        TICK = not TICK
        led_status = fetch_led_status()
        print("LEDstatus: ", led_status)
        set_neopixel_colors(led_status)
        LED_UPDATE_NEEDED = False
        last_update = time.time()
        #print(led_states)


    time.sleep(1)
    print('.', end='')
    try:
        conn, addr = s.accept()  # Accept an incoming connection if available
        _thread.start_new_thread(handle_connection, (conn,))  # Start a new thread to handle the connection
    except OSError:
        pass

