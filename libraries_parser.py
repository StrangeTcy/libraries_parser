from bs4 import BeautifulSoup
import urllib.request
import requests
import json

from collections import OrderedDict

import pkgutil
import pickle

import subprocess
import sys

import datetime
import time

from google.cloud import bigquery



TIMING = True


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




def install(libr_name, version):
    print ("Cleaning up any existing versions of this library...")
    subprocess.check_call(["sudo", sys.executable, "-m", "pip", "uninstall", "--yes", libr_name])
    print (f"Installig library {libr_name} ver. {version} ...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", f"{libr_name}=={version}"])
    except:
        print (f"It seems that something went wrong when trying to install {libr_name} ver. {version}. That's bad...")





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

def get_modules(libr_name, version):
    install(libr_name, version)
    exec(our_magic_function.format(libr_name, libr_name, libr_name, libr_name))
    with open(f"{libr_name}_modules.pkl", "rb") as f:
        our_modules = pickle.load(f)
    return our_modules


def get_category(libr_name):
    urllib.request.urlretrieve("https://raw.githubusercontent.com/ivolution-ai/librarian/main/libs/python.json", "python.json")
    # requests.get("https://raw.githubusercontent.com/ivolution-ai/librarian/main/libs/python.json")
    with open("python.json", "r") as f:
        category_list = json.load(f)
    for keyval in category_list:
        if keyval["id"].lower() == f"py.{libr_name.lower()}":
            return keyval["tech"]


def get_releases(libr_name, github_url):
    def helper(commit_string):
        findings = commit_string.find("a",{'href':True})['data-hovercard-url']
        if 'commit' in findings:
            return findings.split('/')[4] 

    def datetime_helper(d):
        result =  d.find('local-time')
        if not result == None:
            return result['datetime']
        else:
            return d.find('relative-time')['datetime']     

    releases_list_final = []
    commits_list_final = []
    release_dates_filtered = []        
    for p in range(10):
        if p == 0 or p == 1:
            releases_url = f"{github_url}/releases"
        else:
            releases_url = f"{github_url}/releases?page={p}"    
        releases_page = requests.get(releases_url)
        releases_soup = BeautifulSoup(releases_page.content, "html.parser")
        releases_text = releases_soup.findAll(text=True)
        if "There aren’t any releases here" in releases_text:
            print ("We've run out of pages")
        else:
            release_dates = releases_soup.find_all("div", {"class":"mb-2 f4 mr-3 mr-md-0 col-12"})
            release_dates_filtered_ = [datetime_helper(d) for d in release_dates]
            print (f"Our release dates are: {release_dates_filtered} of len {len(release_dates_filtered)}")
            releases_list = releases_soup.find_all("div", {"class":"mr-3 mr-md-0 d-flex"})
            commits_list = releases_soup.find_all("div", {"class":"mb-md-2 mr-3 mr-md-0"})
            releases_list_final_ = [r.find("span", {"class":"ml-1 wb-break-all"}).text.strip("\n      ") for r in releases_list]
            commits_list_final_ = [helper(c) for c in commits_list]
            commits_list_final_ = list(filter(None, commits_list_final_))
            print (f"We have releases {releases_list_final} of len {len(releases_list_final)} and commits {commits_list_final} of len {len(commits_list_final)}")
            release_dates_filtered.extend(release_dates_filtered_)
            releases_list_final.extend(releases_list_final_)
            commits_list_final.extend(commits_list_final_)

    magic_release_commit_dates = (zip(releases_list_final, commits_list_final, release_dates_filtered))
    return magic_release_commit_dates


def get_dependencies(libr_name, version):
    package_json = requests.get(f'https://pypi.org/pypi/{libr_name}/{version}/json', verify = False).json()
    return package_json['info']['requires_dist']


def  get_dependents(libr_name):
    dependents_url = f"https://libraries.io/pypi/{libr_name}/dependents"
    dependents_page = requests.get(dependents_url)
    dependents_soup = BeautifulSoup(dependents_page.content, "html.parser")
    dependents_list = dependents_soup.find_all("div", {"class":"project"})
    dependents_list_final = [d.find("a").text for d in dependents_list]   
    print (f"Library {libr_name} is being depended on by these libraries: {dependents_list_final}")
    # input ("Are we cool yet?")
    if not dependents_list_final == []:
        return dependents_list_final
    else:
        return ["!!This needs further work"]


def form_releases(commit_list, libr_name):
    versions__list = []
    for c in commit_list:
        
        version_dict = \
        {
        "version": c[0],
        "commit":c[1],
        "date":c[2],
        "methods": get_modules(libr_name, c[0])
        }
        versions__list.append(version_dict)
    return versions__list    
    



def get_libraries_attrs(libr_name):
    start_time = time.time()

    basic_url = "https://pypi.org/"
    libr_page_url = basic_url+"project/"+libr_name
    print (f"Getting page {libr_page_url}")
    libr_page = requests.get(libr_page_url)
    print ("Parsing page...")
    libr_page_soup = BeautifulSoup(libr_page.text, "html.parser")
    #print (f"We have got the page for {libr_name}, and it's {libr_page_soup}")
    
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
    plain_github_url = github_data['html_url']


    libr_dependencies = get_dependencies(libr_name, libr_version)
    libr_dependents = get_dependents(libr_name)
    
     
    libr_tech = "blablabla"
    libr_category = get_category(libr_name) #???
    libr_status = "not ready yet"
    rel_com_dates = get_releases(libr_name, plain_github_url)
        

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
                              form_releases(rel_com_dates, libr_name)
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
    time_it_took = str(datetime.timedelta(second=(time.time() - start_time)))
    print (f"It took us {time_it_took} to collect all that data. Saving...")
    with open(f"{libr_name}_everything.json", "w") as f:
        f.write(attrs_json)



if __name__ == "__main__":
    get_libraries_attrs("numpy")    
