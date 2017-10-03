from json import dumps
from subprocess import check_output
from os import path
import xml.etree.ElementTree as ElementTree
import sys
import datetime
import requests

_path = path.join(sys.path[0], 'webhookurl.txt')

with open(_path, 'r') as f:
    webhook_url = f.read()

if not webhook_url:
    quit()

_repos = sys.argv[1]
_rev = sys.argv[2]

def svnl(method, *args):
    '''svnlook'''
    args = list(args)
    return check_output(['svnlook', method, _repos, '--revision', _rev] + args ).rstrip()

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

color = [79, 84, 92]
modifier = 50

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

Author = svnl('author')
Diff = svnl('diff', '--no-diff-deleted', '--no-diff-added')[:1990]
Repo = path.basename(_repos)
Log = svnl('log')
Urls = ''
for f in _changed.split('\n'):
    Urls += '['+f+'](svn://svn.metastruct.net/'+Repo+'/'+f.split(' ')[3] + ')\n'

# steamid thing

steam_id = ''

with open('/home/python/.svns/accesslist') as fp:
    for line in fp:
        if Author in line:
            steam_id = line[:line.find(',')]


profile = 'https://steamcommunity.com/profiles/' + steam_id

# avatar or something

steam_data = requests.get(profile + '?xml=1').content
tree = ElementTree.fromstring(steam_data)
avatar = tree[8].text  # magic number don't ask

d = {
    'username': Author,
    'avatar_url': avatar,
    'content': Log,
    'embeds': [
        {
	    'fields': [
		{
			'name': 'Changed Files:',
			'value': Urls,
			'inline': True
		}
	    ],
            'footer': {
                'text': Repo + ' (rev. ' + _rev + ')',
                'icon_url': 'https://cdn.discordapp.com/avatars/314512567748001793/c5725b2d79c9081dae9d842ccb3d6dff.png'
            },
            'timestamp': datetime.datetime.now(),
            'color': rgb_to_int(color[0], color[1], color[2])
        }
    ]
}
if Diff:
    d['embeds'][0]['description'] = '```diff\n' + Diff + '```'
headers = {'content-type': 'application/json'}
requests.post(webhook_url, data=dumps(d, default=date_handler), headers=headers)
