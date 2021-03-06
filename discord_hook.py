from json import dumps
from subprocess import check_output
from os import path
from dateutil import parser

import xml.etree.ElementTree as ElementTree
import sys, requests, re, datetime, argparse

def parse_args():
    parser = argparse.ArgumentParser(description='Executes a Discordwebhook')
    parser.add_argument('repo', help='repository')
    parser.add_argument('rev', help='svn revision')
    parser.add_argument('webhookfile', help='webhookfile with a list of webhookurls')
    parser.add_argument('-acls', '--accesslist', help='list containing steamid\'s')

    args = parser.parse_args()

    repo = args.repo
    rev = args.rev
    webhookfile = args.webhookfile
    acls = args.accesslist

    return repo, rev, webhookfile, acls

_repos, _rev, _wf, _acls = parse_args()

if not path.exists(_wf):
    exit('Webhookfile does not exist.')

webhook_urls = [line.rstrip('\n') for line in open(_wf)]

def svnl(method, *args):
    '''svnlook'''
    args = list(args)
    return check_output(['svnlook', method, path.abspath(_repos), '--revision', _rev] + args ).rstrip()

def date_handler(obj): return (
    obj.isoformat()
    if isinstance(obj, datetime.datetime)
    or isinstance(obj, datetime.date)
    else None
)

# Color shit

def rgb_to_int(red, green, blue):
    return red * 65536 + green * 256 + blue


def clamp(n, minn, maxn):
    return max(min(maxn, n), minn)

color = [50, 50, 50]
modifier = 75

# how 2 python

def A():
    i = color[1] + modifier
    s = clamp(i, 0, 255)
    color[1] = s

def D():
    i = color[0] + modifier
    s = clamp(i, 0, 255)
    color[0] = s

def U():
    i = color[2] + modifier
    s = clamp(i, 0, 255)
    color[2] = s

_changed = svnl('changed', '--copy-info')

# this is so bad
for line in _changed.split('\n'):
    if line[0][0] == 'A':
        A()
    elif line[0][0] == 'D':
        D()
    elif line[0][0] == 'U':
        U()

author = svnl('author')
avatar = None
date = re.sub('(\s\(.+\))', '', svnl('date'))
raw_diff = svnl('diff', '--diff-copy-from' , '--no-diff-deleted', '--no-diff-added', '-x -w -u --ignore-eol-style')
diff = raw_diff[:1990] + "\n. . ." if len(raw_diff) > 1990 else raw_diff
repo = path.basename(path.abspath(_repos))
log = svnl('log')
urls = ''
for f in _changed.split('\n'):
    urls += f + '\n'

# steamid thing
if _acls is not None and path.exists(_acls):
    steam_id = ''

    with open(path.abspath(_acls)) as fp:
        for line in fp:
            if author in line:
                steam_id = line[:line.find(',')]


    profile = 'https://steamcommunity.com/profiles/' + steam_id

    # avatar or something
    try:
        steam_data = requests.get(profile + '?xml=1').content
        tree = ElementTree.fromstring(steam_data)
        avatar = tree[8].text  # magic number don't ask
    except xml.ElementTree.ParserError:
        pass

def iconurl(repo):
    return {
    #    'srvaddons': '',
    #    'QBox': '',
    }.get(repo, 'https://cdn.discordapp.com/avatars/314512567748001793/c5725b2d79c9081dae9d842ccb3d6dff.png')

d = {
    'username': author,
    'avatar_url': avatar if avatar else 'https://metastruct.net/static/DefaultSteamAvatar.png',
    'content': log,
    'embeds': [
        {
            'fields': [
            ],
            'footer': {
                'text': repo + ' (rev. ' + _rev + ')',
                'icon_url': iconurl(repo)
            },
            #2010-02-15 20:10:20 +0000 (Mon, 15 Feb 2010)
            'timestamp': parser.parse(date),
            'color': rgb_to_int(color[0], color[1], color[2])
        }
    ]
}
if diff:
    d['embeds'][0]['description'] = '```diff\n' + diff + '```'

shit = [tuple(urls.split('\n')[i:i+10]) for i in range(0, len(urls), 25)]

for x in shit:
    if x: # because shit can be empty
        d['embeds'][0]['fields'].append({'name': '---', 'value': '\n'.join(map(str, x))})

headers = {'content-type': 'application/json'}
for webhook in webhook_urls:
    requests.post(webhook, data=dumps(d, default=date_handler), headers=headers)