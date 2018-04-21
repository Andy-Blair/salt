# _*_ coding:utf-8 _*_
import jenkins


class JKoperation(object):
    def __init__(self):
        self._jek_server_url = "http://jk.jingzhengu.com"
        self._user = "admin"
        self._api_token = "80e7048d8f8aaed7dc0bfe5a098648fc"
        self._server = jenkins.Jenkins(self._jek_server_url, username=self._user, password=self._api_token)

    def build_branch(self,proname):
        job_conf = self._server.get_job_config(proname)
        conf_lines = job_conf.splitlines()
        for line in range(len(conf_lines)):
            conf = conf_lines[line]
            if "<hudson.plugins.git.BranchSpec>" in conf:
                branch = conf_lines[line + 1].strip()
                return branch[8:len(branch) - 7]

    def get_git_path(self,proname):
        job_conf = self._server.get_job_config(proname)
        conf_lines = job_conf.splitlines()
        for line in range(len(conf_lines)):
            conf = conf_lines[line]
            if "<url>git@git.jingzhengu.com" in conf:
                git_path = conf.strip().strip("<url>").strip("</url>")
                return git_path

    def last_build_number(self,proname):
        last_build_num = self._server.get_job_info(proname)['lastBuild']['number']
        return last_build_num

    def build_result(self,proname,build_num=None):
        if build_num is None:
            build_num = self.last_build_number(proname)
        build_result = self._server.get_build_info(proname, build_num)['result']
        return build_result

    def build_status(self,proname,build_num=None):
        if build_num is None:
            build_num = self.last_build_number(proname)
        build_status = self._server.get_build_info(proname,build_num)['building']
        return build_status

    def build_job(self,proname,parameter=None):
        self._server.build_job(proname,parameter)
        # return

    def next_build_number(self,proname):
        next_num = self._server.get_job_info(proname)['nextBuildNumber']
        return next_num

    def get_build_output(self,proname,build_num=None):
        if build_num is None:
            build_num = self.last_build_number(proname)
        output = self._server.get_build_console_output(proname, build_num)
        return output
