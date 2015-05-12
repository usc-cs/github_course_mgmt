import subprocess
import csv
import sys
import datetime
import requests
import os
from ConfigParser import SafeConfigParser
import simplejson

"""
	ARGVS:
	1 - "repos.csv"
	2 - "hw2"
	3 - 2014-09-12T11:59:00-0700

	NEED:
	- github_account.conf
	- repos.csv
	- submissions_readme.md
	- submission_issue.md
	- resubmission_issue.md
"""

ORG_NAME = 'usc-csci104-spring2015'
CSV_FILENAME = sys.argv[1]
HW_NAME = sys.argv[2]
DEADLINE = sys.argv[3]
SUBMISSIONS_DIR_NAME = 'submissions_' + HW_NAME
SUBMISSIONS_DIR = '../../' + SUBMISSIONS_DIR_NAME
SAMPLE_README = 'submissions_readme.md'
SUBMISSION_ISSUE_BODY = open('submission_issue.md', 'r').read()
RESUBMISSION_ISSUE_BODY = open('resubmission_issue.md', 'r').read()

parser = SafeConfigParser()
parser.read("github_account.conf")
githubUsername = parser.get("github", "username")
githubPassword = parser.get("github", "password")

def hint(text, color='34'):
	return '\t\033[{}m{}\033[0m'.format(color, text)

def shell(command, cwd=None):
	if cwd is None:
		print hint('/: ' + command)
	else:
		print hint(cwd + '/: ' + command)

	shell_output = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, cwd=cwd)
	return shell_output.communicate()[0]

def gitHubPost(url, payload):
	""" Send a POST request to GitHub via API """
	r = requests.post(url, data=simplejson.dumps(payload), auth=(githubUsername, githubPassword))
	res = simplejson.loads(r.content)
	if r.status_code == 201:
		return res
	else:
		details = ""
		if "errors" in res:
			for e in res["errors"]:
				details += "{}.{}: {}.".format(e["resource"], e["field"], e["code"])
		print "[ERROR][HTTP {}] {} - {}".format(r.status_code, res["message"], details)
		return None

def addIssue(repoName, issueTitle, issueBody, issueAssignee):
	orgName = ORG_NAME
	payload = {"title":issueTitle, "body":issueBody, "assignee":issueAssignee}

	res = gitHubPost("https://api.github.com/repos/{}/{}/issues".format(orgName, repoName), payload)
	if res != None:
		print hint("[CREATE ISSUE] #{} \"{}\" in {}/{}".format(res["number"], res["title"], orgName, repoName), '32')
		return res["number"]
	else:
		print hint("[ERROR][CREATE ISSUE] Failed to create {} in {}/{}".format(issueTitle, orgName, repoName), '31')



"""
==================
BEGIN SCRAPING
==================
"""
with open(CSV_FILENAME, 'r') as csvfile:
	reader = csv.reader(csvfile)
	has_git_init = os.path.isdir(SUBMISSIONS_DIR + '/.git')
	total = 0

	shell('mkdir ' + SUBMISSIONS_DIR_NAME, '../../')

	if not has_git_init:
		shell('git init', SUBMISSIONS_DIR)

	"""
	each row should have:
	repo_name, github_username, [optional] sha

	if sha is provided, then it will use a resubmission_issue.md for the issue instead
	"""
	for row in reader:
		if len(row) is 1:
			continue

		github_username = row[0]
		repo_name = row[1]
		repo_dir = SUBMISSIONS_DIR + '/' + repo_name

		print '---------------------'
		print '> Processing ' + repo_name

		shell('git submodule add --quiet git@github.com:{}/{}.git'.format(ORG_NAME, repo_name), SUBMISSIONS_DIR)

		if len(row) is 3:
			# if a sha is provided, that means this is a resubmission
			print '> cloning resubmission'
			shell('git pull origin master -q', repo_dir)			
			shell('git fetch -q', repo_dir)			

			sha = row[2]
			issue_body = RESUBMISSION_ISSUE_BODY
			issue_title = 'Re-submission Confirmation for ' + HW_NAME.upper()

			# Uncomment the next two lines for redo submissions
			# issue_body = SUBMISSION_ISSUE_BODY
			# issue_title = 'Submission Confirmation for ' + HW_NAME.upper()

			shell_response = shell('git show {} --pretty=format:"%ad|%cn (%ce)|%s" --quiet | cat'.format(sha), repo_dir)
			date, name, subject = shell_response.split('|', 2)
		else:
			# find the right commit before the deadline and get commit details
			issue_body = SUBMISSION_ISSUE_BODY
			issue_title = 'Submission Confirmation for ' + HW_NAME.upper()

			shell_response = shell('git log --pretty=format:"%H|%ad|%cn (%ce)|%s" -1 --before={} | cat'.format(DEADLINE), repo_dir)
			sha, date, name, subject = shell_response.split('|', 3)

		print '> checking out {}, completed at {}'.format(sha, date)
		shell('git checkout -q {}'.format(sha), repo_dir)

		addIssue(repoName=repo_name,
						 issueTitle=issue_title,
						 issueBody=issue_body.format(HW_NAME.upper(), sha, date, name, subject, repo_name, HW_NAME.lower(), HW_NAME.lower(), sha),
						 issueAssignee=github_username)

		total += 1

	print '---------------------'

	if not has_git_init:
		shell('cp {} {}/README.md'.format(SAMPLE_README, SUBMISSIONS_DIR))

	shell('git add --all', SUBMISSIONS_DIR)
	shell('git commit -m "Repository scrape on {}"'.format(datetime.datetime.now()), SUBMISSIONS_DIR)

	if has_git_init:
		shell('git push origin master', SUBMISSIONS_DIR)
	else:
		shell('git remote add origin git@github.com:{}/{}.git'.format(ORG_NAME, SUBMISSIONS_DIR_NAME), SUBMISSIONS_DIR)
		shell('git push -u -f origin master', SUBMISSIONS_DIR)


	print '====================='
	print 'Complete. {} repositories checked out.'.format(total)
	print '====================='
