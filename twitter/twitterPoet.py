#! /usr/bin/env python
from __future__ import division
import nltk, re, urllib,random,math,peewee,datetime,json,twitter
from lxml import etree as ET
import itertools as it

#connect to db
connect = {}
connect['passwd'] = "6nypE4rM3c"
db = peewee.MySQLDatabase('blog', user='blog', **connect)
db.connect()

class Tweetpair(peewee.Model):
	rhyme = peewee.CharField()
	date = peewee.DateField()
	text = peewee.TextField()
	avgLength = peewee.IntegerField()
	used = peewee.IntegerField()
	class Meta:
		database = db

def is_ascii(s):
    return all(ord(c) < 128 for c in s)

def avgLength(s1,s2):
	return len(s1 + s2) / 2

def delta(s1,s2):
	if s2 > s1:
		s1, s2 = s2, s1

	return math.fabs(1 - (len(s1) / len(s2)))

def buildTweetDictionary(rawTweets):
	tweets = {}
	for r in rawTweets:
		tweets[r.text] = r
	return tweets

def delta_lines(lines):
	deltas = [delta(x,y) for (x,y) in list(it.combinations(lines,2))]
	return sum(deltas) / len(deltas)

def getPairs():

	rawPairs =  []
	for rawPair in Tweetpair.select().where(Tweetpair.used == 0):
		rawPairs.append(rawPair)

	endings = [p.rhyme for p in rawPairs if is_ascii(p.rhyme) and p.rhyme != ""]
	print endings[:10]
	endings = list(nltk.FreqDist(endings))
	endings.reverse()
	endings = set(endings[:7])

	pairs = [(p.text.split("><")[0]+">","<"+p.text.split("><")[1]) for p in rawPairs if p.rhyme in endings]

	return (pairs,rawPairs)

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
			final_poems.append(poem[1][0] + poem[1][1]+ poem[1][2]+ poem[1][3])

	print "number of poems : " + str(len(final_poems))
	return final_poems

def updatePairs(poems,tweetDict):
	for poem in poems:
		print poem
		poem = poem.split("><")
		pair1 = poem[0] + "><" + poem[1] + ">"
		pair2 = "<" + poem[2] + "><" + poem[3] + ">"
		print "IMPORTANT TEST :"
		print pair1
		print tweetDict[pair1]
		tweetDict[pair1].used = 1
		tweetDict[pair1].save()




def publishPoems(poems):
	class TweetPoems(peewee.Model):
		date = peewee.DateField()
		text = peewee.TextField()
		class Meta:
			database = db

	today = datetime.datetime.now()
	today = str(today.year)+"-"+str(today.month)+"-"+str(today.day)

	for poem in poems:
		TweetPoems.create(date=today, text=poem)


#Program body

pairs = getPairs()
rawTweets = pairs[1]
pairs = pairs[0]
tweetDict = buildTweetDictionary(rawTweets)

poems = buildPoems(pairs)
updatePairs(poems,tweetDict)
publishPoems(poems)
for p in poems:
	print p
	""
	""