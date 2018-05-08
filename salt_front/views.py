# -*- coding: utf-8 -*-
# from __future__ import unicode_literals

from django.shortcuts import render_to_response, HttpResponse, HttpResponseRedirect, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User, Group
from models import *
from salt import client
import json
from dwebsocket import accept_websocket
import os
import subprocess
import time
import logging
import jkoperation
import gitlaboperation
import publicmethod

logger = logging.getLogger(__name__)

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
        commit = Commit.objects.filter(website_id=web_id).order_by('-com_id')
        tag_list = "<option>请选择</option>\n".decode('utf8')
        for comm in commit:
            tag_list = tag_list + "<option>%s</option>\n".decode('utf8') % comm.tag_name
        return HttpResponse(tag_list)
    elif request.method == "POST":
        tag_name = request.POST["tag_name"]
        web_id = request.POST["web_id"]
        commit = Commit.objects.get(tag_name=tag_name,website_id=web_id)
        message = commit.tag_message
        return HttpResponse(message)


@login_required(login_url=login_url)
def update_detail(request,operate):
    user = User.objects.get(id=request.session['_auth_user_id'])
    login_user = user.last_name + user.first_name
    return render_to_response('update_detail.html',{'login_user': login_user, 'title': 'Web %s Result' % operate.capitalize()})


