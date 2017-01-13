import subprocess
import csv
import sys
import requests
from ConfigParser import SafeConfigParser
import simplejson

"""
    Arguments:
        1: org name (usc-csci104-spring2015)
        2. csv of all students (spec below)
        3. repo prefix (e.g., hw, project)

    CSV file:
        each row = student
        columns = github username, usc username
"""


ORG_NAME = sys.argv[1]
CSV_FILENAME = sys.argv[2]
REPO_PREFIX = sys.argv[3] + '-'
HOOK_URL = 'http://bits.usc.edu/cs104-hooks/push.php'
SSH_KEY = '~/.ssh/usc-csci104-bot_id_rsa'

TEMP_REPOS_DIR = 'temp_repos'
SKELETON_REPO_DIR = 'skeleton_repo'

parser = SafeConfigParser()
parser.read("github_account.conf")
bot_username = parser.get('github', 'username')
bot_password = parser.get('github', 'password')
hook_secret = parser.get('github', 'hook_secret')


def hint(text, color='34'):
    return '\t\033[{}m{}\033[0m'.format(color, text)


def shell(command, cwd=None):
    if cwd is None:
        print hint('/: ' + command)
    else:
        print hint(cwd + '/: ' + command)

    shell_output = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, cwd=cwd)
    return shell_output.communicate()[0]


def github_req(url, payload, method='POST'):
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


def create_repo(repo_name, private=True):
    payload = {'name': repo_name, 'private': private}

    res = github_req('/orgs/' + ORG_NAME + '/repos', payload)
    if res is not None:
        return res['name']
    else:
        return None


def add_repo_hook(repo_name, hook_url, hook_type='json', insecure='1'):
    payload = {
        'name': 'web',
        'active': True,
        'config': {
            'url': hook_url,
            'content_type': hook_type,
            'secret': hook_secret,
            'insecure_ssl': insecure
        }
    }
    res = github_req('/repos/' + ORG_NAME + '/' + repo_name + '/hooks', payload)
    if res is not None:
        return res['id']
    else:
        return None


def create_team(team_name, permission='push'):
    payload = {'name': team_name, 'permission': permission}
    res = github_req('/orgs/' + ORG_NAME + '/teams', payload)
    if res is not None:
        return res['id']
    else:
        return None


def add_team_member(team_id, member_username):
    res = github_req('/teams/' + str(team_id) + '/memberships/' + member_username, None, 'PUT')
    return res is not None


def add_team_repo(team_id, repo_name):
    res = github_req('/teams/' + str(team_id) + '/repos/' + ORG_NAME + '/' + repo_name, None, 'PUT')
    return res is not None


def find_team_id(team_name):
    res = github_req('/orgs/' + ORG_NAME + '/teams', None, 'GET')
    for team in res:
        if team['name'] == team_name:
            return team['id']

    return None

"""
==================
BEGIN SCRAPING
==================
"""

graders_team_id = find_team_id('Graders')
#teaching_staff_team_id = find_team_id('TeachingStaff')
students_team_id = find_team_id('Students')

shell('eval "$(ssh-agent)"')
shell('ssh-add -D')
shell('ssh-add ' + SSH_KEY)
shell('mkdir ' + TEMP_REPOS_DIR)

with open(CSV_FILENAME, 'r') as csvfile:
    reader = csv.reader(csvfile)
    total = 0

    for row in reader:
        gh_username = row[0]
        usc_username = row[1]
        repo_name = REPO_PREFIX + usc_username

        print 'Processing {}, {}'.format(gh_username, usc_username)
        print gh_username, usc_username, repo_name
        print hint('Creating team', 36)
        student_team_id = create_team('student_' + usc_username)
        print hint('Adding student to individual team', 36)
        add_team_member(student_team_id, gh_username)
        print hint('Adding student to team students', 36)
        add_team_member(students_team_id, gh_username)

        print hint('Creating repo', 36)
        create_repo(repo_name)
        print hint('Adding student team to repo', 36)
        add_team_repo(student_team_id, repo_name)
        print hint('Adding staff team to repo', 36)
        add_team_repo(teaching_staff_team_id, repo_name)
        print hint('Adding graders team to repo', 36)
        add_team_repo(graders_team_id, repo_name)
        print hint('Adding hook to repo', 36)
        add_repo_hook(repo_name, HOOK_URL)

        print hint('Preparing initial repo', 36)
        current_repo_dir = TEMP_REPOS_DIR + '/' + repo_name
        shell('mkdir ' + repo_name, TEMP_REPOS_DIR)
        shell('git init', current_repo_dir)
        shell('cp -r ' + SKELETON_REPO_DIR + '/* ' + current_repo_dir + '/')
        shell('git add --all', current_repo_dir)
        shell('git commit -m "Initial commit"', current_repo_dir)
        shell('git remote add origin git@github.com:' + ORG_NAME + '/' + repo_name, current_repo_dir)
        shell('git push origin master -q', current_repo_dir)

        total += 1

    print '---------------------'

print 'Total {} repositories created.'.format(total)

shell('rm -rf ' + TEMP_REPOS_DIR)
shell('ssh-add -D')
shell('ssh-add')
