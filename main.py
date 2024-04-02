import random
import time
import threading
import queue
from util import connection, execute_query

class Question:
    def __init__(self, cursor, difficulty):
        self.cursor = cursor 
        self.difficulty = difficulty
        self.owl_question = None
        self.choices = None
        self.user_answer = None
        self.real_answer = None
        self.asked_questions = set()
        self.question_information = self.get_question_information()
        self.choices_information = self.get_choices_information()
        self.answers_information = self.get_answers_information()
    
    def get_question_information(self):
        query = f"SELECT * FROM questions"
        difficulty_clause = f" where question_difficulty = '{self.difficulty}'" if self.difficulty != 'combination' else ''
        query += difficulty_clause
        results = self.get_query_results(query)
        return [[row[0], row[1], row[2]] for row in results]
    
    def get_choices_information(self):
        query = "SELECT question_id, choice FROM choices"
        results = self.get_query_results(query)
        return [[row[0], row[1]] for row in results]
    
    def get_answers_information(self):
        query = "SELECT question_id, owl_answer FROM answers"
        results = self.get_query_results(query)
        return [[row[0], row[1]] for row in results]

    def get_query_results(self, query):
        self.cursor.execute(query)
        return self.cursor.fetchall()
    
    def read_question_db(self):
        remaining_questions = [{'question_id': q[0], 'owl_question': q[2]} for q in self.question_information if q[2] not in self.asked_questions]
        if remaining_questions:
            selected_question = random.choice(remaining_questions)
            self.owl_question = {'question_id': selected_question['question_id'], 'owl_question': selected_question['owl_question']}
            self.asked_questions.add(selected_question['owl_question'])

    def read_choices_db(self):
        self.choices = [choice[1] for choice in self.choices_information if choice[0] == self.owl_question['question_id']]
        self.choices = '\n'.join(self.choices)

    def actual_answer(self):
        self.real_answer = next((answer[1] for answer in self.answers_information if answer[0] == self.owl_question['question_id']), None)
    
    def print_question(self):
        self.read_question_db()
        self.read_choices_db() 
        self.actual_answer()
        print(self.owl_question['owl_question'])
        print(self.choices)

    def recieve_user_answer(self, prompt: str, queue: queue.Queue):
        print(prompt)
        self.user_answer = input()
        queue.put(self.user_answer)

    def compare_answers(self):
        if self.user_answer == self.real_answer:
            print("Correct!")
            return True
        elif self.user_answer == "":
            print(f"You did not answer in time. The correct answer is: {self.real_answer}")
            return False
        else:
            print(f"Incorrect. The correct answer is: {self.real_answer}")
            return False
        
class Difficulty:
    def __init__(self, hearts, points):
        self.hearts = hearts
        self.points = points

class Easy(Difficulty):
    def __init__(self):
        self.hearts = 5
        self.points = 100
        self.point_loss = 50
        # self.timer_point_loss = 2

class Medium(Difficulty):
    def __init__(self):
        self.hearts = 4
        self.points = 200
        self.point_loss = 70
        # self.timer_point_loss = 5
class Hard(Difficulty):
    def __init__(self):
        self.hearts = 3
        self.points = 300
        self.point_loss = 90
        # self.timer_point_loss = 10

class Combination(Difficulty):
    def __init__(self):
        self.heart = 5
        self.points = 200
        self.point_loss = 70
        # self.timer_point_loss = 5

