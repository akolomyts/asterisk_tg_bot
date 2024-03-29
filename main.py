# import os
import os
import telebot
import requests
import re
from telebot import types  # Імпортуємо класи для створення клавіатури
from config import TOKEN, FORM_API_KEY, YOUR_DOMAIN, PBX_QUEUES
import datetime

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


def process_phone_number(message):
    usertext = message.text.strip()
    handle_commands(message)
    #if usertext.startswith('/'):
    #    bot.reply_to(message, "Ви ввели некоректні дані. Будь ласка, введіть правильний номер телефону.")
    #    return
    usertext = normalize_phone_number(message.text)
    try:
        if usertext:
            headers = {"Form-Api-Key": FORM_API_KEY}
            url = f"https://{YOUR_DOMAIN}.salesdrive.me/api/get_manager_by_phone_number/?phone={usertext}"

            response = requests.get(url, headers=headers)
            data = response.json()

            if data["status"] == "success":
                if "manager" in data:
                    manager = data["manager"]
                    if manager is not None:  # Проверяем, что значение ключа 'manager' не равно None
                        manager_name = manager.get("name", "Невідомо")
                        internal_number = manager.get("internal_number", "Невідомо")
                    else:
                        manager_name = "Невідомо"
                        internal_number = "Невідомо"
                else:
                    manager_name = "Невідомо"
                    internal_number = "Невідомо"

                if "client" in data:
                    client = data["client"]
                    client_name = f"{client.get('fName', 'Unknown')} {client.get('lName', '')}"
                else:
                    client_name = "Невідомо"

                result_message = f"ПІБ: {client_name}\nВідповідальний: {manager_name} [{internal_number}]"
                bot.reply_to(message, result_message, reply_markup=kb_main)
            elif data["status"] == "error" and data["massage"] == "Not found.":
                bot.reply_to(message, "Немає заявок або контактів із цим номером.", reply_markup=kb_main)
            else:
                bot.reply_to(message, "Error. Неможливо отримати інформацію про менеджера.", reply_markup=kb_main)
    #    else:
    #       bot.reply_to(message, "Некоректний номер телефону!!!!", reply_markup=kb_main)
    except Exception as e:
        print(f"Request to the Telegram API was with error: {e}")

def normalize_phone_number(usertext):
    cleaned_number = re.sub(r'^(?:\+?380|0)(\(\)\s-)$', '', usertext)
    digits = re.sub(r'\D', '', cleaned_number)

    if len(digits) == 12:
        formatted_number = f'+{digits}'
        return formatted_number
    elif len(digits) == 10:
        formatted_number = f'+38{digits}'
        return formatted_number
    else:
        return None


# Запис повідомленнь
@bot.message_handler(commands=['help', 'userid', 'server_info', 'size_rec', 'big_dir', 'get_manager', 'pbx_peers', 'pbx_queue', 'last_calls'])
def handle_commands(message):
    current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(log_file_path, 'a') as log_file:
        log_file.write(f"{current_time}\t{message.from_user.id}\t{message.text}\n")

    ## Старт або додівка по боту
    if message.text.startswith('/help'):
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

    ## ІД користувача
    elif message.text.startswith('/userid'):
        user_id = message.from_user.id
        bot.reply_to(message, f"Ваш ID користувача: {user_id}", reply_markup=kb_main)

    ## Коротка інформація про сервер
    elif message.text.startswith('/server_info'):
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
    elif message.text.startswith('/size_rec'):
        mondir_size = os.popen("du -h --max-depth=2 /var/spool/asterisk/monitor/ | sort -k2").read().strip()
        bot.reply_to(message, f"<code>[ Розмір директорій із записами розмови ]\n\n{mondir_size}</code>", parse_mode="HTML", reply_markup=kb_adm)

    ## Список найбільших директорій
    elif message.text.startswith('/big_dir'):
        bot.send_message(message.chat.id, f"Йде підрахунок. Зачекайте будь-ласка", parse_mode="HTML", reply_markup=kb_adm)
        bigdir_size = os.popen("du -h -d2 --exclude=proc / | sort -k2 | egrep '^([0-9]{2,3}|[0-9]{1}.[0-9]{1})G'").read().strip()
        bot.reply_to(message, f"<code>[ Список найбільших директорій ]\n\n{bigdir_size}</code>", parse_mode="HTML", reply_markup=kb_adm)

    ## Пошук відповідального менеджера в CRM Sales Drive.
    elif message.text.startswith('/get_manager'):
        bot.reply_to(message, "Введіть номер телефону клієнта:")
        bot.register_next_step_handler(message, process_phone_number)

    ## /pbx_peers
    elif message.text.startswith('/pbx_peers'):
        peers1 = os.popen("/usr/sbin/asterisk -rx'sip show peers' | grep \"^380\"  | awk '{print $1\"\\t\"$2\"\\t\"$7\"\\t\"$8\" \"$9}' | awk -F'/' '{print $2}' | awk '{print \"[SIM \"NR\"]\", $0}'").read().strip()
        peers2 = os.popen("/usr/sbin/asterisk -rx'pjsip show contacts'| grep sip | sed 's/Contact:\\s*//; s/[0-9]*;ob.*[[:xdigit:]]\\s//g' | sed 's/Avail/OK/' | sed -E 's/(\\.[0-9]+)$/ms/' | awk -F'[/@: ]' '{ print \"[\"$5\"]\\t\"$6\"\\t\"$7\"\\t(\"$15\")\"}'").read().strip()
        
        peers_info = """[  Статус номерів GSM  ]\n\n<code>{}</code>\n
[  Статус внутрішніх номерів АТС  ]\n\n<code>{}</code>
        """.format(peers1, peers2)
        bot.reply_to(message, peers_info, parse_mode="HTML", reply_markup=kb_adm)

    ## /pbx_queue
    elif message.text.startswith('/pbx_queue'):
        queues = PBX_QUEUES
        for queue in queues:
            queue1 = os.popen(f"/usr/sbin/asterisk -rx'queue show {queue}' | grep {queue}  | awk -F',' '{{print $4, $5, $6}}'").read().strip()
            queue2 = os.popen(f"/usr/sbin/asterisk -rx'queue show {queue}' | grep -i Local | sed -e 's/([^()]*)//g' | awk '{{print $1, \"\\t\", $5, \"\\t\", $6}}'").read().strip()
            queue_info = f"<code>[  Статистика черги {queue}  ]\n\n{queue1}</code>\n\n{queue2}"
            bot.reply_to(message, queue_info, parse_mode="HTML", reply_markup=kb_adm)

    ## /last_calls 
    elif message.text.startswith('/last_calls'):
        bot.reply_to(message, f"Функція у розробці", parse_mode="HTML", reply_markup=kb_main)

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    if message.text == "admin_cmd":
        bot.reply_to(message, "admin_cmd", reply_markup=kb_adm)
    elif message.text == "⬅️ back":
        bot.reply_to(message, text="back", reply_markup=kb_main)
    else:
        process_phone_number(message)

def main():
    bot.polling(none_stop=True)

if __name__ == '__main__':
    main()

