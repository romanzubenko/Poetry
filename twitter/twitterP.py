#! /usr/bin/env python
from __future__ import division
import nltk, re, urllib,random,math,peewee,datetime,json,twitter
from lxml import etree as ET
import itertools as it

def is_ascii(s):
    return all(ord(c) < 128 for c in s)

def avgLength(s1,s2):
	return len(s1 + s2) / 2

def delta(s1,s2):
	if s2 > s1:
		s1, s2 = s2, s1

	return math.fabs(1 - (len(s1) / len(s2)))

def linkify(s,tweetDict):
	rawTweet = tweetDict[s]
	return "<a href=\"https://www.twitter.com/"+str(rawTweet.user.screen_name)+"/status/"+str(rawTweet.id)+"\">"+s+"</a>"

def delta_lines(lines):
	deltas = [delta(x,y) for (x,y) in list(it.combinations(lines,2))]
	return sum(deltas) / len(deltas)

def build_Tweet_Dict(tweets):
	dictionary = {}
	for tweet in tweets:
		dictionary[tweet.text] = tweet

	return dictionary


# Get RSS feeds
def getTweets():
	api = twitter.Api(consumer_key='ijjAm2nEn8KTSjndvWKYA',
                    consumer_secret='4xVy7YJLSf6xhGsJ1CTxpz8uHayK3r2xjro8v9N5Oqw',
                    access_token_key='430485845-D45SP00mQkB8V8Jl4KEDFdML5UE0vnZDGLuKPh0E',
                    access_token_secret='W63kab2fdiOnvqQpRgF5juiTpWbEWCZdnLs8MqzsY')

	trends1 = api.GetTrendsDaily()
	trends2 = api.GetTrendsWeekly()
	trends = list(set([s[0].__dict__['name'] for s in trends1] + [s[0].__dict__['name'] for s in trends2]))
	trends = [t for t in trends if is_ascii(t)]
	feeds = []
	queries = ["boston","new+ york","obama","chicago","nfl","LA","miami","nba","fashion","style","cool","good"] + trends
	addresses = []
	tweets = []
	rawTweets = []

	for query in queries:
		searches = api.GetSearch(term=query, per_page=40)
		rawTweets = rawTweets + searches
		tweets = tweets + [s.text for s in searches]

	d = build_Tweet_Dict(rawTweets)
	print "number of tweets : " + str(len(tweets))
	return (tweets,d)


def buildPronounciationDictionary():
	pron_entries = nltk.corpus.cmudict.entries()
	pron = nltk.defaultdict(list)
	for entry in pron_entries:
		pron[entry[0]] = entry[1]
	pron['syrians'] = [] # word syrians has weird pronounciation

	return pron


# Gets titles from feeds builds a dictionary titles-> urls links, builds pronounciation for every title
def getTitles(feeds,articles_links):
	titles = []
	for feed in feeds:
		for item in feed.iter('item'):
			title = item.find('title')
			titles.append(title.text)
			articles_links[title.text] = item.find('link').text

	titles = list(set(titles))

	return titles


# Piece = list of lines that rythm
def formPieces(titles):
	pron_titles = []
	pron_dict = nltk.defaultdict(list)
	# Build titles' pronounciations
	for title in titles:
		tokens = nltk.word_tokenize(title)
		tokens = [w.lower() for w in tokens if re.search('[a-zA-Z]+',w)]
		pronounciation = []
		for token in tokens:
			pronounciation = pronounciation + pron[token]

		pron_titles.append(pronounciation)
		pron_dict["".join(pronounciation[-3:])].append(title)

	endings = ["".join(s[-3:]) for s in pron_titles]
	freq_endings = nltk.FreqDist(endings)
	pieces = []
	i = 0
	while len(pron_dict[freq_endings.keys()[i]]) > 1:
		pieces.append(pron_dict[freq_endings.keys()[i]])
		i += 1

	return (pieces,pron_dict)

