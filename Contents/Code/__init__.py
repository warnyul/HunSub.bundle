import string, os, urllib, zipfile

PODNAPISI_MAIN_PAGE = "http://www.podnapisi.net"
PODNAPISI_SEARCH_PAGE = "http://www.podnapisi.net/subtitles/search/advanced?"

IGNORE_FILE = ".ignoresubtitlesearch"

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

    Log("Unfiltered subs")
    Log(subPages)

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
            Log("Ignoring folder")
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

def handlePart(part):
    fileName = os.path.basename(part.file)

    if not ignoreSearch(part.file):
        Log("Filename: %s" % fileName)
        Log("Release group: %s" % getReleaseGroup(part.file))

        data = {}
        data["keywords"] = fileName

        siList = getSubsForPart(data)

        for si in siList:
            Log(Locale.Language.Match(si.lang))
            part.subtitles[Locale.Language.Match(si.lang)][si.url] = Proxy.Media(si.sub, ext=si.ext)
    else:
        Log("Ignoring search for file %s" % fileName)
        Log("Due to a %s file being present in the same directory" % IGNORE_FILE)


class PodnapisiSubtitlesAgentMovies(Agent.Movies):
    name = 'Podnapisi Movie Subtitles'
    languages = [Locale.Language.English]
    primary_provider = False
    contributes_to = ['com.plexapp.agents.imdb']

    def search(self, results, media, lang):
        Log("Movie search called")
        results.Append(MetadataSearchResult(id = 'null', score = 100))

    def update(self, metadata, media, lang):
        Log("Movie update. Lang %s" % lang)
        for item in media.items:
            for part in item.parts:
                Log("Title: %s" % media.title)
                Log("Filename: %s" % os.path.basename(part.file))
                Log("Release group %s" % getReleaseGroup(part.file))

                handlePart(part)

class PodnapisiSubtitlesAgentTvShows(Agent.TV_Shows):
    name = 'Podnapisi TV Subtitles'
    languages = [Locale.Language.English]
    primary_provider = False
    contributes_to = ['com.plexapp.agents.thetvdb']

    def search(self, results, media, lang):
        Log("TV search called")
        results.Append(MetadataSearchResult(id = 'null', score = 100))

    def update(self, metadata, media, lang):
        Log("TvUpdate. Lang %s" % lang)
        for season in media.seasons:
            for episode in media.seasons[season].episodes:
                for item in media.seasons[season].episodes[episode].items:
                    Log("Show: %s" % media.title)
                    Log("Season: %s, Ep: %s" % (season, episode))
                    for part in item.parts:

                        handlePart(part)

class SubInfo():
    def __init__(self, lang, url, sub, name):
        self.lang = lang
        self.url = url
        self.sub = sub
        self.name = name
        self.ext = string.split(self.name, '.')[-1]
