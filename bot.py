import logging
import shelve
import telebot

import config
import log_messages
import messages

logging.basicConfig(format=u'%(levelname)-8s [%(asctime)s] %(message)s',
                    level=logging.DEBUG,
                    filename=u'bot.log')

bot = telebot.TeleBot(config.token)

opened_dialogues = {}
closed_dialogues = {}
waiting_queue = []

with shelve.open(config.users_db) as users:

    def is_started(user_id):
        return user_id in opened_dialogues \
               or (len(waiting_queue) != 0 and user_id == waiting_queue[0])


    def is_smb_available(user_id):
        return len(waiting_queue) != 0 \
               and (user_id not in closed_dialogues
                    or closed_dialogues.get(user_id) != waiting_queue[0])


    def remove_from_dialogue(first, second, dialogues):
        if first in dialogues:
            del dialogues[first]
        if second in dialogues:
            del dialogues[second]

    def add_to_dialogue(first, second, dialogues):
        dialogues[first] = second
        dialogues[second] = first

    def add_new_user(user_id, username):
        users[str(user_id)] = config.UserProperties(username, False)


    @bot.message_handler(commands=['start'])
    def start(message):
        logging.debug(log_messages.command_received.format(command='/start', id=message.chat.id))
        user_id = message.chat.id
        if is_started(user_id):
            logging.warning(log_messages.second_start)
            return

        bot.send_message(user_id, messages.partner_finding)
        logging.debug(log_messages.partner_finding)

        username = message.from_user.username
        add_new_user(user_id, username)

        if not is_smb_available(user_id):
            waiting_queue.append(user_id)
            logging.debug(log_messages.add_new_user)
        else:
            first = user_id
            second = waiting_queue.pop(0)
            add_to_dialogue(first, second, dialogues=opened_dialogues)
            remove_from_dialogue(first, second, dialogues=closed_dialogues)
            bot.send_message(first, messages.start_talking)
            bot.send_message(second, messages.start_talking)
            logging.debug(log_messages.conversation_started.format(id1=first, id2=second))


    @bot.message_handler(commands=['help'])
    def send_help(message):
        logging.debug(log_messages.command_received.format('/help', message.chat.id))
        bot.send_message(message.chat.id, messages.help_message)


    @bot.message_handler(commands=['leave'])
    def leave(message):
        logging.debug(log_messages.command_received.format('/leave', message.chat.id))
        first = message.chat.id
        if first in waiting_queue:
            waiting_queue.remove(first)
            logging.debug(log_messages.removed_user.format(first))
        if first not in opened_dialogues:
            logging.warning(log_messages.not_chatting.format(message.chat.id))
            return
        second = opened_dialogues[first]
        remove_from_dialogue(first, second, dialogues=opened_dialogues)
        add_to_dialogue(first, second, dialogues=closed_dialogues)
        bot.send_message(second, messages.partner_left)
        logging.debug(log_messages.closed_dialogue_between.format(first, second))


    @bot.message_handler(commands=['change_room'])
    def change_room(message):
        logging.debug(log_messages.change_room.format(message.chat.id))
        user_id = message.chat.id
        if user_id not in opened_dialogues:
            logging.warning(log_messages.not_chatting.format(user_id))
            bot.send_message(user_id, messages.not_chatting)
        if user_id in waiting_queue:
            logging.error(log_messages.cant_change_room.format(message.chat.id))
            return
        leave(message)
        start(message)
        logging.debug(log_messages.change_room.format(message.chat.id))


    @bot.message_handler(commands=['reveal'])
    def reveal(message):
        logging.debug(log_messages.reveal.format(message.chat.id))
        first = message.chat.id
        if first in waiting_queue:
            bot.send_message(first, messages.chat_not_started)
            logging.warning(log_messages.chat_not_started.format(first))
            return
        if first not in opened_dialogues:
            bot.send_message(first, messages.not_chatting)
            logging.warning(log_messages.chat_not_started.format(first))
            return

        second = opened_dialogues[first]
        first_username = users[str(first)].username

        if first_username is None:
            bot.send_message(first, messages.no_username)
            logging.warning(log_messages.no_username.format(first))
            return

        if users[str(second)].revealed:
            second_username = users[str(second)].username
            bot.send_message(
                first,
                messages.user_revealed.format(second_username))
            bot.send_message(
                second,
                messages.user_revealed.format(first_username))
            logging.debug(log_messages.revealed_users.format(first, second))
        else:
            users[str(first)] = config.UserProperties(first_username, True)
            logging.debug(log_messages.set_revealed.format(first))


    @bot.message_handler(content_types=['text'])
    def reply(message):
        logging.debug(log_messages.message_recieved.format('Text', message.chat.id))
        user_id = message.chat.id
        if user_id in opened_dialogues:
            partner = opened_dialogues[user_id]
            if message.forward_from is not None:
                if message.forward_from.id == user_id:
                    bot.send_message(user_id, messages.cant_forward)
                    return
                bot.forward_message(partner, user_id, message.message_id)
                logging.debug(log_messages.forwarded_message
                              .format(user_id, partner, message.message_id, message.forward_from))
            elif message.reply_to_message is not None:
                message_to_forward = message.reply_to_message.message_id
                if message.reply_to_message.from_user.id != user_id:
                    bot.forward_message(partner, user_id, message_to_forward)
                else:
                    bot.send_message(user_id, messages.cant_forward)
                bot.send_message(partner, message.text)
                logging.debug(log_messages.send_reply.format(user_id, partner, message_to_forward))
            else:
                bot.send_message(partner, message.text)
            logging.debug(log_messages.send_message.format('text', user_id, partner))


    @bot.message_handler(content_types=['audio'])
    def reply(message):
        logging.debug(log_messages.message_recieved.format('Audio', message.chat.id))
        user_id = message.chat.id
        if user_id in opened_dialogues:
            partner = opened_dialogues[user_id]
            bot.send_audio(partner, message.audio.file_id)
            logging.debug(log_messages.send_message.format('Audio', user_id, partner))


    @bot.message_handler(content_types=['sticker'])
    def sticker(message):
        logging.debug(log_messages.message_recieved.format('Sticker', message.chat.id))
        user_id = message.chat.id
        if user_id in opened_dialogues:
            partner = opened_dialogues[user_id]
            bot.send_sticker(partner, message.sticker.file_id)
            logging.debug(log_messages.send_message.format('sticker', user_id, partner))


    @bot.message_handler(content_types=['voice'])
    def sticker(message):
        logging.debug(log_messages.message_recieved.format('Voice', message.chat.id))
        user_id = message.chat.id
        if user_id in opened_dialogues:
            partner = opened_dialogues[user_id]
            bot.send_voice(partner, message.voice.file_id)
            logging.debug(log_messages.send_message.format('voice', user_id, partner))


    @bot.message_handler(content_types=['document'])
    def sticker(message):
        logging.debug(log_messages.message_recieved.format('Document', message.chat.id))
        user_id = message.chat.id
        if user_id in opened_dialogues:
            partner = opened_dialogues[user_id]
            bot.send_document(partner, message.document.file_id)
            logging.debug(log_messages.send_message.format('document', user_id, partner))


    @bot.message_handler(content_types=['photo'])
    def sticker(message):
        logging.debug(log_messages.message_recieved.format('Photo', message.chat.id))
        user_id = message.chat.id
        if user_id in opened_dialogues:
            partner = opened_dialogues[user_id]
            bot.send_photo(partner, message.photo[-1].file_id)
            logging.debug(log_messages.send_message.format('photo', user_id, partner))


    @bot.message_handler(content_types=['video'])
    def sticker(message):
        logging.debug(log_messages.message_recieved.format('Video', message.chat.id))
        user_id = message.chat.id
        if user_id in opened_dialogues:
            partner = opened_dialogues[user_id]
            bot.send_video(partner, message.video.file_id)
            logging.debug(log_messages.send_message.format('video', user_id, partner))


    @bot.message_handler(content_types=['location'])
    def sticker(message):
        logging.debug(log_messages.message_recieved.format('Location', message.chat.id))
        user_id = message.chat.id
        if user_id in opened_dialogues:
            partner = opened_dialogues[user_id]
            bot.send_location(partner,
                                  message.location.latitude,
                                  message.location.longitude)
            logging.debug(log_messages.send_message.format('location', user_id, partner))

    bot.polling()
