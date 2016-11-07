import telebot
import requests
import re
import MySQLdb
import time

from datetime import datetime
from telebot import types
from telebot import util
from bs4 import BeautifulSoup

# data sources
TODAY_URL = "http://donantesmalaga.org"
INCOMING_URL = "http://donantesmalaga.org/donar/proximas-colectas-en-malaga"

# database connection settings
DB_HOST="<TYPE DB HOST HERE>"
DB_USER="<TYPE DB USER HERE>"
DB_PASSWORD="<TYPE DB PASSWORD HERE>"
DB_NAME="<TYPE DB NAME HERE>"

bot = telebot.TeleBot("<TYPE YOUR BOT API TOKEN HERE>")

last_cached_date_today = ""
today_info_cached = ""
last_cached_date_incoming = ""
incoming_info_cached = ""

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    '''
    Display the commands and what are they intended for.
    '''
    bot.reply_to(message, build_help_message())
    markup = types.ReplyKeyboardMarkup()
    item_dondehoy = types.KeyboardButton('/dondehoy')
    item_dondeproximamente = types.KeyboardButton('/dondeproximamente')
    item_hedonadohoy = types.KeyboardButton('/hedonadohoy')
    item_puedodonar = types.KeyboardButton('/puedodonar')
    markup.row(item_dondehoy, item_dondeproximamente)
    markup.row(item_hedonadohoy, item_puedodonar)
    bot.send_message(message.chat.id, "\n\nPara continuar escribe un comando o seleccionalo directamente del menu inferior.", reply_markup=markup)

@bot.message_handler(commands=['dondehoy'])
def get_locations_today(message):
    '''
    Retrieve data about where and at what time to donate today.
    '''
    bot.send_chat_action(message.chat.id, 'typing')
    global last_cached_date_today
    global today_info_cached
    today_str = time.strftime("%d/%m/%Y")
    if len(last_cached_date_today) == 0 or last_cached_date_today != today_str:
        # get today's page, parse it and cache it
        today_info = download_locations_today()
        if len(today_info) > 0:
            # send info
            bot.reply_to(message, to_string(today_info))
            # update last cached date for today
            last_cached_date_today = today_str
            today_info_cached = today_info
        else:
            # prevent caching data if no data was retrieved
            bot.reply_to(message, "Parece que hoy no se puede donar (o los datos aun no ha sido publicados)")
    else:
        # return cached data
        bot.reply_to(message, to_string(today_info_cached))
        print("Returned today info from cache")

@bot.message_handler(commands=['dondeproximamente'])
def get_incoming_locations(message):
    '''
    Retrieve data about where and when to donate in the incoming days.
    '''
    chat_id = message.chat.id
    bot.send_chat_action(chat_id, 'typing')
    global last_cached_date_incoming
    global incoming_info_cached
    today_str = time.strftime("%d/%m/%Y")
    if len(last_cached_date_incoming) == 0 or last_cached_date_incoming != today_str:
        # get incoming's page, parse it and cache it
        incoming_info = download_locations_incoming()
        # send info
        send_message_splitting_if_necessary(chat_id, incoming_info)
        # update las cached date for incoming
        last_cached_date_incoming = today_str
        incoming_info_cached = incoming_info
    else:
        # return cached data
        send_message_splitting_if_necessary(chat_id, incoming_info_cached)
        print("Returned incoming info from cache")
    
@bot.message_handler(commands=['hedonadohoy'])
def create_donation_checkpoint(message):
    '''
    Persist that the user donated today so that the period of 2 months for next donation starts counting.
    '''
    execute_insert("INSERT INTO donations (user_id, last_donation_unix_timestamp, notified) VALUES({0}, UNIX_TIMESTAMP(), 0) ON DUPLICATE KEY UPDATE user_id={0}, last_donation_unix_timestamp=UNIX_TIMESTAMP(), notified=0".format(message.from_user.id))
    bot.reply_to(message, "De acuerdo, queda anotado que has donado el {0}".format(time.strftime("%d/%m/%Y")))
    
@bot.message_handler(commands=['puedodonar'])
def can_donate_today(message):
    '''
    Check whether the donor can donate or not based on the last donation date and the fact that more than 2 month should have passed.
    '''
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT FROM_UNIXTIME(last_donation_unix_timestamp, '%d/%m/%Y') FROM donations WHERE user_id={0}".format(message.from_user.id))
    row = cursor.fetchone()
    if cursor.rowcount > 0:
        last_donation_str = row[0]
        last_donation_date = datetime.strptime(last_donation_str, "%d/%m/%Y").date()
        current_date = datetime.now().date()
        days_elapsed = (current_date - last_donation_date).days
        if days_elapsed > 60:
            bot.reply_to(message, "Si, puedes donar. Ya han pasado dos meses desde la ultima vez que donaste el {0} (han pasado {1} dias)".format(last_donation_str, days_elapsed))
        else:
            bot.reply_to(message, "No, aun no puedes donar. No han pasado dos meses desde la ultima vez que donaste el {0} (solo han pasado {1} dias).".format(last_donation_str, days_elapsed))
    else:
       bot.reply_to(message, "No se si puedes donar porque no tengo constancia de cuando fue la ultima vez que lo hiciste.") 
    cursor.close()
    connection.close()

