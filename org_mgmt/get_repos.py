import csv
import sys
import requests
from ConfigParser import SafeConfigParser
import simplejson

# This file obtains all repos and students in a certain organization with a particular prefix, and outputs it to a CSV.

ORG_NAME = sys.argv[1] # e.g. usc-csci350-spring2016
CSV_FILENAME = sys.argv[2] # e.g. output.csv
REPO_PREFIX = sys.argv[3] + '-' # e.g. hw
STUDENT_TEAM_NAME = 'student'

# Get Github Account Info
parser = SafeConfigParser()
parser.read("github_account.conf")
bot_username = parser.get('github', 'username')
bot_password = parser.get('github', 'password')

def hint(text, color='34'):
    return '\t\033[{}m{}\033[0m'.format(color, text)

def github_req(url, payload, method='GET'):
    github_base = 'https://api.github.com'
    print hint('[{}] {}{}'.format(method, github_base, url))

    r = requests.request(method=method,
                         url=github_base + url,
                         data=simplejson.dumps(payload),
                         auth=(bot_username, bot_password))
    try:
        res = simplejson.loads(r.content)
    except:
        res = {}

    while 'next' in r.links:
        print hint('[{}] {}{}'.format(method, r.links['next']['url'], url))
        r = requests.request(method=method,
                             url=r.links['next']['url'],
                             data=simplejson.dumps(payload),
                             auth=(bot_username, bot_password))
        try:
            res += simplejson.loads(r.content)
        except:
            res = {}

    if 200 <= r.status_code < 300:
        return res
    else:
        print res
        details = ""
        if "errors" in res:
            for e in res["errors"]:
                details += "{}.{}: {}.".format(e["resource"], e["field"], e["code"])
        print "[ERROR][HTTP {}] {} - {}".format(r.status_code, res['message'] if 'message' in res else '', details)
        return None


def get_all_repos():
    return github_req('/orgs/' + ORG_NAME + '/repos', None, 'GET')

def get_teams_of_repo(repoName):
    return github_req('/repos/' + ORG_NAME + '/' + repoName + '/teams', None, 'GET')

def get_members_of_team(teamId):
    return github_req('/teams/' + teamId + '/members', None, 'GET')

def find_students_in_repo(repoName):
    teamsRes = get_teams_of_repo(repoName)
    for team in teamsRes:
        if team['name'].startswith(STUDENT_TEAM_NAME):
            membersRes = get_members_of_team(str(team['id']))
            memberslist = []
            for member in membersRes:
                memberslist.append(member['login'])
            return memberslist
    return []

def filter_repos(repos):
    return [repo for repo in repos if repo['name'].startswith(REPO_PREFIX)]


def create_csv(repos):
    with open(CSV_FILENAME, 'wb') as csvfile:
        writer = csv.writer(csvfile)
        for repo in repos:
            csvrow = find_students_in_repo(repo['name']) + [repo['name']]
            writer.writerow(csvrow)


repos = filter_repos(get_all_repos())
create_csv(repos)


