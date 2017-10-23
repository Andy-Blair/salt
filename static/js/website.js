/**
 * Created by duan on 9/7/17.
 */
$(function () {
    $('#website_list').bootstrapTable({
        columns:[
            {checkbox: true},
            {field: 'id', title: 'ID', align:'center', valign:'middle', visible:false},
            {field: 'website_name', title: '站点名称', width:'',  align:'center', valign:'middle'},
            {field: 'website_url', title: '站点域名', width:'',  align:'center', valign:'middle'},
            {field: 'website_type', title: '应用类型', width:'',  align:'center', valign:'middle'},
            {field: 'website_server', title: '服务器', width:'',  align:'center', valign:'middle'},
            {field: 'website_ostype', title: '系统类型', width:'',  align:'center', valign:'middle'},
            {field: 'website_detail', title: '', width:'',  align:'center', valign:'middle', formatter:function (value, row, index) {
                var u = "/salt/website/"+row.id+"/d";
                return '<a href='+u+'>详细信息</a>';
            }},

        ],
        url: '/salt/website_list/',
        method: 'post',
        contentType:'application/json',
        dataType:'json',
        toolbar:'#toolbar',
        pagination: true,
        sortOrder: "asc",
        sidePagination: "client",
        pageNumber: 1,
        pageSize: 20,
        pageList: [10, 20],
        clickToSelect: true,
        search:true,
        singleSelect:true,
        detailview:true,
    });
    $('#web_update,#web_rollback').click(function () {
        var row_data=$('#website_list').bootstrapTable('getSelections');
        if (Object.keys(row_data).length!==0){
            window.open("/salt/website/"+$(this).attr('name')+'/'+row_data[0]['id'])
        }
    });
});
