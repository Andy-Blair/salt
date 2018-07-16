/**
 * Created by andy on 9/7/17.
 */
$(function () {
    $('#website_list').bootstrapTable({
        columns:[
            {checkbox: true,formatter:function (value, row, index) {
                if (row['init_result'] === 0){
                    return {disabled: true}
                };
                return value
            }},
            {field: 'id', title: 'ID', align:'center', valign:'middle', visible:false},
            {field: 'website_status', title: '部署状态', align:'center', valign:'middle', visible:false},
            {field: 'website_name', title: '站点名称', width:'',  align:'center', valign:'middle'},
            {field: 'website_env', title: '部署环境', width:'',  align:'center', valign:'middle'},
            {field: 'website_dev_branch', title: '开发分支', width:'',  align:'center', valign:'middle'},
            {field: 'website_url', title: '站点域名', width:'',  align:'center', valign:'middle', formatter:function (value, row, index) {
                if (row.website_status === 1){
                    return value + '&nbsp&nbsp&nbsp<button class="button button-primary button-pill button-tiny finish_dep" style="padding-left: 10px;padding-right: 10px;margin-right: 5px">结束发布</button>'
                } else {
                    return value
                }
            },events: finish_dep={"click .finish_dep":function (e, value, row, index) {
                $.post("/salt/website/fd/"+row['id']+"/",function (data) {
                    if (data === "success"){
                        alert("代码成功合并到Master分支");
                        window.location.reload()
                    } else {
                        alert("代码合并到Master分支失败")
                    }
                }).fail(function () {
                    alert("代码合并到Master分支失败")
                })
            }}},
            {field: 'website_type', title: '应用类型', width:'',  align:'center', valign:'middle'},
            {field: 'buttons', title: '', width:'170px',  align:'center', valign:'middle', events: tomcatEvents={
                "click .tomcat":function (e, value, row, index) {
                    var update_modal = $(".update_modal");
                    update_modal.text($(this).val());
                    var new_id = 'tomcat_'+$(this).val();
                    update_modal.attr('id',new_id);
                    update_modal.unbind();
                    var modal_table = $("#modal_table tbody");
                    modal_table.empty();
                    var servers_str = row['website_server'];
                    var servers= servers_str.split(",");
                    for(var i=0;i<servers.length;i++){
                        var tr = $("<tr><td style=\"text-align: right; vertical-align: middle; border: 0 solid transparent !important;width: 40%\">" +
                            "<input class=\"bs-checkbox\" type=\"checkbox\" value=\""+servers[i]+"\"></td>" +
                            "<td style=\"text-align: left; vertical-align: middle; border: 0 solid transparent !important;\">"+servers[i]+"</td></tr>");
                        tr.appendTo(modal_table)
                    }
                    $('#modal-update').modal('toggle');
                    $("#"+new_id).click(function () {
                        var servers=[];
                        $.each($("#modal_table input:checkbox:checked"),function () {
                            servers.push($(this).val())
                        });
                        if (servers.length > 0){
                            var servers_str = servers.join(",");
                            window.open("/salt/website/tomcat/"+$(this).text()+"/"+row['id']+'/?&servers='+servers_str)
                        }
                    })
                }
            } ,formatter:function (value, row, index) {
                if (row.website_type === 'tomcat'){
                    return '<button class="button button-primary button-pill button-tiny tomcat" value="start" data-toggle="modal" data-target="" style="padding-left: 10px;padding-right: 10px;margin-right: 5px">Start</button>' +
                        '<button class="button button-primary button-pill button-tiny tomcat" value="stop" data-toggle="modal" data-target="" style="padding-left: 10px;padding-right: 10px;margin-right: 5px">Stop</button>'
                } else {
                    return '-'
                }
            }},
            {field: 'website_server', title: '服务器', width:'',  align:'center', valign:'middle'},
            {field: 'website_detail', title: '', width:'',  align:'center', valign:'middle', formatter:function (value, row, index) {
                var u = "/salt/website/"+row.id+"/history";
                return '<a href='+u+'>历史记录</a>';
            }},
            {field: 'init_result', title: 'init_result', align:'center', valign:'middle',visible:false},
        ],
        url: '/salt/website_list/',
        method: 'post',
        contentType:'application/json',
        dataType:'json',
        async:false,
        toolbar:'#toolbar',
        pagination: true,
        sortOrder: "asc",
        sidePagination: "client",
        pageNumber: 1,
        pageSize: 20,
        pageList: [10, 20],
        clickToSelect: false,
        search:true,
        singleSelect:true,
        detailview:true,
    });
    $('#web_update').click(function () {
        var row_data=$('#website_list').bootstrapTable('getSelections');
        if (Object.keys(row_data).length!==0){
            var modal_table = $("#modal_table tbody");
            modal_table.empty();
            var servers_str = row_data[0]['website_server'];
            var servers= servers_str.split(",");
            for(var i=0;i<servers.length;i++){
                var tr = $("<tr><td style=\"text-align: right; vertical-align: middle; border: 0 solid transparent !important;width: 40%\">" +
                    "<input class=\"bs-checkbox\" type=\"checkbox\" value=\""+servers[i]+"\"></td>" +
                    "<td style=\"text-align: left; vertical-align: middle; border: 0 solid transparent !important;\">"+servers[i]+"</td></tr>");
                tr.appendTo(modal_table)
            }
            var update_modal = $(".update_modal");
            var new_id = $(this).attr('name');
            update_modal.text($(this).text());
            update_modal.attr('id',new_id);
            update_modal.unbind();
            $("#"+new_id).click(function () {
                var servers=[];
                $.each($("#modal_table input:checkbox:checked"),function () {
                    servers.push($(this).val())
                });
                if (servers.length > 0){
                    var servers_str = servers.join(",");
                    window.open("/salt/website/"+$(this).attr('name')+'/?web_id='+row_data[0]['id']+'&servers='+servers_str)
                }
            });
            $('#modal-update').modal('toggle');
        }
    });
    $('#web_rollback').click(function () {
        var row_data=$('#website_list').bootstrapTable('getSelections');
        if (Object.keys(row_data).length!==0){
            $.get("/salt/website/tag/",{web_id:row_data[0]['id']},function (data) {
                var tag = $('#tag');
                tag.empty();
                tag.append(data)
            });
            var modal_table = $("#rollback_modal_table tbody");
            modal_table.empty();
            var servers_str = row_data[0]['website_server'];
            var servers= servers_str.split(",");
            for(var i=0;i<servers.length;i++){
                var tr = $("<tr><td style=\"text-align: right; vertical-align: middle; border: 0 solid transparent !important;width: 5%\">" +
                    "<input class=\"bs-checkbox\" type=\"checkbox\" value=\""+servers[i]+"\"></td>" +
                    "<td style=\"text-align: left; vertical-align: middle; border: 0 solid transparent !important;\">"+servers[i]+"</td></tr>");
                tr.appendTo(modal_table)
            }
            $('#modal-rollback').modal('toggle');
            $('#com_message').empty();
            $('#tag').change(function () {
                var tag_name=$(this).children('option:selected').text();
                if (tag_name === "请选择"){
                    $('#com_message').empty()
                }else {
                    $.post("/salt/website/tag/",{tag_name:tag_name,web_id:row_data[0]['id']},function (data) {
                    $('#com_message').text(data)
                    })
                }

            });
        }
    });
    $('#roll_back').click(function () {
        var tag_name=$('#tag').children('option:selected').text();
        var servers=[];
        $.each($("#rollback_modal_table input:checkbox:checked"),function () {
            servers.push($(this).val())
        });
        if (servers.length > 0){
            var servers_str = servers.join(",");
        }else {
            alert("请至少选择一台服务器");
            return
        }
        if (tag_name === "请选择"){
            alert("请选择回退到哪个Tag版本")
        }else {
            var row_data=$('#website_list').bootstrapTable('getSelections');
            window.open("/salt/website/"+$(this).attr('name')+"?web_id="+row_data[0]['id']+"&tag_name="+tag_name+"&servers="+servers_str)
        }
    });
    $("#build").click(function () {
        var row_data=$('#website_list').bootstrapTable('getSelections');
        if (Object.keys(row_data).length!==0){
            $.post("/salt/website/nt/"+row_data[0]['id']+"/",function (data, status) {
                $("#tag_name").val(data);
                $("#tag_name").attr("readonly","readonly");
                if (Number(data.split('v')[1])!==1){
                    $("#depcon").removeClass('hidden');
                    $("#dep_con").val("")
                }
            });
            $("#tag_message").val("");
            $('#modal-tag').modal('toggle');
        }
    });
    $("#start_build").click(function () {
        var row_data=$('#website_list').bootstrapTable('getSelections');
        var tag_name=$("#tag_name").val();
        var tag_message=$("#tag_message").val();
        if (tag_name.length>0 && tag_message.length>0){
            if ($.trim(tag_name) === $.trim(tag_message)){
                alert("上线内容不可以写Tag名称")
            }else {
                $.post("/salt/website/add/tagname/auth",{tag_name:tag_name,web_id:row_data[0]['id']},function (data, status) {
                if(data === "exsit"){
                    alert("Tag Name已经存在");
                    return false
                }else {
                    if ($("#dep_con").val().length===0 && !$("#depcon").hasClass('hidden')) {
                        alert("请填写重复构建原因");
                        return false;
                    }else {
                        var dep=document.getElementById("dep_con").value.replace(/\r\n/g, '<br/>').replace(/\n/g, '<br/>').replace(/\s/g, ' ');
                        window.open("/salt/website/build/" + row_data[0]['id'] + "?tagname=" + tag_name + "&tagmessage=" + tag_message + '&dep=' + dep);
                        $('#modal-tag').modal('hide');
                    }
                }
            });
            }
        }else {
            alert("上线内容没有填写");
            return false
        }
    })
});