def parse_today_page(html):
    '''
    Parses today info HTML page
    '''
    today_data = []
    soup = BeautifulSoup(html, "lxml")
    table = soup.find('table')
    table_body = table.find('tbody')
    rows = table_body.find_all('tr')[2:-1]
    for row in rows:
        columns = row.find_all('td')
        location = columns[1].text.title().strip()
        info = parse_info_column(columns[2])
        today_data.append({'location': location, 'start': info['start'], 'end': info['end'], 'description': info['info']})
    
    return today_data

def parse_incoming_page(html):
    '''
    Parses incoming info HTML page
    '''
    today_str = time.strftime("%d/%m/%Y")
    parsed_string = "Proximamente puedes donar en los siguientes lugares:\n\n"
    soup = BeautifulSoup(html, "lxml")
    table = soup.find('table')
    rows = table.find_all('tr')[2:-1]
    for row in rows:
        columns = row.find_all('td')
        date = columns[0].text.strip()
        if date == today_str:
            continue # Ignores the line if incoming date is today
        location = columns[1].text.title().strip()
        info = parse_info_column(columns[2])
        parsed_string += "- {0}: {1} ({2})\n".format(date, info['info'], location)
    
    return parsed_string

def parse_info_column(info):
    '''
    Parses the info column by removing line feeds and the date in human readable format
    '''
    titled = info.text.title()
    # remove line feeds from description
    no_linefeeds = titled.replace("\n", " ")
    # remove date from the description
    no_date = re.sub(r'^(\W*\w+\W*){3}', '', no_linefeeds)
    # extract start/end time
    match = re.match(r'.*De (\d+) A (\d+) Horas', no_date)
    start_time = match.group(1)
    end_time = match.group(2)
    # extracts data
    match = re.match(r'.*\((.*)\).*', no_date)
    if match is None:
        # Brackets not found, no tansformation needed
        info = no_date
    else:
        real_location = match.group(1)
        info = "{0} De {1} A {2}".format(real_location, start_time, end_time)
    return {'start': start_time, 'end': end_time, 'info': info}
    
def send_message_splitting_if_necessary(chat_id, long_text):
    '''
    Sends message expected to be long by smartly splitting it
    '''
    lines = long_text.split('\n')
    current_text = ""
    for line in lines:
        current_text += line + '\n'
        if len(current_text) > 3000:
            bot.send_message(chat_id, current_text)
            current_text = ""

def get_db_connection():
    '''
    Helper method to establish db connection
    '''
    return MySQLdb.connect(host=DB_HOST, user=DB_USER, passwd=DB_PASSWORD, db=DB_NAME)

def execute_insert(statement):
    '''
    Executes db insert statement with all the boiler-plate code solved
    '''
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute(statement)
    connection.commit()
    cursor.close()
    connection.close()

def download_locations_today():
    '''
    Download today info page and parses it to a string
    '''
    r = requests.get(TODAY_URL)
    if r.status_code == 200:
        return parse_today_page(r.text)
    else:
        return "Parece que esa informacion no esta disponible en estos momentos. \
        Por favor, intentalo de nuevo mas tarde"

def download_locations_incoming():
    '''
    Download incoming info page and parses it to a (large) string
    '''
    r = requests.get(INCOMING_URL)
    if r.status_code == 200:
        return parse_incoming_page(r.text)
    else:
        return "Hummm, parece que esa informacion no esta disponible en estos momentos. \
        Por favor, intentalo de nuevo mas tarde"
        
def to_string(spots):
    '''
    Print data in human readable format, adding metadata when useful.
    '''
    current_hour = int(time.strftime("%H")) + 1
    string = "Hoy puedes donar en los siguientes lugares:\n\n"
    for spot in spots:
        status = calculate_status(current_hour, int(spot['start']), int(spot['end']))
        string += "- {0} ({1}) [{2}]\n".format(spot['description'], spot['location'], status)
    
    return string
    
def calculate_status(current_hour, start, finish):
    '''
    Calculates the status of a donation spot based on the current time and the spot start/finish times.
    '''
    if current_hour < start:
        time_to_start = start - current_hour
        if time_to_start > 0:
            return "Faltan {0} horas".format(time_to_start)
        else:
            return "Empieza en breve"
    elif current_hour < finish:
        time_left = finish - current_hour
        if time_left > 0:
            return "Disponible, termina en {0} horas".format(time_left)
        else:
            return "Disponible, termina en breve"
    else:
        return "Ya ha finalizado"

def build_help_message():
    '''
    Helper method to build the bot help message
    '''
    return "\n \
DonantesMalagaBot facilita informacion a los donantes de Malaga acerca de los lugares donde se puede donar en el dia de hoy o en los proximos dias.\n \
\n \
Los comandos para interactuar con el bot son: \n \
\n \
/dondehoy - conocer los puntos de donacion en el dia de hoy y los horarios \n \
/dondeproximamente - conocer los puntos de donacion en los proximos dias \n \
/hedonadohoy - hoy he donado sangre, asi que quiero recibir una notificacion cuando pueda volver a donar \n \
/puedodonar - permite saber si puedo donar hoy en base a la fecha de ultima donacion conocida \n \
\n"
    
while True:
    try:
        bot.polling(none_stop=True)
    except:
        print("Telegram API timeout happened")