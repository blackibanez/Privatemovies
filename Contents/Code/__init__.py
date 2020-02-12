# Private.com

import re
from datetime import datetime
import urllib
import urllib2 as urllib
import random

# preferences
preference = Prefs
DEBUG = preference['debug']
if DEBUG:
  Log('Agent debug logging is enabled!')
else:
  Log('Agent debug logging is disabled!')


if len(preference['searchtype']) and preference['searchtype'] != 'all':
  searchtype = preference['searchtype']
else:
  searchtype = 'allsearch'
if DEBUG:Log('Search Type: %s' % str(preference['searchtype']))

# URLS
ADE_BASEURL = 'https://www.private.com'
ADE_SEARCH_MOVIES = ADE_BASEURL + '/search.php?query=%s'

scoreprefs = int(preference['goodscore'].strip())
if scoreprefs > 1:
    GOOD_SCORE = scoreprefs
else:
    GOOD_SCORE = 98
if DEBUG:Log('Result Score: %i' % GOOD_SCORE)

INITIAL_SCORE = 100


def Start():
  HTTP.CacheTime = CACHE_1MINUTE
  HTTP.SetHeader('User-agent', 'Mozilla/5.0 (iPhone; CPU iPhone OS 10_3_1 like Mac OS X) AppleWebKit/603.1.30 (KHTML, like Gecko) Version/10.0 Mobile/14E304 Safari/602.1')

def ValidatePrefs():
  pass

class PrivateAgent(Agent.Movies):
  name = 'Private Movies'
  languages = [Locale.Language.English]
  primary_provider = True
  accepts_from = ['com.plexapp.agents.localmedia']

  def search(self, results, media, lang):
    title = media.name
    if media.primary_metadata is not None:
      title = media.primary_metadata.title

    query = urllib.quote(title)

    # resultarray[] is used to filter out duplicate search results
    resultarray=[]
    if DEBUG: Log('Search Query: %s' % str(ADE_SEARCH_MOVIES % query))
    # Finds the entire media enclosure <DIV> elements then steps through them
    for movie in HTML.ElementFromURL(ADE_SEARCH_MOVIES % query).xpath('//div[@class="film"]/a[@itemprop="url"]'):
      # curName = The text in the 'title' p
      name=movie.get('title')
      score = 100 - Util.LevenshteinDistance(title.lower(), name.lower())
      Log("Name : " + str(name))
      curID=movie.get('href').replace('/','_')
      results.Append(MetadataSearchResult(id = curID, name = str(name), score = score, lang = lang))

      results.Sort('score', descending=True)

  def update(self, metadata, media, lang):
    html = HTML.ElementFromURL(str(metadata.id).replace('_','/'))
    Log("Url video " + str(metadata.id))
    metadata.title = media.title

    # Thumb and Poster
    try:
      img = html.xpath('//div[@class="dvds-photo col-md-3 col-sm-6 col-xs-6"]//img')[0]
      thumbUrl = img.get('srcset').split(' ')[6]

      thumb = HTTP.Request(thumbUrl)
      posterUrl = img.get('srcset').split(' ')[6]
      Log("Url img : " + str(posterUrl))
      metadata.posters[posterUrl] = Proxy.Preview(thumb)
    except Exception, e:
      Log('Got an exception while parsing poster %s' %str(e))

    try:
      art = html.xpath('//meta[@itemprop="thumbnailUrl"]')[0].get('content')
      Log("posters DL: " + art)
      metadata.art[art] = Proxy.Preview(HTTP.Request(art, headers={'Referer': 'http://www.google.com'}).content, sort_order=1)
    except Exception, e:
      Log('Got an exception while parsing background %s' %str(e))

    # Tagline
    try: metadata.tagline = html.xpath('//p[@class="Tagline"]')[0].text_content().strip()
    except: pass

    # Summary.
    try:
      for summary in html.xpath('//p[@class="sinopsys"]'):
        metadata.summary = summary.text_content()
    except Exception, e:
      Log('Got an exception while parsing summary %s' %str(e))

    # Studio
    metadata.studio = "Private"

    # Release
    try:
      date = html.xpath('//meta[@itemprop="uploadDate"]')[0].get('content')
      Log("Date : " + str(date))
      if len(date) > 0:
          date_object = datetime.strptime(date, '%m/%d/%Y')
          metadata.originally_available_at = date_object
          metadata.year = metadata.originally_available_at.year
    except Exception, e:
      Log('Got an exception while parsing Release Date %s' %str(e))

    # Cast - added updated by Briadin / 20190108
    Log('Search for Cast')
    try:
      metadata.roles.clear()
      titleActors = ""
      actors = html.xpath('//ul[@id="featured_pornstars"]//li[@class=" col-lg-2 col-md-4 col-sm-4 col-xs-6 "]')
      if len(actors) > 0:
          for actorPage in actors:
              actorName = actorPage.xpath('.//div[@class="model"]//a')[0].get("title")
              titleActors = titleActors + actorName + " & "
              actorPhotoURL = actorPage.xpath('.//div[@class="model"]//a//picture//img')[0].get("src")
              role = metadata.roles.new()
              role.name = actorName
              role.photo = actorPhotoURL
              Log("Name Actor : " + actorName + "Url Photo : " + str(actorPhotoURL))
          titleActors = titleActors[:-3]
          metadata.title = metadata.title
    except Exception, e:
      Log('Got an exception while parsing cast %s' %str(e))

    # Director
    try:
      metadata.directors.clear()
      htmldirector=html.xpath('//p[@class="director"]/span')[0].text_content().strip()
      if (len(htmldirector) > 0):
        director = metadata.directors.new()
        director.name = htmldirector
        Log("Name Director : " + htmldirector )
    except Exception, e:
      Log('Got an exception while parsing director %s' %str(e))

    # Collections and Series
    try:
      metadata.collections.clear()
      tagline = html.xpath('//p[@class="line-dvd"]')[0].text_content()
      metadata.tagline = tagline
      metadata.collections.add(tagline)
    except: pass

    # Genres
    try:
      metadata.genres.clear()
      ignoregenres = [x.lower().strip() for x in preference['ignoregenres'].split('|')]
      if html.xpath('//*[contains(@class, "col-sm-4 spacing-bottom")]'):
        htmlgenres = HTML.StringFromElement(html.xpath('//*[contains(@class, "col-sm-4 spacing-bottom")]')[2])
        htmlgenres = htmlgenres.replace('\n', '|')
        htmlgenres = htmlgenres.replace('\r', '')
        htmlgenres = htmlgenres.replace('\t', '')
        htmlgenres = HTML.ElementFromString(htmlgenres).text_content()
        htmlgenres = htmlgenres.split('|')
        htmlgenres = filter(None, htmlgenres)
        htmlgenres = htmlgenres[1:]
        htmlgenres = htmlgenres[:-1]
        for gname in htmlgenres:
          if len(gname) > 0:
              if not gname.lower().strip() in ignoregenres: metadata.genres.add(gname)
    except Exception, e:
      Log('Got an exception while parsing genres %s' %str(e))
