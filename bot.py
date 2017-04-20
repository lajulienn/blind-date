import config
import shelve
import telebot

bot = telebot.TeleBot(config.token)

opened_dialogues = {}
closed_dialogues = {}
waiting_queue = []

with shelve.open(config.users_db) as users:

    def is_started(user_id):
        return user_id in opened_dialogues \
               or (len(waiting_queue) != 0 and user_id == waiting_queue[0])


    def is_smb_available(user_id):
        return len(waiting_queue) != 0 and (user_id not in closed_dialogues
                                            or closed_dialogues.get(user_id) != waiting_queue[0])


    def remove_from_list(first, second, list):
        if first in list:
            del list[first]
        if second in list:
            del list[second]

    def add_to_list(first, second, list):
        list[first] = second
        list[second] = first


    def add_new_user(user_id, username):
        users[str(user_id)] = config.UserProperties(username, False)

    @bot.message_handler(commands=['start'])
    def start(message):
        user_id = message.chat.id
        if is_started(user_id):
            return

        bot.send_message(user_id, 'Finding a partner for you...')

        username = message.from_user.username
        add_new_user(user_id, username)

        if not is_smb_available(user_id):
            waiting_queue.append(user_id)
        else:
            first = user_id
            second = waiting_queue.pop(0)
            add_to_list(first, second, list=opened_dialogues)
            remove_from_list(first, second, list=closed_dialogues)
            bot.send_message(first, 'Start talking!')
            bot.send_message(second, 'Start talking!')


    @bot.message_handler(commands=['help'])
    def send_help(message):
        bot.send_message(message.chat.id,
                         'Send "/start" to start a conversation.\n'
                         'Send "/leave" to close a conversation.\n'
                         'Send "/change_room" to change your partner.\n'
                         'Send "/reveal" to allow bot to show your username to your partner. '
                         'It would be shown only provided that '
                         'your partner also sent a reveal command\n')


    @bot.message_handler(commands=['leave'])
    def leave(message):
        first = message.chat.id
        if first in waiting_queue:
            waiting_queue.remove(first)
        if first not in opened_dialogues:
            return
        second = opened_dialogues[first]
        remove_from_list(first, second, list=opened_dialogues)
        add_to_list(first, second, list=closed_dialogues)
        bot.send_message(second, 'Your partner left the chat. :(\n'
                                 'Send "/start" to open a new conversation.')


    @bot.message_handler(commands=['change_room'])
    def change_room(message):
        user_id = message.chat.id
        if user_id in waiting_queue:
            return
        leave(message)
        start(message)


    @bot.message_handler(commands=['reveal'])
    def reveal(message):
        first = message.chat.id
        if not is_started(first):
            bot.send_message(first, 'Start a conversation first.')
            return
        if first not in opened_dialogues:
            bot.send_message(first, 'Your chat has not started yet.')
            return
        second = opened_dialogues[first]
        first_username = users[str(first)].username
        if users[str(second)].revealed:
            second_username = users[str(second)].username
            bot.send_message(first, 'User @' + second_username + ' revealed his username.')
            bot.send_message(second, 'User @' + first_username + ' revealed his username.')
        else:
            users[str(first)] = config.UserProperties(first_username, True)


    @bot.message_handler(func=lambda m: True)
    def reply(message):
        if message.chat.id in opened_dialogues:
            bot.send_message(opened_dialogues[message.chat.id], message.text)


    bot.polling()
