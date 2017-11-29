# _*_ coding: utf-8 _*_
from git import *
import os
import shutil


def git_checkout( git_url, op):
    '''
    :param git_url: The address of the remote repository SSH protocol 
    :param op: update or rollback
    :return: 0-download file success; 1-download file faild
    '''
    work_dir = "/srv/salt/project"
    remote_repo_name = "origin"
    used_branch = "jenkins"
    git_dir_name = git_url.split("/")[-1].split(".")[0]
    git_dir_path = os.path.join(work_dir, git_dir_name)
    g = Git(git_dir_path)
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
        if os.path.isdir(git_dir_path):
            f_list = os.listdir(git_dir_path)
            if len(f_list) > 0:
                for f in f_list:
                    filepath = os.path.join(git_dir_path, f)
                    if os.path.isfile(filepath):
                        os.remove(filepath)
                    elif os.path.isdir(filepath):
                        shutil.rmtree(filepath, True)
        else:
            if os.path.exists(git_dir_path):
                os.remove(git_dir_path)
            os.makedirs(git_dir_path)
        try:
            g.init()
            g.remote("add", remote_repo_name, git_url)
            g.fetch(remote_repo_name)
            g.checkout(used_branch)
        except:
            return 1
    if op == "update":
        diff = g.diff(used_branch, "%s/%s" % (remote_repo_name, used_branch))
        if len(diff) == 0:
            return 0
        else:
            g.pull(remote_repo_name, used_branch)
            return 0
    elif op == "rollback":
        g.reset("--hard", "HEAD~1")
        return 0

if __name__ == "__main__":
    pass
