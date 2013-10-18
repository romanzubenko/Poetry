#! /usr/bin/env python
from __future__ import division
import nltk, re, urllib,random,math,peewee,datetime 
from lxml import etree as ET
import itertools as it

def delta(s1,s2):
	if s2 > s1:
		s1, s2 = s2, s1

	return math.fabs(1 - (len(s1) / len(s2)))

def linkify(s,linkDict):
	return "<a href=\""+linkDict[s]+"\">"+s+"</a>"

def delta_lines(lines):
	deltas = [delta(x,y) for (x,y) in list(it.combinations(lines,2))]
	return sum(deltas) / len(deltas)

# Get RSS feeds
def getRSSfeeds():
	feeds = []
	addresses = [
		"http://feeds.newsweek.com/newsweek/WorldNews",
		"http://feeds.newsweek.com/newsweek/business",
		"http://www.forbes.com/real-time/feed2/",
		"http://www.wsj.com/xml/rss/3_7014.xml",
		"http://online.wsj.com/xml/rss/3_7031.xml",
		"http://www.wallstreetjournal.com/xml/rss/3_7011.xml",
		"http://www.nytimes-se.com/feed/",
		"http://www.ft.com/rss/world",
		"http://www.ft.com/rss/home/us",
		"http://www.economist.com/rss/full_print_edition_rss.xml",
		"http://rss.time.com/web/time/rss/world/index.xml",
		"http://www.guardian.co.uk/world/rss",
		"http://newsrss.bbc.co.uk/rss/newsonline_world_edition/front_page/rss.xml",
		"http://www.washingtonpost.com/wp-dyn/rss/politics/index.xml",
		"http://feeds.foxnews.com/foxnews/latest"
	]

	for url in addresses:
		xml = urllib.urlopen(url)
		tree = ET.parse(xml)
		feeds.append(tree.getroot())

	return feeds


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

	return pieces

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
	pairs = sorted([(delta(x,y),x,y) for (x,y) in pairs if delta(x,y) < 0.41])
	print "number of final pairs : " + str(len(pairs))
	pairs = list(set([(y,z) for (x,y,z) in pairs]))
	
	return pairs

def is_ascii(s):
    return all(ord(c) < 128 for c in s)

def buildPoems(pairs):
	poems = list(it.combinations(pairs,2))
	poems = [[a,b,c,d] for ((a,b),(c,d)) in poems]
	poems = sorted([(delta_lines(poem),poem) for poem in poems if delta_lines(poem) < 0.2])
	
	distinct_pairs = set(("a","b"))
	poem_count = 0
	final_poems = []
	for poem in poems:
		str_set = list(set([poem[1][0],poem[1][1],poem[1][2],poem[1][3]]))
		if len(str_set) == 4 and (poem[1][0],poem[1][1]) not in distinct_pairs and (poem[1][2],poem[1][3]) not in distinct_pairs:
			distinct_pairs.add((poem[1][0],poem[1][1]))
			distinct_pairs.add((poem[1][2],poem[1][3]))
			poem_count += 1

			'''
			is_ascii(s)
			print poem_count
			print poem[1][0]
			print poem[1][1]
			print poem[1][2]
			print poem[1][3]
			print ""
			'''
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

#PROGRAM
feeds = getRSSfeeds()
pron = buildPronounciationDictionary()
articles_links = nltk.defaultdict(str)
titles = getTitles(feeds,articles_links)
pieces = formPieces(titles)
pairs = formPairs(pieces)
poems = buildPoems(pairs)
publishPoems(poems)

