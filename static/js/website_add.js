/**
 * Created by root on 9/22/17.
 */

$(function () {

   $("#apptype").change(function () {
       var apptype=$(this).children('option:selected').text();
       var p = $("#web_path");
       var p2 = $("#war_name");
       var url = $("#web_url").val();
       var tomcat_path = "/apps/product/tomcat/webapps/";
       var iis_path = "D:\\product\\";
       var readonly = false;
       if (url){
           iis_path = iis_path+url;
           readonly = true;
       }
       if (apptype === "tomcat"){
           p.css({'width':'53%'});
           p2.removeClass("hidden");
           p2.attr("required","true");
           p.val(tomcat_path);
           p.attr("readonly","readonly");
       }else if (apptype === "IIS"){
           p2.addClass("hidden");
           p2.removeAttr("required");
           p.css({'width':'100%'});
           if (readonly){
               p.attr("readonly","readonly");
               p.val(iis_path)
           }else {
               p.removeAttr("readonly");
               p.val("d:\\product\\");
           }
       }else {
           p2.addClass("hidden");
           p2.removeAttr("required");
           p.css({'width':'100%'});
           p.removeAttr("readonly");
           p.val('')
       }
   });

});

var isIp = function (){
        var regexp = /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/;

        return function(value){
            var valid = regexp.test(value);

            if(!valid){//首先必须是 xxx.xxx.xxx.xxx 类型的数字，如果不是，返回false
                return false;
            }

            return value.split('.').every(function(num){
                //切割开来，每个都做对比，可以为0，可以小于等于255，但是不可以0开头的俩位数
                //只要有一个不符合就返回false
                if(num.length > 1 && num.charAt(0) === '0'){
                    //大于1位的，开头都不可以是‘0’
                    return false;
                }else if(parseInt(num , 10) > 255){
                    //大于255的不能通过
                    return false;
                }
                return true;
            });
        }
    }();

var server_auth = function (ip) {
    return $.ajax({
        url:'/salt/website/add/server/auth',
        async:false,
        type:"POST",
        data:{'ipaddress':ip}
        });
};

var website_auth = function (url) {
    return $.ajax({
        url:'/salt/website/add/website/auth',
        async:false,
        type:"POST",
        data:{'url':url}
        });
};

var jkname_auth = function (jkname) {
    return $.ajax({
        url:'/salt/website/add/jkname/auth',
        async:false,
        type:"POST",
        data:{'jk_name':jkname}
        });
};

$("#get_branch").click(function () {
    var get_branch_text=$(this).text();
    var gitpath=$("#git_path").val();
    var re_gitpath=/^git@[\S]*.git$/;
    var isgitpath=re_gitpath.test(gitpath);
    var dev_branch=$("#dev_branch");
    if (isgitpath){
        $(this).text("获取中...");
        $(this).attr({'disabled':true});
        $.ajax({
            url:'/salt/website/getbranch/',
            async:false,
            type:"POST",
            data:{'git_path':gitpath},
            success:function (data, status) {
                dev_branch.empty();
                dev_branch.append(data);
                $("#get_branch").removeAttr("disabled");
                $("#get_branch").text(get_branch_text);
            }
        });
    } else {
        alert("Gitpath必须使用内部Git服务器SSH协议地址");
    }
    return false
});

$("#webform").submit(function () {
    var se = $("#apptype");
    var dev_branch = $("#dev_branch");
    var apptype=se.children('option:selected').text();
    var webpath=$("#web_path").val();
    var war_name=$("#war_name").val();
    var gitpath=$("#git_path").val();
    var re_wpath=/^[a-zA-Z]:\\/;
    var iswpath=re_wpath.test(webpath);
    // var re_lpath=/^\/apps\/product\/tomcat\//;
    var re_lpath=/^\//;
    var islpath=re_lpath.test(webpath);
    var re_war =/^.+.war$/;
    var iswar = re_war.test(war_name);
    if(!iswpath && !islpath){
        alert("Web站点物理路径格式不正确");
        return false
    }
    if(apptype==="tomcat" && !iswar){
        alert("War包名字必须包含后缀");
        return false
    }
    var re_gitpath=/^git@[\S]*.git$/;
    var isgitpath=re_gitpath.test(gitpath);
    if (!isgitpath){
        alert("Gitpath必须使用内部Git服务器SSH协议地址");
        return false
    }
    var se_data = se.attr("name")+'='+se.find("option:selected").text();
    if(se.find("option:selected").text()==="请选择"){
        alert("请选择应用类型");
        return false
    }
    if(dev_branch.find("option:selected").text()==="请选择"){
        alert("请选择一个分支");
        return false
    }
    var ips = $("#serverip").val();
    var isIP = ips.split(',').every(function (ip) {
        return isIp(ip)
    });
    if(!isIP){
        alert("部署服务器IP格式不正确");
        return false
    }
    var ip = server_auth(ips);
    if(ip["responseText"].length!==0){
        alert(ip["responseText"]);
        return false;
    }
    var web_url = $("#web_url").val();
    var re_web_url1=/\S*\\+\S*/;
    var re_web_url2=/\S*\/+\S*/;
    if(re_web_url1.test(web_url) || re_web_url2.test(web_url)){
        alert('域名不能包含 "/" "\\" 字符');
        return false
    }
    if(window.location.pathname === "/salt/website/add/"){
        var exsit_web_name = website_auth(web_url);
        if(exsit_web_name["responseText"] === "exsit"){
            alert("域名 "+web_url+" 已存在");
            return false
        }
        var jk_name =$("#jk_name").val();
        var exsit_jkname = jkname_auth(jk_name);
        if(exsit_jkname["responseText"]==="exsit"){
            alert("Jenkins任务名称 "+jk_name+" 已存在");
            return false
        }
    }

    var data = {};
    var form_data = $('form').serializeArray();
    $.each(form_data,function () {
        data[this.name]=this.value
    });
    $.post('/salt/website/add/cpf/',data);
});