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