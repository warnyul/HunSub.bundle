import string
import os
import urllib

PODNAPISI_MAIN_PAGE = "http://www.podnapisi.net"
PODNAPISI_SEARCH_PAGE = "http://www.podnapisi.net/subtitles/search/advanced?"

IGNORE_FILE = ".ignoresubtitlesearch"

METADATA_URL = "http://127.0.0.1:32400/library/metadata/"

OS_PLEX_USERAGENT = 'plexapp.com v9.0'


def Start():
    HTTP.CacheTime = 0
    HTTP.Headers['User-agent'] = OS_PLEX_USERAGENT
    Log("Starting HunSub Plex Agent")


def ValidatePrefs():
    return


# Prepare a list of languages we want subs for
def get_lang_list():
    lang_list = [Prefs["langPref1"]]
    if Prefs["langPref2"] != "None":
        lang_list.append(Prefs["langPref2"])
    return lang_list


# Do a basic search for the filename and return all sub urls found
def simple_search(search_url):
    Log("searchUrl: %s" % search_url)
    elem = HTML.ElementFromURL(search_url)
    sub_pages = []
    subtitles = elem.xpath("//tr[@class='subtitle-entry']")
    for subtitle in subtitles:
        url = PODNAPISI_MAIN_PAGE + subtitle.xpath("./@data-href")[0]
        Log(url)
        sub_pages.append(url)
    return sub_pages


def search_subs(params, lang):

    # Sort the results in order of most downloaded first
    params["language"] = lang
    params["sort"] = "stats.downloads"
    params["order"] = "desc"

    search_url = PODNAPISI_SEARCH_PAGE + urllib.urlencode(params)

    sub_pages = simple_search(search_url)

    # Only get the five first subs for vague matches
    sub_pages = sub_pages[0:5]

    return sub_pages


def download_subs_as_zip(url):
    params = {"container": "zip"}
    params = urllib.urlencode(params)

    zip_files = []

    url = url + "/download?" + params
    Log(url)
    zip_file = Archive.ZipFromURL(url)
    zip_files.append(zip_file)

    return zip_files


def get_files_in_zip_file(zip_file):
    files = []
    for name in zip_file:
        Log("Name in zip: %s" % repr(name))
        if name[-1] == "/":
            # Log("Ignoring folder")
            continue

        sub_data = zip_file[name]
        files.append((name, sub_data))

    return files


def get_subs_for_part(data):
    si_list = []
    for lang in get_lang_list():
        sub_urls = search_subs(data, lang)
        for subUrl in sub_urls:
            zip_files = download_subs_as_zip(subUrl)
            for zipFile in zip_files:
                files = get_files_in_zip_file(zipFile)
                for f in files:
                    (name, subData) = f
                    si = SubInfo(lang, subUrl, subData, name)
                    si_list.append(si)
    return si_list


def get_release_group(filename):
    tmp_file = string.replace(filename, '-', '.')
    split_name = string.split(tmp_file, '.')
    group = split_name[-2]
    return group


def ignore_search(filename):
    path = os.path.dirname(filename)
    ignore_path = os.path.join(path, IGNORE_FILE)

    if os.path.exists(ignore_path):
        return True
    return False


def keyword_search(filename):
    data = {"keywords": filename}
    Log("Keyword search for %s:" % filename)
    si_list = get_subs_for_part(data)
    return si_list


# Fallback method if keyword search doesn't return anything
def media_info_search(media_info):
    data = {}

    Log("Detailed search for:")
    media_info.print_me()

    movie_type = "tv-series"

    if media_info.isMovie:
        movie_type = "movie"
    data["movie_type"] = movie_type

    if media_info.name:
        data["keywords"] = media_info.name

    if media_info.season:
        data["seasons"] = media_info.season

    if media_info.episode:
        data["episodes"] = media_info.episode

    if media_info.year:
        data["year"] = media_info.year

    return get_subs_for_part(data)


def handle_media_info(media_info, part):

    if not ignore_search(media_info.filename):

        si_list = keyword_search(media_info.filename)

        if not si_list:
            Log("No results from keyword/filename search, try harder")
            si_list = media_info_search(media_info)

        for si in si_list:
            Log(Locale.Language.Match(si.lang))
            part.subtitles[Locale.Language.Match(si.lang)][si.url] = Proxy.Media(si.sub, ext=si.ext)
    else:
        Log("Ignoring search for file %s" % media_info.filename)
        Log("Due to a %s file being present in the same directory" % IGNORE_FILE)


class MediaInfo:
    def __init__(self, name, is_movie=True):
        self.name = name
        self.isMovie = is_movie
        self.year = None
        self.filename = None
        self.releaseGroup = None
        self.season = None
        self.episode = None

    def print_me(self):
        Log("Name: %s" % self.name)
        Log("IsMovie: %s" % self.isMovie)
        Log("Year: %s" % self.year)
        Log("Filename: %s" % self.filename)
        # Log("ReleaseGroup: %s" % self.releaseGroup)
        Log("Season: %s " % self.season)
        Log("Episode: %s " % self.episode)


def get_metadata_xml(media_id):
    url = METADATA_URL + media_id
    Log(url)
    elem = XML.ElementFromURL(url)
    return elem


def get_movie_info(media):
    mi = MediaInfo(media.title)

    elem = get_metadata_xml(media.id)

    year = elem.xpath("//Video/@year")
    if len(year) > 0:
        mi.year = year[0]

    return mi


def get_tv_show_info(media):
    i = MediaInfo(media.title, False)

    elem = get_metadata_xml(media.id)
    year = elem.xpath("//Directory/@year")
    if len(year) > 0:
        i.year = year[0]

    return i


class PodnapisiSubtitlesAgentMovies(Agent.Movies):
    name = 'HunSub Movie Subtitles'
    languages = [Locale.Language.English]
    primary_provider = False
    contributes_to = ['com.plexapp.agents.imdb']

    def search(self, results, media, lang):
        Log("Movie search")
        results.Append(MetadataSearchResult(id='null', score=100))

    def update(self, metadata, media, lang):
        Log("Movie update")
        movie_info = get_movie_info(media)
        Log("Title: %s" % media.title)
        for item in media.items:
            for part in item.parts:
                movie_info.filename = os.path.basename(part.file)

                handle_media_info(movie_info, part)


class PodnapisiSubtitlesAgentTvShows(Agent.TV_Shows):
    name = 'HunSub TV Subtitles'
    languages = [Locale.Language.English]
    primary_provider = False
    contributes_to = ['com.plexapp.agents.thetvdb']

    def search(self, results, media, lang):
        Log("TV search")
        results.Append(MetadataSearchResult(id='null', score=100))

    def update(self, metadata, media, lang):
        Log("TV update")
        tv_show_info = get_tv_show_info(media)
        Log("Title: %s" % media.title)
        for season in media.seasons:
            for episode in media.seasons[season].episodes:
                for item in media.seasons[season].episodes[episode].items:
                    for part in item.parts:
                        tv_show_info.season = season
                        tv_show_info.episode = episode
                        tv_show_info.filename = os.path.basename(part.file)
                        handle_media_info(tv_show_info, part)


class SubInfo:
    def __init__(self, lang, url, sub, name):
        self.lang = lang
        self.url = url
        self.sub = sub
        self.name = name
        self.ext = string.split(self.name, '.')[-1]
