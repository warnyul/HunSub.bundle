import string, os, urllib, zipfile

PODNAPISI_MAIN_PAGE = "http://www.podnapisi.net"
PODNAPISI_SEARCH_PAGE = "http://www.podnapisi.net/subtitles/search/advanced?"

IGNORE_FILE = ".ignoresubtitlesearch"

METADATA_URL = "http://127.0.0.1:32400/library/metadata/"

OS_PLEX_USERAGENT = 'plexapp.com v9.0'

def Start():
    HTTP.CacheTime = 0
    HTTP.Headers['User-agent'] = OS_PLEX_USERAGENT
    Log("Starting Podnapisi Plex Agent")

def ValidatePrefs():
    return

#Prepare a list of languages we want subs for
def getLangList():
    langList = [Prefs["langPref1"]]
    if(Prefs["langPref2"] != "None"):
        langList.append(Prefs["langPref2"])
    if(Prefs["langPref3"] != "None"):
        langList.append(Prefs["langPref3"])
    if(Prefs["langPref4"] != "None"):
        langList.append(Prefs["langPref4"])
    return langList

#Do a basic search for the filename and return all sub urls found
def simpleSearch(searchUrl):
    Log("searchUrl: %s" % searchUrl)
    elem = HTML.ElementFromURL(searchUrl)
    subPages = []
    subtitles = elem.xpath("//tr[@class='subtitle-entry']")
    for subtitle in subtitles:
        url = PODNAPISI_MAIN_PAGE + subtitle.xpath("./@data-href")[0]
        Log(url)
        subPages.append(url)
    return subPages

def searchSubs(params, lang):

    #Sort the results in order of most downloaded first
    params["language"] = lang
    params["sort"] = "stats.downloads"
    params["order"] = "desc"

    searchUrl = PODNAPISI_SEARCH_PAGE + urllib.urlencode(params)

    subPages = simpleSearch(searchUrl)

    #Only get the five first subs for vague matches
    subPages = subPages[0:5]

    return subPages

def downloadSubsAsZip(url):
    params = {}
    params["container"] = "zip"
    params = urllib.urlencode(params)

    zipFiles = []

    url = url + "/download?" + params
    Log(url)
    zipFile = Archive.ZipFromURL(url)
    zipFiles.append(zipFile)

    return zipFiles

def getFilesInZipFile(zipFile):
    files = []
    for name in zipFile:
        Log("Name in zip: %s" % repr(name))
        if name[-1] == "/":
            #Log("Ignoring folder")
            continue

        subData = zipFile[name]
        files.append((name, subData))

    return files

def getSubsForPart(data):
    siList = []
    for lang in getLangList():
        subUrls = searchSubs(data, lang)
        for subUrl in subUrls:
            zipFiles = downloadSubsAsZip(subUrl)
            for zipFile in zipFiles:
                files = getFilesInZipFile(zipFile)
                for f in files:
                    (name, subData) = f
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

def keywordSearch(filename):
    data = {}
    data["keywords"] = filename
    Log("Keyword search for %s:" % filename)
    siList = getSubsForPart(data)
    return siList

# Fallback method if keyword search doesn't return anything
def mediaInfoSearch(mediaInfo):
    data = {}

    Log("Detailed search for:")
    mediaInfo.printme()

    movie_type = "tv-series"

    if mediaInfo.isMovie:
        movie_type = "movie"
    data["movie_type"] = movie_type

    if mediaInfo.name:
        data["keywords"] = mediaInfo.name

    if mediaInfo.season:
        data["seasons"] = mediaInfo.season

    if mediaInfo.episode:
        data["episodes"] = mediaInfo.episode

    if mediaInfo.year:
        data["year"] = mediaInfo.year

    return getSubsForPart(data)

def handleMediaInfo(mediaInfo, part):

    if not ignoreSearch(mediaInfo.filename):

        siList = keywordSearch(mediaInfo.filename)

        if not siList:
            Log("No results from keyword/filename search, try harder")
            siList = mediaInfoSearch(mediaInfo)

        for si in siList:
            Log(Locale.Language.Match(si.lang))
            part.subtitles[Locale.Language.Match(si.lang)][si.url] = Proxy.Media(si.sub, ext=si.ext)
    else:
        Log("Ignoring search for file %s" % mediaInfo.filename)
        Log("Due to a %s file being present in the same directory" % IGNORE_FILE)

class MediaInfo():
    def __init__(self, name, isMovie=True):
        self.name = name
        self.isMovie = isMovie
        self.year = None
        self.filename = None
        self.releaseGroup = None
        self.season = None
        self.episode = None

    def printme(self):
        Log("Name: %s" % self.name)
        Log("IsMovie: %s" % self.isMovie)
        Log("Year: %s" % self.year)
        Log("Filename: %s" % self.filename)
        #Log("ReleaseGroup: %s" % self.releaseGroup)
        Log("Season: %s " % self.season)
        Log("Episode: %s " % self.episode)


def getMetadataXML(mediaid):
    url = METADATA_URL + mediaid
    Log(url)
    elem = XML.ElementFromURL(url)
    return elem

def getMovieInfo(media):
    mi = MediaInfo(media.title)

    elem = getMetadataXML(media.id)

    year = elem.xpath("//Video/@year")
    if (len(year) > 0):
        mi.year = year[0]

    return mi

def getTvShowInfo(media):
    i = MediaInfo(media.title, False)

    elem = getMetadataXML(media.id)
    year = elem.xpath("//Directory/@year")
    if (len(year) > 0):
        i.year = year[0]

    return i

class PodnapisiSubtitlesAgentMovies(Agent.Movies):
    name = 'Podnapisi Movie Subtitles'
    languages = [Locale.Language.English]
    primary_provider = False
    contributes_to = ['com.plexapp.agents.imdb']

    def search(self, results, media, lang):
        Log("Movie search")
        results.Append(MetadataSearchResult(id = 'null', score = 100))

    def update(self, metadata, media, lang):
        Log("Movie update")
        movieInfo = getMovieInfo(media)
        Log("Title: %s" % media.title)
        for item in media.items:
            for part in item.parts:
                movieInfo.filename = os.path.basename(part.file)

                handleMediaInfo(movieInfo, part)

class PodnapisiSubtitlesAgentTvShows(Agent.TV_Shows):
    name = 'Podnapisi TV Subtitles'
    languages = [Locale.Language.English]
    primary_provider = False
    contributes_to = ['com.plexapp.agents.thetvdb']

    def search(self, results, media, lang):
        Log("TV search")
        results.Append(MetadataSearchResult(id = 'null', score = 100))

    def update(self, metadata, media, lang):
        Log("TvUpdate")
        tvShowInfo = getTvShowInfo(media)
        Log("Title: %s" % media.title)
        for season in media.seasons:
            for episode in media.seasons[season].episodes:
                for item in media.seasons[season].episodes[episode].items:
                    for part in item.parts:
                        tvShowInfo.season = season
                        tvShowInfo.episode = episode
                        tvShowInfo.filename = os.path.basename(part.file)
                        handleMediaInfo(tvShowInfo, part)


class SubInfo():
    def __init__(self, lang, url, sub, name):
        self.lang = lang
        self.url = url
        self.sub = sub
        self.name = name
        self.ext = string.split(self.name, '.')[-1]
