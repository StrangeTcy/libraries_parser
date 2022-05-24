from typing import OrderedDict
from bs4 import BeautifulSoup
import urllib.request
import requests
import json

from collections import OrderedDict

import pkgutil
import pickle

from google.cloud import bigquery


# Note: depending on where this code is being run, you may require
# additional authentication. See:
# https://cloud.google.com/bigquery/docs/authentication/
client = bigquery.Client()

def get_weekly_downloads(libr_name, version):
  print (f"get_weekly_downloads has received libr_name {libr_name} and version {version}")
  
  query_job = client.query("""
  SELECT COUNT(*) AS num_downloads
  FROM `bigquery-public-data.pypi.file_downloads`
  WHERE file.project = '{}'
  and file.version = '{}'
    -- Only query the last 30 days of history
    AND DATE(timestamp)
      BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
      AND CURRENT_DATE()""".format(libr_name, version))

  results = query_job.result()  # Waits for job to complete.
  
  for row in results:
      print("{} downloads".format(row.num_downloads))
      return row.num_downloads



our_magic_function = \
"""
import pickle
import {}

modules_list = []

for p in pkgutil.walk_packages({}.__path__, {}.__name__+'.'):
    print ("We have module: {{}}".format(p[1]))
    modules_list.append(p[1])

with open("{}_modules.pkl", "wb") as f:
    pickle.dump(modules_list, f)
"""  

def get_modules(libr_name):
    exec(our_magic_function.format(libr_name, libr_name, libr_name, libr_name))
    with open(f"{libr_name}_modules.pkl", "rb") as f:
        our_modules = pickle.load(f)
    return our_modules

#get_modules("torch")    



def get_category(libr_name):
    
    urllib.request.urlretrieve("https://raw.githubusercontent.com/ivolution-ai/librarian/main/libs/python.json", "python.json")
    # requests.get("https://raw.githubusercontent.com/ivolution-ai/librarian/main/libs/python.json")
    with open("python.json", "r") as f:
        category_list = json.load(f)
    for keyval in category_list:
        if keyval["id"].lower() == f"py.{libr_name.lower()}":
            return keyval["tech"]

def get_releases(libr_name):
    def helper(commit_string):
        findings = commit_string.find("a",{'href':True})['data-hovercard-url']
        if 'commit' in findings:
            return findings.split('/')[4] 

    releases_url = "https://github.com/pytorch/pytorch/releases"
    releases_page = requests.get(releases_url)
    releases_soup = BeautifulSoup(releases_page.content, "html.parser")
    releases_list = releases_soup.find_all("div", {"class":"mr-3 mr-md-0 d-flex"})
    commits_list = releases_soup.find_all("div", {"class":"mb-md-2 mr-3 mr-md-0"})
    releases_list_final = [r.find("span", {"class":"ml-1 wb-break-all"}).text.strip("\n      ") for r in releases_list]
    commits_list_final = [helper(c) for c in commits_list]
    commits_list_final = list(filter(None, commits_list_final))
    print (f"We have releases {releases_list_final} of len {len(releases_list_final)} and commits {commits_list_final} of len {len(commits_list_final)}")
    magic_release_commit_dict = dict(zip(releases_list_final, commits_list_final))
    return magic_release_commit_dict

def get_libraries_attrs(libr_name):
    basic_url = "https://pypi.org/"
    libr_page_url = basic_url+"project/"+libr_name
    print (f"Getting page {libr_page_url}")
    libr_page = requests.get(libr_page_url)
    print ("Parsing page...")
    libr_page_soup = BeautifulSoup(libr_page.text, "html.parser")
    print (f"We have got the page for {libr_name}, and it's {libr_page_soup}")
    
    libr_description = libr_page_soup.find("meta", attrs={'name':'description'})["content"]
    libr_tags = [l.text.strip("\n      ") for l in libr_page_soup.find_all("span", {"class":"package-keyword"})]
    libr_tags = list(OrderedDict.fromkeys(libr_tags))
    print (f"Our tags are: {libr_tags}")
    libr_keywords = libr_tags #TODO
    libr_version = libr_page_soup.find("h1", {"class":"package-header__name"}).text.strip("\n      ").split(" ")[1] #"1.0.0"
    
    libr_topics =  libr_page_soup.find_all("a", href = lambda href: href and "/search/?c=Topic+" in href)
    libr_topics_text = [a.text.strip("\n            ") for a in libr_topics]
    print (f"Found topics {libr_topics_text}")
    github_repo_url = "blablabla" #TODO
    
    github_api_url = libr_page_soup.find("div", {"class":"github-repo-info hidden"})['data-url']
    print (f"Our github url is {github_api_url}")
    github_data = json.loads(requests.get(github_api_url).text)
    print (f"Github has returned the following: {github_data}")
    stars = github_data["stargazers_count"]
    forks =  github_data["forks_count"]
    watch = github_data["watchers_count"]
    print (f"This project has {stars} github stars")
    weekly_downloads = get_weekly_downloads(libr_name, libr_version)
    # libr_popularity = "Quite popular"
    libr_dependencies = "typing-extensions" #TODO
    libr_dependents = "torchvision" #TODO
    libr_methods = get_modules(libr_name)
    libr_tech = "blablabla"
    libr_category = get_category(libr_name) #???
    libr_status = "not ready yet"
    rel_com_dict = get_releases(libr_name)
    version_commit = "blablabla"
    version_date = "blablabla"


    attrs_dict = {"language": "Python",
                  "name": libr_name,
                  "repo": github_repo_url,
                  "imports": [libr_name],
                  "tech": libr_tech,
                  "category": libr_category,
                  "status": libr_status,
                  "githubStars": stars,
                  "githubForks": forks,
                  "githubWatch": watch, 
                  "weeklyDownloads":weekly_downloads,
                  "releases":[
                              {
                                "version": libr_version,
                                "commit":version_commit,
                                "date":version_date,
                                "methods": libr_methods
                               }
                  ],
                  "dependencies": libr_dependencies,
                  "dependents": libr_dependents,
                  "packageKeywords": libr_keywords,
                  "packageTopics": libr_topics_text,
                  "githubTopics":github_data["topics"],
                  "description": libr_description,
                  "updatedAt": "2016-04-08T15:06:21.595Z",
                  "tags": libr_tags
                  }
    attrs_json = json.dumps(attrs_dict, indent=4)
    print (f"Our library has these attributes: {attrs_json}")



if __name__ == "__main__":
    get_libraries_attrs("torch")    
