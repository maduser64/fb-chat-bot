import threading
import sys
import json
import ctypes
import datetime
import fbchat
import random
import re
import time
import calendar
import io

from fbchat.models import Like
import stats
import quiz
import consts

CONFIG_FILE = "config.json"
STATS_FILE = "stats.json"

class ArnoldBot(fbchat.Client):
    

    def __init__(self, email, password, thread_fbid, config):
        self.stats = stats
        self.config = config
        self.commands = config[consts.COMMANDS]
        
        self.stats = stats.Stats(STATS_FILE)

        fbchat.Client.__init__(self, email, password, thread_fbid, True, None)
        threads = self.getThreadList(0)
        for item in threads:
            if item.thread_fbid == thread_fbid:
                thread = item

        # Extracts ids from participants and gets full data
        users = []
        for user_id in thread.participants:
            if user_id.startswith("fbid:"):
                users.append(user_id[5:])
        self.full_users = self.getUserInfo(users)

        self.annoy_list = []

        self.mquiz = quiz.Quiz(config["quiz_file"], self.stats)
        self.__quiz_question_count = 0
        self.__quiz_timeout_set = False
        self.__quiz_timer = None
        

                
    def fbidToName(self, fbid):
        for user in self.full_users:
            if user["id"] == fbid:
                return user["firstName"]

    def nameToFbid(self, name):
        for user in self.full_users:
            if user["firstName"] == name:
                return user["id"]

    def fbidToNameCode(self, fbid):
        for user in self.full_users:
            if user["id"] == fbid:
                return user["firstName"] + fbid[-3:]


    def on_message(self, mid, author_id, author_name, message, metadata):
        self.markAsDelivered(author_id, mid) #mark delivered
        self.markAsRead(author_id) #mark read

        # Relays private messages from OPs
        if self.is_operator(author_id):
            self.sendGroup(message)


    def on_message_group(self, mid, author_id, thread_fbid, message, metadata):
        self.markAsDelivered(author_id, mid) #mark delivered
        self.markAsRead(author_id) #mark read
        
        # Message from myself, therefore I sent a message
        if author_id == self.uid: self.stats.updateMessagesSent()

        # If my group and not from myself
        if str(thread_fbid) == self.thread_fbid and author_id != self.uid:

            # Commands
            if message.startswith("!"):
                self.log("%s sent message: '%s'" % (self.fbidToNameCode(author_id), message))

                parts = message.split(" ", 1)
                command_name = parts[0].lower()
                command_args = parts[1] if len(parts) == 2 else None
                
                command = self.getCommand(command_name)

                try:
                    if command: # Command found
                        if command[consts.Cmd.IS_OPER]: # Command is for operators
                            if self.is_operator(author_id): # User is operator
                                getattr(self, command[consts.Cmd.ENTRY_METHOD])(author_id, command, command_args)
                            else: # User is not operator
                                self.sendGroup(config[consts.COMMAND_ERROR_OPER])
                        else: # Not operator command
                            getattr(self, command[consts.Cmd.ENTRY_METHOD])(author_id, command, command_args)

                    else:
                        self.cmd_simple(author_id, command_name, command_args)

                except: # Command not found
                    self.command_log_error()
            
            # Quiz in progress
            elif self.__quiz_timeout_set: self.quiz_guess(author_id, message)
            
            # Responds to stuff in text
            else:
                # Listens to specific things people say
                # Augis
                if self.fbidToName(author_id) == "Augustas":
                    if re.match(r"\bu+g+h+\b", message.lower()) != None:
                        self.sendGroup("Neužpisk su tuo jobanu ugh, kurva.")

            self.global_responder(message.lower(), author_id)
            
            self.annoy(author_id)
            
    def getCommand(self, command_name):
        """Returns a dict of given command with all related info. None if command not found"""
        try:
            for command in self.commands.items():
                if command_name == command[1][consts.Cmd.NAME] or command_name == command[1][consts.Cmd.SHORT]:
                    return self.commands[command[0]]
        except:
            return None

    def is_operator(self, fbid):
        """Returns if given FBID is chatroom operator"""
        return fbid in config["oper_fbid_list"]

    def global_responder(self, message, author_id):
        """Responds, if there are words that match trigger words regex"""
        
        items = config["respond_to_words"]
        matches_lists = []
        message = message.lower()
        # If there are more than few matched lists, stores them
        for i, item in enumerate(items):
            for word in item["triggers"]:
                if re.search(word, message):
                    matches_lists.append(i)
                    break
        # There are triggers
        if len(matches_lists) > 0:
            rnd = random.randint(1, len(matches_lists)) - 1
            rnd_set = matches_lists[rnd]
            rnd = random.randint(1, len(items[rnd_set]["answers"])) - 1
            
            response = items[rnd_set]["answers"][rnd]
            try:
                response = response % self.fbidToName(author_id)
            except:
                pass
            self.sendGroup(response)


    def annoy(self, author_id):
        for item in self.annoy_list:
            if author_id == item["fbid"]:
                if item["count"] > 0:
                    self.sendGroup(item["text"])
                    item["count"] -= 1
                    break
                else:
                    self.sendGroup(config["commands"]["annoy"]["txt_annoy_done"])
                    self.annoy_list.remove(item)
                    break



    def command_log(self, command, param = None):
        ''' Formats command with parameters and sends to be logged
        Args:
            command - name of the executed command
            param (optional) - `str` or `dict` with arguments of the command
        '''

        msg = "Command '%s' executed." % command
        if param:
            msg += " Args: "
            if type(param) == dict:
                for key, value in param.items():
                    msg += "'%s:%s'; " % (key, value)
            else:
                msg += str(param)

        self.log(msg)

    def command_log_error(self, error = ""):
        ''' Logs an unrecognized command or some other error and sends info to chat '''
        self.log("Unrecognized command. " + error)
        self.sendGroup(config["command_error"])
        self.sendGroup(error)
        self.stats.updateCommandsError()
        
    def on_listening(self):
        self.sendGroup(config["on_login"])

    def quizRevealLetter(self, timer):
        if self.mquiz.acceptsAnswer():
            if self.mquiz.revealLetter():
                # Restarts timer
                timer = threading.Timer(self.commands["quiz"]["timeout"], self.quizRevealLetter)
                timer.args = (timer,)
                self.__quiz_timer = timer
                self.__quiz_timer.start()
                self.sendGroup(self.mquiz.getHiddenAnswer())
            else:
                timer.cancel()
                self.__quiz_timer = None
                self.__quiz_timeout_set = False
                msg = self.commands["quiz"]["timeout_text"] % self.mquiz.getAnswer()
                self.sendGroup(msg)

                # More questions
                
                if self.__quiz_question_count > 0:
                    quizGiveQuestion(self.__quiz_question_count)

    def quizGiveQuestion(self):
        self.sendGroup("%s\n\n%s" % (self.mquiz.getQuestion(), self.mquiz.getHiddenAnswer()))

        if not self.__quiz_timeout_set:
            timer = threading.Timer(self.commands["quiz"]["timeout"], self.quizRevealLetter)
            timer.args = (timer,)
            self.__quiz_timer = timer
            self.__quiz_timer.start()
            self.__quiz_timeout_set = True

    def quiz_guess(self, author_id, message):
        # Might be an answer but answers are not accepted
        if self.mquiz.acceptsAnswer():
            points = self.mquiz.guessAnswer(self.fbidToNameCode(author_id), message)
            # Correct answer
            if points:
                msg = self.commands["quiz"]["guess_correct"] % (self.fbidToName(author_id), str(points))
                self.sendGroup(msg)
                self.__quiz_timer.cancel()
                self.__quiz_timer = None
                self.__quiz_timeout_set = False
                self.quizGiveQuestion()

    ############
    ### Commands
    ############

    def cmd_simple(self, author_id, command_name, args):
        """Executes commands, which only respond with a text"""
        try:
            value = self.commands["simple_commands"]["commands"][command_name]
                    
            if args == None: args = 0
            args = int(args)

            msg = self.commands["simple_commands"]["commands"][command_name][args]
            self.sendGroup(msg)
        except:
            self.command_log_error()

    def cmd_simpleCommands(self, author_id, command, args):
        """Adds a command to simple_commands list."""
        try:
            args = args.split(" ", 1)
            new_command_name = "!" + args[0]
            
            # Appending to list
            if new_command_name in command["commands"].keys():
                command["commands"][new_command_name].append(args[1])
            else:
                command["commands"][new_command_name] = [args[1]]

            with open(CONFIG_FILE, "w", encoding = "utf-8") as outfile:
                json.dump(config, outfile, indent = "\t", ensure_ascii = False)

            self.sendGroup(command[consts.Cmd.TXT_EXECUTED] % new_command_name)

        except:
            self.command_log_error()


    def cmd_quiz(self, author_id, command, args):
        # Quiz config entry
        name_code = self.fbidToNameCode(author_id)

        if args == None:
            args = command[consts.Cmd.ARGS]["help"]

        try:
            # Checks if it is a command
            for key, val in command[consts.Cmd.ARGS].items():
                if val == args:
                    if key == "help":
                        self.sendGroup(command["help"])
                        self.command_log(command[consts.Cmd.NAME], args)

                    elif key == "repeat_question":
                        self.command_log(command[consts.Cmd.NAME], args)
                        if self.__quiz_timeout_set:
                            self.sendGroup("%s\n\n%s" % (self.mquiz.getQuestion(), self.mquiz.getHiddenAnswer()))
                        else:
                            self.quizGiveQuestion()

                    elif key == "get_question":
                        self.command_log(command[consts.Cmd.NAME], args)
                        self.quizGiveQuestion()
                            
                    elif key == "user_stats":
                        self.command_log(command[consts.Cmd.NAME], args)
                        stats = self.mquiz.getUserStats(self.fbidToNameCode(author_id))
                        if stats:
                            msg = command["user_stats_text"].format(name = self.fbidToName(author_id), **stats)
                        else:
                            msg = command["user_not_played"]
                        self.sendGroup(msg)

                    elif key == "global_stats":
                        self.command_log(command[consts.Cmd.NAME], args)
                        stats = self.mquiz.getGlobalStats()
                        msg = command["global_stats_text"].format(**stats)
                        self.sendGroup(msg)

                    elif key == "top_3":
                        self.command_log(command[consts.Cmd.NAME], args)
                        users = self.mquiz.getTop(3)

                        msg = command["top_text"]
                        for i, user in enumerate(users):
                            msg += command["top_position_text"] % (str(i + 1), user[0], user[1][quiz.POINTS])
                        self.sendGroup(msg)

                    break
            # Command not found, it is a guess
            else: self.quiz_guess(author_id, " ".join(args))
        except Exception as e:
            self.command_log_error(str(e))



    def cmd_annoy(self, author_id, command, args):
        try:
            args = args.split(" ", 2)
            if len(args) != 3: raise Exception
            name = args[0]
            text = args[2]
            count = int(args[1])
            if count > 5: raise Exception
            
            
            for user in self.full_users:
                if user["firstName"].lower() == name:
                    fbid = user["id"]
                    break
            else: raise Exception
            if fbid == self.uid: raise Exception

            args = { "fbid": fbid, "count": count, "text": text }
            self.annoy_list.append(args)

            args_log = { "name_code": self.fbidToNameCode(fbid), "count": count, "text": text }
            self.command_log(command[consts.Cmd.NAME], args_log)

            self.sendGroup(command[consts.Cmd.TXT_EXECUTED])

        except:
            self.command_log_error()

    def cmd_unannoy(self, author_id, command, args):
        for item in self.annoy_list:
            if item["fbid"] == author_id:
                self.command_log(command[consts.Cmd.NAME])
                self.sendGroup(command[consts.Cmd.TXT_EXECUTED])
                self.annoy_list.remove(item)
                break;
            
    def cmd_say(self, author_id, command, args):
        if args:
            self.command_log(command[consts.Cmd.NAME], args)
            self.sendGroup(args)
        else:
            self.command_log(command[consts.Cmd.NAME])
            self.sendGroup(command[consts.Cmd.TXT_ARGS_ERROR])
            
    def cmd_updateconfig(self, author_id, command, args):
        try:
            with open(CONFIG_FILE, encoding = "utf-8") as infile:
                new_config = json.load(infile)
            config.update(new_config)
            self.command_log(command[consts.Cmd.NAME])
            self.sendGroup(command[consts.Cmd.TXT_EXECUTED])
        except Exception as e:
            self.sendGroup(e)
            self.command_log_error()


    def cmd_savestats(self, author_id, command, args):
        try:
            self.stats.updateCommandsExecuted(self.fbidToNameCode(author_id), command[consts.Cmd.NAME])
            self.stats.updateStats()
            self.command_log(command[consts.Cmd.NAME])
            self.sendGroup(command[consts.Cmd.TXT_EXECUTED])
        except Exception as e:
            self.sendGroup(e)
            self.command_log_error()
           

    def cmd_roll(self, author_id, command, args):
        self.command_log(command[consts.Cmd.NAME])
        rnd = random.randint(0, 14)

        if rnd == 0:
            message = "Aš dūchas."
        elif rnd in (1, 2, 3, 4):
            message = "Augustas dūchas."
        elif rnd in (5, 6, 7):
            message = "Aurelijus dūchas."
        elif rnd in (8, 9, 10):
            message = "Sigitas dūchas."
        elif rnd in (11, 12):
            message = "Dainius dūchas."
        elif rnd in (13, 14):
            message = "Niekas nėra dūchas :)"

        self.sendGroup(message)

    def cmd_time(self, author_id, command, args):
        self.command_log(command[consts.Cmd.NAME])

        now = time.time()
        dtnow = datetime.datetime.now()
        local_time = time.localtime()

        
        msg = time.strftime(command["txt_format"].decode("utf-8"), local_time)
        #msg += "Unix time: %s\n\n" % str(int(now))
        cal = calendar.TextCalendar(calendar.MONDAY).formatmonth(dtnow.year, dtnow.month)
        cal = cal.replace("  ", "   ")
        cal = cal.replace("\n ", "\n  ")
        msg += cal
        
        self.sendGroup(msg)
    
# Config and stats files provided via argument
if len(sys.argv) >= 3:
    CONFIG_FILE = sys.argv[1]
    STATS_FILE = sys.argv[2]
    
with open(CONFIG_FILE, encoding = "utf-8") as infile:
    config = json.load(infile)

ctypes.windll.kernel32.SetConsoleTitleW(config["bot_name"])

bot = ArnoldBot(config[consts.Config.EMAIL], config[consts.Config.PASSWORD], config[consts.Config.THREAD_FBID], config)
bot.listen()