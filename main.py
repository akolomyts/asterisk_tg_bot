import os
import telebot
import requests
import re
from telebot import types  # Імпортуємо класи для створення клавіатури
from config import TOKEN, FORM_API_KEY, YOUR_DOMAIN, PBX_QUEUES

bot = telebot.TeleBot(TOKEN)

# Шлях до файлу, до якого записуватимуться повідомлення
log_file_path = 'messages_log.txt'

# Створюємо клавіатуру з кнопками
kb_main = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
main_bts = ["/get_manager", "/last_calls", "admin_cmd"]
kb_main.add(*main_bts)

kb_adm = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
adm_bts = ["/server_info", "/size_rec", "/big_dir",
           "/pbx_peers", "/pbx_queue","⬅️ back"]
kb_adm.add(*adm_bts)
            
@bot.message_handler(commands=['start', 'help'])
def start(message):
    text_help='''Ось список наявних команд:
    /help - довідка по командам
    /userid - ID користувача
    /server_info - коротка інформація про сервер
    /size_rec - розмір папки з аудіозаписами
    /big_dir - найбільші за рзміром директорії
    /get_manager - дізнатися хто менеджер (salesdrive)
    /pbx_peers - активні внутрішні/зовнішній номера
    /pbx_queue - статистика менеджерів у черзі
    /last_calls - декілька останніх дзвінків'''
    bot.reply_to(message, f"Привіт!\nЯ телеграм бот 🤖 і можу надати деяку інформацію по серверу. \n{text_help}", reply_markup=kb_main)

@bot.message_handler(commands=['userid'])
def userid(message):
    user_id = message.from_user.id
    bot.reply_to(message, f"Ваш ID користувача: {user_id}", reply_markup=kb_main)

## Коротка інформація про сервер
@bot.message_handler(commands=['server_info'])
def server_info(message):
    hostname = os.popen("hostname").read().strip()
    system_load = os.popen("cat /proc/loadavg | cut -d \" \" -f1").read().strip()
    number_of_processes = os.popen("ps aux | wc -l").read().strip()
    disk_usage0 = os.popen("/bin/df -Th / 2>/dev/null | tail -n 1 | awk '{ print $6 }'").read().strip()
    disk_usage1 = os.popen("/bin/df -Th / 2>/dev/null | tail -n 1 | awk '{ print $3 }'").read().strip()
    number_of_logged_in_users = os.popen("users | wc -w").read().strip()
    memory_usage0 = os.popen("free | awk 'FNR == 2 {printf(\"%.0f%%\", (($3+$5)*100/$2))}'").read().strip()
    memory_usage1 = os.popen("free -h | awk 'FNR == 2 {print $2}'").read().strip()
    system_uptime = os.popen("uptime | sed 's/.*up \\([^,]*\\), .*/\\1/'").read().strip()
    ip_address = os.popen("hostname -I | awk '{print $1}'").read().strip()

    srv_info = """
    <code>[  {} Server info  ]</code>
    
    System load: {}
    Process: {}
    Disk usage of '/' partition: {} of {}
    Number of users logged in: {}
    Memory usage: {} of {}
    System uptime: {}
    IP address: {}
    """.format(hostname, system_load, number_of_processes, disk_usage0, disk_usage1, number_of_logged_in_users, memory_usage0, memory_usage1, system_uptime, ip_address)

    # Send the message to the user
    bot.reply_to(message, srv_info, parse_mode="HTML", reply_markup=kb_adm)


## Розмір директорії із записами розмови
@bot.message_handler(commands=['size_rec'])
def size_rec(message):
    mondir_size = os.popen("du -h --max-depth=2 /var/spool/asterisk/monitor/ | sort -k2").read().strip()
    bot.reply_to(message, f"<code>[ Розмір директорій із записами розмови ]\n\n{mondir_size}</code>", parse_mode="HTML", reply_markup=kb_adm)


## Список найбільших директорій
@bot.message_handler(commands=['big_dir'])
def big_dir(message):
    bigdir_size = os.popen("du -h -d2 --exclude=proc / | sort -k2 | egrep '^([0-9]{2,3}|[0-9]{1}.[0-9]{1})G'").read().strip()
    bot.reply_to(message, f"<code>[ Список найбільших директорій ]\n\n{bigdir_size}</code>", parse_mode="HTML", reply_markup=kb_adm)


## Пошук відповідального менеджера в CRM Sales Drive.
@bot.message_handler(commands=['get_manager'])
def get_manager(message):
    bot.reply_to(message, "Введіть номер телефону клієнта:")
    bot.register_next_step_handler(message, process_phone_number)