@accept_websocket
def detail_socket(request,operate):
    if request.is_websocket():
        web_id = request.GET.get("web_id")
        tag_name = request.GET.get("tag_name")
        # servers = request.GET.get("servers").split(",")
        if operate != "update" and operate != "rollback":
            request.websocket.send("错误的操作")
        else:
            for soc_m in request.websocket:
                try:
                    operate = operate
                    web_info = Website.objects.get(website_id=web_id)
                    web_url = web_info.url
                    apptype = web_info.type
                    sls_name = web_url.replace(".","_")
                    re_tomcat = False
                    # web_servers_info = web_info.server.values()
                    web_server_ip = request.GET.get("servers").split(",")
                    # for i in range(len(web_servers_info)):
                    #     web_server_ip.append(web_servers_info[i]["ipaddress"])
                    cli = client.LocalClient()
                    request.websocket.send("正在更新......\n\n")
                    for i in web_server_ip:
                        request.websocket.send("\n%s:\n" % i.strip().encode('utf8'))
                        if operate == "update":
                            sync_re = cli.cmd(tgt=i.strip(), fun='state.sls', arg=['pkg.script.web_git.%s.%s_update' % (sls_name, sls_name)])
                            logger.info("update_result %s" % sync_re)
                        else:
                            commit = Commit.objects.get(tag_name=tag_name,website_id=web_id)
                            commit_id = commit.commit_id
                            file_path = "/srv/salt/pkg/script/web_git/%s/%s_rollback.sls" % (sls_name, sls_name)
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
                            sync_re = cli.cmd(tgt=i.strip(), fun='state.sls', arg=['pkg.script.web_git.%s.%s_rollback' % (sls_name, sls_name)])
                            logger.info("rollback_result %s" % sync_re)
                        result = publicmethod.get_dval(sync_re,"result")
                        if result:
                            re_tomcat = True
                            request.websocket.send("------当前版本信息------\n")
                            stdout = publicmethod.get_dval(sync_re,"stdout")
                            com = Commit.objects.get(commit_id=stdout.strip())
                            request.websocket.send("\nTag Name:\n%s\n" % com.tag_name.encode('utf8'))
                            request.websocket.send("\nMessage:\n%s\n" % com.tag_message.encode('utf8'))
                            request.websocket.send("\n------更新完成！------\n\n")
                        else:
                            stderr = publicmethod.get_dval(sync_re,"stderr")
                            comment = publicmethod.get_dval(sync_re,"comment")
                            request.websocket.send("错误信息：\n")
                            request.websocket.send("Comment:\n%s\n" % comment)
                            request.websocket.send("ERROR:\n%s\n" % stderr)

                        # --- Read Tomcat Log. start ---
                        if web_info.type.lower() == "tomcat" and re_tomcat:
                            war_folder = os.path.splitext(web_info.path)[0]
                            # 配置远程服务器的IP，帐号，密码，端口等，因做了双机密钥信任，所以不需要密码
                            r_user = "app"
                            r_ip = i.strip()
                            r_port = 22
                            r_log = "/apps/product/tomcat/logs/catalina.out"  # tomcat的启动日志路径
                            cmd_rlog = "/usr/bin/ssh -p {port} {user}@{ip} /usr/bin/tail -f -n 0 {log_path}".format(user=r_user, ip=r_ip, port=r_port, log_path=r_log)
                            cmd_tstart = "/usr/bin/ssh -p {port} {user}@{ip} /apps/product/tomcat/bin/startup.sh".format(user=r_user, ip=r_ip, port=r_port)
                            p_rlog = subprocess.Popen(cmd_rlog, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                            tom_stop_re = cli.cmd(tgt=r_ip, fun='state.sls', arg=['pkg.script.tomcat_shutdown'])
                            logger.info("tomcat_stop_result %s" % tom_stop_re)
                            tom_stop_result = publicmethod.get_dval(tom_stop_re,'stdout')
                            tom_stop_false = False
                            if tom_stop_result is not None:
                                if len(tom_stop_result) != 0:
                                    request.websocket.send(tom_stop_result+"\n\n")
                                    del_war_folder_re = cli.cmd(tgt=r_ip, fun='cmd.run', arg=['rm -rf %s' % war_folder])
                                    logger.info("del_war_folder_result %s" % del_war_folder_re)
                                else:
                                    tom_stop_false = True
                            else:
                                tom_stop_false = True
                            if tom_stop_false:
                                request.websocket.send("Error: can't stop Tomcat")
                                kill_tail_re = cli.cmd(tgt=r_ip, fun='state.sls', arg=['pkg.script.kill_tail'])
                                logger.info(kill_tail_re)
                                break
                            tomcat_start = cli.cmd(tgt=r_ip, fun='state.sls', arg=['pkg.script.tomcat_start'])
                            logger.info("Tomcat_start_result %s" % tomcat_start)
                            start_result = publicmethod.get_dval(tomcat_start, "result")
                            if start_result is False:
                                request.websocket.send("Tomcat start failed\n")
                                kill_tail_re = cli.cmd(tgt=r_ip, fun='state.sls', arg=['pkg.script.kill_tail'])
                                logger.info("kill_tail_result %s " % kill_tail_re)
                                continue
                            else:
                                start_out = publicmethod.get_dval(tomcat_start, "stdout")
                                request.websocket.send(start_out + "\n")

                            while p_rlog.poll() == None:
                                re_log = p_rlog.stdout.readline()
                                request.websocket.send(re_log)
                                if "Server startup in" in re_log:
                                    break
                            kill_tail_re = cli.cmd(tgt=r_ip, fun='state.sls', arg=['pkg.script.kill_tail'])
                            logger.info("kill_tail_result %s " % kill_tail_re)
                            if publicmethod.get_dval(kill_tail_re, "result"):
                                request.websocket.send("------Start End------")
                        # --- Read Tomcat Log. end ---
                    break
                except Exception:
                    request.websocket.send("更新失败,请联系管理员!")
                    raise
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
    servers = website.server.all()
    server_ip = []
    web_server_os = None
    for server in servers:
        server_ip.append(server.ipaddress)
        web_server_os = server.ostype
    web_server_ip = ','.join(server_ip)
    jk_name = Jenkins.objects.get(website=website).jk_name
    return render_to_response('website_detail.html',{'login_user':login_user,'website':website,'jk_name':jk_name,
                                                     'web_server_ip':web_server_ip,'web_server_os':web_server_os,})


@login_required(login_url=login_url)
def website_add(request):
    user = User.objects.get(id=request.session['_auth_user_id'])
    login_user = user.last_name + user.first_name
    if request.method == "GET":
        return render_to_response('website_add.html', {'login_user':login_user})
    elif request.method == "POST":
        rec_data = request.POST
        if rec_data['apptype'] == 'tomcat':
            web_path = rec_data['web_path'] + rec_data['war_name']
        else:
            web_path = rec_data['web_path']
        web = Website(name=rec_data['web_name'],url=rec_data['web_url'],path=web_path,dev_branch=rec_data['dev_branch'],
                      type=rec_data['apptype'],git_url=rec_data['web_git_url'],deploy_env=rec_data['deploy_env'])
        web.save()
        for ip in rec_data['serverip'].split(','):
            web.server.add(Servers.objects.get(ipaddress=ip))
        jk = Jenkins(jk_name=rec_data['jk_name'],website=web)
        jk.save()
        return HttpResponseRedirect('/salt/website_manage/')


@login_required(login_url=login_url)
def create_pro_file(request):
    rec_data = request.POST
    count = 0
    has_web = False
    while count < 5:
        exsite_web = Website.objects.filter(url=rec_data["web_url"])
        if exsite_web:
            has_web = True
            break
        count += 1
        time.sleep(1)
    if has_web:
        web = Website.objects.get(url=rec_data["web_url"])
        result = publicmethod.create_pro_file(web,rec_data['serverip'].split(','))
        if result == "success":
            web.init_result = 1
            web.save()
    else:
        logger.error("check web timeout!")
    return HttpResponse()


@login_required(login_url=login_url)
def website_modify(request,web_id):
    user = User.objects.get(id=request.session['_auth_user_id'])
    login_user = user.last_name + user.first_name
    webinfo = Website.objects.get(website_id=web_id)
    jk_name = Jenkins.objects.get(website=webinfo).jk_name
    servers = []
    for i in webinfo.server.all():
        servers.append(i.ipaddress)
    serverip = ','.join(servers)
    if request.method == "GET":
        war_name = os.path.split(webinfo.path)[1]
        return render_to_response('website_modify.html', {'webinfo':webinfo, 'serverip':serverip, 'login_user':login_user,'jk_name':jk_name,'war_name':war_name})
    elif request.method == "POST":
        rec_data = request.POST
        if rec_data['apptype'] == 'tomcat':
            web_path = rec_data['web_path'] + rec_data['war_name']
        else:
            web_path = rec_data['web_path']
        if rec_data['web_name'] == webinfo.name and rec_data['web_url'] == webinfo.url and rec_data['dev_branch'] == webinfo.dev_branch \
            and web_path == webinfo.path and rec_data['apptype'] == webinfo.type and rec_data['web_git_url'] == webinfo.git_url \
            and rec_data['serverip'] == serverip and rec_data['deploy_env'] == webinfo.deploy_env and rec_data['jk_name'] == jk_name:
            return HttpResponseRedirect('/salt/website_manage/')
        else:
            webinfo.name = rec_data['web_name']
            webinfo.url = rec_data['web_url']
            webinfo.path = web_path
            webinfo.type = rec_data['apptype']
            webinfo.git_url = rec_data['web_git_url']
            webinfo.deploy_env = rec_data['deploy_env']
            webinfo.dev_branch = rec_data['dev_branch']
            webinfo.save()
            webinfo.server.clear()
            for ip in rec_data['serverip'].split(','):
                webinfo.server.add(Servers.objects.get(ipaddress=ip))
            webinfo.save()
            jk = Jenkins.objects.get(website=webinfo)
            jk.jk_name = rec_data['jk_name']
            jk.save()
            return HttpResponseRedirect('/salt/website_manage/')


@login_required(login_url=login_url)
def server_auth(request):
    if request.method == "POST":
        rec_data = request.POST
        for ip in rec_data['ipaddress'].split(','):
            exsit_ip = Servers.objects.filter(ipaddress=ip)
            if not exsit_ip:
                return HttpResponse(ip)
        return HttpResponse()


@login_required(login_url=login_url)
def website_auth(request):
    if request.method == "POST":
        rec_data = request.POST
        exsit_web = Website.objects.filter(url=rec_data["url"])
        if exsit_web:
            return HttpResponse("exsit")
        return HttpResponse()


@login_required(login_url=login_url)
def jkname_auth(request):
    if request.method == "POST":
        rec_data = request.POST
        exsit_jkname = Jenkins.objects.filter(jk_name=rec_data['jk_name'])
        if exsit_jkname:
            return HttpResponse("exsit")
        return HttpResponse()


@login_required(login_url=login_url)
def tagname_auth(request):
    if request.method == "POST":
        rec_data = request.POST
        web = Website.objects.get(website_id=rec_data["web_id"])
        proname = ".".join(web.git_url.split(":")[1].split(".")[:-1])
        tag_name = "%s_%s" %(web.deploy_env,rec_data["tag_name"])
        gl = gitlaboperation.Gitlaboperation(proname)
        tags = [tag.name for tag in gl.get_tags()]
        if tag_name in tags:
            return HttpResponse("exsit")
        else:
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
                init_fail = False
                init_result = i.init_result
                if init_result == 0:
                    d['website_url'] = i.url + '...<font color="#FF0000">not init</font>'
                    init_fail = True
                else:
                    d['website_url'] = i.url
                if init_fail:
                    d['init_result'] = 0
                else:
                    d['init_result'] = 1
                web_type = i.type
                d['website_type'] = web_type
                d['website_env'] = i.deploy_env
                d['website_dev_branch'] = i.dev_branch
                server = i.server.values()
                ips = []
                for item in range(len(server)):
                    ip = server[item]['ipaddress']
                    ips.append(ip)
                    d['website_ostype'] = server[item]['ostype']
                d['website_server'] = ','.join(ips)
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
                d['website_env'] = web.deploy_env
                d['website_dev_branch'] = web.dev_branch
                init_fail = False
                init_result = web.init_result
                if init_result == 0:
                    d['website_url'] = web.url + '...<font color="#FF0000">not init</font>'
                    init_fail = True
                else:
                    d['website_url'] = web.url
                if init_fail:
                    d['init_result'] = 0
                else:
                    d['init_result'] = 1
                server = web.server.values()
                ips = []
                for item in range(len(server)):
                    ip = server[item]['ipaddress']
                    ips.append(ip)
                    d['website_ostype'] = server[item]['ostype']
                d['website_server'] = ','.join(ips)
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


@login_required(login_url=login_url)
def history(request,web_id):
    user = User.objects.get(id=request.session['_auth_user_id'])
    login_user = user.last_name + user.first_name
    commit = Commit.objects.filter(website_id=web_id).order_by('-com_id')
    history = []
    for i in commit:
        data = {}
        data['update_time'] = i.update_date
        data['tag_name'] = i.tag_name
        data['message'] = i.tag_message
        history.append(data)
    return render_to_response("website_history.html",{'login_user':login_user,'history':history})


@login_required(login_url=login_url)
def tomcat_operation(request,operation,web_id):
    user = User.objects.get(id=request.session['_auth_user_id'])
    login_user = user.last_name + user.first_name
    return render_to_response('update_detail.html',{'login_user': login_user, 'title': 'Tomcat %s Result' % operation.capitalize()})


@accept_websocket
def tomcat_op_result(request,operation,web_id):
    if request.is_websocket():
        # web_info = Website.objects.get(website_id=web_id)
        # web_servers_info = web_info.server.values()
        web_server_ip = request.GET.get("servers").split(",")
        cli = client.LocalClient()
        for soc_m in request.websocket:
            try:
                for i in range(len(web_server_ip)):
                    ipadd = web_server_ip[i]
                    request.websocket.send(ipadd.encode('utf8') + ":\n")
                    tomcat_check = cli.cmd(tgt=ipadd, fun='state.sls', arg=['pkg.script.tomcat_check'])
                    logger.info("tomcat_check_result %s" % tomcat_check)
                    result = publicmethod.get_dval(tomcat_check, "result")
                    if result:
                        tomcat_statu = publicmethod.get_dval(tomcat_check,"stdout")
                        if tomcat_statu == operation.lower():
                            request.websocket.send("Tomcat already %s\n" % tomcat_statu)
                        elif tomcat_statu == "start" or tomcat_statu == "stop":
                            if operation.lower() == 'start':
                                r_user = "app"
                                r_ip = ipadd
                                r_port = 22
                                r_log = "/apps/product/tomcat/logs/catalina.out"  # tomcat的启动日志路径
                                cmd_rlog = "/usr/bin/ssh -p {port} {user}@{ip} /usr/bin/tail -f -n 0 {log_path}".format(user=r_user,ip=r_ip,port=r_port,log_path=r_log)
                                p_rlog = subprocess.Popen(cmd_rlog, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                                tomcat_start = cli.cmd(tgt=ipadd, fun='state.sls', arg=['pkg.script.tomcat_start'])
                                logger.info("Tomcat_start_result %s" % tomcat_start)
                                start_result = publicmethod.get_dval(tomcat_start,"result")
                                if start_result is False:
                                    request.websocket.send("Tomcat start failed\n")
                                    kill_tail_re = cli.cmd(tgt=r_ip, fun='state.sls', arg=['pkg.script.kill_tail'])
                                    logger.info("kill_tail_result %s " % kill_tail_re)
                                    continue
                                else:
                                    start_out = publicmethod.get_dval(tomcat_start,"stdout")
                                    request.websocket.send(start_out+"\n")
                                while p_rlog.poll() == None:
                                    re_log = p_rlog.stdout.readline()
                                    request.websocket.send(re_log)
                                    if "Server startup in" in re_log:
                                        break
                                kill_tail_re = cli.cmd(tgt=r_ip, fun='state.sls', arg=['pkg.script.kill_tail'])
                                logger.info("kill_tail_result %s " % kill_tail_re)
                                if publicmethod.get_dval(kill_tail_re,"result"):
                                    request.websocket.send("------Start End------")
                            elif operation.lower() == 'stop':
                                tom_stop_re = cli.cmd(tgt=ipadd, fun='state.sls', arg=['pkg.script.tomcat_shutdown'])
                                logger.info("tomcat_stop_result %s" % tom_stop_re)
                                tom_stop_result = publicmethod.get_dval(tom_stop_re, 'stdout')
                                if tom_stop_result is not None:
                                    if len(tom_stop_result) != 0:
                                        request.websocket.send(tom_stop_result + "\n\n")
                                    else:
                                        request.websocket.send("Error: can't stop Tomcat\n")
                        else:
                            request.websocket.send(tomcat_statu + '\n')
                    else:
                        request.websocket.send("unknown tomcat status\n")
                break
            except Exception:
                request.websocket.send("执行失败,请联系管理员!\n")
                raise
        request.websocket.close()


@login_required(login_url=login_url)
def build(request,web_id):
    user = User.objects.get(id=request.session['_auth_user_id'])
    login_user = user.last_name + user.first_name
    return render_to_response('update_detail.html',{'login_user':login_user,'title':"Jenkins Build Result"})


@accept_websocket
def build_socket(request,web_id,):
    if request.is_websocket():
        for soc_m in request.websocket:
            tag_name = request.GET.get("tagname")
            tag_message = request.GET.get("tagmessage")
            web_info = Website.objects.get(website_id=web_id)
            proname = ".".join(web_info.git_url.split(":")[1].split(".")[:-1])
            dev_branch = web_info.dev_branch
            deploy_env = web_info.deploy_env
            try:
                gl = gitlaboperation.Gitlaboperation(proname)
                build_branch = 'online'
                br_lsit = gl.get_branches()
                if build_branch not in br_lsit:
                    try:
                        request.websocket.send("没有online分支，正在创建online分支……\n")
                        gl.create_branch(name=build_branch,ref='master',protect=True)
                        request.websocket.send("online分支创建成功！\n\n")
                    except Exception:
                        request.websocket.send("online分支创建失败，请联系管理员!\n\n")
                request.websocket.send("正在将开发分支%s合并到online分支……\n" % web_info.dev_branch.encode('utf8'))
                merge = gl.merge_branch(source=dev_branch,target=build_branch,title="merge %s to %s" % (dev_branch,build_branch))
                if merge:
                    request.websocket.send("分支合并成功！\n\n")
                    web_info.merge_result = "success"
                    web_info.build_result = "-"
                    web_info.create_tag_result = "-"
                    web_info.save()
            except Exception:
                merge_result = web_info.merge_result
                if merge_result == "success":
                    request.websocket.send("分支已合并，跳过此步骤！\n\n")
                else:
                    request.websocket.send("分支合并失败，请联系管理员!\n")
                    raise
            try:
                build_result = web_info.build_result
                request.websocket.send("Jenkins构建中…………\n\n")
                jk_name = Jenkins.objects.get(website_id=web_id).jk_name
                jk = jkoperation.JKoperation()
                next_build_num = jk.next_build_number(jk_name.encode('utf8'))
                if build_result != "success":
                    jk.build_job(proname=jk_name.encode('utf8'),parameter={"push":"true","deploy_branch":"%s_deploy" % deploy_env,"git_path":web_info.git_url,"test_build":"false"})
                    read_console = True
                else:
                    read_console = False
                    request.websocket.send("最新代码已经构建成功，跳过此步骤！\n\n")
            except Exception:
                request.websocket.send("构建失败,请联系管理员!\n")
                raise
            if read_console:
                try:
                    while True:
                        try:
                            building = jk.build_status(jk_name.encode('utf8'),next_build_num)
                            if building:
                                break
                            else:
                                time.sleep(1)
                                continue
                        except Exception:
                            time.sleep(1)
                            continue
                    pre = []
                    read_console_time_out = 0
                    while True:
                        try:
                            output = jk.get_build_output(jk_name.encode('utf8'),next_build_num)
                        except Exception,e:
                            if "Connection timed out" in e:
                                if read_console_time_out > 5:
                                    request.websocket.send("构建信息读取超时!\n")
                                    raise
                                else:
                                    read_console_time_out += 1
                                    time.sleep(1)
                                    continue
                            else:
                                raise
                        tmp = [i.decode('gbk').encode('utf8') for i in output.splitlines() if i not in pre]
                        if len(tmp) > 0:
                            pre = output.splitlines()
                            request.websocket.send("\n".join(tmp))
                            request.websocket.send("\n")
                        else:
                            building = jk.build_status(jk_name.encode('utf8'),next_build_num)
                            if building:
                                time.sleep(1)
                            else:
                                break
                except Exception:
                    request.websocket.send("构建信息读取失败!\n")
                    raise
            try:
                build_result = jk.build_result(jk_name.encode('utf8'),next_build_num)
                if build_result == "SUCCESS":
                    request.websocket.send("\n\n构建成功！\n\n")
                    web_info.build_result = "success"
                    web_info.save()
                    request.websocket.send("正在创建Tag标签……\n")
                    tag = gl.create_tag(name="%s_%s" % (deploy_env,tag_name),branch="%s_deploy" % deploy_env,message=tag_message)
                    commit_id = tag.commit.id
                    com = Commit(tag_name="%s_%s" % (deploy_env,tag_name),tag_message=tag_message,commit_id=commit_id,website=web_info)
                    com.save()
                    request.websocket.send("Tag标签创建成功！\n\n")
                    if web_info.merge_result == web_info.build_result == "success":
                        if web_info.type != "IIS":
                            web_info.merge_result = "-"
                        web_info.build_result = "-"
                        web_info.save()
                else:
                    request.websocket.send("构建失败，不创建Tag标签！\n")
            except Exception:
                request.websocket.send("Tag标签创建失败,请联系管理员!\n")
                raise
            break
        request.websocket.close()


@login_required(login_url=login_url)
def get_git_branchs(request):
    git_path = request.POST['git_path']
    git_pro_name = git_path.split(":")[1].split(".")[0]
    gl = gitlaboperation.Gitlaboperation(proname=git_pro_name)
    branchs = gl.get_branches()
    branch_list = "<option>请选择</option>\n".decode('utf8')
    for i in branchs:
        if i == "online_deploy" or i == "sandbox_deploy" or i == "online" or i == "master":
            continue
        else:
            branch_list = branch_list + "<option>%s</option>\n".decode('utf8') % i
    return HttpResponse(branch_list)


@login_required(login_url=login_url)
def re_init(request):
    web_id = request.POST.get("web_id")
    servers = request.POST.get("servers")
    if web_id == "all":
        webs = Website.objects.all()
        for web in webs:
            servers = web.server.values()
            server_list = [server['ipaddress'] for server in servers]
            result = publicmethod.create_pro_file(web,server_list)
            if result == "success":
                web.init_result = 1
                web.save()
            else:
                web.init_result = 0
                web.save()
    elif web_id is not None:
        web = Website.objects.get(website_id=web_id)
        server_li = servers.split(",")
        result = publicmethod.create_pro_file(web,server_li)
        if result == "success":
            web.init_result = 1
            web.save()
        else:
            web.init_result = 0
            web.save()
    else:
        return HttpResponse("Reinit Failer")
    return HttpResponse("Reinit End")
