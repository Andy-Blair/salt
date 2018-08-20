#!/usr/bin/python
# _*_ coding:utf-8 _*_

import shutil
import os
import sys
reload(sys)
sys.setdefaultencoding('utf8')

if sys.platform == 'win32':
    os.environ["PATH"] = os.environ["PATH"] + ";C:\\Program Files\\Git\\cmd;"
    os.environ["HOME"] = "C:\\Users\\app"
from git import *

git_url = ""
git_path = ""
lweb_path = "/apps/product/tomcat/webapps/"
if sys.platform != 'win32':
    file_path = os.path.split(os.path.realpath(__file__))
    git_path = file_path[0] + "/%s" % file_path[1].split(".")[0]
used_branch = ""
remote_repo_name = "online"
operator = sys.argv[1]
try:
    commit_id = sys.argv[2]
except Exception:
    commit_id = None
if not os.path.isdir(git_path):
    if os.path.isfile(git_path):
        os.remove(git_path)
    os.makedirs(git_path)
g = Git(working_dir=git_path)
config = g.config("-l").splitlines()
if "user.email=jenkins@jingzhengu.com" not in config or "user.name=jenkins" not in config:
    g.config("--global", "user.email", "jenkins@jingzhengu.com")
    g.config("--global", "user.name", "jenkins")
re_init = False
try:
    g.rev_parse("--is-inside-work-tree")
    remote_repo_url = g.remote("-v").splitlines()[0].split()[1]
    if remote_repo_url != git_url:
        re_init = True
except Exception:
    re_init = True
if re_init:
    dir_list = os.listdir(git_path)
    for d in dir_list:
        f = os.path.join(git_path, d)
        if os.path.isdir(f):
            shutil.rmtree(f)
        elif os.path.isfile(f):
            os.remove(f)
    g.init()
    g.remote("add", remote_repo_name, git_url)
    g.fetch(remote_repo_name, used_branch)
    g.checkout(used_branch)
    if operator == "rollback":
        g.reset("--hard", commit_id)
else:
    cur_branch = g.symbolic_ref("--short", "-q", "HEAD")
    if cur_branch != used_branch:
        g.checkout(used_branch)
    if operator == "rollback":
        g.reset("--hard", commit_id)
    else:
        try:
            g.pull(remote_repo_name, used_branch)
        except Exception:
            g.reset("--hard", "%s/%s" % (remote_repo_name, used_branch))
            g.pull(remote_repo_name, used_branch)

print g.log("-n", "1").splitlines()[0].split()[1]

if sys.platform != 'win32':
    os.popen("cp -r %s/* %s" % (git_path, lweb_path))
