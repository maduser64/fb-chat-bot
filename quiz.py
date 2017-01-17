import io
import stats
import random
import re
import time

HIDDEN_CHAR = "-"

# JSON field names
QUIZ = "quiz"
QUESTIONS = "total_questions"
ANSWERED = "total_answered"
GUESSED = "total_guessed"
LAST_ANSWERED = "last_answered"
LAST_GUESSED = "last_guessed"
LAST_QUESTION = "last_question"
LAST_ANSWER = "last_answer"
USERS = "users"
USER_COMBO = "combo"
POINTS = "points"

class Quiz():
    """Module responsible for all quiz related things"""

    def __init__(self, quiz_file, stats):
        self.__stats = stats
        self.__accepts_answers = False
        self.__current_combo = []

        with open(quiz_file, "r") as infile:
            self.__lines = infile.readlines()

    def acceptsAnswer(self):
        return self.__accepts_answers

    def getQuestion(self):
        if not self.__accepts_answers:
            return self.getNewQuestion()
        return self.__question

    def getAnswer(self):
        return self.__answer
    
    def getHiddenAnswer(self):
        return self.__hidden
    
    def getUserStats(self, name_code):
        try:
            return self.__stats.vals[QUIZ][USERS][name_code]
        except:
            return None

    def getGlobalStats(self):
        return self.__stats.vals[QUIZ]

    def getNewQuestion(self):
        """Generates and returns new question"""
        self.updateQuizQuestions()
        self.__accepts_answers = True

        rnd = random.randint(0, len(self.__lines))
        parts = self.__lines[rnd].split("|")
        self.__question = parts[0]
        self.__answer = parts[1]
        self.__hidden = re.sub("[0-9a-zA-Z]", HIDDEN_CHAR, self.__answer)
        self.__hidden_count = len(self.__hidden)
        return self.__question

    def revealLetter(self):
        """Makes one letter visible. First revealed is first, other random. Returns if full reveal"""
        # All letters hidden
        string = list(self.__hidden)
        if self.__hidden_count == len(self.__answer):
            string[0] = self.__answer[0]
            self.__hidden = "".join(string)
            self.__hidden_count -= 1
            return True
        # First letter revelaled
        elif self.__hidden_count > 1:
            rnd = random.randint(1, len(self.__answer) - 1)
            while self.__hidden[rnd] != HIDDEN_CHAR:
                rnd = random.randint(1, len(self.__answer) - 1)
            string[rnd] = self.__answer[rnd]
            self.__hidden = "".join(string)
            self.__hidden_count -= 1
            return True
        # One letter left, reveal answer
        else:
            self._hidden = self.__answer
            self.__accepts_answers = False
            return False

    def guessAnswer(self, name_code, guess):
        """If guess is correct, updates stats and returns points. Returns `None` otherwise"""
        self.updateQuizGuessed(name_code)
        if unidecode(guess.lower()) == self.__answer.lower():
            self.__accepts_answers = False

            if not self.__current_combo: self.__current_combo.append(name_code)
            else:
                if self.__current_combo[-1] == name_code:
                    self.__current_combo.append(name_code)
                else:
                    self.__current_combo.clear()
                    self.__current_combo.append(name_code)

            return self.givePoints(name_code)
        return None

    def givePoints(self, name_code):
        """Calculates points, updates stats, returns amount of points"""
        points = self.__hidden_count / len(self.__answer)
        points = round(points * 10)
        points = 1 if points == 0 else points

        self.updateQuizPoints(name_code, points)
        return points

    def updateQuizQuestions(self):
        self.__stats.vals[QUIZ][QUESTIONS] += 1
        self.__stats.makeDirty()
    
    def updateQuizGuessed(self, name_code):
        stats = self.__stats.vals[QUIZ]
        time_now = time.strftime("%Y-%m-%d %H:%M:%S",time.localtime())

        stats[GUESSED] += 1
        stats[LAST_GUESSED] = time_now
        
        try: user = stats[USERS][name_code]
        except:
            self.insertUserToStats(name_code)
            user = stats[USERS][name_code]

        user[GUESSED] += 1
        user[LAST_GUESSED] = time_now

        self.__stats.makeDirty()
    
    def updateQuizPoints(self, name_code, points):
        stats = self.__stats.vals[QUIZ]
        time_now = time.strftime("%Y-%m-%d %H:%M:%S",time.localtime())

        stats[ANSWERED] += 1
        stats[LAST_ANSWERED] = time_now
        stats[LAST_QUESTION] = self.__question
        stats[LAST_ANSWER] = self.__answer
        
        try: user = stats[USERS][name_code]
        except:
            self.insertUserToStats(name_code)
            user = stats[USERS][name_code]
         
        user[POINTS] += points
        user[ANSWERED] += 1
        user[LAST_ANSWERED] = time_now

        if self.__current_combo[-1] == name_code:
            if user[USER_COMBO] < len(self.__current_combo):
                user[USER_COMBO] = len(self.__current_combo)

        user[LAST_QUESTION] = self.__question
        user[LAST_ANSWER] = self.__answer

        self.__stats.makeDirty()

    def insertUserToStats(self, name_code):
        """Creates user entry in stats"""
        stats = self.__stats.vals[QUIZ][USERS]
        stats[name_code] = { POINTS : 0,
                             ANSWERED: 0,
                             GUESSED : 0,
                             USER_COMBO: 0,
                             LAST_ANSWERED : "",
                             LAST_GUESSED : "",
                             LAST_QUESTION : "",
                             LAST_ANSWER : "" }
        self.__stats.makeDirty()

    def getTop(self, count):
        """Returns a list of tuples of given number of top users sorted by points"""
        if count < 1: raise ValueError

        users = self.__stats.vals[QUIZ][USERS]
        users = sorted(users.items(), key = lambda x: x[1][POINTS], reverse = True)
        return users[:count]
        
def unidecode(string):
    result = ""
    for i in string:
        if i == 'ą': result += 'a'
        elif i == 'č': result += 'c'
        elif i == 'ę': result += 'e'
        elif i == 'ė': result += 'e'
        elif i == 'į': result += 'i'
        elif i == 'š': result += 's'
        elif i == 'ų': result += 'u'
        elif i == 'ū': result += 'u'
        elif i == 'ž': result += 'z'
        else: result += i

    return result
