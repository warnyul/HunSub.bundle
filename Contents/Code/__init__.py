import string
import os
import urllib
import re

SEARCH_PAGE = "http://hosszupuskasub.com/sorozatok.php?"

IGNORE_FILE = ".ignoresubtitlesearch"

METADATA_URL = "http://127.0.0.1:32400/library/metadata/"

OS_PLEX_USER_AGENT = 'plexapp.com v9.0'


def Start():
    HTTP.CacheTime = 0
    HTTP.Headers['User-Agent'] = OS_PLEX_USER_AGENT
    Log('Starting HunSub Plex Agent')


def ValidatePrefs():
    Log('ValidatePrefs called')
    return


def get_language_list():
    language_list = [Prefs["langPref1"]]
    if Prefs["langPref2"] != "None":
        language_list.append(Prefs["langPref2"])
    return language_list


class SubMetaInfo:
    def __init__(self, url, release_groups):
        self.url = url
        self.release_groups = release_groups


# Do a basic search for the filename and return all sub urls found
def simple_search(search_url):
    Log("searchUrl: %s" % search_url)
    data = HTML.ElementFromURL(search_url)
    sub_pages = []
    subtitles = data.xpath(
        '/html/body/div[@id="stranka"]/center/table[2]//tr/td[2]//table//tr[position()>1]')

    Log("subtitles count %d", len(subtitles))

    for subtitle in subtitles:
        release_group_line = subtitle.xpath('string(./td[2])')
        match_object = re.search("\(([a-zA-Z0-9-, ]+)\)", release_group_line, re.M | re.I)

        url = subtitle.xpath('./td[7]/a[2]/@href')

        if not match_object or len(url) == 0:
            continue

        Log("Subtitle: %s" % url[0])
        Log("Release Group: %s" % match_object.group(1))
        sub_pages.append(SubMetaInfo(url[0], match_object.group(1).split(', ')))

    return sub_pages


def search_subs(params, lang):
    # Sort the results in order of most downloaded first
    params['nyelvtipus'] = '1' if (lang == 'hu') else '2' if (lang == "en") else '%'

    search_url = SEARCH_PAGE + urllib.urlencode(params)

    sub_pages = simple_search(search_url)

    # Only get the five first subs for vague matches
    return sub_pages[0:5]


def download_subs_as_zip(url):
    Log("Download sub as zip: %s" % url)

    zip_files = []

    zip_file = Archive.ZipFromURL(url)
    zip_files.append(zip_file)

    return zip_files


def get_files_in_zip_file(zip_file):
    files = []
    for name in zip_file:
        Log("Name in zip: %s" % repr(name))
        if name[-1] == "/":
            # Ignore folder
            continue

        sub_data = zip_file[name]
        files.append((name, sub_data))

    return files


def get_subs_for_part(media_info, data):
    sub_info_list = []
    for lang in get_language_list():
        subs = search_subs(data, lang)
        for sub in subs:
            has_match = find_release_match(media_info, sub.releaseGroups)

            Log("find subtitle for this release %s %s %s" % (has_match, media_info.filename, sub.releaseGroups))
            if not has_match:
                continue

            zip_files = download_subs_as_zip(sub.url)
            for zipFile in zip_files:
                files = get_files_in_zip_file(zipFile)
                for f in files:
                    (name, subData) = f
                    si = SubInfo(lang, sub.url, subData, name)
                    sub_info_list.append(si)
    return sub_info_list


def find_release_match(media_info, release_groups):

    for releaseGroup in release_groups:
        count = 0
        release_group_items = releaseGroup.replace('-', ' ').split(' ')
        for item in release_group_items:
            # Log("find %s release in %s" % (item, media_info.filename))
            if item.lower() in media_info.filename.lower():
                count = count + 1

        if count == len(release_group_items):
            return True

    return False


def ignore_search(filename):
    path = os.path.dirname(filename)
    ignore_path = os.path.join(path, IGNORE_FILE)

    if os.path.exists(ignore_path):
        return True
    return False


# Fallback method if keyword search doesn't return anything
def media_info_search(media_info):
    data = {}

    Log("Detailed search for:")
    media_info.print_me()

    if media_info.name:
        data["cim"] = media_info.name

    if media_info.season:
        data["evad"] = "s%s" % media_info.season.zfill(2)

    if media_info.episode:
        data["resz"] = "e%s" % media_info.episode.zfill(2)

    return get_subs_for_part(media_info, data)


def handle_media_info(media_info, part):
    if not ignore_search(media_info.filename):

        sub_info_list = media_info_search(media_info)

        for si in sub_info_list:
            Log(Locale.Language.Match(si.lang))
            part.subtitles[Locale.Language.Match(si.lang)][si.url] = Proxy.Media(si.sub, ext=si.ext, format=si.ext)

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
        Log("ReleaseGroup: %s" % self.releaseGroup)
        Log("Season: %s " % self.season)
        Log("Episode: %s " % self.episode)


def get_metadata_xml(media_id):
    url = METADATA_URL + media_id
    Log(url)
    elem = XML.ElementFromURL(url)
    return elem


def get_tv_show_info(media):
    i = MediaInfo(media.title, False)

    elem = get_metadata_xml(media.id)
    year = elem.xpath("//Directory/@year")
    if len(year) > 0:
        i.year = year[0]

    return i


class HunSubAgentTvShows(Agent.TV_Shows):
    name = 'HunSub TV Subtitles'
    languages = [Locale.Language.English]
    primary_provider = False
    contributes_to = ['com.plexapp.agents.thetvdb', 'com.plexapp.agents.themoviedb']


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
