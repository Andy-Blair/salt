#!/usr/bin/python
# _*_ coding:utf-8 _*_

import shutil
import os
import sys
reload(sys)
sys.setdefaultencoding('utf8')

if sys.platform == 'win32':
    os.environ["PATH"] = os.environ["PATH"] + "C:\\Program Files\\Git\\cmd;"
    os.environ["HOME"] = "C:\\Users\\app"
from git import *

git_url = ""
git_path = ""
if sys.platform != 'win32':
    lweb_path = git_path
    file_path = os.path.split(os.path.realpath(__file__))
    git_path = file_path[0] + "/%s" % file_path[1].split(".")[0]
    if not os.path.exists(git_path + "/"):
        if os.path.exists(git_path):
            os.remove(git_path)
        os.mkdir(git_path+"/")
used_branch = "jenkins"
remote_repo_name = "online"
operator = sys.argv[1]
try:
    commit_id = sys.argv[2]
except Exception:
    commit_id = None
g = Git(working_dir=git_path)
config = g.config("-l").splitlines()
if "user.email=jenkins@jingzhengu.com" not in config or "user.name=jenkins" not in config:
    g.config("--global","user.email","jenkins@jingzhengu.com")
    g.config("--global","user.name","jenkins")
re_init = False
try:
    g.rev_parse("--is-inside-work-tree")
    remote_repo_url = g.remote("-v").splitlines()[0].split()[1]
    if remote_repo_url != git_url:
        re_init = True
    else:
        local_branch = g.branch().splitlines()
        for i in local_branch:
            if used_branch in i:
                jek_branch = local_branch[local_branch.index(i)].split()
                if len(jek_branch) != 2:
                    g.checkout(used_branch)
            else:
                re_init = True
except:
    re_init = True
if re_init:
    if os.path.isdir(git_path):
        f_list = os.listdir(git_path)
        if len(f_list) > 0:
            for f in f_list:
                filepath = os.path.join(git_path, f)
                if os.path.isfile(filepath):
                    os.remove(filepath)
                elif os.path.isdir(filepath):
                    shutil.rmtree(filepath, True)
    else:
        if os.path.exists(git_path):
            os.remove(git_path)
        os.makedirs(git_path)
    g.init()
    g.remote("add", remote_repo_name, git_url)
    g.fetch(remote_repo_name)
    g.checkout(used_branch)
else:
    if operator =="rollback":
        g.reset("--hard", commit_id)
    else:
        try:
            g.pull(remote_repo_name, used_branch)
        except Exception:
            g.reset("--hard","%s/%s" % (remote_repo_name,used_branch))
            g.pull(remote_repo_name, used_branch)
if sys.platform == 'win32':
    os.popen("icacls %s /setowner app /T /C /L" % git_path)
    os.popen("icacls %s /inheritance:e /T /C /L" % git_path)

print g.log("-n","1").splitlines()[0].split()[1]

if sys.platform != 'win32':
    os.popen("cp -r %s/* %s/" % (git_path, lweb_path))
