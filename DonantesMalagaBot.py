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
    bot.send_chat_action(message.chat.id, 'typing')
    global last_cached_date_today
    global today_info_cached
    today_str = time.strftime("%d/%m/%Y")
    if len(last_cached_date_today) == 0 or last_cached_date_today != today_str:
        # get today's page, parse it and cache it
        today_info = download_locations_today()
        if len(today_info) > 0:
            # send info
            bot.reply_to(message, today_info)
            # update last cached date for today
            last_cached_date_today = today_str
            today_info_cached = today_info
        else:
            # prevent caching data if no data was retrieved
            bot.reply_to(message, "Parece que hoy no se puede donar (o los datos aun no ha sido publicados)")
    else:
        # return cached data
        bot.reply_to(message, today_info_cached)
        print("Returned today info from cache")

@bot.message_handler(commands=['dondeproximamente'])
def get_incoming_locations(message):
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
    execute_insert("INSERT INTO donations (user_id, last_donation_unix_timestamp, notified) VALUES({0}, UNIX_TIMESTAMP(), 0) ON DUPLICATE KEY UPDATE user_id={0}, last_donation_unix_timestamp=UNIX_TIMESTAMP(), notified=0".format(message.from_user.id))
    bot.reply_to(message, "De acuerdo, queda anotado que has donado el {0}".format(time.strftime("%d/%m/%Y")))
    
@bot.message_handler(commands=['puedodonar'])
def can_donate_today(message):
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
    close_db_connection(connection)

# Parses today info HTML page
def parse_today_page(html):
    parsed_string = ""
    soup = BeautifulSoup(html, "lxml")
    table = soup.find('table')
    table_body = table.find('tbody')
    rows = table_body.find_all('tr')[2:-1]
    for row in rows:
        columns = row.find_all('td')
        location = parse_location_column(columns[1])
        info = parse_info_column(columns[2])
        parsed_string += "- {0} ({1})\n".format(info, location)
    
    if len(parsed_string) == 0:
        return "";
    else:
        return "Hoy puedes donar en los siguientes lugares:\n\n" + parsed_string

# Parses incoming info HTML page
def parse_incoming_page(html):
    parsed_string = "Proximamente puedes donar en los siguientes lugares:\n\n"
    soup = BeautifulSoup(html, "lxml")
    table = soup.find('table')
    rows = table.find_all('tr')[2:-1]
    for row in rows:
        columns = row.find_all('td')
        date = columns[0].text.strip()
        location = parse_location_column(columns[1])
        info = parse_info_column(columns[2])
        parsed_string += "- {0}: {1} ({2})\n".format(date, info, location)
    
    return parsed_string

# Parses the location column by just stripping it
def parse_location_column(location):
    return location.text.title().strip()

# Parses the info column by removing line feeds and the date in human readable format
def parse_info_column(info):
    titled = info.text.title()
    no_date = re.sub(r'^(\W*\w+\W*){3}', '', titled)
    no_linefeeds = no_date.replace("\n", " ")
    return no_linefeeds
    
# Sends message expected to be long by smartly splitting it
def send_message_splitting_if_necessary(chat_id, long_text):
    lines = long_text.split('\n')
    current_text = ""
    for line in lines:
        current_text += line + '\n'
        if len(current_text) > 3000:
            bot.send_message(chat_id, current_text)
            current_text = ""

# Helper method to establish db connection
def get_db_connection():
    return MySQLdb.connect(host=DB_HOST, user=DB_USER, passwd=DB_PASSWORD, db=DB_NAME)
    
# Helper method to close db connection
def close_db_connection(connection):
    connection.close()

# Executes db insert statement with all the boiler-plate code solved
def execute_insert(statement):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute(statement)
    connection.commit()
    cursor.close()
    close_db_connection(connection)

# Downloads today info page and parses it to a string
def download_locations_today():
    r = requests.get(TODAY_URL)
    if r.status_code == 200:
        return parse_today_page(r.text)
    else:
        return "Parece que esa informacion no esta disponible en estos momentos. \
        Por favor, intentalo de nuevo mas tarde"

# Donwnload incoming info page and parses it to a (large) string
def download_locations_incoming():
    r = requests.get(INCOMING_URL)
    if r.status_code == 200:
        return parse_incoming_page(r.text)
    else:
        return "Hummm, parece que esa informacion no esta disponible en estos momentos. \
        Por favor, intentalo de nuevo mas tarde"

# Helper method to build the bot help message
def build_help_message():
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
    
bot.polling(none_stop=True)