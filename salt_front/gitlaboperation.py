# _*_ coding:utf-8 _*_
import gitlab


class Gitlaboperation(object):
    def __init__(self,proname):
        self._url = "http://git.jingzhengu.com/"
        self._token = "yB6dxyz1xdxDsXPqzzr9"
        self._gl = gitlab.Gitlab(url=self._url,private_token=self._token,api_version='3')
        try:
            self._pro = self._gl.projects.get(proname)
        except Exception:
            self._pro = self._gl.projects.create(proname)

    def get_branches(self):
        branchs = self._pro.branches.list()
        branch_list = [br.name for br in branchs]
        return branch_list

    def get_branch_info(self,name):
        br = self._pro.branches.get(name)
        return br

    def create_branch(self,name,ref='master',protect=False):
        br = self._pro.branches.create({'branch_name': name, 'ref': ref})
        if protect:
            br.protect()
        return

    def del_branch(self,name):
        br = self._pro.branches.delete(name)
        return

    def merge_branch(self,source,target,title):
        mr = self._pro.mergerequests.create({'source_branch':source,'target_branch':target,'title':title})
        try:
            mr.merge()
            return True
        except Exception:
            mr.delete()
            raise
            # return False

    def create_tag(self,name,branch,message):
        tag = self._pro.tags.create({'tag_name': name, 'ref': branch,'message':message})
        return tag

    def get_tags(self):
        tags = self._pro.tags.list()
        return tags