def process_phone_number(message):
    phone_number = message.text.strip()
    if phone_number.startswith('/'):
        bot.reply_to(message, "Ви ввели некоректні дані. Будь ласка, введіть правильний номер телефону.")
        return
    phone_number = normalize_phone_number(message.text)
    if phone_number:
        headers = {"Form-Api-Key": FORM_API_KEY}
        url = f"https://{YOUR_DOMAIN}.salesdrive.me/api/get_manager_by_phone_number/?phone={phone_number}"

        response = requests.get(url, headers=headers)
        data = response.json()

        if data["status"] == "success":
            manager = data["manager"]
            client = data["client"]
            manager_name = manager.get("name", "Невідомо")
            internal_number = manager.get("internal_number", "Невідомо")
            client_name = f"{client.get('fName', 'Unknown')} {client.get('lName', '')}"

            result_message = f"ПІБ: {client_name}\nВідповідальний: {manager_name} [{internal_number}]"
            bot.reply_to(message, result_message, reply_markup=kb_main)
        elif data["status"] == "error" and data["massage"] == "Not found.":
            bot.reply_to(message, "Немає заявок або контактів із цим номером.", reply_markup=kb_main)
        else:
            bot.reply_to(message, "Неможливо отримати інформацію про менеджера.", reply_markup=kb_main)
    else:
        bot.reply_to(message, "Некоректний номер телефону!", reply_markup=kb_main)

def normalize_phone_number(phone_number):
    cleaned_number = re.sub(r'^(?:\+?380|0)(\(\)\s-)$', '', phone_number)
    digits = re.sub(r'\D', '', cleaned_number)

    if len(digits) == 12:
        formatted_number = f'+{digits}'
        return formatted_number
    elif len(digits) == 10:
        formatted_number = f'+38{digits}'
        return formatted_number
    else:
        return None

#"/pbx_peers"
@bot.message_handler(commands=['pbx_peers'])
def pbx_peers(message):
    peers1 = os.popen("/usr/sbin/asterisk -rx'sip show peers' | grep \"^380\"  | awk '{print $1\"\\t\"$2\"\\t\"$7\"\\t\"$8\" \"$9}' | awk -F'/' '{print $2}' | awk '{print \"[SIM \"NR\"]\", $0}'").read().strip()
    peers2 = os.popen("/usr/sbin/asterisk -rx'pjsip show contacts'| grep sip | sed 's/Contact:\\s*//; s/[0-9]*;ob.*[[:xdigit:]]\\s//g' | sed 's/Avail/OK/' | sed -E 's/(\\.[0-9]+)$/ms/' | awk -F'[/@: ]' '{ print \"[\"$5\"]\\t\"$6\"\\t\"$7\"\\t(\"$15\")\"}'").read().strip()

    peers_info = """
<code>[  Статус номерів GSM  ]

{}

[  Статус внутрішніх номерів АТС  ]

{}</code>
  """.format(peers1, peers2)

    bot.reply_to(message, peers_info, parse_mode="HTML", reply_markup=kb_adm)


#"/pbx_queue"
@bot.message_handler(commands=['pbx_queue'])
def pbx_queue(message):
    queues = PBX_QUEUES
    for queue in queues:
        queue1 = os.popen(f"/usr/sbin/asterisk -rx'queue show {queue}' | grep {queue}  | awk -F',' '{{print $4, $5, $6}}'").read().strip()
        queue2 = os.popen(f"/usr/sbin/asterisk -rx'queue show {queue}' | grep -i Local | sed -e 's/([^()]*)//g' | awk '{{print $1, \"\\t\", $5, \"\\t\", $6}}'").read().strip()
        queue_info = f"<code>[  Статистика черги {queue}  ]\n\n{queue1}</code>\n\n{queue2}"
        bot.reply_to(message, queue_info, parse_mode="HTML", reply_markup=kb_adm)


#"/last_calls"



@bot.message_handler()
def get_user_text(message):
    if message.text == "admin_cmd":
        bot.reply_to(message, "admin_cmd", reply_markup=kb_adm)
    elif message.text == "⬅️ back":
        bot.reply_to(message, text="back", reply_markup=kb_main)



@bot.message_handler(func=lambda message: True)
def log_messages(message):
    with open(log_file_path, 'a') as log_file:
        log_file.write(f"User {message.from_user.id}: {message.text}\n")


def main():
    bot.polling(none_stop=True)

if __name__ == '__main__':
    main()

