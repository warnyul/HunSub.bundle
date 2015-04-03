#hdbits.org

import string, os, urllib, zipfile, re, copy

PODNAPISI_MAIN_PAGE = "http://www.podnapisi.net"
PODNAPISI_SEARCH_PAGE = "http://www.podnapisi.net/en/ppodnapisi/search?sT=%d&"
MOVIE_SEARCH = PODNAPISI_SEARCH_PAGE % 0
TV_SEARCH = PODNAPISI_SEARCH_PAGE % 1
IGNORE_FILE = ".ignoresubtitlesearch"

OS_PLEX_USERAGENT = 'plexapp.com v9.0'
subtitleExt       = ['utf','utf8','utf-8','sub','srt','smi','rt','ssa','aqt','jss','ass','idx']

langPrefs2Podnapisi = {'sq':'29','ar':'12','be':'50','bs':'10','bg':'33','ca':'53','zh':'17','cs':'7','da':'24','nl':'23','en':'2','et':'20','fi':'31','fr':'8','de':'5','el':'16','he':'22','hi':'42','hu':'15','is':'6','id':'54','it':'9','ja':'11','ko':'4','lv':'21','lt':'19','mk':'35','ms':'55','no':'3','pl':'26','pt':'32','ro':'13','ru':'27','sr':'36','sk':'37','sl':'1','es':'28','sv':'25','th':'44','tr':'30','uk':'46','vi':'51','hr':'38'}

mediaCopies = {}

def Start():
    HTTP.CacheTime = 0
    HTTP.Headers['User-agent'] = OS_PLEX_USERAGENT
    Log("START CALLED")

def ValidatePrefs():
    return

#Prepare a list of languages we want subs for
def getLangList():
    langList = [Prefs["langPref1"]]
    if(Prefs["langPref2"] != "None"):
        langList.append(Prefs["langPref2"])

    return langList

def tvSearch(params, lang):
    Log("Params: %s" % urllib.urlencode(params))
    searchUrl = TV_SEARCH + urllib.urlencode(params)
    return simpleSearch(searchUrl, lang)

def movieSearch(params, lang):
    Log("Params: %s" % urllib.urlencode(params))
    searchUrl = MOVIE_SEARCH + urllib.urlencode(params)
    return simpleSearch(searchUrl, lang)


#Do a basic search for the filename and return all sub urls found
def simpleSearch(searchUrl, lang = 'eng'):
    Log("searchUrl: %s" % searchUrl)
    elem = HTML.ElementFromURL(searchUrl)
    subs = []
    subtitles = elem.xpath("//subtitle")
    for subtitle in subtitles:
        url = subtitle.xpath('./url/text()')[0]
        release = subtitle.xpath('./release/text()')
        if len(release) > 0:
            release = release[0]
        t = (url, release)
        subs.append(t)
    return subs

class SubInfo():
    def __init__(self, lang, url, sub, name):
        self.lang = lang
        self.url = url
        self.sub = sub
        self.name = name
        self.ext = string.split(self.name, '.')[-1]

def doSearch(data, lang, isTvShow):
    if(isTvShow):
        return tvSearch(data, lang)

    return movieSearch(data, lang)

def searchSubs(data, lang, isTvShow):
    d = dict(data) # make a copy so that we still include release group for other searches
    releaseGroup = d['sR']
    del d['sR']
    subUrls = doSearch(d, lang, isTvShow)

    Log("Release group %s" % releaseGroup)

    filteredSubs = [x for x in subUrls if releaseGroup in x[1]]
    Log("Filtered subs")
    Log(filteredSubs)

    Log("Unfiltered subs")
    Log(subUrls)

    if len(filteredSubs) > 0:
        Log("filtered subs found, returning them")
        subUrls = filteredSubs

    subUrls = [x[0] for x in subUrls]

    return subUrls

