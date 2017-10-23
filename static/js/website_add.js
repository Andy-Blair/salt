/**
 * Created by root on 9/22/17.
 */

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

$("form").submit(function () {
    var se = $("#apptype");
    var webpath=$("#web_path").val();
    var gitpath=$("#git_path").val();
    var re_wpath=/^[a-zA-Z]:\\/;
    var iswpath=re_wpath.test(webpath);
    var re_lpath=/^\/apps\/product\/tomcat\//;
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
    };
    var ip = hasip(ips);
    if(ip["responseText"].length!==0){
        alert("no server "+ip["responseText"]);
        return false;
    }
});

var hasip = function (ip) {
    var re=$.ajax({
        url:'/salt/website_manage/au',
        async:false,
        type:"POST",
        data:{'serverip':ip}
        });
    return re
};