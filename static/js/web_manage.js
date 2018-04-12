/**
 * Created by root on 9/20/17.
 */

function confirmAct() {
    if(confirm('确定要执行此操作吗?')){
        return true;
    }else {
        return false;
    }
}

$(function () {
    $('#website_list').bootstrapTable({
        columns:[
            {checkbox: true},
            {field: 'id', title: 'ID', align:'center', valign:'middle', visible:false},
            {field: 'website_name', title: '站点名称', width:'',  align:'center', valign:'middle'},
            {field: 'website_env', title: '部署环境', width:'',  align:'center', valign:'middle'},
            {field: 'website_url', title: '站点域名', width:'',  align:'center', valign:'middle'},
            {field: 'website_type', title: '应用类型', width:'',  align:'center', valign:'middle'},
            {field: 'website_server', title: '服务器', width:'',  align:'center', valign:'middle'},
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
        clickToSelect: false,
        search:true,
        singleSelect:true,
        detailview:true,
    });
   $('#add').click(function () {
       var u = "/salt/"+$(this).attr("id");
        location.href = "/salt/website/"+$(this).attr("id");
    });
   $('#modify').click(function () {
       var row_data=$('#website_list').bootstrapTable('getSelections');
       if (Object.keys(row_data).length!==0){
           location.href = ("/salt/website/"+$(this).attr('id')+'/'+row_data[0]['id']);
        }
    });
   $('#del').click(function () {
       var row_data=$('#website_list').bootstrapTable('getSelections');
       if (Object.keys(row_data).length!==0){
           // location.href = ("/salt/website/"+$(this).attr('id')+'/'+row_data[0]['id']);
           var cho = confirmAct();
           if(cho){
               var url = '/salt/website/'+$(this).attr('id')+'/'+row_data[0]['id']+'/';
               $.post(url,function (data,status) {
                   alert("删除成功");
                   // alert(status);
                   window.location.reload()
               })
           }
        }
    });
});