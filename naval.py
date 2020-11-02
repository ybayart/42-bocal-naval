#! /usr/local/bin/python3

import slack, time, requests, json, os, sys, mutagen.mp3, random
from subprocess import call
from pygame import mixer
from api42 import api
from utils import *

SLACK_TOKEN=os.environ.get("SLACK_TOKEN_YAYABOT")
FLOOR=[
	{
		"name": "e2",
		"desc": "\
	r13:  14\n\
	r12:  23\n\
	r11:  23\n\
	r10:  23\n\
	 r9:  20\n\
	 r8:  21\n\
	 r7:  23\n\
	 r6:  20\n\
	 r5:  22\n\
	 r4:  23\n\
	 r3:  21\n\
	 r2:  23\n\
	 r1:  14\n"
	},
	{
		"name": "e3",
		"desc": "\
	r13:  14\n\
	r12:  23\n\
	r11:  23\n\
	r10:  23\n\
	 r9:  20\n\
	 r8:  21\n\
	 r7:  23\n\
	 r6:  20\n\
	 r5:  22\n\
	 r4:  23\n\
	 r3:  21\n\
	 r2:  23\n\
	 r1:  14\n"
	}
]


class NavalWar():
	def __init__(self):
		self.players = dict()
		self.current_player = None
		self.chans_id = []
		self.shoots = 0
		self.bot = slack.RTMClient(token=SLACK_TOKEN)
		self.client = slack.WebClient(SLACK_TOKEN)
		self.ensure_slack()
		self.ensure_args()
		mixer.init()
		self.api = api()
		self.init_players()
		slack.RTMClient.run_on(event='message')(self.run)
		self.bot.start()

	def ensure_slack(self):
		self.bot_info = self.client.api_call("auth.test")
		if self.bot_info.get("ok") is True:
			print("✅ Connection succed\n",
				f"{yellow('team')} : {blue(self.bot_info['team'])}\n",
				f"{yellow('user')} : {blue(self.bot_info['user'])}\n")
		else:
			print("❌ Connection failed\nRetry...")
			self.__init__()

	def ensure_args(self):
		if len(sys.argv) != 3:
			exit(red(f"Usage: {sys.argv[0]} <player1> <player2>"))
		self.players[0] = sys.argv[1].lower()
		self.players[1] = sys.argv[2].lower()
		for player in self.players:
			loop = True
			for mailcomp in ["42.fr", "42paris.fr", "student.42.fr"]:
				if loop == True:
					response = self.user_info(self.players[player]+"@"+mailcomp)
					if response is not False:
						self.players[player] = response["user"]
						loop = False
			if loop is False:
				print(yellow(f"player ({FLOOR[player]['name']})"), " : ", blue(self.players[player]["id"]), " | ", blue(self.players[player]["real_name"]))
			else:
				exit(f"{red('user')} {blue(self.players[player])} {red('not found')}")
		print("")

	def user_info(self, mail):
		try:
			return self.client.api_call("users.lookupByEmail?email={}".format(mail))
		except:
			return False
	
	def init_players(self):
		self.current_player = random.choice(list(self.players))
		for player in self.players:
			self.chans_id.append(self.client.chat_postMessage(
				text="You're in naval war !\n",
				channel=self.players[player]["id"],
				as_user=True).get("channel"))
			self.client.chat_postMessage(
				text="\
War summary:\n\
	You face <@{}>\n\
	You're in `{}`\
	```{}```\n\
	{}".format(
	self.players[not player]["id"],
	FLOOR[player]["name"],
	FLOOR[player]["desc"],
	"*You start!*" if self.current_player == player else "You follow"),
				channel=self.players[player]["id"],
				as_user=True
			)
		print(blue(self.players[self.current_player]["real_name"]), "start")
		self.ask_victim()
	
	def play_sound(self, sound, repeat):
		mp3 = mutagen.mp3.MP3(sound)
		mixer.init(frequency=mp3.info.sample_rate)
		mixer.music.load(sound)
		mixer.music.play(loops=repeat)
		if repeat == 0:
			time.sleep(float(mp3.info.length))
	
	def ask_victim(self):
		self.shoots += 1
		self.play_sound("sonar.mp3", -1)
		self.client.chat_postMessage(
			text="Round `{}`\nYou need to enter your target\n*JUST TYPE rXpX*".format(int((self.shoots + 1) / 2)),
			channel=self.players[self.current_player]["id"],
			as_user=True
		)
	

	def is_for_me(self):
		if (not (self.event.get("bot_id")) and
			self.event.get("text") and
			self.event.get("channel") in self.chans_id and
			self.event.get("user") == self.players[self.current_player]["id"]):
			return True
		else:
			return False
	
	def maketrans_host(self, host):
		newhost = host
		newhost = newhost.replace("r", ", r")
		newhost = newhost.replace("p", ", paix")
		return newhost
	
	def reset(self, victim):
		print("!reboot {}".format(victim["host"]))
		print("!home-reset {}".format(victim["user"]["login"]))
		user = self.api.scrapper("users/{}".format(victim["user"]["login"]))
		call(["say -v Thomas '{} {}'".format(random.choice(list(["Bisous", "Cadeau", "Imoteppe", "Félicitation"])), user["first_name"])], shell=True)
	
	def ensure_location(self):
		host = FLOOR[self.current_player]["name"]+self.event.get("text").lower()
		victim = self.api.scrapper("campus/1/locations?filter[active]=true&filter[host]={}".format(host))
		print(green(host) if victim != 0 else red(host))
		self.add_reac("boom" if victim != 0 else "ocean")
		mixer.quit()
		call(["say -v Thomas '{}'".format(self.maketrans_host(host))], shell=True)
		if victim != 0:
			self.play_sound(random.choice(list(["touche-1.mp3", "touche-2-debris.mp3", "touche-3-bang.mp3"])), 0)
			self.reset(victim[0])
		else:
			self.play_sound("coup-dans-leau.mp3", 0)
	
	def switch_player(self):
		self.current_player = not self.current_player
		self.ask_victim()

	def add_reac(self, reaction):
		self.client.reactions_add(
			channel=self.event.get("channel"),
			name=reaction,
			timestamp=self.event.get("ts")
		)

	def run(self, **payload):
		self.event = payload['data']
		if self.is_for_me() is True:
			self.ensure_location()
			time.sleep(2)
			self.switch_player()

if __name__ == "__main__":
	try:
		naval = NavalWar()
	except KeyboardInterrupt:
		print("toto")
