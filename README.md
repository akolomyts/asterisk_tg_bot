# asterisk_tg_bot
asterisk_tg_bot

## functions
"/help", "/userid", "/server_info", "/size_rec",
"/get_manager", "/pbx_peers", "/pbx_queue", "/last_calls"

## Install
- cd /srv
- git clone https://github.com/akolomyts/asterisk_tg_bot.git
- cp ./telegram-bot.service /etc/systemd/system/
- systemctl daemon-reload
- systemctl restart telegram-bot.service
