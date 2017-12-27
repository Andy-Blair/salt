# -*- coding: utf-8 -*-
# from __future__ import unicode_literals

from django.shortcuts import render_to_response, HttpResponse, HttpResponseRedirect, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User, Group
from models import *
from salt import client
import json
import git_checkout
from dwebsocket import accept_websocket
import os
import subprocess
import sys

# Create your views here.
login_url = "/salt/login/"
website_url = "/salt/website/"


def login_view(request):
    # 登陆验证
    if request.method == 'POST':
        username = request.POST.get('username')
        passwd = request.POST.get('password')
        user = authenticate(username=username, password=passwd)
        if user is not None and user.is_active:
            login(request,user)
            return HttpResponseRedirect(website_url)
    return render_to_response('login.html')


@login_required(login_url=login_url)
def logout_view(request):
    # 退出登陆
    logout(request)
    return HttpResponseRedirect(login_url)


@login_required(login_url=login_url)
def website(request):
    user = User.objects.get(id=request.session['_auth_user_id'])
    login_user = user.last_name + user.first_name
    return render_to_response('website.html',{'login_user':login_user})


@login_required(login_url=login_url)
def website_tag(request):
    if request.method == "GET":
        web_id = request.GET["web_id"]
        commit = Commit.objects.filter(website_id=web_id)
        tag_list = "<option>请选择</option>\n".decode('utf8')
        for comm in commit:
            tag_list = tag_list + "<option>%s</option>\n".decode('utf8') % comm.tag_name
        return HttpResponse(tag_list)
    elif request.method == "POST":
        tag_name = request.POST["tag_name"]
        web_id = request.POST["web_id"]
        commit = Commit.objects.get(tag_name=tag_name,website_id=web_id)
        message = "commit   %s\nAuthor:  %s\nDate:    %s\n\n%s".decode('utf8') % (commit.commit_id,commit.author,commit.date,commit.message)
        return HttpResponse(message)


@login_required(login_url=login_url)
def update_detail(request,operate):
    user = User.objects.get(id=request.session['_auth_user_id'])
    login_user = user.last_name + user.first_name
    return render_to_response('update_detail.html',{'login_user':login_user})