# Forms pairs of lines that rythm and have no defects
def formPairs(pieces):
	pairs = []
	# make all the possible rythmic pairs pairs 
	for piece in pieces:
		pairs = pairs + list(it.combinations(piece,2))

	# delete those whose last words are the same or last word is all-digit or there is no pronounciation of last word
	new_pairs = []
	for pair in pairs:
		line1 = nltk.word_tokenize(pair[0])
		line2 = nltk.word_tokenize(pair[1])

		if not (line1[-1].lower() == line2[-1].lower() or re.search('[0-9]+',line1[-1]) or re.search('[0-9]+',line2[-1]) or re.search('syrians',line2[-1].lower()) or len(pron[line1[-1].lower()]) == 0 or len(pron[line2[-1].lower()]) == 0):
			new_pairs.append(pair)


	pairs = new_pairs
	pairs = sorted([(delta(x,y),x,y) for (x,y) in pairs if delta(x,y) < 0.51])
	print "number of final pairs : " + str(len(pairs))
	pairs = list(set([(y,z) for (x,y,z) in pairs]))
	
	return pairs

def buildPoems(pairs):
	poems = list(it.combinations(pairs,2))
	poems = [[a,b,c,d] for ((a,b),(c,d)) in poems]
	poems = sorted([(delta_lines(poem),poem) for poem in poems if delta_lines(poem) < 0.5])
	
	distinct_pairs = set(("a","b"))
	poem_count = 0
	final_poems = []
	for poem in poems:
		str_set = list(set([poem[1][0],poem[1][1],poem[1][2],poem[1][3]]))
		if len(str_set) == 4 and (poem[1][0],poem[1][1]) not in distinct_pairs and (poem[1][2],poem[1][3]) not in distinct_pairs:
			distinct_pairs.add((poem[1][0],poem[1][1]))
			distinct_pairs.add((poem[1][2],poem[1][3]))
			poem_count += 1
			final_poems.append(linkify(poem[1][0],articles_links) + linkify(poem[1][1],articles_links) + linkify(poem[1][2],articles_links) + linkify(poem[1][3],articles_links))

	print "number of poems : " + str(len(final_poems))
	return final_poems

def publishPoems(poems):
	connect = {}
	connect['passwd'] = "6nypE4rM3c"
	db = peewee.MySQLDatabase('blog', user='blog', **connect)
	db.connect()
	class News(peewee.Model):
		date = peewee.DateField()
		text = peewee.TextField()
		class Meta:
			database = db

	today = datetime.datetime.now()
	today = str(today.year)+"-"+str(today.month)+"-"+str(today.day)

	for poem in poems:
		News.create(date=today, text=poem)


def publishPairs(pairs,tweetDict,pron_dict):
	connect = {}
	connect['passwd'] = "6nypE4rM3c"
	db = peewee.MySQLDatabase('blog', user='blog', **connect)
	db.connect()

	

	class TweetPair(peewee.Model):
		rhyme = peewee.CharField()
		date = peewee.DateField()
		text = peewee.TextField()
		avgLength = peewee.IntegerField()
		used = peewee.IntegerField()
		class Meta:
			database = db

	today = datetime.datetime.now()
	today = str(today.year)+"-"+str(today.month)+"-"+str(today.day)


	for pair in pairs:
		try:
			text = linkify(pair[0],tweetDict) + linkify(pair[1],tweetDict)
			rhyme =	"".join(pron[pair[0][-1]])[-3:]
			length = avgLength(pair[0],pair[1])
			
			print "IMPORTANT"
			print pron_dict[pair[0]]

			print "text :"+ text
			print "rhyme :"+ rhyme
			print "today :"+ today
			print "length :"+ str(length)
			print ""

			TweetPair.create(date=today, text=text, avgLength = length, used="0",rhyme = rhyme)
		except Exception as e:
			print "error"



#PROGRAM



tweets = getTweets()
tweetDictionary = tweets[1]
tweets = tweets[0]

''' # RESEARCH PART
raw = " ".join(tweets)
tokens = nltk.word_tokenize(raw)
fdist = nltk.FreqDist(tokens)
words = fdist.keys()[:100]
for w in words:
	print w
'''

pron = buildPronounciationDictionary()
articles_links = nltk.defaultdict(str)
pieces = formPieces(tweets)

pron_dict = pieces[1]
pieces = pieces[0]

pairs = formPairs(pieces)
publishPairs(pairs,tweetDictionary,pron_dict)


