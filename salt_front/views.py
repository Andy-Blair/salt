# -*- coding: utf-8 -*-
# from __future__ import unicode_literals

from django.shortcuts import render_to_response, HttpResponse, HttpResponseRedirect, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from models import *
from salt import client
import json
from dwebsocket import accept_websocket
import os
import time
import logging
import jkoperation
import gitlaboperation
import publicmethod
import socket
import datetime

socket.setdefaulttimeout(300)
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
    web_id = request.GET.get("web_id")
    web_info = Website.objects.get(website_id=web_id)
    web_name = web_info.name
    return render_to_response('update_detail.html',{'login_user': login_user, 'title': '%s Web %s Result' % (web_name,operate.capitalize())})


@accept_websocket
def detail_socket(request,operate):
    if request.is_websocket():
        user = User.objects.get(id=request.session['_auth_user_id'])
        user_name = user.last_name + user.first_name
        web_id = request.GET.get("web_id")
        tag_name = request.GET.get("tag_name")
        dep_con = request.GET.get("dep")
        web_info = Website.objects.get(website_id=web_id)
        if web_info.send_email:
            emails = Email_user.objects.all()
            receiver = []
            for em in emails:
                if em.send:
                    receiver.append(em.email)
            will_send = True
        else:
            receiver = []
            will_send = False
        if operate != "update" and operate != "rollback":
            request.websocket.send("错误的操作")
        else:
            for soc_m in request.websocket:
                operate = operate
                web_url = web_info.url
                apptype = web_info.type
                sls_name = web_url.replace(".","_")
                re_tomcat = False
                web_server_ip = request.GET.get("servers").split(",")
                cli = client.LocalClient()
                request.websocket.send("正在更新......\n\n")
                for i in web_server_ip:
                    try:
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
                            tagname = com.tag_name
                            tag_mes = com.tag_message
                            request.websocket.send("\nTag Name:\n%s\n" % tagname.encode('utf8'))
                            request.websocket.send("\nMessage:\n%s\n" % tag_mes.encode('utf8'))
                            request.websocket.send("\n------更新完成！------\n\n")
                            mes = "Tag名称：%s<br/><br/>Tag信息：<br/>%s<br/>" % (tagname, tag_mes)
                        else:
                            stderr = publicmethod.get_dval(sync_re,"stderr")
                            comment = publicmethod.get_dval(sync_re,"comment")
                            request.websocket.send("错误信息：\n")
                            request.websocket.send("Comment:\n%s\n" % comment)
                            request.websocket.send("ERROR:\n%s\n" % stderr)
                            mes = stderr
                    except Exception:
                        request.websocket.send("更新失败,请联系管理员!")
                        mes = "更新失败"
                        raise
                    finally:
                        if will_send:
                            content = "操作人：%s<br/><br/>操作类型：%s<br/><br/>项目：%s<br/><br/>更新原因：<br/>%s<br/><br/>详细信息：<br/>%s<br/><br/>" % (user_name, operate, web_info.name, dep_con, mes)
                            publicmethod.send_mail(receiver, content)
                            will_send = False
                    # --- Read Tomcat Log start ---
                    if web_info.type.lower() == "tomcat" and re_tomcat:
                        war_folder = os.path.splitext(web_info.path)[0]
                        ipadd = i.strip()
                        tom_stop_re = cli.cmd(tgt=ipadd, fun='state.sls', arg=['pkg.script.tomcat_shutdown'])
                        logger.info("tomcat_stop_result %s" % tom_stop_re)
                        tom_stop_result = publicmethod.get_dval(tom_stop_re,'stdout')
                        tom_stop_false = False
                        if tom_stop_result is not None:
                            if len(tom_stop_result) != 0:
                                request.websocket.send(tom_stop_result+"\n\n")
                                del_war_folder_re = cli.cmd(tgt=ipadd, fun='cmd.run', arg=['rm -rf %s' % war_folder])
                                logger.info("del_war_folder_result %s" % del_war_folder_re)
                            else:
                                tom_stop_false = True
                        else:
                            tom_stop_false = True
                        if tom_stop_false:
                            request.websocket.send("Error: can't stop Tomcat")
                            break
                        read_result = cli.cmd_async(tgt=ipadd, fun="cmd.script",arg=['salt://pkg/script/read_tomcat.py'])
                        logger.info("read_tom_log %s" % read_result)
                        tomcat_start = cli.cmd(tgt=ipadd, fun='state.sls', arg=['pkg.script.tomcat_start'])
                        logger.info("Tomcat_start_result %s" % tomcat_start)
                        start_result = publicmethod.get_dval(tomcat_start, "result")
                        if start_result is False:
                            request.websocket.send("Tomcat start failed\n")
                            continue
                        else:
                            start_out = publicmethod.get_dval(tomcat_start, "stdout")
                            request.websocket.send(start_out + "\n")
                            if read_result != 0:
                                while True:
                                    read_log = cli.cmd(tgt=ipadd, fun='cmd.script', arg=['salt://pkg/script/read_log.py'])
                                    log_con = publicmethod.get_dval(read_log, 'stdout')
                                    if len(log_con) > 0:
                                        request.websocket.send(log_con)
                                        if "Server startup in" in log_con:
                                            request.websocket.send("\n------Start End------\n")
                                            break
                            else:
                                request.websocket.send("Can't read tomcat log\n")
                    # --- Read Tomcat Log end ---
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
            web.user.add(user)
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
        web = Website.objects.filter(url=rec_data["web_url"])
        result = publicmethod.create_pro_file(web[0],rec_data['serverip'].split(','))
        if result == "success":
            web.update(init_result=1)
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
            for s in webinfo.server.all():
                webinfo.server.remove(s)
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
            try:
                exsit_ip = Servers.objects.get(ipaddress=ip)
            except Exception:
                return HttpResponse("%s 不存在" % ip)
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
def website_list(request):
    if request.method == "POST":
        user = User.objects.get(id=request.session['_auth_user_id'])
        data = []
        show_all = False
        if user.username == "admin":
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
                d['website_status'] = i.deploy_status
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
            webs = user.website_set.all()
            for web in webs:
                d = {}
                d['id'] = web.website_id
                d['website_name'] = web.name
                d['website_url'] = web.url
                d['website_type'] = web.type
                d['website_env'] = web.deploy_env
                d['website_status'] = web.deploy_status
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
    if user.username != "admin":
        return HttpResponseRedirect('/')
    if request.method == "POST":
        cli = client.LocalClient()
        re_id = cli.cmd(tgt='*',fun='grains.item',arg= ['os'])
        for k, v in re_id.items():
            exsit = Servers.objects.filter(ipaddress=k)
            if exsit:
                continue
            else:
                server = Servers(ipaddress=k, ostype=v['os'], user=user)
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
    web_info = Website.objects.get(website_id=web_id)
    web_name = web_info.name
    return render_to_response('update_detail.html',{'login_user': login_user, 'title': '%s Tomcat %s Result' % (web_name,operation.capitalize())})


