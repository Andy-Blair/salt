/**
 * Created by duan on 9/7/17.
 */
$(function () {
    $('#server_list').bootstrapTable({
        columns:[
            {field: 'id', title: 'ID',width:'', align:'center', valign:'middle'},
            {field: 'ipaddress', title: 'IP', width:'',  align:'center', valign:'middle'},
            {field: 'ostype', title: '系统类型', width:'',  align:'center', valign:'middle'},
            {field: 'describe', title: '描述', width:'',  align:'center', valign:'middle'},
        ],
        url: '/salt/server_list/',
        method: 'get',
        contentType:'application/json',
        dataType:'json',
        toolbar:'#toolbar',
        pagination: true,
        sortOrder: "asc",
        sidePagination: "client",
        pageNumber: 1,
        pageSize: 20,
        pageList: [10, 20, 50],
        clickToSelect: true,
        search:true,
        singleSelect:true,
    });
    $("#update_servers").click(function () {
        $.post('/salt/server_manage/',function (data, status) {
            alert(status);
            window.location.reload()
        })
    })
});
