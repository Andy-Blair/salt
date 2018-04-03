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
            {field: 'website_name', title: '站点名称', width:'',  align:'center', valign:'middle'},
            {field: 'website_url', title: '站点域名', width:'',  align:'center', valign:'middle'},
            {field: 'website_type', title: '应用类型', width:'',  align:'center', valign:'middle'},
            {field: 'buttons', title: '', width:'170px',  align:'center', valign:'middle', formatter:function (value, row, index) {
                if (row.website_type === 'tomcat'){
                    return '<button class="button button-primary button-pill button-tiny tomcat" value="start">Start</button>  <button class="button button-primary button-pill button-tiny tomcat" value="stop">Stop</button>'
                } else {
                    return '-'
                }
            }},
            {field: 'website_server', title: '服务器', width:'',  align:'center', valign:'middle'},
            {field: 'website_env', title: '部署环境', width:'',  align:'center', valign:'middle'},
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
            window.open("/salt/website/"+$(this).attr('name')+'/?web_id='+row_data[0]['id'])
        }
    });
    $('#rollback').click(function () {
        var row_data=$('#website_list').bootstrapTable('getSelections');
        if (Object.keys(row_data).length!==0){
            $.get("/salt/website/tag/",{web_id:row_data[0]['id']},function (data) {
                var tag = $('#tag');
                tag.empty();
                tag.append(data)
            });
            $('#modal-container-576146').modal('toggle');
            $('#tag').change(function () {
                var tag_name=$(this).children('option:selected').text();
                if (tag_name === "请选择"){
                    $('#com_message').val('')
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
        if (tag_name === "请选择"){
            alert("请选择要回退到哪个Tag")
        }else {
            var row_data=$('#website_list').bootstrapTable('getSelections');
            window.open("/salt/website/"+$(this).attr('name')+"?web_id="+row_data[0]['id']+"&tag_name="+tag_name)
        }
    });
    $('#website_list').on('post-body.bs.table',function () {
        $(".tomcat").click(function () {
            var row_data=$('#website_list').bootstrapTable('getSelections');
            // alert($(this).val());
            if (Object.keys(row_data).length!==0){
                window.open("/salt/website/tomcat/"+$(this).val()+"/"+row_data[0]['id'])
            }
        })
    });
});