@accept_websocket
def tomcat_op_result(request,operation,web_id):
    if request.is_websocket():
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
                                read_result = cli.cmd_async(tgt=ipadd, fun="cmd.script", arg=['salt://pkg/script/read_tomcat.py'])
                                logger.info("read_tom_log %s" % read_result)
                                tomcat_start = cli.cmd(tgt=ipadd, fun='state.sls', arg=['pkg.script.tomcat_start'])
                                logger.info("Tomcat_start_result %s" % tomcat_start)
                                start_result = publicmethod.get_dval(tomcat_start,"result")
                                if start_result is False:
                                    request.websocket.send("Tomcat start failed\n")
                                    continue
                                else:
                                    start_out = publicmethod.get_dval(tomcat_start,"stdout")
                                    request.websocket.send(start_out+"\n")
                                    if read_result != 0:
                                        while True:
                                            read_log = cli.cmd(tgt=ipadd, fun='cmd.script',arg=['salt://pkg/script/read_log.py'])
                                            log_con = publicmethod.get_dval(read_log, 'stdout')
                                            if len(log_con) > 0:
                                                request.websocket.send(log_con)
                                                if "Server startup in" in log_con:
                                                    request.websocket.send("\n------Start End------\n")
                                                    break
                                    else:
                                        request.websocket.send("Can't read tomcat log\n")
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
    web_info = Website.objects.get(website_id=web_id)
    web_name = web_info.name
    return render_to_response('update_detail.html',{'login_user':login_user,'title':"%s Build Result" % web_name})