class Game:

    difficulties = {"easy": Easy, "medium": Medium, "hard": Hard}#makes dictionary that assigns easy, med, hard to the classes, but have not created instances yet

    def __init__(self, difficulty, max_questions=10):
        self.difficulty = self.create_difficulty(difficulty)
        self.max_hearts = self.difficulty.hearts
        self.max_questions = max_questions
        self.hearts = self.max_hearts #setting users hearts to the max number of hearts at the start of the game
        self.questions_answered = 0
        self.conn, self.cursor = connection()
        self.timer_duration = 10
        # self.timer_point_loss = self.difficulty.timer_point_loss
        self.timer_running = True
        self.myqueue = queue.Queue()

    def game_over(self, username, score):
        if self.hearts == 0:  
            print(f"Game over {username}. You have failed your OWL's with no hearts left. :( \n Your final score is: {score}.")
            completion_time = time.strftime('%Y-%m-%d %H:%M:%S')
            player_instance.user_info_to_db(username, score, completion_time)
            game_instance.list_leaderboard()
            self.cursor.close()
            self.conn.close()
        if self.hearts > 0 and self.questions_answered == 10:
            print(f"Congratulations {username}! You have successfully passed your OWL's with a score of: {score}!")
            completion_time = time.strftime('%Y-%m-%d %H:%M:%S')
            player_instance.user_info_to_db(username, score, completion_time)
            game_instance.list_leaderboard()
            self.cursor.close()
            self.conn.close()

    def list_leaderboard(self):
        self.cursor.execute("SELECT * FROM user_score ORDER BY player_score")
        leaderboard = self.cursor.fetchall()
        for entry in leaderboard:
            print(f"name: {entry[1]} score: {entry[2]} timestamp: {entry[3]}")
        
    def create_difficulty(self, difficulty):
        return self.difficulties[difficulty]() #creates instance of the easy/med/hard class

    def play_game(self, question_instance, player_instance):
        while self.questions_answered < self.max_questions and self.hearts > 0: #while questions answered is smaller than the max questions and hearts remaining are greater than 0:
            question_thread = threading.Thread(target=question_instance.recieve_user_answer, args=("Please enter your choice: ", self.myqueue), daemon=True)
            question_instance.print_question() #calls the print_question method from the question class (that has been assigned to the question_instance instance for class Question)
            question_thread.start()
            try:
                question_instance.user_answer = self.myqueue.get(timeout=12)
            except queue.Empty:
                question_instance.user_answer = ""
            if not question_instance.compare_answers(): #if the response doesn't match the question_answer method in question class (with response being passed in)
                self.hearts -= 1 #heart is lost
                player_instance.decrease_score(self.difficulty.point_loss)
            else:
                player_instance.increase_score(self.difficulty.points)
            self.questions_answered += 1 #answered question increases
            print(f"{player_instance.username}, you have {self.hearts} hearts remaining.") #prints the hearts remaining
            print(f"Your score: {player_instance.score}")
            self.game_over(player_instance.username, player_instance.score) #calls this method to check for remaining hearts

class Player:
    def __init__(self, cursor, conn, username):
        self.score = 0
        self.cursor = cursor
        self.conn = conn
        self.username = username

    def increase_score(self, amount):
        self.score += amount

    def decrease_score(self, amount):
        self.score -= amount

    def user_info_to_db(self, username, score, completion_time):
        self.cursor.execute("INSERT INTO user_score (player_name, player_score, score_date) VALUES (%s, %s, %s)", (username, score, completion_time))
        self.conn.commit()
        

class Menu:
    def __init__(self):            
        self.menu_options = ['easy', 'medium', 'hard', 'combination']
        self.user_choice = None

    def choose_difficulty(self, username):
        difficulty_options = "\n easy: O.W.L.s year level 5 \n medium: O.W.L.s year level 6 (N.E.W.T.) \n hard: O.W.L.s year level 7 (N.E.W.T.) \n combination: A random mixture!"
        self.user_choice = input(f"Greetings to all Witches and Wizards, especially {username}! What level of O.W.L's would you like to play? {difficulty_options}\n")
        if self.user_choice in self.menu_options:
            return self.user_choice
        else:
            print("Invalid option.")


if __name__ == "__main__":

    username = input("Please enter your username: ")
    menu = Menu()
    difficulty = menu.choose_difficulty(username)
    game_instance = Game(difficulty)
    player_instance = Player(game_instance.cursor, game_instance.conn, username)
    question_instance = Question(game_instance.cursor, difficulty)
    game_instance.play_game(question_instance, player_instance)
