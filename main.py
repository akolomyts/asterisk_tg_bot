import os
import telebot
import requests
from telebot import types  # Импортируем классы для создания клавиатур
#from kb import kb_main, kb_status, kb_command, gen_markup

# Получаем значение токена из переменных окружения
TOKEN = "6395262263:AAEZRhi9tYytq8sEZ0lOvh1tYad016nAHFo"

# Создаем объект бота
bot = telebot.TeleBot(TOKEN)

# Создаем клавиатуру с кнопками
keyboard = types.ReplyKeyboardMarkup(row_width=4, resize_keyboard=True)
buttons = [
    "/help", "/userid", "/server_info", "/size_rec",
    "/get_manager", "/pbx_peers", "/pbx_queue", "/last_calls",
    "/get_manager", "/pbx_peers", "/pbx_queue", "/last_calls"
]
keyboard.add(*buttons)

@bot.message_handler(commands=['start', 'help'])
def start(message):
    text_help='''Cписок доступных команд:
    /help - справка по командам
    /userid - id пользователя
    /server_info - краткая информация о сервере
    /size_rec - размер папки с аудиозаписями
    /get_manager - узнать кто менеджер (salesdrive)
    /pbx_peers - активные внутренние/внешине номера
    /pbx_queue - статистика менеджеров в очереди
    /last_calls - несколько последних звонков'''
    bot.send_message(message.chat.id, f"Привет!\nЯ бот 🤖 для управления сервером. Вот доступные команды: \n{text_help}", reply_markup=keyboard)

@bot.message_handler(commands=['userid'])
def userid(message):
    user_id = message.from_user.id
    bot.send_message(message.chat.id, f"Ваш ID пользователя: {user_id}")

## Краткая информацио о сервере
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

    # Build the message
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


## Размер директории с записями разговора
@bot.message_handler(commands=['size_rec'])
def size_rec(message):
    mondir_size = os.popen("du -h --max-depth=2 /var/spool/asterisk/monitor/ | sort -k2").read().strip()
    bot.send_message(message.chat.id, f"<code>[ Размер директорий с записями разговора ]\n\n{mondir_size}</code>", parse_mode="HTML")


## Список наибОльших директорий
@bot.message_handler(commands=['big_dir'])
def big_dir(message):
    bigdir_size = os.popen("du -h -d2 --exclude=proc / | sort -k2 | egrep '^([0-9]{2,3}|[0-9]{1}.[0-9]{1})G'").read().strip()
    bot.send_message(message.chat.id, f"<code>[ Список наибОльших директорий ]\n\n{bigdir_size}</code>", parse_mode="HTML")


## Поиск ответственного менеджера в CRMке Sales Drive.
@bot.message_handler(commands=['get_manager'])
def get_manager(message):
    bot.send_message(message.chat.id, "Введите номер телефона:")
    bot.register_next_step_handler(message, process_phone_number)

def process_phone_number(message):
    phone_number = message.text
    headers = {"Form-Api-Key": "jS1dfsEWv8qofWtrNXCjCLg2nZFruAaukOAtLFAuKNJ3_LXcQuGx6diFGEQshncSt2kPmr"}
    url = f"https://proftechnika.salesdrive.me/api/get_manager_by_phone_number/?phone={phone_number}"

    response = requests.get(url, headers=headers)
    data = response.json()

    if data["status"] == "success":
        manager = data["manager"]
        client = data["client"]
        manager_name = manager.get("name", "Неизвестно")
        internal_number = manager.get("internal_number", "Неизвестно")
        client_name = f"{client.get('fName', 'Unknown')} {client.get('lName', '')}"

        result_message = f"ФИО: {client_name}\nОтветственный: {manager_name} [{internal_number}]"
        bot.send_message(message.chat.id, result_message)
    elif data["status"] == "error" and data["massage"] == "Not found.":
        bot.send_message(message.chat.id, "Нет заявок или контактов с этим номером.")
    else:
        bot.send_message(message.chat.id, "Не удалось получить информацию о менеджере.")

#"/pbx_peers"
@bot.message_handler(commands=['pbx_peers'])
def pbx_peers(message):
    peers1 = os.popen("/usr/sbin/asterisk -rx'sip show peers' | grep \"^380\"  | awk '{print $1\"\\t\"$2\"\\t\"$7\"\\t\"$8\" \"$9}' | awk -F'/' '{print $2}' | awk '{print \"[SIM \"NR\"]\", $0}'").read().strip()
    peers2 = os.popen("/usr/sbin/asterisk -rx'pjsip show contacts'| grep sip | sed 's/Contact:\\s*//; s/[0-9]*;ob.*[[:xdigit:]]\\s//g' | sed 's/Avail/OK/' | sed -E 's/(\\.[0-9]+)$/ms/' | awk -F'[/@: ]' '{ print \"[\"$5\"]\\t\"$6\"\\t\"$7\"\\t(\"$15\")\"}'").read().strip()

    peers_info = """
<code>[  Статус номерів GSM  ]

{}

[  Статус вн номерів АТС  ]

{}</code>
  """.format(peers1, peers2)

    bot.send_message(message.chat.id, peers_info, parse_mode="HTML")


#"/pbx_queue"
@bot.message_handler(commands=['pbx_queue'])
def pbx_queue(message):
    queues = [510]
    for queue in queues:
#        queue1 = os.popen("/usr/sbin/asterisk -rx"queue show {queue}" | head -n -1 | tail -n -3 | sed -e 's/([^()]*)//g' | awk '{print $1, $5, $6}'").read().strip()
        queue1 = os.popen(f"/usr/sbin/asterisk -rx'queue show {queue}' | head -n -1 | tail -n -3 | sed -e 's/([^()]*)//g' | awk '{{print $1, $5, $6}}'").read().strip()
        queue_info = f"<code>[  Статистика черги {queue}  ]\n {queue1} </code>"
        bot.send_message(message.chat.id, queue_info, parse_mode="HTML")


#"/last_calls"


def main():
    bot.polling(none_stop=True)

if __name__ == '__main__':
    main()

