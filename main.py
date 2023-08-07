import os
import telebot
import requests
import re
from telebot import types  # Імпортуємо класи для створення клавіатури
from config import TOKEN, FORM_API_KEY, YOUR_DOMAIN

bot = telebot.TeleBot(TOKEN)

# Створюємо клавіатуру з кнопками
keyboard = types.ReplyKeyboardMarkup(row_width=4, resize_keyboard=True)
buttons = [
    "/help", "/userid", "/server_info", "/size_rec",
    "/get_manager", "/pbx_peers", "/pbx_queue", "/last_calls"
]
keyboard.add(*buttons)

@bot.message_handler(commands=['start', 'help'])
def start(message):
    text_help='''Ось список наявних команд:
    /help - довідка по командам
    /userid - ID користувача
    /server_info - коротка інформація про сервер
    /size_rec - розмір папки з аудіозаписами
    /get_manager - дізнатися хто менеджер (salesdrive)
    /pbx_peers - активні внутрішні/зовнішній номера
    /pbx_queue - статистика менеджерів у черзі
    /last_calls - декілька останніх дзвінків'''
    bot.send_message(message.chat.id, f"Привіт!\nЯ телеграм бот 🤖 і можу надати деяку інформацію по серверу. \n{text_help}", reply_markup=keyboard)

@bot.message_handler(commands=['userid'])
def userid(message):
    user_id = message.from_user.id
    bot.send_message(message.chat.id, f"Ваш ID користувача: {user_id}")

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
    bot.send_message(message.chat.id, srv_info, parse_mode="HTML")


## Розмір директорії із записами розмови
@bot.message_handler(commands=['size_rec'])
def size_rec(message):
    mondir_size = os.popen("du -h --max-depth=2 /var/spool/asterisk/monitor/ | sort -k2").read().strip()
    bot.send_message(message.chat.id, f"<code>[ Розмір директорій із записами розмови ]\n\n{mondir_size}</code>", parse_mode="HTML")


## Список найбільших директорій
@bot.message_handler(commands=['big_dir'])
def big_dir(message):
    bigdir_size = os.popen("du -h -d2 --exclude=proc / | sort -k2 | egrep '^([0-9]{2,3}|[0-9]{1}.[0-9]{1})G'").read().strip()
    bot.send_message(message.chat.id, f"<code>[ Список найбільших директорій ]\n\n{bigdir_size}</code>", parse_mode="HTML")


## Пошук відповідального менеджера в CRM Sales Drive.
@bot.message_handler(commands=['get_manager'])
def get_manager(message):
    bot.send_message(message.chat.id, "Введіть номер телефону клієнта:")
    bot.register_next_step_handler(message, process_phone_number)

def normalize_phone_number(phone_number):
    # Удаление всех символов, кроме цифр, пробелов, круглых скобок и дефисов
    cleaned_number = re.sub(r'[^\d\s()\-.]', '', phone_number)
    
    # Извлечение только цифр из номера
    digits = re.sub(r'\D', '', cleaned_number)
    
    # Проверка наличия 9 цифр
    if len(digits) == 9:
        # Форматирование номера
        formatted_number = f'+380{digits}'
        print(formatted_number)
        return formatted_number
    else:
        return None
#bot.send_message(message.chat.id, "Невірний формат номера")
#get_manager()

def process_phone_number(message):
    normalized_number = normalize_phone_number(message.text)
    if normalized_number:
        headers = {"Form-Api-Key": "FORM_API_KEY"}
        url = f"https://YOUR_DOMAIN.salesdrive.me/api/get_manager_by_phone_number/?phone={normalized_number}"

        response = requests.get(url, headers=headers)
        data = response.json()

        if data["status"] == "success":
            manager = data["manager"]
            client = data["client"]
            manager_name = manager.get("name", "Невідомо")
            internal_number = manager.get("internal_number", "Невідомо")
            client_name = f"{client.get('fName', 'Unknown')} {client.get('lName', '')}"

            result_message = f"ФИО: {client_name}\nВідповідальний: {manager_name} [{internal_number}]"
            bot.send_message(message.chat.id, result_message)
        elif data["status"] == "error" and data["massage"] == "Not found.":
            bot.send_message(message.chat.id, "Немає заявок або контактів із цим номером.")
        else:
            bot.send_message(message.chat.id, "Неможливо отримати інформацію про менеджера.")
    else:
        bot.send_message(message.chat.id, "Некоректний номер телефону!")

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

    bot.send_message(message.chat.id, peers_info, parse_mode="HTML")


#"/pbx_queue"
@bot.message_handler(commands=['pbx_queue'])
def pbx_queue(message):
    queues = [510]
    for queue in queues:
        queue1 = os.popen(f"/usr/sbin/asterisk -rx'queue show {queue}' | head -n -1 | tail -n -3 | sed -e 's/([^()]*)//g' | awk '{{print $1, $5, $6}}'").read().strip()
        queue_info = f"<code>[  Статистика черги {queue}  ]\n {queue1} </code>"
        bot.send_message(message.chat.id, queue_info, parse_mode="HTML")


#"/last_calls"


def main():
    bot.polling(none_stop=True)

if __name__ == '__main__':
    main()

