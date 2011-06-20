#hdbits.org

import string, os, urllib, zipfile

PODNAPISI_MAIN_PAGE = "http://www.podnapisi.net"
PODNAPISI_SEARCH_PAGE = "http://www.podnapisi.net/en/ppodnapisi/search?tbsl=%d&"
MOVIE_SEARCH = PODNAPISI_SEARCH_PAGE % 2
TV_SEARCH = PODNAPISI_SEARCH_PAGE % 3

OS_PLEX_USERAGENT = 'plexapp.com v9.0'
subtitleExt       = ['utf','utf8','utf-8','sub','srt','smi','rt','ssa','aqt','jss','ass','idx']

langPrefs2Podnapisi = {'en':'2', 'sv':'25'}

def Start():
    HTTP.CacheTime = 0
    HTTP.Headers['User-agent'] = OS_PLEX_USERAGENT
    Log("START CALLED")

#Prepare a list of languages we want subs for
def getLangList():
    langList = [Prefs["langPref1"]]
    if(Prefs["langPref2"] != "None"):
        langList.append(Prefs["langPref2"])

    return langList


#Do a basic search for the filename and return all sub urls found
def simpleSearch(params, lang = 'eng'):
    Log("Params: %s" % urllib.urlencode(params))
    searchUrl = TV_SEARCH + urllib.urlencode(params)
    Log("searchUrl: %s" % searchUrl)
    elem = HTML.ElementFromURL(searchUrl)
    
    subUrls = []

    subpages = elem.xpath("//table[@class='seznam']//tbody//tr//td[1]//a/@href")
    for subpage in subpages:
        subPageUrl = PODNAPISI_MAIN_PAGE + subpage
        Log("Subpage: %s" % subPageUrl)
        pageElem = HTML.ElementFromURL(subPageUrl)
        downloadUrl = pageElem.xpath("//div[@class='podnapis_tabele_download']//a[contains(@href,'download')]/@href")[0]
        downloadUrl = PODNAPISI_MAIN_PAGE + downloadUrl
        Log("DownloadURL: %s" % downloadUrl)
        subUrls.append(downloadUrl)

    return subUrls


class SubInfo():
    lang = None
    url = None
    sub = None
    subExt = None

def getSubsForPart(part):
    Log("Filename: %s" % fileName)

def getReleaseGroup(filename):
    tmpFile = string.replace(filename, '-', '.')
    splitName = string.split(tmpFile, '.')
    group = splitName[-2]
    return group

class PodnapisiSubtitlesAgentMovies(Agent.Movies):
    name = 'Podnapisi Movie Subtitles'
    languages = [Locale.Language.English]
    primary_provider = False
    contributes_to = ['com.plexapp.agents.imdb']

    def search(self, results, media, lang):
        Log("MOVIE SEARCH CALLED")    
        results.Append(MetadataSearchResult(id = 'null', score = 100))

    def update(self, metadata, media, lang):
            Log("MOVIE UPDATE CALLED")
            for item in media.items:
                for part in item.parts:
                    pass

class PodnapisiSubtitlesAgentMovies(Agent.TV_Shows):
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
                        for lang in getLangList():
                            Log("Release group: %s" % getReleaseGroup(part.file))
                            Log("Lang: %s,%s" % (lang, langPrefs2Podnapisi[lang]))
                            data = {}
                            data['sK'] = media.title
                            data['sTS'] = season
                            data['sTE'] = episode
                            data['sR'] = getReleaseGroup(part.file)
                            data['sJ'] = langPrefs2Podnapisi[lang]
                            subUrls = simpleSearch(data)
                            for subUrl in subUrls:
                                Log("Getting subtitle from: %s" % subUrl)
                                zipArchive = Archive.ZipFromURL(subUrl)
                                for name in zipArchive:
                                    Log("Name in zip: %s" % name)
                                    subData = zipArchive[name]
                                    part.subtitles[Locale.Language.Match(lang)][subUrl] = Proxy.Media(subData, ext='srt') 


