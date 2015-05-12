import subprocess
import csv
import sys
import datetime
import dateutil.parser
import requests
import os
from ConfigParser import SafeConfigParser
import simplejson

"""
	ARGVS:
	1 - "repos.csv"

	NEED:
	- github_account.conf
"""

ORG_NAME = 'usc-csci104-spring2015'
CSV_FILENAME = sys.argv[1]

parser = SafeConfigParser()
parser.read("github_account.conf")
githubUsername = parser.get("github", "username")
githubPassword = parser.get("github", "password")

def hint(text, color='34'):
	return '\t\033[{}m{}\033[0m'.format(color, text)

def githubPost(url, payload):
	""" Send a POST request to GitHub via API """
	r = requests.post(url, data=simplejson.dumps(payload), auth=(githubUsername, githubPassword))
	res = simplejson.loads(r.content)
	if r.status_code == 201 or r.status_code == 200:
		return res
	else:
		details = ""
		if "errors" in res:
			for e in res["errors"]:
				details += "{}.{}: {}.".format(e["resource"], e["field"], e["code"])
		print "[ERROR][HTTP {}] {} - {}".format(r.status_code, res["message"], details)
		return None

def githubPatch(url, payload):
	""" Send a POST request to GitHub via API """
	r = requests.patch(url, data=simplejson.dumps(payload), auth=(githubUsername, githubPassword))
	res = simplejson.loads(r.content)
	if r.status_code == 201 or r.status_code == 200:
		return res
	else:
		details = ""
		if "errors" in res:
			for e in res["errors"]:
				details += "{}.{}: {}.".format(e["resource"], e["field"], e["code"])
		print "[ERROR][HTTP {}] {} - {}".format(r.status_code, res["message"], details)
		return None

def githubGet(url):
	""" Send a POST request to GitHub via API """
	r = requests.get(url, auth=(githubUsername, githubPassword))
	res = simplejson.loads(r.content)
	if r.status_code == 201 or r.status_code == 200:
		return res
	else:
		details = ""
		if "errors" in res:
			for e in res["errors"]:
				details += "{}.{}: {}.".format(e["resource"], e["field"], e["code"])
		print "[ERROR][HTTP {}] {} - {}".format(r.status_code, res["message"], details)
		return None

def closeIssue(repoName, issueNumber):
	orgName = ORG_NAME

	payload = {"body": "I'm automatically closing this issue now since there has not been any activity for three weeks."}
	# payload = {"body": "My apologies. This issue was created by mistake."}

	res = githubPost("https://api.github.com/repos/{}/{}/issues/{}/comments".format(orgName, repoName, issueNumber), payload)
	if res != None:
		print hint("[COMMENT ISSUE] #{} in {}".format(issueNumber, repoName), '32')
	else:
		print hint("[ERROR][COMMENT ISSUE] Failed to close {} in {}".format(issueNumber, repoName), '31')

	payload = {"state": "closed"}
	res = githubPatch("https://api.github.com/repos/{}/{}/issues/{}".format(orgName, repoName, issueNumber), payload)
	if res != None:
		print hint("[CLOSED ISSUE] #{} \"{}\" in {}".format(res["number"], res["title"], repoName), '32')
		return res["number"]
	else:
		print hint("[ERROR][CREATE ISSUE] Failed to close {} in {}".format(issueNumber, repoName), '31')


"""
==================
BEGIN SCRAPING
==================
"""
with open(CSV_FILENAME, 'r') as csvfile:
	reader = csv.reader(csvfile)
	total = 0
	totalIssues = 0

	now = datetime.datetime.now()
	two_weeks = datetime.timedelta(weeks=2)
	three_weeks = datetime.timedelta(weeks=3)

	"""
	each row should have:
	repo_name, github_username
	"""
	for row in reader:
		if len(row) is 1:
			continue

		github_username = row[0]
		repo_name = row[1]



		print '---------------------'
		print '> Processing ' + repo_name

		
		issues = githubGet("https://api.github.com/repos/{}/{}/issues".format(ORG_NAME, repo_name))
		total_issues_count = len(issues)
		closed_issues_count = 0
		for issue in issues:
			# Uncomment next line to close all submission confirmations
			# if 'Submission Confirmation for HW4' in issue['title'] or 'Re-submission Confirmation' in issue['title']:
			# if 'Submission Confirmation for HW4' in issue['title']:

			# Uncomment next two lines to close all comment = 0 issues
			issue_updated_date = dateutil.parser.parse(issue['updated_at'])
			if issue['comments'] == 0 and issue_updated_date.replace(tzinfo=None) < now - three_weeks:
				closeIssue(repo_name, issue['number'])
				totalIssues += 1
				closed_issues_count += 1

		print '> Closed {} out of {} issues in total'.format(closed_issues_count, total_issues_count)
		total += 1

	print '---------------------'


	print '====================='
	print 'Complete. {} repositories cleaned. {} issues closed'.format(total, totalIssues)
	print '====================='
