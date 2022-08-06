#!/usr/bin/env python3

__copyright__ = "Copyright (C) 2022 Roberto Di Cosmo"
__license__ = "GPL-3.0-or-later"

import sys
import dateutil.parser
import datetime
from datetime import datetime
from dateutil.tz import tzutc
import requests
import re
import time
from itertools import islice
from swh.web.client.client import WebAPIClient

import click

# global variable holding headers parameters
headers={}
swhcli={}

def swhstatus(projecturl,lastcdate):
   global swhcli
   try:
      d=swhcli.last_visit(projecturl)
      swhlastvisit=d['date']
      status=d['status']
      lastcommitdate=(datetime.strptime(lastcdate,'%Y-%m-%dT%H:%M:%SZ')).replace(tzinfo=tzutc())
      if (swhlastvisit >= lastcommitdate and status == "full"):
          return([swhlastvisit,status,"UPTODATE"])
      if (status =="full"):
          return([swhlastvisit,status,"TOUPDATE"])
      else:
          return([swhlastvisit,status,"FAILED"])
   except:
       return(['','','NOTINSWH'])
   
def latestCommitInfo(u, r):
    """ Get info about the latest commit of a GitHub repo """
    global headers
    url='https://api.github.com/repos/{}/{}/commits?per_page=1'.format(u, r)
    rawrepourl="https://github.com/{}/{}".format(u,r)
    canonurl='https://api.github.com/repos/{}/{}'.format(u, r)
    response = requests.get(url,headers=headers)
    if (response.status_code==200):
      commit = response.json()[0]
      commit['number'] = re.search('\d+$', response.links['last']['url']).group()
      lastcommitdate = ((commit['commit'])['author'])['date']
      # get the info on the repository
      repoinfo=requests.get(canonurl,headers=headers).json()
      # get the canonical name from GitHub
      canonicalurl = repoinfo['html_url']
      # get the number of stars
      try:
         stars=repoinfo['stargazers_count']
      except:
         stars=''
      # see if it is a fork
      try:
         forkurl=repoinfo['parent']['html_url']
         sourceurl=repoinfo['source']['html_url']
      except:
         forkurl=''
         sourceurl=''
      if (forkurl==''):
         isfork=''
      else:
         isfork='ISFORK'
      # check presence in SWH
      [swhlastvisit,visitstatus,status]=swhstatus(canonicalurl,lastcommitdate)
      print("{};{};{};{};{};{};{};{};{};{}".format(
              canonicalurl,
              commit['number'],
              lastcommitdate,
              swhlastvisit,
              visitstatus,
              status,
              isfork,
              forkurl,
              sourceurl,
              stars,
              flush=True
            ))
      return([200,canonicalurl])
    elif (response.status_code==404):
      print(rawrepourl+";NOTINGITHUB")
    elif (response.status_code==451):
      print(rawrepourl+";NOWPRIVATEINGITHUB")
    elif (response.status_code==403):
      print("Got 403, probably no more steam: limit {}, remaining {}\n".
          format(response.headers['x-ratelimit-limit'],
                 response.headers['x-ratelimit-remaining']
                 )
            +"Restart from: " + rawrepourl,
            file=sys.stderr
          )
      return([403,rawrepourl,response.headers['x-ratelimit-remaining']])
    else:
      print(response.status_code,file=sys.stderr,flush=True)
      return([response.status_code,rawrepourl])
    return([200,rawrepourl])

# default base URL for GitHub repositories
BASE_URL = "https://github.com/"

# default batch size for accessing the repository API
BATCH_SIZE = 50;

# Click docs: https://click.palletsprojects.com/en/8.0.x/options/
@click.command(
    help="""UNIX filter that gets the number of commits and last commit date
    about a list of GitHub repository URLS, one per line.

    You can pass "-" to read repository URLS from standard input."""
)
@click.option(
    "-b",
    "--base-url",
    default=BASE_URL,
    metavar="BASEURL",
    show_default=True,
    help="base URL for the repositories in the argument list",
)
@click.option(
    "-s",
    "--batch-size",
    default=BATCH_SIZE,
    metavar="BATCHSIZE",
    type=int,
    show_default=True,
    help="requests up to SIZE repo information from GitHub at the same time",
)
@click.option(
    "-w",
    "--wait-time",
    default=1800, # time to reload rate limit for non authenticated GH users
    metavar="THROTTLETIME",
    type=int,
    show_default=True,
    help="requests up to SIZE repo information from GitHub at the same time",
)
@click.option(
    "-t",
    "--bearer-token",
    default="",
    metavar="FORGETOKEN",
    show_default=True,
    help="bearer token to bypass forge rate limit",
)
@click.option(
    "-a",
    "--swh-bearer-token",
    default="",
    metavar="SWHTOKEN",
    show_default=True,
    help="bearer token to bypass SWH API rate limit",
)
@click.argument("repo_list", type=click.File("rt"), required=True)
def main(repo_list,batch_size,base_url,wait_time,bearer_token,swh_bearer_token):
    global headers
    global swhcli
    if (swh_bearer_token):
       swhcli = WebAPIClient(api_url="https://archive.softwareheritage.org/api/1/",
                             bearer_token=swh_bearer_token)
    else:
       swhcli = WebAPIClient(api_url="https://archive.softwareheritage.org/api/1/")
    if (bearer_token):
        headers["Authorization"] = "Bearer "+bearer_token
    repos = (line.rstrip() for line in repo_list)
    # we assume each line is of the form "https://github.com/user/repository"
    for repo in repos:
     try:
      u,r,*rest=repo.replace(base_url,"").split("/")
      if (len(rest) > 0):
          print("Check repo : "+ repo + " u="+u+" r="+r, file=sys.stderr)         
          # if rate limit is hit, repeat until it succeeds (wait time is required)
      while True:
         status,repourl,*rest=latestCommitInfo(u,r)
         if (status == 403):
          [rateleft]=rest
          if (int(rateleft) == 0):
             print("Sleeping for : "+ str(wait_time) +" seconds", file=sys.stderr)
             time.sleep(wait_time)
          else:
             print("Skipping repository : "+ repourl + "; raised 403 with " + str(rateleft) +" API ratelimit", file=sys.stderr)
             break
         else:
          break
     except:
             print("Skipping repository : "+ repo + " - raised exception", file=sys.stderr)

if __name__ == "__main__":
    main()

