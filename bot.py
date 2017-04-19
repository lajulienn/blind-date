import config
from collections import deque
import shelve
import telebot

bot = telebot.TeleBot(config.token)

opened_dialogues = shelve.open(config.opened_dialogues_db)
closed_dialogues = shelve.open(config.closed_dialogues_db)
waiting_queue = deque()


@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, 'Finding a partner for you...')
    if message.chat.id in opened_dialogues:
        return
    if waiting_queue.empty() or closed_dialogues[message.chat.id] == waiting_queue.index(0):
        waiting_queue.append(message.chat.id)
    else:
        first = message.chat.id
        second = waiting_queue.popleft()
        opened_dialogues[first] = second
        opened_dialogues[second] = first
        del closed_dialogues[first]
        del closed_dialogues[second]
        bot.send_message(first, 'Start talking!')
        bot.send_message(second, 'Start talking!')


@bot.message_handler(commands=['help'])
def send_help(message):
    bot.send_message(message.chat.id, 'I am your mirror... Arghh')


@bot.message_handler(func=lambda m: True)
def repeat_all_messages(message):  # Название функции не играет никакой роли, в принципе
    bot.send_message(message.chat.id, message.text)

# receiving new messages
bot.polling(none_stop=True)
