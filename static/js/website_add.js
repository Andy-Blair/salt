/**
 * Created by root on 9/22/17.
 */

$(function () {
   $("#apptype").change(function () {
       var apptype=$(this).children('option:selected').text();
       var p = $("#web_path");
       var url = $("#web_url").val();
       var tomcat_path = "/apps/product/tomcat/webapps/";
       var iis_path = "D:\\product\\";
       var readonly = false;
       if (url){
           iis_path = iis_path+url;
           readonly = true;
       }
       if (apptype === "tomcat"){
           p.val(tomcat_path);
           p.attr("readonly","readonly");
       }else if (apptype === "IIS"){
           if (readonly){
               p.attr("readonly","readonly");
               p.val(iis_path)
           }else {
               p.removeAttr("readonly");
               p.val("d:\\product\\");
           }
       }else {
           p.removeAttr("readonly");
           p.val('')
       }
   })
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

$("#webform").submit(function () {
    var se = $("#apptype");
    var webpath=$("#web_path").val();
    var gitpath=$("#git_path").val();
    var re_wpath=/^[a-zA-Z]:\\/;
    var iswpath=re_wpath.test(webpath);
    // var re_lpath=/^\/apps\/product\/tomcat\//;
    var re_lpath=/^\//;
    var islpath=re_lpath.test(webpath);
    if(!iswpath && !islpath){
        alert("Web站点物理路径格式不正确");
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
        alert("no server "+ip["responseText"]);
        return false;
    }
    var web_url = $("#web_url").val();
    var exsit_web_name = website_auth(web_url);
    if(exsit_web_name["responseText"] === "exsit"){
        alert(web_url+"  already exsit");
        return false
    }
    var data = {};
    var form_data = $('form').serializeArray();
    $.each(form_data,function () {
        data[this.name]=this.value
    });
    $.post('/salt/website/add/cpf/',data);
});