def getSubsForPart(data, isTvShow=True):
    siList = []
    for lang in getLangList():
        Log("Lang: %s,%s" % (lang, langPrefs2Podnapisi[lang]))
        data['sJ'] = langPrefs2Podnapisi[lang]

        subUrls = searchSubs(data, lang, isTvShow)

        for subUrl in subUrls:
            Log("Getting subtitle from: %s" % subUrl)
            zipArchive = Archive.ZipFromURL(subUrl)
            for name in zipArchive:
                Log("Name in zip: %s" % repr(name))
                if name[-1] == "/":
                    Log("Ignoring folder")
                    continue

                subData = zipArchive[name]
                si = SubInfo(lang, subUrl, subData, name)
                siList.append(si)

    return siList

def getReleaseGroup(filename):
    tmpFile = string.replace(filename, '-', '.')
    splitName = string.split(tmpFile, '.')
    group = splitName[-2]
    return group

def ignoreSearch(filename):
    path = os.path.dirname(filename)
    ignorepath = os.path.join(path, IGNORE_FILE)

    if os.path.exists(ignorepath):
        return True
    return False

class PodnapisiSubtitlesAgentMovies(Agent.Movies):
    name = 'Podnapisi Movie Subtitles'
    languages = [Locale.Language.English]
    primary_provider = False
    contributes_to = ['com.plexapp.agents.imdb']

    def search(self, results, media, lang):
        Log("MOVIE SEARCH CALLED")
        mediaCopy = copy.copy(media.primary_metadata)
        uuid = String.UUID()
        mediaCopies[uuid] = mediaCopy
        results.Append(MetadataSearchResult(id = uuid, score = 100))

    def update(self, metadata, media, lang):
        Log("MOVIE UPDATE CALLED")
        mc = mediaCopies[metadata.id]
        for item in media.items:
            for part in item.parts:
                Log("Title: %s" % media.title)
                Log("Filename: %s" % os.path.basename(part.file))
                Log("Year: %s" % mc.year)
                Log("Release group %s" % getReleaseGroup(part.file))

                data = {}
                data['sK'] = media.title
                data['sR'] = getReleaseGroup(part.file)
                data['sY'] = mc.year

                if not ignoreSearch(part.file):
                    siList = getSubsForPart(data, False)

                    for si in siList:
                        Log(Locale.Language.Match(si.lang))
                        part.subtitles[Locale.Language.Match(si.lang)][si.url] = Proxy.Media(si.sub, ext=si.ext)
                else:
                    Log("Ignoring search for file %s" % os.path.basename(part.file))
                    Log("Due to a %s file being present in the same directory" % IGNORE_FILE)

        del(mediaCopies[metadata.id])


class PodnapisiSubtitlesAgentTvShows(Agent.TV_Shows):
    name = 'Podnapisi TV Subtitles'
    languages = [Locale.Language.English]
    primary_provider = False
    contributes_to = ['com.plexapp.agents.thetvdb']

    def search(self, results, media, lang):
        Log("TV SEARCH CALLED")
        results.Append(MetadataSearchResult(id = 'null', score = 100))

    def update(self, metadata, media, lang):
        Log("TvUpdate. Lang %s" % lang)
        for season in media.seasons:
            for episode in media.seasons[season].episodes:
                for item in media.seasons[season].episodes[episode].items:
                    Log("show: %s" % media.title)
                    Log("Season: %s, Ep: %s" % (season, episode))
                    for part in item.parts:
                        Log("Release group: %s" % getReleaseGroup(part.file))
                        Log("Filename: %s" % os.path.basename(part.file))
                        data = {}
                        data['sK'] = media.title
                        data['sTS'] = season
                        data['sTE'] = episode
                        data['sR'] = getReleaseGroup(part.file)

                        if not ignoreSearch(part.file):
                            siList = getSubsForPart(data)
                            for si in siList:
                                Log(Locale.Language.Match(si.lang))
                                part.subtitles[Locale.Language.Match(si.lang)][si.url] = Proxy.Media(si.sub, ext=si.ext)
                        else:
                            Log("Ignoring search for file %s" % os.path.basename(part.file))
                            Log("Due to a %s file being present in the same directory" % IGNORE_FILE)


