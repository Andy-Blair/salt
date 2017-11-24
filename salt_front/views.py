# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render_to_response, HttpResponse, HttpResponseRedirect, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User, Group
from django.http import Http404
from models import *
from salt import client
import json
import git_checkout
from dwebsocket import accept_websocket
import os
import subprocess


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
def update_detail(request,operate,web_id):
    user = User.objects.get(id=request.session['_auth_user_id'])
    login_user = user.last_name + user.first_name
    return render_to_response('update_detail.html',{'login_user':login_user})


@accept_websocket
def detail_socket(request,operate,web_id):
    if request.is_websocket():
        for m in request.websocket:
            operate = operate
            web_info = Website.objects.get(website_id=web_id)
            web_git_url = web_info.git_url
            sync = False
            re_tomcat = False

            # --- checkout code to local(/srv/salt/project) from remote. start ---
            # pro = web_git_url.split("/")[1:]
            # rel_git_url = "git@git.jingzhengu.com:jenkins/" + "/".join(pro)
            request.websocket.send("正在获取更新文件......\n\n".encode('utf8'))
            result = git_checkout.git_checkout(git_url=web_git_url,op=operate)
            if result == 0:
                sync = True
                request.websocket.send("获取更新文件成功！\n\n".encode('utf8'))
            else:
                request.websocket.send("获取更新文件失败，请联系运维部！\n\n".encode('utf8'))
            # --- checkout code to local(/srv/salt/project) from remote. end ---

            if sync:
                web_servers_info = web_info.server_id.values()
                web_server_ip = []
                web_server_ostype = None
                for i in range(len(web_servers_info)):
                    web_server_ip.append(web_servers_info[i]["ipaddress"])
                    web_server_ostype = web_servers_info[i]["ostype"]
                pro_name = web_git_url.split("/")[-1].split(".")[0]
                web_path = web_info.path

                # --- create pro_name.sls file and add call-command to top.sls. start ---
                sls_files = os.listdir("/srv/salt/project")
                if "%s.sls" % pro_name not in sls_files:
                    if web_server_ostype.lower() == "windows":
                        data = [pro_name + ":\n", "  file.recurse:\n", "    - name: %s\n" % web_path,
                                "    - source: salt://project/%s\n" % pro_name, "    - mkdir: True\n"]
                    else:
                        data = [pro_name + ":\n", "  file.recurse:\n", "    - name: %s\n" % web_path,
                                "    - source: salt://project/%s\n" % pro_name, "    - user: app\n","    - group: app\n",
                                "    - file_mode: 644\n",
                                "    - dir_mode: 755\n", "    - mkdir: True\n"]
                    pro_sls = open('/srv/salt/project/%s.sls' % pro_name, str('w+'))
                    pro_sls.writelines(data)
                    pro_sls.close()
                    top_sls = open('/srv/salt/top.sls', str('a+'))
                    top_sls_data = str("    - project.%s" % pro_name)
                    top_sls_content = top_sls.readlines()
                    if top_sls_data not in top_sls_content:
                        top_sls.write(top_sls_data)
                    top_sls.close()
                # --- create pro_name.sls file and add call-command to top.sls. end ---

                # --- sync files from server. start ---
                cli = client.LocalClient()
                request.websocket.send("正在更新......\n\n".encode('utf8'))
                for i in web_server_ip:
                    request.websocket.send(i.strip().encode('utf8')+":\n".encode('utf8'))
                    sync_re = cli.cmd(tgt=i.strip(), fun='state.sls', arg=('project.%s' % pro_name,))
                    def get_change(dic):
                        # get change files
                        for k, v in dic.items():
                            if k == "changes":
                                return v
                            else:
                                if isinstance(v, dict):
                                    return get_change(v)

                    update_file = get_change(sync_re)
                    if len(update_file) != 0:
                        re_tomcat = True
                        for k,v in update_file.items():
                            # ch = v.items()[0][1]
                            # v_ch = str("  ") + k + str(' ...... ') + ch + "\n"
                            v_ch = str("  ") + k + "\n"
                            request.websocket.send(v_ch.encode('utf8'))
                    else:
                        request.websocket.send("文件都是最新的，不需要更新！\n".encode('utf8'))
                    request.websocket.send("\n".encode('utf8'))
                # --- sync files from server. end ---

                    # --- Read Tomcat Log. start ---
                    if web_info.type.lower() == "tomcat" and re_tomcat:
                        # 配置远程服务器的IP，帐号，密码，端口等，因做了双机密钥信任，所以不需要密码
                        r_user = "app"
                        r_ip = i.strip()
                        r_port = 22
                        r_log = "/apps/product/tomcat/logs/catalina.out"  # tomcat的启动日志路径
                        cmd_rlog = "/usr/bin/ssh -p {port} {user}@{ip} /usr/bin/tail -f {log_path}".format(user=r_user, ip=r_ip, port=r_port, log_path=r_log)
                        cmd_tstart = "/usr/bin/ssh -p {port} {user}@{ip} /apps/product/tomcat/bin/startup.sh".format(user=r_user, ip=r_ip, port=r_port)
                        # cmd_tstop = "/usr/bin/ssh -p {port} {user}@{ip} /apps/product/script/tomcat_shutdown.sh".format(user=r_user, ip=r_ip, port=r_port)
                        # cmd_kill_tail = "/usr/bin/ssh -p {port} {user}@{ip} /apps/product/script/kill_tail.sh".format(user=r_user, ip=r_ip, port=r_port)
                        p_rlog = subprocess.Popen(cmd_rlog, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                        # p_stop = subprocess.Popen(cmd_tstop, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                        tom_stop_re = cli.cmd(tgt=r_ip, fun='state.sls', arg=('pkg.scripts.tomcat_shutdown'))
                        request.websocket.send("Tomcat has stopped\n\n".encode('utf8'))
                        p_start = subprocess.Popen(cmd_tstart, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                        while p_start.poll() == None:
                            start_l = p_start.stdout.readline()
                            request.websocket.send(start_l.encode('utf8'))

                        while p_rlog.poll() == None:
                            re_log = p_rlog.stdout.readline()
                            request.websocket.send(re_log.encode('utf8'))
                            if "Server startup in" in re_log:
                                # request.websocket.send("---END---\n".encode('utf8'))
                                break
                        kill_tail_re = cli.cmd(tgt=r_ip, fun='state.sls', arg=('pkg.scripts.kill_tail'))
                    request.websocket.send("------更新完成！------\n\n".encode('utf8'))
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
            web.server_id.add(Servers.objects.get(ipaddress=ip.decode('utf8')))
        return HttpResponseRedirect('/salt/website_manage/')


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
        if "超级管理员" in group_names:
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
                ip = []
                for item in range(len(server)):
                    ip.append(server[item]['ipaddress'])
                    d['website_ostype'] = server[item]['ostype']
                d['website_server'] = ','.join(ip)
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
                ip = []
                for item in range(len(server)):
                    ip.append(server[item]['ipaddress'])
                    d['website_ostype'] = server[item]['ostype']
                d['website_server'] = '，'.join(ip)
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
    if "超级管理员" not in group_names:
        return HttpResponseRedirect('/')
    if request.method == "POST":
        cli = client.LocalClient()
        re_id = cli.cmd(tgt='*',fun='grains.item',arg= ('os',))
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