@accept_websocket
def detail_socket(request,operate):
    if request.is_websocket():
        web_id = request.GET.get("web_id")
        tag_name = request.GET.get("tag_name")
        if operate != "update" and operate != "rollback":
            request.websocket.send("错误的操作")
        else:
            for soc_m in request.websocket:
                operate = operate
                web_info = Website.objects.get(website_id=web_id)
                web_url = web_info.url
                apptype = web_info.type
                sls_name = web_url.replace(".","_")
                re_tomcat = False
                web_servers_info = web_info.server_id.values()
                web_server_ip = []
                for i in range(len(web_servers_info)):
                    web_server_ip.append(web_servers_info[i]["ipaddress"])
                cli = client.LocalClient()
                request.websocket.send("正在更新......\n\n")
                for i in web_server_ip:
                    request.websocket.send(i.strip().encode('utf8') +":\n")
                    if operate == "update":
                        sync_re = cli.cmd(tgt=i.strip(), fun='state.sls', arg=['pkg.scripts.web_git.%s.%s_update' % (sls_name, sls_name)])
                    else:
                        commit = Commit.objects.get(tag_name=tag_name)
                        commit_id = commit.commit_id
                        file_path = "/srv/salt/pkg/scripts/web_git/%s/%s_rollback.sls" % (sls_name, sls_name)
                        f = open(file_path,'r')
                        lines = f.readlines()
                        f.close()
                        for line in range(len(lines)):
                            if "name" in lines[line]:
                                if apptype == "IIS":
                                    lines[line] = "    - name: python d:/product/web_git/%s.py rollback %s\n" % (sls_name,commit_id)
                                else:
                                    lines[line] = "    - name: python /apps/product/web_git/%s.py rollback %s\n" % (sls_name, commit_id)
                                break
                        new_f = open(file_path,'w')
                        new_f.writelines(lines)
                        new_f.close()
                        sync_re = cli.cmd(tgt=i.strip(), fun='state.sls', arg=['pkg.scripts.web_git.%s.%s_rollback' % (sls_name, sls_name)])
                    def get_dval(dic,key):
                        # get change files
                        for k, v in dic.items():
                            if k == key:
                                return v
                            else:
                                if isinstance(v, dict):
                                    return get_dval(v,key)
                    print sync_re
                    result = get_dval(sync_re,"result")
                    if result:
                        stdout = get_dval(sync_re,"stdout")
                        request.websocket.send("  " + stdout + "\n")
                        request.websocket.send("------更新完成！------\n\n")
                        re_tomcat = True
                        all_message = stdout.split("\n")
                        commit_id = "-"
                        author = "-"
                        date = "-"
                        message = all_message[4:]
                        tag_name = "-"
                        for m in message:
                            if "Tag:" in m:
                                tag_name = m.split(":")[1].strip()
                        for all_m in all_message:
                            if all_m.startswith("commit"):
                                commit_id = all_m.split()[1]
                            elif all_m.startswith("Author"):
                                author = all_m.split(":")[1].strip()
                            elif all_m.startswith("Date"):
                                date = all_m.split("e:")[1].strip()
                        if operate == "update":
                            try:
                                Commit.objects.get(tag_name=tag_name,website_id=web_id)
                            except Exception:
                                website = Website.objects.get(website_id=web_id)
                                com = Commit(tag_name=tag_name,commit_id=commit_id,author=author,date=date,message="\n".join(message),website_id=website)
                                com.save()
                    else:
                        stderr = get_dval(sync_re,"stderr")
                        comment = get_dval(sync_re,"comment")
                        request.websocket.send("错误信息：\n")
                        request.websocket.send("  " + comment + "\n")
                        request.websocket.send("  " + stderr + "\n")

                    # --- Read Tomcat Log. start ---
                    if web_info.type.lower() == "tomcat" and re_tomcat:
                        # 配置远程服务器的IP，帐号，密码，端口等，因做了双机密钥信任，所以不需要密码
                        r_user = "app"
                        r_ip = i.strip()
                        r_port = 22
                        r_log = "/apps/product/tomcat/logs/catalina.out"  # tomcat的启动日志路径
                        cmd_rlog = "/usr/bin/ssh -p {port} {user}@{ip} /usr/bin/tail -f {log_path}".format(user=r_user, ip=r_ip, port=r_port, log_path=r_log)
                        cmd_tstart = "/usr/bin/ssh -p {port} {user}@{ip} /apps/product/tomcat/bin/startup.sh".format(user=r_user, ip=r_ip, port=r_port)
                        p_rlog = subprocess.Popen(cmd_rlog, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                        tom_stop_re = cli.cmd(tgt=r_ip, fun='state.sls', arg=['pkg.scripts.tomcat_shutdown'])
                        request.websocket.send("Tomcat has stopped\n\n")
                        p_start = subprocess.Popen(cmd_tstart, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                        while p_start.poll() == None:
                            start_l = p_start.stdout.readline()
                            request.websocket.send(start_l)

                        while p_rlog.poll() == None:
                            re_log = p_rlog.stdout.readline()
                            request.websocket.send(re_log)
                            if "Server startup in" in re_log:
                                break
                        kill_tail_re = cli.cmd(tgt=r_ip, fun='state.sls', arg=['pkg.scripts.kill_tail'])

                    # --- Read Tomcat Log. end ---
                break
        request.websocket.close()


@login_required(login_url=login_url)
def website_manage(request):
    user = User.objects.get(id=request.session['_auth_user_id'])
    login_user = user.last_name + user.first_name
    return render_to_response('website_manage.html',{'login_user':login_user})


@login_required(login_url=login_url)
def website_detail(request,web_id):
    user = User.objects.get(id=request.session['_auth_user_id'])
    login_user = user.last_name + user.first_name
    website = Website.objects.get(website_id=web_id)
    servers = website.server_id.all()
    server_ip = []
    web_server_os = None
    for server in servers:
        server_ip.append(server.ipaddress)
        web_server_os = server.ostype
    web_server_ip = ','.join(server_ip)
    return render_to_response('website_detail.html',{'login_user':login_user,'website':website,'web_server_ip':web_server_ip,'web_server_os':web_server_os})


@login_required(login_url=login_url)
def website_add(request):
    user = User.objects.get(id=request.session['_auth_user_id'])
    login_user = user.last_name + user.first_name
    if request.method == "GET":
        return render_to_response('website_add.html', {'login_user':login_user})
    elif request.method == "POST":
        rec_data = request.POST
        web = Website(name=rec_data['web_name'],url=rec_data['web_url'],path=rec_data['web_path'],
                      type=rec_data['apptype'],git_url=rec_data['web_git_url'])
        web.save()
        for ip in rec_data['serverip'].split(','):
            web.server_id.add(Servers.objects.get(ipaddress=ip))
        return HttpResponseRedirect('/salt/website_manage/')


@login_required(login_url=login_url)
def create_pro_file(request):

    def get_dval(dic, key):
        # get change files
        for k, v in dic.items():
            if k == key:
                return v
            else:
                if isinstance(v, dict):
                    return get_dval(v, key)

    rec_data = request.POST
    cli = client.LocalClient()
    git_pyscript = "/srv/salt/pkg/scripts/git_update.py"
    py_content = open(git_pyscript, 'r')
    py_lines = py_content.readlines()
    py_content.close()
    py_flen = len(py_lines)
    for num in range(py_flen):
        if py_lines[num].strip() == 'git_url = ""':
            py_lines[num] = py_lines[num].replace(py_lines[num], "git_url = '%s'" % rec_data['web_git_url'] + "\n")
        elif py_lines[num].strip() == 'git_path = ""':
            if rec_data['apptype'] == "IIS":
                py_lines[num] = py_lines[num].replace(py_lines[num],"git_path = '%s'" % rec_data['web_path'].replace('\\','\\\\') + "\n")
            else:
                py_lines[num] = py_lines[num].replace(py_lines[num], "git_path = '%s'" % rec_data['web_path'] + "\n")
    pyscript_name = rec_data['web_url'].replace(".", "_")
    web_scr_dir = "/srv/salt/pkg/scripts/web_git/%s" % pyscript_name
    if not os.path.exists(web_scr_dir + "/"):
        if os.path.exists(web_scr_dir):
            os.remove(web_scr_dir)
        os.mkdir(web_scr_dir + "/")
    new_py = open("/srv/salt/pkg/scripts/web_git/%s/%s.py" % (pyscript_name, pyscript_name), "w")
    new_py.writelines(py_lines)
    new_py.close()
    push_slsmode = "/srv/salt/pkg/scripts/git_update.sls"
    sls_content = open(push_slsmode, 'r')
    sls_lines = sls_content.readlines()
    sls_content.close()
    sls_flen = len(sls_lines)
    for num in range(sls_flen):
        if "- source:" in sls_lines[num]:
            if rec_data['apptype'] == "IIS":
                sls_lines[num - 1] = "    " + sls_lines[num - 1].strip() + " d:/product/web_git/%s.py\n" % pyscript_name
            else:
                sls_lines[num - 1] = "    " + sls_lines[num - 1].strip() + " /apps/product/web_git/%s.py\n" % pyscript_name
            sls_lines[num] = "    " + sls_lines[num].strip() + "%s/%s.py\n" % (pyscript_name, pyscript_name)
    new_sls = open("/srv/salt/pkg/scripts/web_git/%s/%s.sls" % (pyscript_name, pyscript_name), "w")
    new_sls.writelines(sls_lines)
    new_sls.close()
    git_run_script = "/srv/salt/pkg/scripts/git_update_run.sls"
    sls_git_content = open(git_run_script, 'r')
    sls_git_lines = sls_git_content.readlines()
    sls_git_content.close()
    sls_git_flen = len(sls_git_lines)
    for num in range(sls_git_flen):
        if "- name:" in sls_git_lines[num]:
            if rec_data['apptype'] == "IIS":
                sls_git_lines[num] = "    " + sls_git_lines[
                    num].strip() + " d:/product/web_git/%s.py update\n" % pyscript_name
            else:
                sls_git_lines[num] = "    " + sls_git_lines[
                    num].strip() + " /apps/product/web_git/%s.py update\n" % pyscript_name
                sls_git_lines.append("    - user: app")
    update_git_sls = open("/srv/salt/pkg/scripts/web_git/%s/%s_update.sls" % (pyscript_name, pyscript_name), "w")
    update_git_sls.writelines(sls_git_lines)
    update_git_sls.close()
    rollback_git_sls = open("/srv/salt/pkg/scripts/web_git/%s/%s_rollback.sls" % (pyscript_name, pyscript_name), "w")
    rollback_git_sls.writelines(sls_git_lines)
    rollback_git_sls.close()
    top_sls = open("/srv/salt/top.sls", "a+")
    top_data = ["    - pkg.scripts.web_git.%s.%s\n" % (pyscript_name, pyscript_name),
                "    - pkg.scripts.web_git.%s.%s_update\n" % (pyscript_name, pyscript_name),
                "    - pkg.scripts.web_git.%s.%s_rollback\n" % (pyscript_name, pyscript_name)]
    top_sls_lines = top_sls.readlines()
    for top_item in top_data:
        if top_item not in top_sls_lines:
            top_sls.write(top_item)
    top_sls.close()
    for ip in rec_data['serverip'].split(','):
        sync_re = cli.cmd(tgt=ip, fun="state.sls", arg=["pkg.scripts.web_git.%s.%s" % (pyscript_name, pyscript_name)])
        result = get_dval(sync_re,"result")
        if result:
            server = Servers.objects.get(ipaddress=ip)
            server.init_result = 1
            server.save()

    return HttpResponse()


@login_required(login_url=login_url)
def website_modify(request,web_id):
    user = User.objects.get(id=request.session['_auth_user_id'])
    login_user = user.last_name + user.first_name
    webinfo = Website.objects.get(website_id=web_id)
    servers = []
    for i in webinfo.server_id.all():
        servers.append(i.ipaddress)
    serverip = ','.join(servers)
    if request.method == "GET":
        return render_to_response('website_modify.html', {'webinfo':webinfo, 'serverip':serverip, 'login_user':login_user})
    elif request.method == "POST":
        rec_data = request.POST
        if rec_data['web_name'] == webinfo.name and rec_data['web_url'] == webinfo.url and rec_data['web_path'] == webinfo.path and rec_data['apptype'] == webinfo.type and rec_data['web_git_url'] == webinfo.git_url and rec_data['serverip'] == serverip:
            return HttpResponseRedirect('/salt/website_manage/')
        else:
            webinfo.name = rec_data['web_name']
            webinfo.url = rec_data['web_url']
            webinfo.path = rec_data['web_path']
            webinfo.type = rec_data['apptype']
            webinfo.git_url = rec_data['web_git_url']
            webinfo.save()
            webinfo.server_id.clear()
            for ip in rec_data['serverip'].split(','):
                webinfo.server_id.add(Servers.objects.get(ipaddress=ip))
            webinfo.save()
            return HttpResponseRedirect('/salt/website_manage/')


@login_required(login_url=login_url)
def website_server_au(request):
    if request.method == "POST":
        rec_data = request.POST
        for ip in rec_data['serverip'].split(','):
            exsit_ip = Servers.objects.filter(ipaddress=ip)
            if not exsit_ip:
                return HttpResponse(ip)
        return HttpResponse()


@login_required(login_url=login_url)
def website_del(request,web_id):
    if request.method == "POST":
        webinfo = Website.objects.get(website_id=web_id)
        webinfo.delete()
        return HttpResponse()
    return HttpResponseRedirect('/salt/website_manage/')


@login_required(login_url=login_url)
def wesite_list(request):
    if request.method == "POST":
        user = User.objects.get(id=request.session['_auth_user_id'])
        groups = user.groups.all()
        data = []
        web_id = []
        show_all = False
        group_names = []
        for group in groups:
            group_names.append(group.name)
        if "超级管理员".decode('utf8') in group_names:
            show_all = True
        if show_all:
            wesite = Website.objects.all()
            for i in wesite:
                d = {}
                d['id'] = i.website_id
                d['website_name'] = i.name
                d['website_url'] = i.url
                d['website_type'] = i.type
                server = i.server_id.values()
                ips = []
                init_fail = False
                for item in range(len(server)):
                    ip = server[item]['ipaddress']
                    init_result = server[item]['init_result']
                    if init_result == 0:
                        ip = ip + '...<font color="#FF0000">not init</font>'
                        init_fail = True
                    ips.append(ip)
                    d['website_ostype'] = server[item]['ostype']
                d['website_server'] = ','.join(ips)
                if init_fail:
                    d['init_result'] = 0
                else:
                    d['init_result'] = 1
                data.append(d)
        else:
            for group in groups:
                servers = group.servers_set.all()
                for server in servers:
                    website_info = server.website_set.all()
                    for web in website_info:
                        web_id.append(web.website_id)
            web_ids = list(set(web_id))
            for i in web_ids:
                web = Website.objects.get(website_id=i)
                d = {}
                d['id'] = web.website_id
                d['website_name'] = web.name
                d['website_url'] = web.url
                d['website_type'] = web.type
                server = web.server_id.values()
                ips = []
                init_fail = False
                for item in range(len(server)):
                    ip = server[item]['ipaddress']
                    init_result = server[item]['init_result']
                    if init_result == 0:
                        ip = ip + '...<font color="#FF0000">not init</font>'
                        init_fail = True
                    ips.append(ip)
                    d['website_ostype'] = server[item]['ostype']
                d['website_server'] = ','.join(ips)
                if init_fail:
                    d['init_result'] = 0
                else:
                    d['init_result'] = 1
                data.append(d)
        return HttpResponse(json.dumps(data), content_type="application/json")


@login_required(login_url=login_url)
def server_manage(request):
    user = User.objects.get(id=request.session['_auth_user_id'])
    login_user = user.last_name + user.first_name
    groups = user.groups.all()
    group_names = []
    for group in groups:
        group_names.append(group.name)
    if "超级管理员".decode('utf8') not in group_names:
        return HttpResponseRedirect('/')
    if request.method == "POST":
        cli = client.LocalClient()
        re_id = cli.cmd(tgt='*',fun='grains.item',arg= ['os'])
        for k , v in re_id.items():
            exsit = Servers.objects.filter(ipaddress=k)
            if exsit:
                continue
            else:
                print "no exsit"
                server = Servers(ipaddress=k,ostype=v['os'],group=Group.objects.get(name="超级管理员"))
                server.save()
        return HttpResponse()
    return render_to_response('server_manage.html',{'login_user':login_user})


@login_required(login_url=login_url)
def server_list(request):
    servers = Servers.objects.all()
    data = []
    for i in servers:
        d = {}
        d['id'] = i.server_id
        d['ipaddress'] = i.ipaddress
        d['ostype'] = i.ostype
        d['describe'] = i.describe
        data.append(d)
    return HttpResponse(json.dumps(data), content_type="application/json")
