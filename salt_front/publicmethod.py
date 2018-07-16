# _*_ coding:utf-8 _*_
from salt import client
import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.header import Header
import random
import string

logger = logging.getLogger(__name__)


def get_dval(dic, key):
    '''
    :param dic: Dictionary
    :param key: The key to find.
    :return: The value of the key
    '''
    for k, v in dic.items():
        if k == key:
            return v
        else:
            if isinstance(v, dict) and len(v) > 0:
                return get_dval(v, key)


def create_pro_file(web, servers):
    '''
    :param web: Database query object
    :param servers: IP list
    :return: Dictionary
    '''
    result = {}
    cli = client.LocalClient()
    git_pyscript = "/srv/salt/pkg/script/git_update.py"
    py_content = open(git_pyscript, 'r')
    py_lines = py_content.readlines()
    py_content.close()
    py_flen = len(py_lines)
    for num in range(py_flen):
        if py_lines[num].strip() == 'git_url = ""':
            py_lines[num] = py_lines[num].replace(py_lines[num], "git_url = '%s'" % web.git_url + "\n")
        elif py_lines[num].strip() == 'git_path = ""':
            if web.type == "IIS":
                py_lines[num] = py_lines[num].replace(py_lines[num],"git_path = '%s'" % web.path.replace('\\', '\\\\') + "\n")
        if py_lines[num].startswith("used_branch"):
            if web.deploy_env == "online":
                py_lines[num] = 'used_branch = "online_deploy"\n'
            else:
                py_lines[num] = 'used_branch = "sandbox_deploy"\n'
        if py_lines[num].startswith("remote_repo_name"):
            if web.deploy_env == "online":
                py_lines[num] = 'remote_repo_name = "online"\n'
            else:
                py_lines[num] = 'remote_repo_name = "sanbox"\n'
    pyscript_name = web.url.replace(".", "_")
    web_scr_dir = "/srv/salt/pkg/script/web_git/%s" % pyscript_name
    if not os.path.exists(web_scr_dir + "/"):
        if os.path.exists(web_scr_dir):
            os.remove(web_scr_dir)
        os.mkdir(web_scr_dir + "/")
    new_py = open("/srv/salt/pkg/script/web_git/%s/%s.py" % (pyscript_name, pyscript_name), "w")
    new_py.writelines(py_lines)
    new_py.close()
    push_slsmode = "/srv/salt/pkg/script/git_update.sls"
    sls_content = open(push_slsmode, 'r')
    sls_lines = sls_content.readlines()
    sls_content.close()
    sls_flen = len(sls_lines)
    for num in range(sls_flen):
        if "- source:" in sls_lines[num]:
            if web.type == "IIS":
                sls_lines[num - 1] = "    " + sls_lines[
                    num - 1].strip() + " d:/product/web_git/%s.py\n" % pyscript_name
            else:
                sls_lines[num - 1] = "    " + sls_lines[
                    num - 1].strip() + " /apps/product/web_git/%s.py\n" % pyscript_name
            sls_lines[num] = "    " + sls_lines[num].strip() + "%s/%s.py\n" % (pyscript_name, pyscript_name)
    new_sls = open("/srv/salt/pkg/script/web_git/%s/%s.sls" % (pyscript_name, pyscript_name), "w")
    new_sls.writelines(sls_lines)
    new_sls.close()
    git_run_script = "/srv/salt/pkg/script/git_update_run.sls"
    sls_git_content = open(git_run_script, 'r')
    sls_git_lines = sls_git_content.readlines()
    sls_git_content.close()
    sls_git_flen = len(sls_git_lines)
    for num in range(sls_git_flen):
        if "- name:" in sls_git_lines[num]:
            if web.type == "IIS":
                sls_git_lines[num] = "    " + sls_git_lines[
                    num].strip() + " d:/product/web_git/%s.py update\n" % pyscript_name
            else:
                sls_git_lines[num] = "    " + sls_git_lines[
                    num].strip() + " /apps/product/web_git/%s.py update\n" % pyscript_name
                sls_git_lines.append("    - user: app")
    update_git_sls = open("/srv/salt/pkg/script/web_git/%s/%s_update.sls" % (pyscript_name, pyscript_name), "w")
    update_git_sls.writelines(sls_git_lines)
    update_git_sls.close()
    rollback_git_sls = open("/srv/salt/pkg/script/web_git/%s/%s_rollback.sls" % (pyscript_name, pyscript_name), "w")
    rollback_git_sls.writelines(sls_git_lines)
    rollback_git_sls.close()
    top_sls = open("/srv/salt/top.sls", "a+")
    top_data = ["    - pkg.script.web_git.%s.%s\n" % (pyscript_name, pyscript_name),
                "    - pkg.script.web_git.%s.%s_update\n" % (pyscript_name, pyscript_name),
                "    - pkg.script.web_git.%s.%s_rollback\n" % (pyscript_name, pyscript_name)]
    top_sls_lines = top_sls.readlines()
    for top_item in top_data:
        if top_item not in top_sls_lines:
            top_sls.write(top_item)
    top_sls.close()
    for ip in servers:
        sync_re = cli.cmd(tgt=ip, fun="state.sls",arg=["pkg.script.web_git.%s.%s" % (pyscript_name, pyscript_name)])
        logger.info("create_project_script_result %s" % sync_re)
        re = get_dval(sync_re, "result")
        result[ip] = re
    val = result.values()
    new_li = list(set(val))
    if len(new_li) == 1 and new_li[0] == True:
        init = "success"
    else:
        init = "failer"
    return init


def send_mail(recver,content):
    '''
    :param recver: type:List,receve user list
    :param content: string
    '''
    sender = "release@jingzhengu.com"
    message = MIMEText(content, 'html', 'utf-8')
    message['Form'] = Header(sender, "utf-8")
    message['To'] = Header(";".join(recver), 'utf-8')
    subject = '上线通知'
    message['Subject'] = Header(subject, 'utf-8')
    try:
        smtpObj = smtplib.SMTP(host="mail.jingzhengu.com", port=25)
        smtpObj.sendmail(sender, recver, message.as_string())
        smtpObj.quit()
        logger.info("邮件发送成功")
    except smtplib.SMTPException as e:
        logger.error("邮件发送失败")
        logger.error(e)


def create_random_str():
    r = ''.join(random.sample(string.ascii_letters + string.digits, 6))
    return r
