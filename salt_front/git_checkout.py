# _*_ coding: utf-8 _*_
from git import *
import os


def git_checkout( git_url, op):
    '''
    
    :param git_url: 
    :param op: 
    :return: 0-get file success; 1-files don't need update; 2-can't find project
    '''
    work_dir = "/srv/salt/project"
    files = os.listdir(work_dir)
    git_dir_name = git_url.split("/")[-1].split(".")[0]
    git_dir_path = os.path.join(work_dir, git_dir_name)
    if op == "update":
        pull = False
        if git_dir_name in files:
            if os.path.isdir(git_dir_path):
                work_dir = git_dir_path
                pull = True
            else:
                os.remove(git_dir_path)
        g = Git(work_dir)
        if pull:
            diff = g.diff("master", "origin/master")
            if len(diff) == 0:
                return 1
            else:
                g.pull()
                return 0
        else:
            g.clone(git_url)
            return 0
    elif op == "rollback":
        back = False
        if git_dir_name in files:
            if os.path.isdir(git_dir_path):
                work_dir = git_dir_path
                back = True
            else:
                os.remove(git_dir_path)
            g = Git(work_dir)
            if back:
                g.reset("--hard", "HEAD~1")
                return 0
            else:
                return 2
        else:
            return 2


if __name__ == "__main__":
    pass