@accept_websocket
def build_socket(request,web_id,):
    if request.is_websocket():
        for soc_m in request.websocket:
            tag_name = request.GET.get("tagname").lower()
            tag_message = request.GET.get("tagmessage")
            web_info = Website.objects.get(website_id=web_id)
            proname = ".".join(web_info.git_url.split(":")[1].split(".")[:-1])
            dev_branch = web_info.dev_branch
            deploy_env = web_info.deploy_env
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
            try:
                request.websocket.send("正在将开发分支%s合并到online分支……\n" % web_info.dev_branch.encode('utf8'))
                if web_info.type != "IIS":
                    merge = gl.merge_branch(source=dev_branch, target=build_branch,title="merge %s to %s" % (dev_branch, build_branch))
                    if merge:
                        request.websocket.send("分支合并成功！\n\n")
                        web_info.merge_result = "success"
                        web_info.build_result = "-"
                        web_info.create_tag_result = "-"
                        web_info.save()
                else:
                    request.websocket.send("IIS项目暂时跳过合并分支！\n\n")
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
                while True:
                    try:
                        building = jk.build_status(jk_name.encode('utf8'), next_build_num)
                        if building:
                            break
                        else:
                            time.sleep(1)
                            continue
                    except Exception:
                        time.sleep(1)
                        continue
                pre = []
                while True:
                    try:
                        output = jk.get_build_output(jk_name.encode('utf8'),next_build_num)
                    except Exception:
                        try:
                            building = jk.build_status(jk_name.encode('utf8'), next_build_num)
                            if not building:
                                request.websocket.send("\n\n警告：构建信息获取失败！\n\n")
                                break
                        except Exception:
                            pass
                        time.sleep(2)
                        continue
                    output_list = output.splitlines()
                    tmp = [i.decode('gbk').encode('utf8') for i in output_list if i not in pre]
                    if len(tmp) > 0:
                        pre = output_list
                        request.websocket.send("\n".join(tmp))
                        request.websocket.send("\n")
                    else:
                        building = jk.build_status(jk_name.encode('utf8'),next_build_num)
                        if not building:
                            if output_list[-1].startswith("Finished:"):
                                break
                    time.sleep(2)
            try:
                build_result = jk.build_result(jk_name.encode('utf8'),next_build_num)
                if build_result == "SUCCESS":
                    request.websocket.send("\n\n构建成功！\n\n")
                    web_info.build_result = "success"
                    web_info.save()
                    request.websocket.send("正在创建Tag标签……\n")
                    tag = gl.create_tag(name="%s_%s" % (deploy_env,tag_name),branch="%s_deploy" % deploy_env,message=tag_message)
                    try:
                        commit_id = tag.commit.id
                        com = Commit(tag_name="%s_%s" % (deploy_env,tag_name),tag_message=tag_message,commit_id=commit_id,website=web_info)
                        com.save()
                        web_info.last_comit = tag.commit.id
                        web_info.save()
                    except Exception:
                        tag.delete()
                        raise
                    request.websocket.send("Tag标签创建成功！\n\n")
                    if web_info.merge_result == web_info.build_result == "success":
                        if web_info.type != "IIS":
                            web_info.merge_result = "-"
                        web_info.build_result = "-"
                        web_info.deploy_status = 1
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
    git_pro_name = ".".join(git_path.split(":")[1].split(".")[0:-1])
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


@login_required(login_url=login_url)
def finish_dep(request,web_id):
    web_info = Website.objects.get(website_id=web_id)
    git_path = web_info.git_url
    gpname = ".".join(git_path.split(":")[1].split(".")[0:-1])
    gl = gitlaboperation.Gitlaboperation(proname=gpname)
    merge = gl.merge_branch(source="online", target="master", title="merge online to master")
    if merge:
        web_info.deploy_status = 0
        web_info.save()
        return HttpResponse("success")
    else:
        return HttpResponse("failer")


@login_required(login_url=login_url)
def next_tag(request,web_id):
    web_info = Website.objects.get(website_id=web_id)
    try:
        tag_name = Commit.objects.get(commit_id=web_info.last_comit).tag_name.lower()
        tag_sp = tag_name.split("_")[1].split("v")
        tag_date = tag_sp[0]
        tag_nu = tag_sp[1]
    except Exception:
        tag_date = None
    cur_date = datetime.datetime.now().strftime("%Y%m%d")
    if cur_date == tag_date:
        next_tagname = "%sv%s" % (tag_date,int(tag_nu)+1)
    else:
        next_tagname = "%sv1" % cur_date
    return HttpResponse(next_tagname)
